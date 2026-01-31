"""
AI Integration API
Provides endpoints for AI models to interact with the resume system
"""
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..db.supabase import get_supabase_client
from ..services.evaluation_service import get_evaluation_service
from ..services.google_drive_service import get_drive_service
from ..services.job_service import get_job

router = APIRouter(prefix="/api/v1/ai", tags=["AI Integration"])

class SearchResumesRequest(BaseModel):
    job_id: Optional[str] = None
    filename_pattern: Optional[str] = None
    limit: int = 10

class EvaluateResumeRequest(BaseModel):
    job_id: str
    resume_content: str
    resume_filename: str

class AIResponse(BaseModel):
    success: bool
    data: Any
    message: Optional[str] = None

@router.post("/search-resumes", response_model=AIResponse)
async def search_resumes(request: SearchResumesRequest):
    """Search for resumes in Google Drive"""
    try:
        drive_service = get_drive_service()

        if request.job_id:
            # Get resumes folder for this job
            resumes_folder = await drive_service.get_or_create_job_folder(
                request.job_id, f"Job {request.job_id}"
            )
            files = await drive_service.list_files_in_folder(resumes_folder)
        else:
            # Search in root folder
            root_folder = await drive_service.get_or_create_root_folder()
            files = await drive_service.list_files_in_folder(root_folder)

        # Filter by filename pattern if provided
        if request.filename_pattern:
            files = [
                f for f in files
                if request.filename_pattern.lower() in f.get('name', '').lower()
            ]

        # Limit results
        files = files[:request.limit]

        return AIResponse(
            success=True,
            data=files,
            message=f"Found {len(files)} resume(s)"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/read-resume/{file_id}", response_model=AIResponse)
async def read_resume(file_id: str):
    """Read content of a specific resume file"""
    try:
        drive_service = get_drive_service()
        content = await drive_service.download_file(file_id)
        text_content = content.decode('utf-8', errors='ignore')

        return AIResponse(
            success=True,
            data={"content": text_content, "file_id": file_id},
            message="Resume content retrieved successfully"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read resume: {str(e)}")

@router.post("/evaluate-resume", response_model=AIResponse)
async def evaluate_resume(request: EvaluateResumeRequest):
    """Evaluate a resume against job requirements"""
    try:
        evaluation_service = get_evaluation_service()
        result = await evaluation_service.evaluate_single_resume(
            job_id=request.job_id,
            resume_content=request.resume_content,
            resume_filename=request.resume_filename
        )

        return AIResponse(
            success=True,
            data=result,
            message="Resume evaluation completed"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")

@router.get("/job/{job_id}", response_model=AIResponse)
async def get_job_for_ai(job_id: str):
    """Get job details for AI processing"""
    try:
        job = await get_job(job_id)

        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        return AIResponse(
            success=True,
            data=job,
            message="Job details retrieved"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get job: {str(e)}")

@router.get("/job/{job_id}/evaluations", response_model=AIResponse)
async def get_job_evaluations_for_ai(
    job_id: str,
    limit: int = Query(50, description="Maximum number of evaluations to return")
):
    """Get evaluations for a job"""
    try:
        evaluation_service = get_evaluation_service()
        evaluations = await evaluation_service.get_job_evaluations(job_id)

        # Limit results
        evaluations = evaluations[:limit]

        return AIResponse(
            success=True,
            data=evaluations,
            message=f"Retrieved {len(evaluations)} evaluation(s)"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get evaluations: {str(e)}")

@router.get("/stats", response_model=AIResponse)
async def get_system_stats():
    """Get system statistics for AI context"""
    try:
        client = get_supabase_client()

        # Get counts
        jobs_count = client.table("jobs").select("*", count="exact").execute()
        resumes_count = client.table("resumes").select("*", count="exact").execute()
        evaluations_count = client.table("evaluations").select("*", count="exact").execute()

        stats = {
            "total_jobs": jobs_count.count,
            "total_resumes": resumes_count.count,
            "total_evaluations": evaluations_count.count,
            "system_status": "operational"
        }

        return AIResponse(
            success=True,
            data=stats,
            message="System statistics retrieved"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

@router.get("/capabilities", response_model=AIResponse)
async def get_ai_capabilities():
    """Describe what AI can do with this system"""
    capabilities = {
        "search_resumes": {
            "description": "Search for resumes in Google Drive by job ID or filename",
            "endpoint": "/api/v1/ai/search-resumes",
            "method": "POST",
            "parameters": {
                "job_id": "Optional job ID to search within",
                "filename_pattern": "Optional filename pattern to match",
                "limit": "Maximum results to return (default: 10)"
            }
        },
        "read_resume": {
            "description": "Read the content of a specific resume file",
            "endpoint": "/api/v1/ai/read-resume/{file_id}",
            "method": "GET",
            "parameters": {
                "file_id": "Google Drive file ID of the resume"
            }
        },
        "evaluate_resume": {
            "description": "Evaluate a resume against job requirements using AI",
            "endpoint": "/api/v1/ai/evaluate-resume",
            "method": "POST",
            "parameters": {
                "job_id": "Job ID to evaluate against",
                "resume_content": "Text content of the resume",
                "resume_filename": "Original filename of the resume"
            }
        },
        "get_job": {
            "description": "Get details of a specific job posting",
            "endpoint": "/api/v1/ai/job/{job_id}",
            "method": "GET"
        },
        "get_evaluations": {
            "description": "Get all evaluations for a specific job",
            "endpoint": "/api/v1/ai/job/{job_id}/evaluations",
            "method": "GET",
            "parameters": {
                "limit": "Maximum evaluations to return (default: 50)"
            }
        },
        "system_stats": {
            "description": "Get system statistics and counts",
            "endpoint": "/api/v1/ai/stats",
            "method": "GET"
        }
    }

    return AIResponse(
        success=True,
        data=capabilities,
        message="AI integration capabilities retrieved"
    )
