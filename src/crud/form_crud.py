"""
CRUD operations for form processing logs
"""

from typing import Optional, List
from sqlalchemy.orm import Session
from ..models import FileProcessingLog

class FormCRUD:
    """CRUD operations for form processing"""
    
    @staticmethod
    def create_processing_log(
        db: Session,
        user_id: int,
        filename: str,
        file_size: int = None,
        file_hash: str = None,
        session_id: str = None
    ) -> FileProcessingLog:
        """Create a new processing log entry"""
        log = FileProcessingLog(
            user_id=user_id,
            original_filename=filename,
            file_size=file_size,
            file_hash=file_hash,
            session_id=session_id
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log
    
    @staticmethod
    def get_by_id(db: Session, log_id: int) -> Optional[FileProcessingLog]:
        """Get processing log by ID"""
        return db.query(FileProcessingLog).filter(FileProcessingLog.id == log_id).first()
    
    @staticmethod
    def get_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[FileProcessingLog]:
        """Get processing logs for a user"""
        return db.query(FileProcessingLog).filter(
            FileProcessingLog.user_id == user_id
        ).order_by(FileProcessingLog.upload_timestamp.desc()).offset(skip).limit(limit).all()
    
    @staticmethod
    def get_by_session(db: Session, session_id: str) -> Optional[FileProcessingLog]:
        """Get processing log by session ID"""
        return db.query(FileProcessingLog).filter(
            FileProcessingLog.session_id == session_id
        ).first()
    
    @staticmethod
    def update_processing_result(
        db: Session,
        log: FileProcessingLog,
        success: bool,
        processing_time: int = None,
        output_files: List[str] = None,
        error_details: str = None,
        confidence_score: str = None
    ) -> FileProcessingLog:
        """Update processing log with results"""
        log.success = success
        if processing_time is not None:
            log.processing_time = processing_time
        if output_files is not None:
            log.output_files = output_files
        if error_details is not None:
            log.error_details = error_details
        if confidence_score is not None:
            log.confidence_score = confidence_score
        
        db.commit()
        db.refresh(log)
        return log
    
    @staticmethod
    def get_all_processing_logs(db: Session, skip: int = 0, limit: int = 100) -> List[FileProcessingLog]:
        """Get all processing logs with pagination"""
        return db.query(FileProcessingLog).order_by(
            FileProcessingLog.upload_timestamp.desc()
        ).offset(skip).limit(limit).all()