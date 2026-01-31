from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from ..models.schemas import (
    JobCreate, JobUpdate, JobResponse, JobListResponse
)
from ..services import job_service

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.post("/", response_model=JobResponse, status_code=201)
async def create_job(job_data: JobCreate):
    """Create a new job with auto-generated JOBID"""
    try:
        return await job_service.create_job(job_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=JobListResponse)
async def list_jobs(
    query: Optional[str] = Query(None, description="Search by title or JOBID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100)
):
    """List all jobs with optional search and pagination"""
    return await job_service.list_jobs(query=query, page=page, page_size=page_size)


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str):
    """Get a job by JOBID"""
    job = await job_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    return job


@router.put("/{job_id}", response_model=JobResponse)
async def update_job(job_id: str, job_data: JobUpdate):
    """Update a job (JOBID remains immutable)"""
    job = await job_service.update_job(job_id, job_data)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    return job


@router.delete("/{job_id}", status_code=204)
async def delete_job(job_id: str):
    """Delete a job and all associated resumes and evaluations"""
    deleted = await job_service.delete_job(job_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
