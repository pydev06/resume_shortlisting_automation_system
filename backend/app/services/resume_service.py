import logging
from typing import Optional, List

from .google_drive_service import get_drive_service
from .job_service import get_job, update_job_drive_folder
from ..db.supabase import get_supabase_client
from ..models.schemas import ResumeResponse, ResumeListResponse

logger = logging.getLogger("resume_shortlisting")

ALLOWED_MIME_TYPES = {
    'application/pdf': '.pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx'
}


def get_mime_type(file_name: str) -> Optional[str]:
    """Get MIME type from file extension"""
    ext = file_name.lower().split('.')[-1] if '.' in file_name else ''
    mime_map = {
        'pdf': 'application/pdf',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    }
    return mime_map.get(ext)


async def upload_resume(
    job_id: str,
    file_content: bytes,
    file_name: str
) -> ResumeResponse:
    """Upload a resume for a job"""
    client = get_supabase_client()
    drive_service = get_drive_service()
    
    # Validate job exists
    job = await get_job(job_id)
    if not job:
        raise ValueError(f"Job not found: {job_id}")
    
    # Validate file type
    mime_type = get_mime_type(file_name)
    if not mime_type:
        raise ValueError(f"Invalid file type. Allowed: PDF, DOCX")
    
    # Get or create job folder in Google Drive
    folder_id = await drive_service.get_or_create_job_folder(job_id, job.title)
    
    # Update job with folder ID if not set
    if not job.google_drive_folder_id:
        await update_job_drive_folder(job_id, folder_id)
    
    # Upload to Google Drive
    drive_file_id = await drive_service.upload_file(
        file_content=file_content,
        file_name=file_name,
        folder_id=folder_id,
        mime_type=mime_type
    )
    
    # Extract candidate name from file name (remove extension)
    candidate_name = file_name.rsplit('.', 1)[0] if '.' in file_name else file_name
    
    # Save to database
    data = {
        "job_id": job_id,
        "file_name": file_name,
        "google_drive_file_id": drive_file_id,
        "candidate_name": candidate_name
    }
    
    result = client.table("resumes").insert(data).execute()
    
    if not result.data:
        # Cleanup: delete from Google Drive if DB insert fails
        await drive_service.delete_file(drive_file_id)
        raise ValueError("Failed to save resume to database")
    
    logger.info(f"Uploaded resume: {file_name} for job {job_id}")
    
    # Log audit
    client.table("audit_logs").insert({
        "entity_type": "resume",
        "entity_id": str(result.data[0]["id"]),
        "action": "uploaded",
        "details": {"job_id": job_id, "file_name": file_name}
    }).execute()
    
    return ResumeResponse(**result.data[0])


async def upload_multiple_resumes(
    job_id: str,
    files: List[tuple]  # List of (file_content, file_name)
) -> List[ResumeResponse]:
    """Upload multiple resumes for a job"""
    results = []
    errors = []
    
    for file_content, file_name in files:
        try:
            resume = await upload_resume(job_id, file_content, file_name)
            results.append(resume)
        except Exception as e:
            errors.append({"file_name": file_name, "error": str(e)})
            logger.error(f"Failed to upload {file_name}: {e}")
    
    if errors and not results:
        raise ValueError(f"All uploads failed: {errors}")
    
    return results


async def get_resume(resume_id: int) -> Optional[ResumeResponse]:
    """Get a resume by ID"""
    client = get_supabase_client()
    result = client.table("resumes").select("*").eq("id", resume_id).execute()
    
    if not result.data:
        return None
    
    return ResumeResponse(**result.data[0])


async def list_resumes(job_id: str) -> ResumeListResponse:
    """List all resumes for a job"""
    client = get_supabase_client()
    
    # Validate job exists
    job = await get_job(job_id)
    if not job:
        raise ValueError(f"Job not found: {job_id}")
    
    result = client.table("resumes").select("*", count="exact").eq("job_id", job_id).order("upload_timestamp", desc=True).execute()
    
    resumes = [ResumeResponse(**r) for r in result.data]
    total = result.count if result.count else len(resumes)
    
    return ResumeListResponse(resumes=resumes, total=total)


async def delete_resume(resume_id: int) -> bool:
    """Delete a single resume"""
    client = get_supabase_client()
    drive_service = get_drive_service()
    
    # Get resume
    resume = await get_resume(resume_id)
    if not resume:
        return False
    
    # Delete from Google Drive
    await drive_service.delete_file(resume.google_drive_file_id)
    
    # Delete from database (cascade will delete evaluation)
    client.table("resumes").delete().eq("id", resume_id).execute()
    
    logger.info(f"Deleted resume: {resume_id}")
    
    # Log audit
    client.table("audit_logs").insert({
        "entity_type": "resume",
        "entity_id": str(resume_id),
        "action": "deleted",
        "details": {"job_id": resume.job_id, "file_name": resume.file_name}
    }).execute()
    
    return True


async def delete_all_resumes(job_id: str) -> int:
    """Delete all resumes for a job"""
    client = get_supabase_client()
    drive_service = get_drive_service()
    
    # Get job
    job = await get_job(job_id)
    if not job:
        raise ValueError(f"Job not found: {job_id}")
    
    # Get all resumes
    resumes = await list_resumes(job_id)
    
    # Delete from Google Drive
    for resume in resumes.resumes:
        await drive_service.delete_file(resume.google_drive_file_id)
    
    # Delete from database
    client.table("resumes").delete().eq("job_id", job_id).execute()
    
    logger.info(f"Deleted all {resumes.total} resumes for job {job_id}")
    
    # Log audit
    client.table("audit_logs").insert({
        "entity_type": "job",
        "entity_id": job_id,
        "action": "all_resumes_deleted",
        "details": {"count": resumes.total}
    }).execute()
    
    return resumes.total


async def download_resume(resume_id: int) -> tuple:
    """Download a resume file, returns (file_content, file_name)"""
    drive_service = get_drive_service()
    
    resume = await get_resume(resume_id)
    if not resume:
        raise ValueError(f"Resume not found: {resume_id}")
    
    file_content = await drive_service.download_file(resume.google_drive_file_id)
    
    return file_content, resume.file_name
