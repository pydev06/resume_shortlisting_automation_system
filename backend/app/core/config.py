from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Supabase
    supabase_url: str
    supabase_key: str
    
    # Google Drive
    google_drive_credentials_path: str = "credentials.json"
    google_drive_root_folder_name: str = "Hiring"
    
    # OpenAI
    openai_api_key: str
    
    # App settings
    debug: bool = False
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()
