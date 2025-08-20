"""
Secured medical form processing routes with authentication and audit logging
"""
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os
import tempfile
import shutil
import logging

from database import get_db, User
from auth import get_current_user, require_permission
from secure_endpoints import (
    SecureFileProcessor, require_file_processing_permission,
    require_file_download_permission, validate_file_upload,
    get_processing_session, check_rate_limit
)

# Import existing pipeline components
try:
    from pipeline import (
        create_pipeline, process_medical_form, PipelineConfig, PipelineResult
    )
    PIPELINE_AVAILABLE = True
except ImportError:
    PIPELINE_AVAILABLE = False

from progress_tracker import progress_tracker, ProgressCallback, ProgressStage
from hipaa_compliance import validate_hipaa_config, log_phi_access, HIPAAValidator

router = APIRouter(prefix="/api/secure", tags=["Secure Medical Forms"])

logger = logging.getLogger(__name__)

@router.post("/process-complete")
async def secure_process_complete(
    request: Request,
    file: UploadFile = Depends(validate_file_upload),
    method: str = Query("openai", description="Processing method: 'openai', 'auto', or 'legacy'"),
    output_format: str = Query("both", description="Output format: 'mnr', 'ash', or 'both'"),
    enhanced: bool = Query(True, description="Use enhanced PDF filler"),
    session_id: Optional[str] = Depends(get_processing_session),
    use_optimized: bool = Query(True, description="Use optimized processing with caching"),
    current_user: User = Depends(require_file_processing_permission()),
    db: Session = Depends(get_db),
    _rate_check: bool = Depends(check_rate_limit)
):
    """
    Secure complete pipeline: Upload MNR -> Extract -> Generate Filled PDF
    Requires authentication and appropriate permissions
    """
    
    if not PIPELINE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Pipeline components not available")
    
    # Log file upload
    processing_log = await SecureFileProcessor.log_file_upload(
        db=db, user=current_user, request=request, file=file, session_id=session_id
    )
    
    # Initialize progress tracking
    progress_callback = None
    if session_id:
        progress_callback = ProgressCallback(session_id, progress_tracker)
        progress_tracker.update_progress(
            session_id, 
            ProgressStage.UPLOAD, 
            0.05, 
            f"File uploaded by {current_user.email}, preparing for processing"
        )
    
    processing_start_time = datetime.now(timezone.utc)
    
    try:
        # Update processing log with start time
        processing_log.processing_started = processing_start_time
        db.commit()
        
        # Create HIPAA-compliant pipeline configuration
        config_dict = {
            "extraction_method": method,
            "output_format": output_format,
            "enhanced_filling": enhanced,
            "save_intermediate": True,
            # HIPAA Compliance fields
            "user_id": current_user.id,
            "session_id": session_id,
            "user_email": current_user.email,
            "user_role": current_user.role.value,
            "processing_session": session_id,  # Link to progress tracking
            "audit_enabled": True,
            "phi_encryption": True
        }
        
        # Validate HIPAA compliance
        hipaa_validation = validate_hipaa_config(config_dict)
        if not hipaa_validation['is_compliant']:
            logger.error(f"HIPAA compliance validation failed: {hipaa_validation['errors']}")
            raise HTTPException(
                status_code=400, 
                detail=f"HIPAA compliance validation failed: {', '.join(hipaa_validation['errors'])}"
            )
        
        # Log any HIPAA warnings
        for warning in hipaa_validation['warnings']:
            logger.warning(f"🔒 HIPAA Warning: {warning}")
        
        # Log PHI access initiation
        log_phi_access(
            current_user.id, 
            current_user.email, 
            "phi_processing_initiated",
            {"file_name": file.filename, "session_id": session_id}
        )
        
        # Save uploaded file temporarily and also save original
        temp_file_path = None
        original_filename = None
        try:
            import tempfile
            import shutil
            from pathlib import Path
            
            # Create temporary file with correct extension
            file_ext = os.path.splitext(file.filename)[1].lower() if file.filename else '.pdf'
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
                temp_file_path = temp_file.name
                file_content = await file.read()
                temp_file.write(file_content)
            
            # Also save the original file in outputs directory for viewing
            OUTPUT_DIR = Path(__file__).parent / "outputs"
            OUTPUT_DIR.mkdir(exist_ok=True)
            
            # Generate a unique filename for the original
            original_filename = f"original_{os.urandom(4).hex()}_{file.filename}"
            original_path = OUTPUT_DIR / original_filename
            
            # Save the original file
            with open(original_path, 'wb') as f:
                f.write(file_content)
            
            # Process the medical form using the pipeline
            if output_format == "both":
                # Generate both MNR and ASH PDFs
                # First generate MNR
                config_mnr = config_dict.copy()
                config_mnr["output_format"] = "mnr"
                result_mnr = process_medical_form(
                    pdf_path=temp_file_path,
                    output_format="mnr",
                    extraction_method=method,
                    config=config_mnr
                )
                
                # Then generate ASH using the same extracted data
                if result_mnr.success and result_mnr.extraction_result:
                    config_ash = config_dict.copy()
                    config_ash["output_format"] = "ash"
                    # Use the already extracted data to avoid re-extraction
                    result_ash = process_medical_form(
                        pdf_path=temp_file_path,
                        output_format="ash",
                        extraction_method=method,
                        config=config_ash
                    )
                    
                    # Combine results - use MNR as primary
                    result = result_mnr
                    # Store both PDF paths
                    result.mnr_pdf = result_mnr.output_pdf
                    result.ash_pdf = result_ash.output_pdf if result_ash.success else None
                else:
                    result = result_mnr
            else:
                # Single format processing
                result = process_medical_form(
                    pdf_path=temp_file_path,
                    output_format=output_format,
                    extraction_method=method,
                    config=config_dict
                )
            
        finally:
            # Clean up temporary file
            if temp_file_path and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
        
        # Calculate processing time
        processing_time = int((datetime.now(timezone.utc) - processing_start_time).total_seconds() * 1000)
        
        # Prepare output files list
        output_files = []
        if result.output_pdf:
            output_files.append(result.output_pdf)
        
        # Log processing completion
        await SecureFileProcessor.log_file_processing(
            db=db,
            user=current_user,
            request=request,
            processing_log=processing_log,
            method=method,
            output_format=output_format,
            success=result.success,
            processing_time=processing_time,
            fields_extracted=result.fields_extracted,
            fields_filled=result.fields_filled,
            output_files=output_files
        )
        
        # Final progress update
        if session_id:
            progress_tracker.update_progress(
                session_id,
                ProgressStage.COMPLETED,
                1.0,
                f"Processing completed successfully by {current_user.email}"
            )
        
        # Get extracted data from results
        extracted_data = {}
        if result.extraction_result and result.extraction_result.data:
            extracted_data = result.extraction_result.data

        # Prepare response
        response_data = {
            "success": result.success,
            "message": f"Processing complete - {output_format.upper()} PDF generated",
            "extracted_data": extracted_data,
            "method_used": method,
            "output_format": output_format,
            "enhanced_filling": enhanced,
            "processing_time": processing_time,
            "fields_extracted": result.fields_extracted,
            "fields_filled": result.fields_filled,
            "cost": result.total_cost or 0.0,
            "session_id": session_id,
            "processed_by": {
                "user_id": current_user.id,
                "email": current_user.email,
                "role": current_user.role.value
            },
            # Add original file information
            "original_filename": original_filename,
            "original_file_url": f"/api/secure/download/{original_filename}" if original_filename else None
        }
        
        # Add file URLs if files were generated
        if result.output_pdf:
            filename = os.path.basename(result.output_pdf)
            if output_format.lower() == "mnr":
                response_data["mnr_pdf_url"] = f"/api/secure/download/{filename}"
                response_data["pdf_url"] = response_data["mnr_pdf_url"]  # Backward compatibility
            elif output_format.lower() == "ash":
                response_data["ash_pdf_url"] = f"/api/secure/download/{filename}"
                response_data["pdf_url"] = response_data["ash_pdf_url"]  # Backward compatibility
            else:  # both formats 
                # Check if we have both PDFs
                if hasattr(result, 'mnr_pdf') and result.mnr_pdf:
                    mnr_filename = os.path.basename(result.mnr_pdf)
                    response_data["mnr_pdf_url"] = f"/api/secure/download/{mnr_filename}"
                    response_data["pdf_url"] = response_data["mnr_pdf_url"]  # Default to MNR
                
                if hasattr(result, 'ash_pdf') and result.ash_pdf:
                    ash_filename = os.path.basename(result.ash_pdf)
                    response_data["ash_pdf_url"] = f"/api/secure/download/{ash_filename}"
                
                # Fallback if attributes not set
                if "mnr_pdf_url" not in response_data:
                    response_data["mnr_pdf_url"] = f"/api/secure/download/{filename}"
                    response_data["pdf_url"] = response_data["mnr_pdf_url"]
        
        return response_data
        
    except Exception as e:
        logger.error(f"Processing failed for user {current_user.email}: {str(e)}")
        
        # Calculate processing time even for failures
        processing_time = int((datetime.now(timezone.utc) - processing_start_time).total_seconds() * 1000)
        
        # Log processing failure
        await SecureFileProcessor.log_file_processing(
            db=db,
            user=current_user,
            request=request,
            processing_log=processing_log,
            method=method,
            output_format=output_format,
            success=False,
            processing_time=processing_time,
            error_details=str(e)
        )
        
        # Update progress with failure
        if session_id:
            progress_tracker.update_progress(
                session_id,
                ProgressStage.FAILED,
                0.0,
                f"Processing failed: {str(e)}"
            )
        
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@router.get("/download/{filename}")
async def secure_download_file(
    filename: str,
    request: Request,
    current_user: User = Depends(require_file_download_permission()),
    db: Session = Depends(get_db)
):
    """Secure file download with audit logging"""
    
    # Construct file path
    from pathlib import Path
    BASE_DIR = Path(__file__).parent
    OUTPUT_DIR = BASE_DIR / "outputs"
    file_path = OUTPUT_DIR / filename
    
    # Verify file exists and is safe
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    # Verify file is within allowed directory (security check)
    try:
        file_path.resolve().relative_to(OUTPUT_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied - invalid file path")
    
    # Log download
    await SecureFileProcessor.log_file_download(
        db=db,
        user=current_user,
        request=request,
        filename=filename,
        file_path=str(file_path)
    )
    
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/pdf"
    )

