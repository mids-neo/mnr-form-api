"""
FastAPI dependencies package

Contains reusable dependencies for route handlers.
Dependencies handle common operations like authentication, database sessions, etc.
"""

from .auth_dependencies import get_current_user, get_admin_user, require_authentication
from .database_dependencies import get_db_session
from .validation_dependencies import validate_file_upload, validate_form_data

__all__ = [
    "get_current_user",
    "get_admin_user", 
    "require_authentication",
    "get_db_session",
    "validate_file_upload",
    "validate_form_data"
]