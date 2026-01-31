import logging
from datetime import datetime
from typing import Optional, List

from .job_service import get_job
from .resume_parser import extract_text, extract_candidate_name
from .resume_service import get_resume, download_resume
from .skill_extractor import get_skill_extractor
from ..db.supabase import get_supabase_client
from ..models.schemas import (
    EvaluationResponse, EvaluationListResponse, EvaluationSummary,
    EvaluationFilterParams, SkillMatch
)

logger = logging.getLogger("resume_shortlisting")


async def evaluate_resume(resume_id: int) -> EvaluationResponse:
    """Evaluate a single resume against its job description"""
    client = get_supabase_client()
    skill_extractor = get_skill_extractor()
    
    # Get resume
    resume = await get_resume(resume_id)
    if not resume:
        raise ValueError(f"Resume not found: {resume_id}")
    
    # Get job
    job = await get_job(resume.job_id)
    if not job:
        raise ValueError(f"Job not found: {resume.job_id}")
    
    # Check if already evaluated
    existing = client.table("evaluations").select("*").eq("resume_id", resume_id).execute()
    if existing.data:
        return EvaluationResponse(
            **existing.data[0],
            candidate_name=resume.candidate_name,
            file_name=resume.file_name
        )
    
    # Download and parse resume
    file_content, file_name = await download_resume(resume_id)
    resume_text = extract_text(file_content, file_name)
    
    # Extract candidate name
    candidate_name = extract_candidate_name(resume_text, file_name)
    
    # Update candidate name in resume if different
    if candidate_name != resume.candidate_name:
        client.table("resumes").update({"candidate_name": candidate_name}).eq("id", resume_id).execute()
    
    # Extract skills from resume
    resume_skills = await skill_extractor.extract_skills_from_resume(resume_text)
    
    # Evaluate match
    evaluation = await skill_extractor.evaluate_match(
        resume_text=resume_text,
        resume_skills=resume_skills,
        job_description=job.description,
        job_title=job.title
    )
    
    # Prepare matched skills
    matched_skills = [
        SkillMatch(
            skill=s.get("skill", ""),
            matched=s.get("matched", False),
            relevance_score=s.get("relevance_score", 0.0)
        )
        for s in evaluation.get("matched_skills", [])
    ]
    
    # Save evaluation
    eval_data = {
        "resume_id": resume_id,
        "job_id": resume.job_id,
        "match_score": evaluation.get("match_score", 0),
        "status": evaluation.get("status", "Not OK"),
        "justification": evaluation.get("justification", ""),
        "skills_extracted": resume_skills.get("skills", []),
        "skills_matched": [s.model_dump() for s in matched_skills],
        "experience_years": resume_skills.get("experience_years"),
        "education": resume_skills.get("education"),
        "previous_roles": resume_skills.get("previous_roles", [])
    }
    
    result = client.table("evaluations").insert(eval_data).execute()
    
    if not result.data:
        raise ValueError("Failed to save evaluation")
    
    logger.info(f"Evaluated resume {resume_id}: {evaluation.get('match_score')}% - {evaluation.get('status')}")
    
    # Log audit
    client.table("audit_logs").insert({
        "entity_type": "evaluation",
        "entity_id": str(result.data[0]["id"]),
        "action": "created",
        "details": {
            "resume_id": resume_id,
            "job_id": resume.job_id,
            "match_score": evaluation.get("match_score"),
            "status": evaluation.get("status")
        }
    }).execute()
    
    return EvaluationResponse(
        **result.data[0],
        candidate_name=candidate_name,
        file_name=file_name
    )


async def evaluate_all_resumes(job_id: str) -> List[EvaluationResponse]:
    """Evaluate all resumes for a job"""
    client = get_supabase_client()
    
    # Get all resumes for job
    resumes = client.table("resumes").select("id").eq("job_id", job_id).execute()
    
    if not resumes.data:
        return []
    
    results = []
    for resume in resumes.data:
        try:
            evaluation = await evaluate_resume(resume["id"])
            results.append(evaluation)
        except Exception as e:
            logger.error(f"Failed to evaluate resume {resume['id']}: {e}")
    
    return results


async def get_evaluation(evaluation_id: int) -> Optional[EvaluationResponse]:
    """Get an evaluation by ID"""
    client = get_supabase_client()
    
    result = client.table("evaluations").select("*").eq("id", evaluation_id).execute()
    
    if not result.data:
        return None
    
    eval_data = result.data[0]
    
    # Get resume info
    resume = await get_resume(eval_data["resume_id"])
    
    return EvaluationResponse(
        **eval_data,
        candidate_name=resume.candidate_name if resume else None,
        file_name=resume.file_name if resume else "Unknown"
    )


async def list_evaluations(
    job_id: str,
    filters: Optional[EvaluationFilterParams] = None
) -> EvaluationListResponse:
    """List all evaluations for a job with optional filters"""
    client = get_supabase_client()
    
    # Get job
    job = await get_job(job_id)
    if not job:
        raise ValueError(f"Job not found: {job_id}")
    
    # Build query
    query = client.table("evaluations").select("*", count="exact").eq("job_id", job_id)
    
    if filters:
        if filters.status:
            query = query.eq("status", filters.status.value)
        if filters.min_score is not None:
            query = query.gte("match_score", filters.min_score)
        if filters.max_score is not None:
            query = query.lte("match_score", filters.max_score)
        
        # Apply sorting
        desc = filters.sort_order == "desc"
        query = query.order(filters.sort_by, desc=desc)
    else:
        query = query.order("match_score", desc=True)
    
    result = query.execute()
    
    # Get resume info for each evaluation
    evaluations = []
    for eval_data in result.data:
        resume = await get_resume(eval_data["resume_id"])
        evaluations.append(EvaluationResponse(
            **eval_data,
            candidate_name=resume.candidate_name if resume else None,
            file_name=resume.file_name if resume else "Unknown"
        ))
    
    return EvaluationListResponse(
        evaluations=evaluations,
        total=result.count if result.count else len(evaluations),
        job_id=job_id,
        job_title=job.title
    )


