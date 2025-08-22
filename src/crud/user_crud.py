"""
CRUD operations for User model
"""

from typing import Optional, List
from sqlalchemy.orm import Session
from ..models import User, UserRole

class UserCRUD:
    """CRUD operations for User model"""
    
    @staticmethod
    def create(db: Session, email: str, hashed_password: str, full_name: str, role: UserRole = UserRole.GUEST) -> User:
        """Create a new user"""
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
    def get_by_id(db: Session, user_id: int) -> Optional[User]:
        """Get user by ID"""
        return db.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    def get_by_email(db: Session, email: str) -> Optional[User]:
        """Get user by email"""
        return db.query(User).filter(User.email == email).first()
    
    @staticmethod
    def get_all(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
        """Get all users with pagination"""
        return db.query(User).offset(skip).limit(limit).all()
    
    @staticmethod
    def update(db: Session, user: User, **kwargs) -> User:
        """Update user fields"""
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    def delete(db: Session, user: User) -> bool:
        """Delete a user"""
        db.delete(user)
        db.commit()
        return True
    
    @staticmethod
    def activate(db: Session, user: User) -> User:
        """Activate a user account"""
        user.is_active = True
        user.is_verified = True
        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    def deactivate(db: Session, user: User) -> User:
        """Deactivate a user account"""
        user.is_active = False
        db.commit()
        db.refresh(user)
        return user