"""
Authentication service for handling user management and auth operations
"""

from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from ..models import User, UserSession, UserRole, get_db
from ..auth.auth import PasswordHash, JWTManager

class AuthService:
    """Service for authentication operations"""
    
    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
        """Authenticate a user with email and password"""
        user = db.query(User).filter(User.email == email).first()
        if user and PasswordHash.verify_password(password, user.hashed_password):
            return user
        return None
    
    @staticmethod
    def create_user(db: Session, email: str, password: str, full_name: str, role: UserRole = UserRole.GUEST) -> User:
        """Create a new user"""
        hashed_password = PasswordHash.hash_password(password)
        user = User(
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            role=role
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """Get user by email"""
        return db.query(User).filter(User.email == email).first()
    
    @staticmethod
    def update_last_login(db: Session, user: User) -> None:
        """Update user's last login timestamp"""
        user.last_login = datetime.utcnow()
        db.commit()