"""
Database dependencies for FastAPI routes
"""

from sqlalchemy.orm import Session
from ..models import get_db

def get_db_session() -> Session:
    """Dependency to get database session"""
    return get_db()