@router.post("/create-progress-session")
async def secure_create_progress_session(
    current_user: User = Depends(get_current_user)
):
    """Create a new progress tracking session (authenticated)"""
    session_id = progress_tracker.create_session()
    
    logger.info(f"Progress session {session_id} created for user {current_user.email}")
    
    return {
        "session_id": session_id,
        "created_by": current_user.email,
        "created_at": datetime.now(timezone.utc).isoformat()
    }

@router.get("/processing-history")
async def get_processing_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's file processing history"""
    
    from database import FileProcessingLog
    
    # Get processing logs for current user
    query = db.query(FileProcessingLog).filter(
        FileProcessingLog.user_id == current_user.id
    ).order_by(FileProcessingLog.upload_timestamp.desc())
    
    # Apply pagination
    logs = query.offset(skip).limit(limit).all()
    total = query.count()
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "logs": [
            {
                "id": log.id,
                "filename": log.original_filename,
                "file_size": log.file_size,
                "processing_method": log.processing_method,
                "output_format": log.output_format,
                "success": log.success,
                "processing_time": log.processing_time,
                "fields_extracted": log.fields_extracted,
                "fields_filled": log.fields_filled,
                "upload_timestamp": log.upload_timestamp,
                "processing_completed": log.processing_completed,
                "output_files": log.output_files
            }
            for log in logs
        ]
    }

