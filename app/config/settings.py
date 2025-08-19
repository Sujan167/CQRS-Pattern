import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # API Settings
    API_V1_STR: str = "/v1"
    PROJECT_NAME: str = "CQRS Task Management API"
    VERSION: str = "1.0.0"
    
    
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    class Config:
        env_file = ".env"


# Create settings instance
settings = Settings()
