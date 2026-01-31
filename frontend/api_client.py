import os
from typing import Optional, List, Dict, Any

import requests
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")


class APIClient:
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
    
    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """Handle API response and raise exceptions for errors"""
        if response.status_code >= 400:
            try:
                error = response.json()
                raise Exception(error.get("detail", "Unknown error"))
            except ValueError:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
        
        if response.status_code == 204:
            return {}
        
        return response.json()
    
    # Job endpoints
    def create_job(self, title: str, description: str) -> Dict[str, Any]:
        """Create a new job"""
        response = requests.post(
            f"{self.base_url}/jobs/",
            json={"title": title, "description": description}
        )
        return self._handle_response(response)
    
    def list_jobs(self, query: Optional[str] = None, page: int = 1, page_size: int = 10) -> Dict[str, Any]:
        """List jobs with optional search"""
        params = {"page": page, "page_size": page_size}
        if query:
            params["query"] = query
        
        response = requests.get(f"{self.base_url}/jobs/", params=params)
        return self._handle_response(response)
    
    def get_job(self, job_id: str) -> Dict[str, Any]:
        """Get a job by ID"""
        response = requests.get(f"{self.base_url}/jobs/{job_id}")
        return self._handle_response(response)
    
    def update_job(self, job_id: str, title: Optional[str] = None, description: Optional[str] = None) -> Dict[str, Any]:
        """Update a job"""
        data = {}
        if title:
            data["title"] = title
        if description:
            data["description"] = description
        
        response = requests.put(f"{self.base_url}/jobs/{job_id}", json=data)
        return self._handle_response(response)
    
    def delete_job(self, job_id: str) -> None:
        """Delete a job"""
        response = requests.delete(f"{self.base_url}/jobs/{job_id}")
        self._handle_response(response)
    
    # Resume endpoints
    def upload_resume(self, job_id: str, file) -> Dict[str, Any]:
        """Upload a single resume"""
        files = {"file": (file.name, file.getvalue(), file.type)}
        response = requests.post(f"{self.base_url}/resumes/{job_id}/upload", files=files)
        return self._handle_response(response)
    
    def upload_multiple_resumes(self, job_id: str, files: List) -> List[Dict[str, Any]]:
        """Upload multiple resumes"""
        file_list = [("files", (f.name, f.getvalue(), f.type)) for f in files]
        response = requests.post(f"{self.base_url}/resumes/{job_id}/upload-multiple", files=file_list)
        return self._handle_response(response)
    
    def list_resumes(self, job_id: str) -> Dict[str, Any]:
        """List all resumes for a job"""
        response = requests.get(f"{self.base_url}/resumes/{job_id}")
        return self._handle_response(response)
    
    def download_resume(self, resume_id: int) -> bytes:
        """Download a resume file"""
        response = requests.get(f"{self.base_url}/resumes/download/{resume_id}")
        if response.status_code >= 400:
            raise Exception(f"Failed to download resume: {response.status_code}")
        return response.content
    
    def delete_resume(self, resume_id: int) -> None:
        """Delete a single resume"""
        response = requests.delete(f"{self.base_url}/resumes/{resume_id}")
        self._handle_response(response)
    
    def delete_all_resumes(self, job_id: str) -> Dict[str, Any]:
        """Delete all resumes for a job"""
        response = requests.delete(f"{self.base_url}/resumes/job/{job_id}/all")
        return self._handle_response(response)
    
    # Evaluation endpoints
    def evaluate_resume(self, resume_id: int) -> Dict[str, Any]:
        """Evaluate a single resume"""
        response = requests.post(f"{self.base_url}/evaluations/resume/{resume_id}")
        return self._handle_response(response)
    
    def evaluate_all_resumes(self, job_id: str) -> List[Dict[str, Any]]:
        """Evaluate all resumes for a job"""
        response = requests.post(f"{self.base_url}/evaluations/job/{job_id}/all")
        return self._handle_response(response)
    
    def list_evaluations(
        self,
        job_id: str,
        status: Optional[str] = None,
        min_score: Optional[float] = None,
        max_score: Optional[float] = None,
        sort_by: str = "match_score",
        sort_order: str = "desc"
    ) -> Dict[str, Any]:
        """List evaluations for a job with filters"""
        params = {"sort_by": sort_by, "sort_order": sort_order}
        if status:
            params["status"] = status
        if min_score is not None:
            params["min_score"] = min_score
        if max_score is not None:
            params["max_score"] = max_score
        
        response = requests.get(f"{self.base_url}/evaluations/job/{job_id}", params=params)
        return self._handle_response(response)
    
    def get_evaluation_summary(self, job_id: str) -> Dict[str, Any]:
        """Get evaluation summary for a job"""
        response = requests.get(f"{self.base_url}/evaluations/job/{job_id}/summary")
        return self._handle_response(response)
    
    def get_evaluation(self, evaluation_id: int) -> Dict[str, Any]:
        """Get a specific evaluation"""
        response = requests.get(f"{self.base_url}/evaluations/{evaluation_id}")
        return self._handle_response(response)
    
    def re_evaluate_resume(self, resume_id: int) -> Dict[str, Any]:
        """Re-evaluate a resume"""
        response = requests.post(f"{self.base_url}/evaluations/resume/{resume_id}/re-evaluate")
        return self._handle_response(response)


# Singleton instance
api_client = APIClient()