@router.get("/stats")
async def get_user_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user processing statistics"""
    
    from database import FileProcessingLog
    from sqlalchemy import func, and_
    
    # Total files processed
    total_files = db.query(FileProcessingLog).filter(
        FileProcessingLog.user_id == current_user.id
    ).count()
    
    # Successful vs failed
    successful_files = db.query(FileProcessingLog).filter(
        and_(
            FileProcessingLog.user_id == current_user.id,
            FileProcessingLog.success == True
        )
    ).count()
    
    # This month's activity
    from datetime import datetime, timezone
    from dateutil.relativedelta import relativedelta
    
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    this_month = db.query(FileProcessingLog).filter(
        and_(
            FileProcessingLog.user_id == current_user.id,
            FileProcessingLog.upload_timestamp >= month_start
        )
    ).count()
    
    # Average processing time
    avg_time = db.query(func.avg(FileProcessingLog.processing_time)).filter(
        and_(
            FileProcessingLog.user_id == current_user.id,
            FileProcessingLog.success == True,
            FileProcessingLog.processing_time.isnot(None)
        )
    ).scalar()
    
    return {
        "user": {
            "email": current_user.email,
            "role": current_user.role.value,
            "member_since": current_user.created_at.isoformat()
        },
        "statistics": {
            "total_files_processed": total_files,
            "successful_processes": successful_files,
            "failed_processes": total_files - successful_files,
            "success_rate": round((successful_files / total_files * 100), 2) if total_files > 0 else 0,
            "this_month_activity": this_month,
            "average_processing_time_ms": round(avg_time, 2) if avg_time else None
        }
    }