async def get_evaluation_summary(job_id: str) -> EvaluationSummary:
    """Get evaluation summary statistics for a job"""
    client = get_supabase_client()
    
    # Get job
    job = await get_job(job_id)
    if not job:
        raise ValueError(f"Job not found: {job_id}")
    
    # Get total resumes
    resumes = client.table("resumes").select("id", count="exact").eq("job_id", job_id).execute()
    total_resumes = resumes.count if resumes.count else 0
    
    # Get evaluations
    evaluations = client.table("evaluations").select("*").eq("job_id", job_id).execute()
    
    evaluated = len(evaluations.data)
    ok_to_proceed = sum(1 for e in evaluations.data if e["status"] == "OK to Proceed")
    not_ok = sum(1 for e in evaluations.data if e["status"] == "Not OK")
    pending = total_resumes - evaluated
    
    avg_score = 0.0
    if evaluations.data:
        avg_score = sum(e["match_score"] for e in evaluations.data) / len(evaluations.data)
    
    return EvaluationSummary(
        job_id=job_id,
        job_title=job.title,
        total_resumes=total_resumes,
        evaluated=evaluated,
        ok_to_proceed=ok_to_proceed,
        not_ok=not_ok,
        pending=pending,
        average_score=round(avg_score, 2)
    )


async def re_evaluate_resume(resume_id: int) -> EvaluationResponse:
    """Re-evaluate a resume (delete existing evaluation and create new one)"""
    client = get_supabase_client()
    
    # Delete existing evaluation
    client.table("evaluations").delete().eq("resume_id", resume_id).execute()
    
    # Re-evaluate
    return await evaluate_resume(resume_id)


async def delete_evaluations_by_job(job_id: str) -> int:
    """Delete all evaluations for a job"""
    client = get_supabase_client()
    
    # Get count before delete for logging
    count_result = client.table("evaluations").select("id", count="exact").eq("job_id", job_id).execute()
    count = count_result.count if count_result.count else 0
    
    # Delete evaluations
    client.table("evaluations").delete().eq("job_id", job_id).execute()
    
    logger.info(f"Deleted {count} evaluations for job {job_id}")
    
    # Log audit
    client.table("audit_logs").insert({
        "entity_type": "job",
        "entity_id": job_id,
        "action": "all_evaluations_deleted",
        "details": {"count": count}
    }).execute()
    
    return count


# Singleton instance (no state needed, just functions)
_evaluation_service = None


def get_evaluation_service():
    """Get evaluation service instance"""
    global _evaluation_service
    if _evaluation_service is None:
        # Since evaluation_service is just functions, we can return the module
        # But for consistency with other services, we'll create a simple class
        class EvaluationService:
            async def evaluate_single_resume(self, job_id: str, resume_content: str, resume_filename: str):
                """Evaluate resume content directly without database storage"""
                from .job_service import get_job
                from .resume_parser import extract_text, extract_candidate_name
                from .skill_extractor import get_skill_extractor
                
                client = get_supabase_client()
                skill_extractor = get_skill_extractor()
                
                # Get job
                job = await get_job(job_id)
                if not job:
                    raise ValueError(f"Job not found: {job_id}")
                
                # Extract candidate name from filename/content
                candidate_name = extract_candidate_name(resume_content, resume_filename)
                
                # Extract skills from resume
                resume_skills = skill_extractor.extract_skills(resume_content)
                
                # Extract skills from job description (as job requirements)
                job_description = f"{job.title} {job.description}"
                job_skills = skill_extractor.extract_skills(job_description)
                
                # Compare skills
                matched_skills = [skill for skill in resume_skills if any(js.lower() in skill.lower() for js in job_skills)]
                
                # Calculate match score
                match_score = len(matched_skills) / len(job_skills) if job_skills else 0.0
                
                # Determine status
                if match_score >= 0.7:
                    status = "OK to Proceed"
                elif match_score >= 0.4:
                    status = "Borderline"
                else:
                    status = "Not OK"
                
                # Create evaluation response
                evaluation = {
                    "job_id": job_id,
                    "resume_id": None,  # No database resume
                    "candidate_name": candidate_name,
                    "file_name": resume_filename,
                    "match_score": round(match_score * 100, 1),
                    "status": status,
                    "matched_skills": matched_skills,
                    "missing_skills": [js for js in job_skills if not any(js.lower() in skill.lower() for skill in resume_skills)],
                    "all_skills": resume_skills,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }
                
                return evaluation
            
            async def get_job_evaluations(self, job_id: str):
                supabase_client = get_supabase_client()
                response = supabase_client.table('evaluations').select('*').eq('job_id', job_id).execute()
                return response.data
        
        _evaluation_service = EvaluationService()
    return _evaluation_service
