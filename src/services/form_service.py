"""
Form processing service for handling medical form operations
"""

from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from ..models import FileProcessingLog, User
from ..pipeline import process_medical_form, PipelineConfig, PipelineResult

class FormService:
    """Service for form processing operations"""
    
    @staticmethod
    def process_form(
        user: User,
        file_path: str,
        config: PipelineConfig,
        db: Session
    ) -> PipelineResult:
        """Process a medical form with the given configuration"""
        
        # Create processing log entry
        log_entry = FileProcessingLog(
            user_id=user.id,
            original_filename=file_path.split('/')[-1],
            processing_method=config.extraction_method,
            output_format=config.output_format
        )
        db.add(log_entry)
        db.commit()
        
        try:
            # Process the form using the pipeline
            result = process_medical_form(file_path, config)
            
            # Update log with results
            log_entry.success = result.success
            log_entry.processing_time = result.processing_time_ms
            log_entry.output_files = result.output_files
            log_entry.error_details = result.error_message
            
            db.commit()
            return result
            
        except Exception as e:
            log_entry.success = False
            log_entry.error_details = str(e)
            db.commit()
            raise
    
    @staticmethod
    def get_user_processing_history(db: Session, user_id: int) -> List[FileProcessingLog]:
        """Get processing history for a user"""
        return db.query(FileProcessingLog).filter(
            FileProcessingLog.user_id == user_id
        ).order_by(FileProcessingLog.upload_timestamp.desc()).all()
    
    @staticmethod
    def validate_form_data(form_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate form data structure"""
        # Add form validation logic here
        return {"is_valid": True, "errors": []}