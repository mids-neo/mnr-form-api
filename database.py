"""
Database configuration and models for authentication and audit logging
"""
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Enum, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
from datetime import datetime, timedelta
import enum
import os

# Database URL - use SQLite for development, PostgreSQL for production
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./medical_forms_auth.db")

engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class UserRole(enum.Enum):
    """User roles for role-based access control"""
    ADMIN = "admin"           # Full system access
    PHYSICIAN = "physician"   # Can process and view all medical forms
    NURSE = "nurse"          # Can process medical forms, limited admin access
    TECHNICIAN = "technician" # Can upload and process forms, no admin access
    VIEWER = "viewer"        # Read-only access to processed forms
    GUEST = "guest"          # Limited demo access

class AuditAction(enum.Enum):
    """Types of audit actions to track"""
    LOGIN = "login"
    LOGOUT = "logout"
    REGISTER = "register"
    PASSWORD_CHANGE = "password_change"
    MFA_ENABLE = "mfa_enable"
    MFA_DISABLE = "mfa_disable"
    FILE_UPLOAD = "file_upload"
    FILE_PROCESS = "file_process"
    FILE_DOWNLOAD = "file_download"
    FILE_DELETE = "file_delete"
    USER_CREATE = "user_create"
    USER_UPDATE = "user_update"
    USER_DELETE = "user_delete"
    ROLE_CHANGE = "role_change"
    SYSTEM_ACCESS = "system_access"
    API_ACCESS = "api_access"
    DATA_EXPORT = "data_export"

class User(Base):
    """User model for authentication"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.GUEST, nullable=False)
    
    # Account status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    # MFA settings
    mfa_enabled = Column(Boolean, default=False)
    mfa_secret = Column(String(255), nullable=True)  # TOTP secret
    backup_codes = Column(JSON, nullable=True)  # List of backup codes
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Security
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")

class UserSession(Base):
    """Active user sessions for JWT token management"""
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token_id = Column(String(255), unique=True, index=True, nullable=False)  # JWT jti claim
    device_info = Column(String(500), nullable=True)  # User agent, IP, etc.
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    user = relationship("User", back_populates="sessions")

class AuditLog(Base):
    """Comprehensive audit logging for all system activities"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Can be null for system actions
    session_id = Column(Integer, ForeignKey("user_sessions.id"), nullable=True)
    
    # Action details
    action = Column(Enum(AuditAction), nullable=False)
    resource_type = Column(String(50), nullable=True)  # e.g., "medical_form", "user", "system"
    resource_id = Column(String(100), nullable=True)   # ID of the affected resource
    
    # Context information
    endpoint = Column(String(255), nullable=True)      # API endpoint accessed
    method = Column(String(10), nullable=True)         # HTTP method
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    # Details and metadata
    details = Column(JSON, nullable=True)              # Additional context (file names, sizes, etc.)
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    
    # Sensitive data tracking
    contains_phi = Column(Boolean, default=False)      # Protected Health Information
    data_classification = Column(String(50), default="internal")  # public, internal, confidential, restricted
    
    # Timestamps
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="audit_logs")

class FileProcessingLog(Base):
    """Detailed logging for medical form processing activities"""
    __tablename__ = "file_processing_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_id = Column(String(255), nullable=True)  # Progress session ID
    
    # File information
    original_filename = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=True)
    file_hash = Column(String(64), nullable=True)      # SHA-256 hash
    upload_path = Column(String(500), nullable=True)
    
    # Processing details
    processing_method = Column(String(50), nullable=True)  # openai, legacy, etc.
    output_format = Column(String(50), nullable=True)      # mnr, ash, both
    processing_time = Column(Integer, nullable=True)       # milliseconds
    
    # Results
    success = Column(Boolean, default=False)
    fields_extracted = Column(Integer, nullable=True)
    fields_filled = Column(Integer, nullable=True)
    confidence_score = Column(String(10), nullable=True)
    error_details = Column(Text, nullable=True)
    
    # Output files
    output_files = Column(JSON, nullable=True)         # List of generated file paths
    
    # Compliance and security
    contains_phi = Column(Boolean, default=True)       # Assume medical forms contain PHI
    retention_until = Column(DateTime(timezone=True), nullable=True)  # Data retention policy
    
    # Timestamps
    upload_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    processing_started = Column(DateTime(timezone=True), nullable=True)
    processing_completed = Column(DateTime(timezone=True), nullable=True)

def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Role hierarchy and permissions
ROLE_PERMISSIONS = {
    UserRole.ADMIN: {
        "can_manage_users": True,
        "can_view_audit_logs": True,
        "can_process_forms": True,
        "can_download_files": True,
        "can_delete_files": True,
        "can_export_data": True,
        "can_change_system_settings": True,
    },
    UserRole.PHYSICIAN: {
        "can_manage_users": False,
        "can_view_audit_logs": True,
        "can_process_forms": True,
        "can_download_files": True,
        "can_delete_files": True,
        "can_export_data": True,
        "can_change_system_settings": False,
    },
    UserRole.NURSE: {
        "can_manage_users": False,
        "can_view_audit_logs": False,
        "can_process_forms": True,
        "can_download_files": True,
        "can_delete_files": False,
        "can_export_data": False,
        "can_change_system_settings": False,
    },
    UserRole.TECHNICIAN: {
        "can_manage_users": False,
        "can_view_audit_logs": False,
        "can_process_forms": True,
        "can_download_files": True,
        "can_delete_files": False,
        "can_export_data": False,
        "can_change_system_settings": False,
    },
    UserRole.VIEWER: {
        "can_manage_users": False,
        "can_view_audit_logs": False,
        "can_process_forms": False,
        "can_download_files": True,
        "can_delete_files": False,
        "can_export_data": False,
        "can_change_system_settings": False,
    },
    UserRole.GUEST: {
        "can_manage_users": False,
        "can_view_audit_logs": False,
        "can_process_forms": True,  # Limited demo access
        "can_download_files": False,
        "can_delete_files": False,
        "can_export_data": False,
        "can_change_system_settings": False,
    },
}

def has_permission(user_role: UserRole, permission: str) -> bool:
    """Check if a user role has a specific permission"""
    return ROLE_PERMISSIONS.get(user_role, {}).get(permission, False)