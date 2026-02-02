import logging
import re
from datetime import datetime
from typing import Optional, List, Dict, Any

from .job_service import get_job
from .resume_parser import extract_text, extract_candidate_name
from .resume_service import get_resume, download_resume
from .skill_extractor import get_skill_extractor
from ..db.supabase import get_supabase_client
from ..models.schemas import (
    EvaluationResponse, EvaluationListResponse, EvaluationSummary,
    EvaluationFilterParams, SkillMatch, RankingBreakdown
)

logger = logging.getLogger("resume_shortlisting")


def calculate_ranking_breakdown(
    resume_text: str,
    resume_skills: Dict[str, Any],
    job_description: str,
    job_title: str,
    match_score: float
) -> RankingBreakdown:
    """Calculate detailed ranking breakdown for tiebreaker evaluation"""
    
    # 1. Experience Score (15% weight)
    experience_score = _calculate_experience_score(resume_skills, job_description)
    
    # 2. Education Score (10% weight)
    education_score = _calculate_education_score(resume_skills, job_description)
    
    # 3. Skills Quality Score (5% weight)
    skills_quality_score = _calculate_skills_quality_score(resume_skills, job_description)
    
    # 4. Keyword Density Score (5% weight)
    keyword_density_score = _calculate_keyword_density_score(resume_text, job_description)
    
    # Composite Score: 70% match_score + 15% experience + 10% education + 5% skills_quality + 5% keyword_density
    composite_score = (
        match_score * 0.7 +
        experience_score * 0.15 +
        education_score * 0.10 +
        skills_quality_score * 0.05 +
        keyword_density_score * 0.05
    )
    
    return RankingBreakdown(
        experience_score=experience_score,
        education_score=education_score,
        skills_quality_score=skills_quality_score,
        keyword_density_score=keyword_density_score,
        composite_score=round(composite_score, 2)
    )


def _calculate_experience_score(resume_skills: Dict[str, Any], job_description: str) -> float:
    """Calculate experience relevance score"""
    experience_years = resume_skills.get('experience_years', 0)
    if not experience_years:
        return 0.0
    
    # Extract experience requirements from job description
    exp_patterns = [
        r'(\d+)\+?\s*years?\s*(?:of\s*)?experience',
        r'(\d+)\s*-\s*(\d+)\s*years?\s*(?:of\s*)?experience',
        r'minimum\s*(\d+)\s*years?',
        r'at\s*least\s*(\d+)\s*years?'
    ]
    
    required_exp = None
    for pattern in exp_patterns:
        match = re.search(pattern, job_description.lower())
        if match:
            if len(match.groups()) == 2:
                # Range like "3-5 years"
                required_exp = int(match.group(2))  # Use upper bound
            else:
                required_exp = int(match.group(1))
            break
    
    if not required_exp:
        # If no specific requirement, score based on general experience
        if experience_years >= 10:
            return 100.0
        elif experience_years >= 5:
            return 85.0
        elif experience_years >= 3:
            return 70.0
        elif experience_years >= 1:
            return 50.0
        else:
            return 25.0
    
    # Score based on meeting requirements
    if experience_years >= required_exp:
        # Bonus for exceeding requirements
        excess = experience_years - required_exp
        bonus = min(excess * 2, 20)  # Max 20 bonus points
        return min(100.0, 80.0 + bonus)
    elif experience_years >= required_exp * 0.8:
        return 70.0
    elif experience_years >= required_exp * 0.6:
        return 50.0
    elif experience_years >= required_exp * 0.4:
        return 30.0
    else:
        return 10.0


def _calculate_education_score(resume_skills: Dict[str, Any], job_description: str) -> float:
    """Calculate education relevance score with exact and higher degree matching"""
    education = resume_skills.get('education', '')
    if not education:
        return 0.0
    
    education_str = str(education).lower()
    
    # Extract education requirements from job description
    required_degree = _extract_required_degree(job_description)
    
    # Education level hierarchy (higher to lower)
    education_hierarchy = {
        'phd': 100,
        'doctorate': 100,
        'master': 85,
        'm\.?s\.?': 85,
        'mba': 85,
        'bachelor': 70,
        'b\.?s\.?': 70,
        'b\.?a\.?': 65,
        'associate': 50,
        'diploma': 40,
        'certificate': 30
    }
    
    # Find candidate's education level
    candidate_level = None
    candidate_score = 0
    for level, score in education_hierarchy.items():
        if re.search(level, education_str):
            candidate_level = level
            candidate_score = score
            break
    
    if not candidate_level:
        return 0.0
    
    # Calculate score based on job requirements
    if required_degree:
        score = _calculate_degree_match_score(candidate_level, required_degree, education_hierarchy)
    else:
        # No specific requirement - use base score
        score = candidate_score
    
    # Field relevance bonus
    relevance_bonus = _calculate_field_relevance_bonus(education_str, job_description)
    
    return min(100.0, score + relevance_bonus)


