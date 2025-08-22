"""
API request and response models for the MNR Form Processing API
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

# Authentication Models
class UserLogin(BaseModel):
    """User login request"""
    email: Optional[str] = None
    username_or_email: Optional[str] = None
    password: str
    totp_code: Optional[str] = None


class UserRegister(BaseModel):
    """User registration request"""
    email: str = Field(..., pattern=r'^[^@]+@[^@]+\.[^@]+$')
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=1)
    role: Optional[str] = "guest"

class TokenResponse(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: int
    role: str
    full_name: str

class UserResponse(BaseModel):
    """User information response"""
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    is_verified: bool
    mfa_enabled: bool
    created_at: datetime
    last_login: Optional[datetime]

# File Processing Models
class ProcessingMethod(str, Enum):
    """Available processing methods"""
    AUTO = "auto"
    OPENAI = "openai"
    LEGACY = "legacy"

class OutputFormat(str, Enum):
    """Output format options"""
    MNR = "mnr"
    ASH = "ash"
    BOTH = "both"

class ProcessingRequest(BaseModel):
    """Form processing request"""
    extraction_method: ProcessingMethod = ProcessingMethod.AUTO
    output_format: OutputFormat = OutputFormat.ASH
    enhanced_filling: bool = True
    save_intermediate: bool = True

class ProcessingProgress(BaseModel):
    """Processing progress update"""
    session_id: str
    stage: str
    progress: float = Field(..., ge=0, le=100)
    message: str
    timestamp: datetime
    error: Optional[str] = None

class ProcessingResult(BaseModel):
    """Processing completion result"""
    session_id: str
    success: bool
    processing_time_ms: int
    extracted_data: Optional[Dict[str, Any]] = None
    output_files: List[str] = []
    confidence_score: Optional[str] = None
    error_message: Optional[str] = None
    warnings: List[str] = []

class FileUploadResponse(BaseModel):
    """File upload response"""
    filename: str
    file_size: int
    file_hash: str
    upload_path: str
    session_id: str
    timestamp: datetime

# Form Data Models
class PatientInfo(BaseModel):
    """Patient information"""
    name: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    member_id: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None

class ProviderInfo(BaseModel):
    """Healthcare provider information"""
    name: Optional[str] = None
    clinic: Optional[str] = None
    phone: Optional[str] = None
    fax: Optional[str] = None
    npi: Optional[str] = None

class TreatmentInfo(BaseModel):
    """Treatment and therapy information"""
    diagnosis: Optional[str] = None
    treatment_history: List[str] = []
    pain_levels: Dict[str, Any] = {}
    frequency: Optional[str] = None
    duration: Optional[str] = None

class FormData(BaseModel):
    """Complete form data structure"""
    patient: PatientInfo
    provider: ProviderInfo
    treatment: TreatmentInfo
    additional_fields: Dict[str, Any] = {}

# Error Response Models
class ErrorDetail(BaseModel):
    """Error detail information"""
    code: str
    message: str
    field: Optional[str] = None

class ErrorResponse(BaseModel):
    """API error response"""
    error: str
    details: List[ErrorDetail] = []
    timestamp: datetime
    request_id: Optional[str] = None

# Health Check Models
class HealthStatus(BaseModel):
    """System health status"""
    status: str
    timestamp: datetime
    version: str
    database_connected: bool
    pipeline_ready: bool
    dependencies: Dict[str, bool] = {}

# File Management Models
class FileInfo(BaseModel):
    """File information"""
    filename: str
    file_size: int
    file_type: str
    upload_date: datetime
    processing_status: str
    output_files: List[str] = []

class FileListResponse(BaseModel):
    """List of files response"""
    files: List[FileInfo]
    total_count: int
    page: int
    page_size: int