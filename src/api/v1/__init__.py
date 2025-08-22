"""
API v1 routes

Organizes all v1 API endpoints in a structured manner.
"""

from fastapi import APIRouter
from ...auth.auth_routes import router as auth_router
from ...auth.secure_medical_routes import router as medical_router

api_router = APIRouter(prefix="/api/v1")

# Include all route modules
api_router.include_router(auth_router, tags=["Authentication"])
api_router.include_router(medical_router, prefix="/medical", tags=["Medical Forms"])

__all__ = ["api_router"]