"""
API routes package

This package contains all API route modules organized by functionality.
Routes are typically organized by resource type (users, forms, files, etc.)
"""

from .v1 import api_router

__all__ = ["api_router"]