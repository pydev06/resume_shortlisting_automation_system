import io
import logging
import os
from typing import Optional, List

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload

from ..core.config import get_settings

logger = logging.getLogger("resume_shortlisting")

SCOPES = ['https://www.googleapis.com/auth/drive']


class GoogleDriveService:
    def __init__(self):
        self.settings = get_settings()
        self.service = None
        self._root_folder_id = None
    
    def _get_credentials(self):
        """Get credentials using OAuth 2.0 (web app flow)"""
        creds = None
        token_path = 'token.json'
        creds_path = self.settings.google_drive_credentials_path
        
        # Check for existing token
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        
        # If no valid credentials, do OAuth flow
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(creds_path):
                    raise FileNotFoundError(
                        f"Google OAuth credentials file not found: {creds_path}. "
                        f"Download OAuth client credentials from Google Cloud Console."
                    )
                
                # For web app credentials, we need to handle the redirect URI properly
                from google_auth_oauthlib.flow import Flow
                
                # Create flow with web app credentials
                flow = Flow.from_client_secrets_file(
                    creds_path, 
                    scopes=SCOPES,
                    redirect_uri='http://localhost:8000/auth/callback'
                )
                
                auth_url, _ = flow.authorization_url(prompt='consent')
                print(f'Please visit this URL to authorize: {auth_url}')
                print('After authorization, copy the full redirect URL from your browser')
                print('and paste it here:')
                redirect_url = input('Full redirect URL: ').strip()
                
                # Extract authorization code from redirect URL
                from urllib.parse import parse_qs, urlparse
                parsed_url = urlparse(redirect_url)
                query_params = parse_qs(parsed_url.query)
                
                if 'code' not in query_params:
                    raise ValueError("No authorization code found in redirect URL")
                
                auth_code = query_params['code'][0]
                
                # Exchange code for token
                flow.fetch_token(code=auth_code)
                creds = flow.credentials
            
            # Save the credentials for next run
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
        
        return creds
    
    def _get_service(self):
        """Get or create Google Drive service"""
        if self.service is None:
            creds = self._get_credentials()
            self.service = build('drive', 'v3', credentials=creds)
        return self.service
    
    async def get_or_create_root_folder(self) -> str:
        """Get or create the root 'Hiring' folder. Prioritizes folders NOT owned by service account."""
        if self._root_folder_id:
            return self._root_folder_id
        
        service = self._get_service()
        folder_name = self.settings.google_drive_root_folder_name
        
        # Search for existing folder - include shared folders
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = service.files().list(
            q=query, 
            spaces='drive', 
            fields='files(id, name, owners, shared, ownedByMe)',
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        files = results.get('files', [])
        
        if files:
            # IMPORTANT: Prefer folders NOT owned by service account (user's shared folder)
            # Service accounts have no storage quota, so we must use user's folder
            user_folders = [f for f in files if not f.get('ownedByMe', True)]
            if user_folders:
                self._root_folder_id = user_folders[0]['id']
                logger.info(f"Using user's shared folder: {folder_name} ({self._root_folder_id})")
            else:
                # Fall back to any available folder (will fail on upload if service account owned)
                self._root_folder_id = files[0]['id']
                logger.warning(f"No user-shared folder found, using: {folder_name} ({self._root_folder_id})")
        else:
            raise ValueError(
                f"No '{folder_name}' folder found. Please create a '{folder_name}' folder in your Google Drive "
                f"and share it with the service account email (with Editor access)."
            )
        
        return self._root_folder_id
    
    async def get_or_create_job_folder(self, job_id: str, job_title: str) -> str:
        """Get or create a job folder: <JOBID>_<JobTitle>/resumes"""
        service = self._get_service()
        root_folder_id = await self.get_or_create_root_folder()
        
        # Sanitize job title for folder name
        safe_title = "".join(c for c in job_title if c.isalnum() or c in (' ', '-', '_')).strip()
        job_folder_name = f"{job_id}_{safe_title}"
        
        # Search for existing job folder
        query = f"name='{job_folder_name}' and '{root_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        files = results.get('files', [])
        
        if files:
            job_folder_id = files[0]['id']
        else:
            # Create job folder
            file_metadata = {
                'name': job_folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [root_folder_id]
            }
            folder = service.files().create(body=file_metadata, fields='id').execute()
            job_folder_id = folder.get('id')
            logger.info(f"Created job folder: {job_folder_name}")
        
        # Get or create resumes subfolder
        query = f"name='resumes' and '{job_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        files = results.get('files', [])
        
        if files:
            resumes_folder_id = files[0]['id']
        else:
            # Create resumes subfolder
            file_metadata = {
                'name': 'resumes',
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [job_folder_id]
            }
            folder = service.files().create(body=file_metadata, fields='id').execute()
            resumes_folder_id = folder.get('id')
            logger.info(f"Created resumes folder for job: {job_id}")
        
        return resumes_folder_id
    
    async def upload_file(
        self,
        file_content: bytes,
        file_name: str,
        folder_id: str,
        mime_type: str
    ) -> str:
        """Upload a file to Google Drive and return the file ID"""
        service = self._get_service()
        
        file_metadata = {
            'name': file_name,
            'parents': [folder_id]
        }
        
        media = MediaIoBaseUpload(
            io.BytesIO(file_content),
            mimetype=mime_type,
            resumable=True
        )
        
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        
        file_id = file.get('id')
        logger.info(f"Uploaded file: {file_name} ({file_id})")
        
        return file_id
    
    async def download_file(self, file_id: str) -> bytes:
        """Download a file from Google Drive"""
        service = self._get_service()
        
        request = service.files().get_media(fileId=file_id)
        file_buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(file_buffer, request)
        
        done = False
        while not done:
            status, done = downloader.next_chunk()
        
        return file_buffer.getvalue()
    
    async def delete_file(self, file_id: str) -> bool:
        """Delete a file from Google Drive"""
        service = self._get_service()
        
        try:
            service.files().delete(fileId=file_id).execute()
            logger.info(f"Deleted file: {file_id}")
            return True
        except HttpError as e:
            logger.error(f"Failed to delete file {file_id}: {e}")
            return False
    
    async def delete_folder(self, folder_id: str) -> bool:
        """Delete a folder and all its contents from Google Drive"""
        service = self._get_service()
        
        try:
            service.files().delete(fileId=folder_id).execute()
            logger.info(f"Deleted folder: {folder_id}")
            return True
        except HttpError as e:
            logger.error(f"Failed to delete folder {folder_id}: {e}")
            return False
    
    async def list_files_in_folder(self, folder_id: str) -> List[dict]:
        """List all files in a folder"""
        service = self._get_service()
        
        query = f"'{folder_id}' in parents and trashed=false"
        results = service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name, mimeType, createdTime)'
        ).execute()
        
        return results.get('files', [])


# Singleton instance
_drive_service: Optional[GoogleDriveService] = None


def get_drive_service() -> GoogleDriveService:
    global _drive_service
    if _drive_service is None:
        _drive_service = GoogleDriveService()
    return _drive_service


def reset_drive_service():
    """Reset the singleton to force re-initialization"""
    global _drive_service
    _drive_service = None
