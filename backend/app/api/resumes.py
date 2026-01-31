from typing import List

from fastapi import APIRouter, HTTPException, UploadFile, File, Response

from ..models.schemas import ResumeResponse, ResumeListResponse
from ..services import resume_service

router = APIRouter(prefix="/resumes", tags=["Resumes"])

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {'.pdf', '.docx'}


def validate_file(file: UploadFile):
    """Validate file type and size"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="File name is required")
    
    ext = '.' + file.filename.lower().split('.')[-1] if '.' in file.filename else ''
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )


@router.post("/{job_id}/upload", response_model=ResumeResponse, status_code=201)
async def upload_resume(job_id: str, file: UploadFile = File(...)):
    """Upload a single resume for a job"""
    validate_file(file)
    
    try:
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="File too large. Max size: 10MB")
        
        return await resume_service.upload_resume(job_id, content, file.filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{job_id}/upload-multiple", response_model=List[ResumeResponse], status_code=201)
async def upload_multiple_resumes(job_id: str, files: List[UploadFile] = File(...)):
    """Upload multiple resumes for a job"""
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    # Validate all files first
    for file in files:
        validate_file(file)
    
    try:
        file_data = []
        for file in files:
            content = await file.read()
            if len(content) > MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=400,
                    detail=f"File {file.filename} too large. Max size: 10MB"
                )
            file_data.append((content, file.filename))
        
        return await resume_service.upload_multiple_resumes(job_id, file_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{job_id}", response_model=ResumeListResponse)
async def list_resumes(job_id: str):
    """List all resumes for a job"""
    try:
        return await resume_service.list_resumes(job_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/download/{resume_id}")
async def download_resume(resume_id: int):
    """Download a resume file"""
    try:
        content, filename = await resume_service.download_resume(resume_id)
        
        # Determine content type
        ext = filename.lower().split('.')[-1] if '.' in filename else ''
        content_type = 'application/pdf' if ext == 'pdf' else 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        
        return Response(
            content=content,
            media_type=content_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{resume_id}", status_code=204)
async def delete_resume(resume_id: int):
    """Delete a single resume"""
    deleted = await resume_service.delete_resume(resume_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Resume not found: {resume_id}")


@router.delete("/job/{job_id}/all", status_code=200)
async def delete_all_resumes(job_id: str):
    """Delete all resumes for a job"""
    try:
        count = await resume_service.delete_all_resumes(job_id)
        return {"message": f"Deleted {count} resumes", "count": count}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