def _extract_required_degree(job_description: str) -> Optional[str]:
    """Extract required education level from job description"""
    job_desc_lower = job_description.lower()
    
    # Look for specific degree requirements
    degree_patterns = [
        (r'phd|doctorate|doctoral', 'phd'),
        (r'master.*degree|m\.?s\.?|master\'s|mba', 'master'),
        (r'bachelor.*degree|b\.?s\.?|b\.?a\.?|bachelor\'s', 'bachelor'),
        (r'associate.*degree|associate\'s', 'associate'),
        (r'diploma', 'diploma'),
        (r'certificate|certification', 'certificate')
    ]
    
    for pattern, degree in degree_patterns:
        if re.search(pattern, job_desc_lower):
            return degree
    
    return None


def _calculate_degree_match_score(candidate_level: str, required_level: str, hierarchy: Dict[str, int]) -> float:
    """Calculate score based on candidate's degree vs required degree"""
    # Get hierarchy positions
    levels = list(hierarchy.keys())
    
    try:
        candidate_idx = levels.index(candidate_level)
        required_idx = levels.index(required_level)
    except ValueError:
        return hierarchy.get(candidate_level, 0)
    
    # Exact match - full score
    if candidate_level == required_level:
        return hierarchy[candidate_level]
    
    # Higher degree than required - bonus points
    if candidate_idx < required_idx:  # Higher level (lower index = higher degree)
        base_score = hierarchy[required_level]
        excess_levels = required_idx - candidate_idx
        bonus = min(excess_levels * 10, 20)  # Up to 20 bonus points
        return min(100.0, base_score + bonus)
    
    # Lower degree than required - penalty
    if candidate_idx > required_idx:
        deficit_levels = candidate_idx - required_idx
        penalty = deficit_levels * 15  # 15 points per level deficit
        return max(0, hierarchy[candidate_level] - penalty)
    
    return hierarchy.get(candidate_level, 0)


def _calculate_field_relevance_bonus(education_str: str, job_description: str) -> float:
    """Calculate field of study relevance bonus"""
    tech_fields = ['computer science', 'software engineering', 'information technology',
                   'data science', 'computer engineering', 'software development', 'artificial intelligence',
                   'machine learning', 'cybersecurity', 'cloud computing']
    business_fields = ['business', 'management', 'finance', 'marketing', 'economics', 'accounting']
    engineering_fields = ['engineering', 'mechanical', 'electrical', 'civil', 'chemical']
    
    job_desc_lower = job_description.lower()
    
    # Tech field relevance
    if any(field in education_str for field in tech_fields):
        if any(tech in job_desc_lower for tech in ['software', 'technical', 'developer', 'engineer', 'data', 'ai', 'machine learning']):
            return 15
        elif any(tech in job_desc_lower for tech in ['it', 'technology', 'system']):
            return 10
    
    # Business field relevance
    elif any(field in education_str for field in business_fields):
        if any(biz in job_desc_lower for biz in ['business', 'management', 'analyst', 'strategy']):
            return 12
        elif any(biz in job_desc_lower for biz in ['finance', 'marketing']):
            return 8
    
    # Engineering field relevance
    elif any(field in education_str for field in engineering_fields):
        if any(eng in job_desc_lower for tech in ['engineer', 'engineering', 'technical']):
            return 12
    
    return 0


def _calculate_skills_quality_score(resume_skills: Dict[str, Any], job_description: str) -> float:
    """Calculate skills quality score based on skill relevance and rarity"""
    skills = resume_skills.get('skills', [])
    if not skills:
        return 0.0
    
    # Define high-value skills (rare/advanced)
    high_value_skills = {
        'machine learning', 'artificial intelligence', 'deep learning', 'neural networks',
        'cloud architecture', 'devops', 'kubernetes', 'docker', 'microservices',
        'blockchain', 'cybersecurity', 'data engineering', 'big data',
        'react', 'angular', 'vue.js', 'node.js', 'python', 'java', 'scala',
        'aws', 'azure', 'gcp', 'terraform', 'ansible'
    }
    
    # Count high-value skills
    high_value_count = sum(1 for skill in skills if any(hv in skill.lower() for hv in high_value_skills))
    
    # Score based on percentage of high-value skills
    if len(skills) == 0:
        return 0.0
    
    high_value_ratio = high_value_count / len(skills)
    
    # Additional bonus for total skill count (more skills = better)
    skill_count_bonus = min(len(skills) * 2, 20)  # Max 20 bonus points
    
    base_score = high_value_ratio * 80  # Max 80 from high-value ratio
    
    return min(100.0, base_score + skill_count_bonus)


