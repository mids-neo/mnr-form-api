"""
Application configuration settings
"""

import os
from typing import Optional
from pydantic import BaseSettings, Field

class Settings(BaseSettings):
    """Application settings"""
    
    # API Configuration
    app_name: str = "MNR Form API"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False, env="DEBUG")
    
    # Server Configuration
    host: str = Field(default="0.0.0.0", env="API_HOST")
    port: int = Field(default=8000, env="API_PORT")
    
    # Database Configuration
    database_url: str = Field(env="DATABASE_URL")
    
    # Security Configuration
    secret_key: str = Field(env="JWT_SECRET_KEY")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # OpenAI Configuration
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    
    # File Upload Configuration
    max_file_size: int = 50 * 1024 * 1024  # 50MB
    upload_dir: str = "data/uploads"
    output_dir: str = "data/outputs"
    
    # CORS Configuration
    cors_origins: list = ["http://localhost:3000", "http://localhost:8080", "https://your-frontend-domain.com"]
    cors_credentials: bool = True
    cors_methods: list = ["*"]
    cors_headers: list = ["*"]
    
    # Logging Configuration
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Global settings instance
settings = Settings()