"""
Authentication dependencies for FastAPI routes
"""

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..models import User, UserRole, get_db
from ..auth.auth import get_current_user as _get_current_user

def get_current_user(db: Session = Depends(get_db)) -> User:
    """Dependency to get the current authenticated user"""
    return _get_current_user(db)

def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Dependency that requires admin role"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

def require_authentication():
    """Dependency that just requires authentication (any role)"""
    return Depends(get_current_user)

def require_role(required_role: UserRole):
    """Dependency factory that requires a specific role"""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role {required_role.value} required"
            )
        return current_user
    return role_checker