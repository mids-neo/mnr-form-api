"""
Configuration settings for MNR Form API
"""
import os
from typing import List

# Environment
ENV = os.getenv("ENV", "development")
IS_PRODUCTION = ENV == "production"

# CORS Configuration
def get_cors_origins() -> List[str]:
    """Get CORS origins based on environment"""
    
    # Base origins for local development
    origins = [
        "http://localhost",
        "http://localhost:80",
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ]
    
    # Add production origins
    if IS_PRODUCTION:
        production_origins = [
            "https://preview--mnr-form-ai.lovable.app",
            "https://mnr-form-ai.lovable.app", 
            "https://*.lovable.app",  # Allow all Lovable subdomains
            "https://medicaldocai.com",  # Your custom domain
            "https://www.medicaldocai.com",  # Your custom domain with www
        ]
        origins.extend(production_origins)
        
        # Add custom domain if configured
        custom_domain = os.getenv("CUSTOM_DOMAIN")
        if custom_domain:
            origins.extend([
                f"https://{custom_domain}",
                f"https://www.{custom_domain}"
            ])
    
    # Add environment-specific frontend URL
    frontend_url = os.getenv("FRONTEND_URL")
    if frontend_url:
        origins.append(frontend_url)
    
    return origins

# API Configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# File limits
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
ALLOWED_EXTENSIONS = {".pdf"}

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO" if IS_PRODUCTION else "DEBUG")