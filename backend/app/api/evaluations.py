from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from ..models.schemas import (
    EvaluationResponse, EvaluationListResponse, EvaluationSummary,
    EvaluationStatus, EvaluationFilterParams
)
from ..services import evaluation_service

router = APIRouter(prefix="/evaluations", tags=["Evaluations"])


@router.post("/resume/{resume_id}", response_model=EvaluationResponse, status_code=201)
async def evaluate_resume(resume_id: int):
    """Evaluate a single resume against its job description"""
    try:
        return await evaluation_service.evaluate_resume(resume_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/job/{job_id}/all", response_model=list[EvaluationResponse])
async def evaluate_all_resumes(job_id: str):
    """Evaluate all resumes for a job"""
    try:
        return await evaluation_service.evaluate_all_resumes(job_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/job/{job_id}", response_model=EvaluationListResponse)
async def list_evaluations(
    job_id: str,
    status: Optional[EvaluationStatus] = Query(None),
    min_score: Optional[float] = Query(None, ge=0, le=100),
    max_score: Optional[float] = Query(None, ge=0, le=100),
    min_experience: Optional[float] = Query(None, ge=0),
    max_experience: Optional[float] = Query(None, ge=0),
    skills_keyword: Optional[str] = Query(None),
    education_keyword: Optional[str] = Query(None),
    sort_by: str = Query("match_score", pattern="^(match_score|evaluated_at|candidate_name|experience_years)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$")
):
    """List all evaluations for a job with optional filters"""
    filters = EvaluationFilterParams(
        status=status,
        min_score=min_score,
        max_score=max_score,
        min_experience=min_experience,
        max_experience=max_experience,
        skills_keyword=skills_keyword,
        education_keyword=education_keyword,
        sort_by=sort_by,
        sort_order=sort_order
    )
    
    try:
        return await evaluation_service.list_evaluations(job_id, filters)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/job/{job_id}/summary", response_model=EvaluationSummary)
async def get_evaluation_summary(job_id: str):
    """Get evaluation summary statistics for a job"""
    try:
        return await evaluation_service.get_evaluation_summary(job_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{evaluation_id}", response_model=EvaluationResponse)
async def get_evaluation(evaluation_id: int):
    """Get a specific evaluation by ID"""
    evaluation = await evaluation_service.get_evaluation(evaluation_id)
    if not evaluation:
        raise HTTPException(status_code=404, detail=f"Evaluation not found: {evaluation_id}")
    return evaluation


@router.post("/resume/{resume_id}/re-evaluate", response_model=EvaluationResponse)
async def re_evaluate_resume(resume_id: int):
    """Re-evaluate a resume (delete existing evaluation and create new one)"""
    try:
        return await evaluation_service.re_evaluate_resume(resume_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
