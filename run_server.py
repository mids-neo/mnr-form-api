#!/usr/bin/env python3
"""
Production-ready server startup script
Works both locally and in Docker/AWS environments
"""
import os
import sys

# Ensure the app can find the src module
app_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, app_dir)

if __name__ == "__main__":
    import uvicorn
    
    # Get configuration from environment
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    reload = os.getenv("ENV", "development") == "development"
    
    print(f"Starting MNR Form API server on {host}:{port}")
    print(f"Environment: {os.getenv('ENV', 'development')}")
    print(f"Python path: {sys.path}")
    
    uvicorn.run(
        "src.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )