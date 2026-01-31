from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class EvaluationStatus(str, Enum):
    OK_TO_PROCEED = "OK to Proceed"
    NOT_OK = "Not OK"
    PENDING = "Pending"


# Job Schemas
class JobCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="Job title")
    description: str = Field(..., min_length=1, description="Job description")


class JobUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, min_length=1)


class JobResponse(BaseModel):
    id: int
    job_id: str = Field(..., description="Auto-generated 5-character alphanumeric JOBID")
    title: str
    description: str
    google_drive_folder_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class JobListResponse(BaseModel):
    jobs: List[JobResponse]
    total: int
    page: int
    page_size: int


# Resume Schemas
class ResumeResponse(BaseModel):
    id: int
    job_id: str
    file_name: str
    google_drive_file_id: str
    upload_timestamp: datetime
    candidate_name: Optional[str] = None


class ResumeListResponse(BaseModel):
    resumes: List[ResumeResponse]
    total: int


# Evaluation Schemas
class SkillMatch(BaseModel):
    skill: str
    matched: bool
    relevance_score: float = Field(..., ge=0, le=1)


class EvaluationResponse(BaseModel):
    id: int
    resume_id: int
    job_id: str
    candidate_name: Optional[str] = None
    file_name: str
    match_score: float = Field(..., ge=0, le=100, description="Match percentage")
    status: EvaluationStatus
    justification: str
    skills_extracted: List[str]
    skills_matched: List[SkillMatch]
    experience_years: Optional[float] = None
    education: Optional[str] = None
    previous_roles: List[str] = []
    evaluated_at: datetime


class EvaluationListResponse(BaseModel):
    evaluations: List[EvaluationResponse]
    total: int
    job_id: str
    job_title: str


class EvaluationSummary(BaseModel):
    job_id: str
    job_title: str
    total_resumes: int
    evaluated: int
    ok_to_proceed: int
    not_ok: int
    pending: int
    average_score: float


# Search and Filter Schemas
class JobSearchParams(BaseModel):
    query: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)


class EvaluationFilterParams(BaseModel):
    status: Optional[EvaluationStatus] = None
    min_score: Optional[float] = Field(None, ge=0, le=100)
    max_score: Optional[float] = Field(None, ge=0, le=100)
    sort_by: str = Field(default="match_score", pattern="^(match_score|evaluated_at|candidate_name)$")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")
