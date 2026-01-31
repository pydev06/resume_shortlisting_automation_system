import logging
import random
import string
from typing import Optional

from ..db.supabase import get_supabase_client
from ..models.schemas import JobCreate, JobUpdate, JobResponse, JobListResponse

logger = logging.getLogger("resume_shortlisting")


def generate_job_id() -> str:
    """Generate a unique 5-character alphanumeric JOBID (e.g., A1234)"""
    first_char = random.choice(string.ascii_uppercase)
    remaining = ''.join(random.choices(string.digits, k=4))
    return f"{first_char}{remaining}"


async def create_job(job_data: JobCreate) -> JobResponse:
    """Create a new job with auto-generated JOBID"""
    client = get_supabase_client()
    
    # Generate unique JOBID
    max_attempts = 10
    for _ in range(max_attempts):
        job_id = generate_job_id()
        existing = client.table("jobs").select("job_id").eq("job_id", job_id).execute()
        if not existing.data:
            break
    else:
        raise ValueError("Failed to generate unique JOBID after multiple attempts")
    
    data = {
        "job_id": job_id,
        "title": job_data.title,
        "description": job_data.description
    }
    
    result = client.table("jobs").insert(data).execute()
    
    if not result.data:
        raise ValueError("Failed to create job")
    
    logger.info(f"Created job with JOBID: {job_id}")
    
    # Log audit
    client.table("audit_logs").insert({
        "entity_type": "job",
        "entity_id": job_id,
        "action": "created",
        "details": {"title": job_data.title}
    }).execute()
    
    return JobResponse(**result.data[0])


async def get_job(job_id: str) -> Optional[JobResponse]:
    """Get a job by JOBID"""
    client = get_supabase_client()
    result = client.table("jobs").select("*").eq("job_id", job_id).execute()
    
    if not result.data:
        return None
    
    return JobResponse(**result.data[0])


async def get_job_by_id(id: int) -> Optional[JobResponse]:
    """Get a job by internal ID"""
    client = get_supabase_client()
    result = client.table("jobs").select("*").eq("id", id).execute()
    
    if not result.data:
        return None
    
    return JobResponse(**result.data[0])


async def list_jobs(
    query: Optional[str] = None,
    page: int = 1,
    page_size: int = 10
) -> JobListResponse:
    """List jobs with optional search and pagination"""
    client = get_supabase_client()
    
    offset = (page - 1) * page_size
    
    # Build query
    db_query = client.table("jobs").select("*", count="exact")
    
    if query:
        # Search in title and job_id
        db_query = db_query.or_(f"title.ilike.%{query}%,job_id.ilike.%{query}%")
    
    # Apply pagination and ordering
    result = db_query.order("created_at", desc=True).range(offset, offset + page_size - 1).execute()
    
    jobs = [JobResponse(**job) for job in result.data]
    total = result.count if result.count else len(jobs)
    
    return JobListResponse(
        jobs=jobs,
        total=total,
        page=page,
        page_size=page_size
    )


async def update_job(job_id: str, job_data: JobUpdate) -> Optional[JobResponse]:
    """Update a job (JOBID remains immutable)"""
    client = get_supabase_client()
    
    # Check if job exists
    existing = await get_job(job_id)
    if not existing:
        return None
    
    # Build update data
    update_data = {}
    if job_data.title is not None:
        update_data["title"] = job_data.title
    if job_data.description is not None:
        update_data["description"] = job_data.description
    
    if not update_data:
        return existing
    
    result = client.table("jobs").update(update_data).eq("job_id", job_id).execute()
    
    if not result.data:
        return None
    
    logger.info(f"Updated job: {job_id}")
    
    # Log audit
    client.table("audit_logs").insert({
        "entity_type": "job",
        "entity_id": job_id,
        "action": "updated",
        "details": update_data
    }).execute()
    
    return JobResponse(**result.data[0])


async def delete_job(job_id: str) -> bool:
    """Delete a job and all associated resumes and evaluations"""
    from .evaluation_service import delete_evaluations_by_job
    from .resume_service import delete_all_resumes
    
    # Check if job exists
    existing = await get_job(job_id)
    if not existing:
        return False
    
    # Delete all evaluations for the job
    await delete_evaluations_by_job(job_id)
    
    # Delete all resumes for the job (deletes from DB and Google Drive)
    await delete_all_resumes(job_id)
    
    # Delete job
    client = get_supabase_client()
    result = client.table("jobs").delete().eq("job_id", job_id).execute()
    
    logger.info(f"Deleted job: {job_id}")
    
    # Log audit
    client.table("audit_logs").insert({
        "entity_type": "job",
        "entity_id": job_id,
        "action": "deleted",
        "details": {"title": existing.title}
    }).execute()
    
    return True


async def update_job_drive_folder(job_id: str, folder_id: str) -> bool:
    """Update the Google Drive folder ID for a job"""
    client = get_supabase_client()
    
    result = client.table("jobs").update({
        "google_drive_folder_id": folder_id
    }).eq("job_id", job_id).execute()
    
    return bool(result.data)