def _calculate_keyword_density_score(resume_text: str, job_description: str) -> float:
    """Calculate keyword density score"""
    # Extract important keywords from job description
    job_words = re.findall(r'\b\w+\b', job_description.lower())
    
    # Filter out common words
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'must'}
    
    keywords = [word for word in job_words if word not in stop_words and len(word) > 2]
    keyword_counts = {}
    
    for keyword in keywords:
        keyword_counts[keyword] = job_words.count(keyword)
    
    # Get top 20 most frequent keywords
    top_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:20]
    
    if not top_keywords:
        return 0.0
    
    # Count keyword matches in resume
    resume_words = re.findall(r'\b\w+\b', resume_text.lower())
    resume_word_count = len(resume_words)
    
    if resume_word_count == 0:
        return 0.0
    
    keyword_matches = 0
    for keyword, _ in top_keywords:
        keyword_matches += resume_words.count(keyword)
    
    # Calculate density (matches per 1000 words)
    density = (keyword_matches / resume_word_count) * 1000
    
    # Score based on density
    if density >= 50:
        return 100.0
    elif density >= 40:
        return 85.0
    elif density >= 30:
        return 70.0
    elif density >= 20:
        return 55.0
    elif density >= 10:
        return 40.0
    else:
        return 25.0


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
    
    # Calculate ranking breakdown for tiebreaker evaluation
    ranking_breakdown = calculate_ranking_breakdown(
        resume_text=resume_text,
        resume_skills=resume_skills,
        job_description=job.description,
        job_title=job.title,
        match_score=evaluation.get("match_score", 0)
    )
    
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
        "previous_roles": resume_skills.get("previous_roles", []),
        "ranking_breakdown": ranking_breakdown.model_dump()
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
        if filters.min_experience is not None:
            query = query.gte("experience_years", filters.min_experience)
        if filters.max_experience is not None:
            query = query.lte("experience_years", filters.max_experience)
        
        # Apply sorting with tiebreaker logic
        desc = filters.sort_order == "desc"
        sort_field = filters.sort_by
        
        # If sorting by match_score, use composite_score for tiebreaking
        if sort_field == "match_score":
            # First sort by the primary field
            query = query.order(sort_field, desc=desc)
            result = query.execute()
            
            # Apply tiebreaker sorting in Python for more control
            evaluations = []
            for eval_data in result.data:
                resume = await get_resume(eval_data["resume_id"])
                eval_response = EvaluationResponse(
                    **eval_data,
                    candidate_name=resume.candidate_name if resume else None,
                    file_name=resume.file_name if resume else "Unknown"
                )
                evaluations.append(eval_response)
            
            # Sort with tiebreakers
            evaluations.sort(key=lambda x: (
                x.match_score if not desc else -x.match_score,
                # Use composite_score as first tiebreaker if available
                -(x.ranking_breakdown.composite_score if x.ranking_breakdown and x.ranking_breakdown.composite_score else 0) if desc 
                else (x.ranking_breakdown.composite_score if x.ranking_breakdown and x.ranking_breakdown.composite_score else 0),
                # Experience years as second tiebreaker
                -(x.experience_years if x.experience_years else 0) if desc
                else (x.experience_years if x.experience_years else 0),
                # Education score as third tiebreaker
                -(x.ranking_breakdown.education_score if x.ranking_breakdown and x.ranking_breakdown.education_score else 0) if desc
                else (x.ranking_breakdown.education_score if x.ranking_breakdown and x.ranking_breakdown.education_score else 0)
            ))
        else:
            query = query.order(sort_field, desc=desc)
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
    else:
        # Default sorting: match_score with tiebreakers
        query = query.order("match_score", desc=True)
        result = query.execute()
        
        evaluations = []
        for eval_data in result.data:
            resume = await get_resume(eval_data["resume_id"])
            eval_response = EvaluationResponse(
                **eval_data,
                candidate_name=resume.candidate_name if resume else None,
                file_name=resume.file_name if resume else "Unknown"
            )
            evaluations.append(eval_response)
        
        # Apply default tiebreaker sorting
        evaluations.sort(key=lambda x: (
            -x.match_score,  # Higher match score first
            -(x.ranking_breakdown.composite_score if x.ranking_breakdown and x.ranking_breakdown.composite_score else 0),  # Higher composite score
            -(x.experience_years if x.experience_years else 0),  # More experience
            -(x.ranking_breakdown.education_score if x.ranking_breakdown and x.ranking_breakdown.education_score else 0)  # Higher education score
        ))
    
    # Apply keyword filters in Python (since Supabase text search on JSON is complex)
    if filters:
        if filters.skills_keyword:
            keyword = filters.skills_keyword.lower()
            evaluations = [
                e for e in evaluations
                if any(keyword in skill.lower() for skill in (e.skills_extracted or []))
            ]
        if filters.education_keyword:
            keyword = filters.education_keyword.lower()
            evaluations = [
                e for e in evaluations
                if e.education and keyword in e.education.lower()
            ]
    
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
