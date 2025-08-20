"""
Secure wrapper for existing medical form processing endpoints
"""
from datetime import datetime, timezone
from typing import Optional
from fastapi import Depends, HTTPException, Request, UploadFile, File, Query
from sqlalchemy.orm import Session
import hashlib
import os

from database import get_db, User, FileProcessingLog, AuditAction
from auth import get_current_user, require_permission, log_audit_event, get_client_ip, get_user_agent

class SecureFileProcessor:
    """Secure wrapper for file processing operations"""
    
    @staticmethod
    async def log_file_upload(
        db: Session,
        user: User,
        request: Request,
        file: UploadFile,
        session_id: Optional[str] = None
    ) -> FileProcessingLog:
        """Log file upload for audit trail"""
        
        # Read file content for hash
        file_content = await file.read()
        file_hash = hashlib.sha256(file_content).hexdigest()
        
        # Reset file position
        await file.seek(0)
        
        # Create processing log entry
        processing_log = FileProcessingLog(
            user_id=user.id,
            session_id=session_id,
            original_filename=file.filename,
            file_size=len(file_content),
            file_hash=file_hash,
            upload_timestamp=datetime.now(timezone.utc),
            contains_phi=True  # Assume medical forms contain PHI
        )
        
        db.add(processing_log)
        db.commit()
        db.refresh(processing_log)
        
        # Log audit event
        await log_audit_event(
            db=db,
            action=AuditAction.FILE_UPLOAD,
            user_id=user.id,
            resource_type="medical_form",
            resource_id=str(processing_log.id),
            endpoint=str(request.url.path),
            method=request.method,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            details={
                "filename": file.filename,
                "file_size": len(file_content),
                "file_hash": file_hash[:16],  # Partial hash for identification
                "session_id": session_id
            },
            contains_phi=True,
            data_classification="confidential"
        )
        
        return processing_log
    
    @staticmethod
    async def log_file_processing(
        db: Session,
        user: User,
        request: Request,
        processing_log: FileProcessingLog,
        method: str,
        output_format: str,
        success: bool,
        processing_time: Optional[int] = None,
        fields_extracted: Optional[int] = None,
        fields_filled: Optional[int] = None,
        output_files: Optional[list] = None,
        error_details: Optional[str] = None
    ):
        """Log file processing completion"""
        
        # Update processing log
        processing_log.processing_method = method
        processing_log.output_format = output_format
        processing_log.success = success
        processing_log.processing_time = processing_time
        processing_log.fields_extracted = fields_extracted
        processing_log.fields_filled = fields_filled
        processing_log.output_files = output_files
        processing_log.error_details = error_details
        processing_log.processing_completed = datetime.now(timezone.utc)
        
        if not processing_log.processing_started:
            processing_log.processing_started = processing_log.upload_timestamp
        
        db.commit()
        
        # Log audit event
        await log_audit_event(
            db=db,
            action=AuditAction.FILE_PROCESS,
            user_id=user.id,
            resource_type="medical_form",
            resource_id=str(processing_log.id),
            endpoint=str(request.url.path),
            method=request.method,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            details={
                "processing_method": method,
                "output_format": output_format,
                "processing_time_ms": processing_time,
                "fields_extracted": fields_extracted,
                "fields_filled": fields_filled,
                "output_files_count": len(output_files) if output_files else 0
            },
            success=success,
            error_message=error_details,
            contains_phi=True,
            data_classification="confidential"
        )
    
    @staticmethod
    async def log_file_download(
        db: Session,
        user: User,
        request: Request,
        filename: str,
        file_path: str
    ):
        """Log file download for audit trail"""
        
        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        
        await log_audit_event(
            db=db,
            action=AuditAction.FILE_DOWNLOAD,
            user_id=user.id,
            resource_type="file",
            resource_id=filename,
            endpoint=str(request.url.path),
            method=request.method,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            details={
                "filename": filename,
                "file_size": file_size,
                "file_path": file_path
            },
            contains_phi=True,  # Assume downloaded files contain PHI
            data_classification="confidential"
        )

def require_file_processing_permission():
    """Dependency to check file processing permissions"""
    return require_permission("can_process_forms")

def require_file_download_permission():
    """Dependency to check file download permissions"""
    return require_permission("can_download_files")

def require_file_delete_permission():
    """Dependency to check file deletion permissions"""
    return require_permission("can_delete_files")

async def validate_file_upload(file: UploadFile = File(...)) -> UploadFile:
    """Validate uploaded file"""
    
    # Check file size (max 100MB)
    MAX_FILE_SIZE = 100 * 1024 * 1024
    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB"
        )
    
    # Check file extension
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")
    
    allowed_extensions = {'.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.tif'}
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    return file

async def get_processing_session(
    session_id: Optional[str] = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Optional[str]:
    """Get or validate processing session"""
    
    if session_id:
        # Validate that session belongs to current user
        # You could implement session ownership validation here
        pass
    
    return session_id

async def check_rate_limit(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> bool:
    """Check if user has exceeded rate limits"""
    
    from datetime import timedelta
    
    # Count recent uploads (last hour)
    recent_uploads = db.query(FileProcessingLog).filter(
        FileProcessingLog.user_id == user.id,
        FileProcessingLog.upload_timestamp > datetime.now(timezone.utc) - timedelta(hours=1)
    ).count()
    
    # Rate limits by role
    rate_limits = {
        "admin": 1000,
        "physician": 500,
        "nurse": 200,
        "technician": 100,
        "viewer": 0,
        "guest": 10
    }
    
    limit = rate_limits.get(user.role.value, 10)
    
    if recent_uploads >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Maximum {limit} uploads per hour for {user.role.value} role"
        )
    
    return True