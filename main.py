#!/usr/bin/env python3
"""
FastAPI backend for MNR Form processing
Updated with OpenAI integration achieving 92% accuracy
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import json
import os
import tempfile
import shutil
import logging
import asyncio
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path
from functools import lru_cache
import hashlib
import copy

# Import progress tracking
from progress_tracker import progress_tracker, ProgressCallback, ProgressStage

# Import modular pipeline components
try:
    from pipeline import (
        create_pipeline,
        process_medical_form,
        get_pipeline_capabilities,
        PipelineConfig,
        PipelineResult
    )
    PIPELINE_AVAILABLE = True
except ImportError as e:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.error(f"Pipeline components not available: {e}")
    PIPELINE_AVAILABLE = False

# Legacy components are not available in this installation
LEGACY_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============= OPTIMIZATION: Template Pre-loading =============
TEMPLATE_CACHE = {}
EXTRACTION_CACHE = {}  # Cache extraction results
CACHE_TTL = timedelta(hours=1)  # Cache time-to-live
PDF_METHOD_CACHE = {}  # Cache which PDF method works for each template

def preload_templates():
    """Pre-load PDF templates into memory at startup"""
    template_dir = Path(__file__).parent / "templates"
    templates = {
        "mnr": "mnr_form.pdf",
        "ash": "ash_medical_form.pdf"
    }
    
    for key, filename in templates.items():
        template_path = template_dir / filename
        if template_path.exists():
            try:
                with open(template_path, 'rb') as f:
                    TEMPLATE_CACHE[key] = f.read()
                    logger.info(f"✅ Pre-loaded template: {filename}")
            except Exception as e:
                logger.error(f"❌ Failed to pre-load template {filename}: {e}")
    
    return TEMPLATE_CACHE

def get_file_hash(file_content: bytes) -> str:
    """Generate hash of file content for caching"""
    return hashlib.md5(file_content).hexdigest()

@lru_cache(maxsize=10)
def get_cached_extraction(file_hash: str, method: str):
    """Get cached extraction result if available and not expired"""
    cache_key = f"{file_hash}_{method}"
    if cache_key in EXTRACTION_CACHE:
        cached_data, timestamp = EXTRACTION_CACHE[cache_key]
        if datetime.now() - timestamp < CACHE_TTL:
            logger.info(f"✅ Using cached extraction for {cache_key[:8]}...")
            return cached_data
    return None

def cache_extraction(file_hash: str, method: str, result: Any):
    """Cache extraction result"""
    cache_key = f"{file_hash}_{method}"
    EXTRACTION_CACHE[cache_key] = (result, datetime.now())
    logger.info(f"💾 Cached extraction for {cache_key[:8]}...")

app = FastAPI(
    title="MNR Form API", 
    version="1.0.0",
    description="Medical Necessity Review Form Processing API"
)

@app.on_event("startup")
async def startup_event():
    """Initialize application resources on startup"""
    logger.info("🚀 Starting MNR Form API...")
    
    # Pre-load templates
    preload_templates()
    
    # Initialize PDF method cache
    PDF_METHOD_CACHE["mnr"] = None  # Will be determined on first use
    PDF_METHOD_CACHE["ash"] = None  # Will be determined on first use
    
    logger.info("✅ Application startup complete")

# Environment-based CORS configuration
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8080")
CORS_ORIGINS = [
    FRONTEND_URL,
    "http://localhost",           # Docker frontend on port 80
    "http://localhost:80",        # Docker frontend explicit port
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:8080",
    "https://mnr-form-ai.netlify.app",  # Add your frontend domain
    "https://mnr-form-ai.vercel.app",   # Add your frontend domain
]

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Base paths for static files
BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
TEMPLATE_DIR = BASE_DIR / "templates"
CONFIG_DIR = BASE_DIR / "config"

# Create directories if they don't exist
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
TEMPLATE_DIR.mkdir(exist_ok=True)
CONFIG_DIR.mkdir(exist_ok=True)

class ProcessFormRequest(BaseModel):
    mnr_pdf_name: str
    extract_only: bool = False
    method: str = "openai"  # "openai" or "legacy"
    
class FormField(BaseModel):
    name: str
    value: Any
    field_type: str = "text"
    
class UpdateFormRequest(BaseModel):
    form_id: str
    fields: Dict[str, Any]

class FormResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    file_path: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    method_used: Optional[str] = None

@app.get("/")
async def root():
    if PIPELINE_AVAILABLE:
        capabilities = get_pipeline_capabilities()
        return {
            "message": "MNR Form Processing API with Modular Pipeline", 
            "version": "3.0.0",
            "architecture": "Modular Pipeline",
            "pipeline_status": capabilities,
            "features": {
                "modular_pipeline": PIPELINE_AVAILABLE,
                "legacy_compatibility": LEGACY_AVAILABLE,
                "supported_formats": ["MNR", "ASH"]
            }
        }
    else:
        return {
            "message": "MNR Form Processing API", 
            "version": "3.0.0",
            "error": "Pipeline components not available",
            "legacy_available": LEGACY_AVAILABLE
        }

@app.post("/api/upload-mnr", response_model=FormResponse)
async def upload_mnr_pdf(file: UploadFile = File(...)):
    """Upload an MNR file (PDF or image) for processing"""
    try:
        # Validate file type - support PDF and common image formats
        allowed_extensions = ['.pdf', '.jpeg', '.jpg', '.png', '.gif', '.bmp', '.tiff', '.webp']
        file_ext = '.' + file.filename.split('.')[-1].lower() if '.' in file.filename else ''
        
        if file_ext not in allowed_extensions:
            raise HTTPException(status_code=400, detail="Only PDF files and images (JPEG, PNG, GIF, BMP, TIFF, WebP) are allowed")
        
        # Save uploaded file
        file_path = UPLOAD_DIR / file.filename
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return FormResponse(
            success=True,
            message=f"File uploaded successfully",
            data={"filename": file.filename, "path": str(file_path)}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/extract-mnr", response_model=FormResponse)
async def extract_mnr_data(request: ProcessFormRequest):
    """Extract data from MNR PDF using modular pipeline"""
    try:
        mnr_pdf_path = UPLOAD_DIR / request.mnr_pdf_name
        
        if not mnr_pdf_path.exists():
            raise HTTPException(status_code=404, detail="MNR PDF not found")
        
        if PIPELINE_AVAILABLE:
            # Use modular pipeline for extraction
            logger.info(f"🚀 Processing with modular pipeline: {request.mnr_pdf_name}")
            
            # Configure pipeline for extraction only
            config = PipelineConfig(
                extraction_method=request.method.lower(),
                output_format="mnr",
                save_intermediate=False,
                include_metadata=True
            )
            
            # Create pipeline and extract data
            pipeline = create_pipeline(config.to_dict())
            result = pipeline._execute_extraction(str(mnr_pdf_path))
            
            if result.success:
                return FormResponse(
                    success=True,
                    message=f"Data extracted successfully with {result.method_used}",
                    data={"mnr_data": result.data},
                    metadata=result.metadata if hasattr(result, 'metadata') else None,
                    method_used=result.method_used
                )
            else:
                raise HTTPException(status_code=500, detail=f"Extraction failed: {result.error}")
        
        # Fallback to legacy if pipeline not available
        elif LEGACY_AVAILABLE:
            logger.info(f"🔧 Fallback to legacy processing: {request.mnr_pdf_name}")
            
            # Extract text using OCR
            ocr_text = extract_text_from_pdf(str(mnr_pdf_path))
            
            if not ocr_text:
                # Fallback to sample data if OCR fails
                sample_data = {
                    "Height": {"feet": 5, "inches": 2},
                    "Weight_lbs": 170,
                    "Primary_Care_Physician": "Dr Ayoub",
                    "Physician_Phone": "800-443-0815",
                    "Employer": "Retired",
                    "Under_Physician_Care": {"No": False, "Yes": True, "Conditions": "Shoulder"},
                    "Current_Health_Problems": "Need shoulder replacement",
                    "When_Began": "Nov/24",
                    "How_Happened": "Overtime usage/Fall",
                    "Treatment_Received": {
                        "Surgery": False, 
                        "Medications": True, 
                        "Physical_Therapy": False, 
                        "Chiropractic": False, 
                        "Massage": False, 
                        "Injections": False
                    },
                    "Pain_Level": {"Average_Past_Week": 7, "Worst_Past_Week": 9, "Current": 9},
                    "Symptoms_Past_Week_Percentage": {"71-80%": True},
                    "Pain_Medication": "Advil",
                    "Pregnant": {"No": True, "Yes": False},
                    "_metadata": {
                        "extraction_method": "Sample Data (OCR Failed)",
                        "accuracy_expected": "N/A"
                    }
                }
                
                return FormResponse(
                    success=True,
                    message="OCR not available, using sample data",
                    data={"mnr_data": sample_data},
                    method_used="sample"
                )
            
            # Parse OCR output
            extracted_data = parse_ocr_output(ocr_text)
            
            # Load template if available
            template_path = CONFIG_DIR / "patience_mnr_form_fields.json"
            if template_path.exists():
                template = load_json(str(template_path))
                mnr_data = merge_into_template(template, extracted_data)
            else:
                mnr_data = extracted_data
            
            # Add metadata
            mnr_data['_metadata'] = {
                'extraction_method': 'Legacy OCR',
                'accuracy_expected': '52%'
            }
            
            return FormResponse(
                success=True,
                message="Data extracted successfully with legacy OCR",
                data={"mnr_data": mnr_data},
                method_used="legacy"
            )
        
        # No processing method available
        raise HTTPException(
            status_code=500, 
            detail="No extraction methods available"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/map-to-ash", response_model=FormResponse)
async def map_mnr_to_ash_endpoint(mnr_data: Dict[str, Any]):
    """Map MNR data to ASH form format using modular pipeline"""
    try:
        if PIPELINE_AVAILABLE:
            # Use modular pipeline for mapping
            from pipeline import map_mnr_to_ash_format
            
            ash_data = map_mnr_to_ash_format(mnr_data)
            
            return FormResponse(
                success=True,
                message="Data mapped to ASH format successfully with modular pipeline",
                data={"ash_data": ash_data}
            )
        elif LEGACY_AVAILABLE:
            # Fallback to legacy mapping
            ash_data = map_mnr_to_ash(mnr_data)
            
            # Create ASH form using only MNR data
            ash_form_data = create_ash_from_mnr_only(ash_data)
            
            return FormResponse(
                success=True,
                message="Data mapped to ASH format successfully with legacy mapper",
                data={"ash_data": ash_form_data}
            )
        else:
            raise HTTPException(status_code=500, detail="No mapping methods available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate-pdf")
async def generate_filled_pdf(
    form_data: Dict[str, Any], 
    template: str = Query("mnr", description="Template type: 'mnr' or 'ash'"),
    enhanced: bool = Query(True, description="Use enhanced PDF filler")
):
    """Generate filled PDF from extracted form data"""
    try:
        # Determine template and output filename
        if template.lower() == "ash":
            template_path = TEMPLATE_DIR / "ash_medical_form.pdf"
            output_filename = f"ash_filled_{os.urandom(4).hex()}.pdf"
        else:
            # Default to MNR template
            template_path = TEMPLATE_DIR / "mnr_form.pdf"
            output_filename = f"mnr_filled_{os.urandom(4).hex()}.pdf"
        
        if not template_path.exists():
            raise HTTPException(status_code=404, detail=f"Template PDF not found: {template_path}")
        
        output_path = OUTPUT_DIR / output_filename
        
        # Use pipeline fillers
        if PIPELINE_AVAILABLE:
            logger.info("🚀 Using pipeline PDF filler")
            if template.lower() == "ash":
                from pipeline import fill_ash_pdf
                result = fill_ash_pdf(form_data, str(template_path), str(output_path))
                success = result.success
            else:
                from pipeline import fill_mnr_pdf
                result = fill_mnr_pdf(form_data, str(template_path), str(output_path))
                success = result.success
        else:
            logger.error("Pipeline components not available")
            success = False
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to fill PDF")
        
        return FileResponse(
            path=str(output_path),
            filename=output_filename,
            media_type="application/pdf"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/create-progress-session")
async def create_progress_session():
    """Create a new progress tracking session"""
    session_id = progress_tracker.create_session()
    return {"session_id": session_id}

@app.websocket("/ws/progress/{session_id}")
async def websocket_progress(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time progress updates"""
    await websocket.accept()
    
    try:
        progress_tracker.register_websocket(session_id, websocket)
        
        # Send current progress if session exists
        current_progress = progress_tracker.get_session_progress(session_id)
        if current_progress:
            # Send latest update
            updates = current_progress.get("updates", [])
            if updates:
                latest_update = updates[-1]
                await websocket.send_text(json.dumps(latest_update.to_dict()))
        
        # Keep connection alive
        while True:
            try:
                # Wait for ping or other messages
                await websocket.receive_text()
            except WebSocketDisconnect:
                break
    except WebSocketDisconnect:
        pass
    finally:
        progress_tracker.unregister_websocket(session_id)

@app.post("/api/process-complete")
async def process_complete_pipeline(
    file: UploadFile = File(...),
    method: str = Query("openai", description="Processing method: 'openai', 'auto', or 'legacy'"),
    output_format: str = Query("both", description="Output format: 'mnr', 'ash', or 'both'"),
    enhanced: bool = Query(True, description="Use enhanced PDF filler"),
    session_id: Optional[str] = Query(None, description="Progress tracking session ID"),
    use_optimized: bool = Query(True, description="Use optimized processing with caching")
):
    """Complete pipeline: Upload MNR -> Extract -> Generate Filled PDF using modular pipeline"""
    
    # Initialize progress tracking
    progress_callback = None
    if session_id:
        progress_callback = ProgressCallback(session_id, progress_tracker)
        progress_tracker.update_progress(
            session_id, 
            ProgressStage.UPLOAD, 
            0.05, 
            "File uploaded successfully, preparing for processing"
        )
    
    try:
        # Save uploaded file with original name for later reference
        original_filename = file.filename or f"uploaded_{os.urandom(4).hex()}"
        original_path = UPLOAD_DIR / original_filename
        
        # Save a temporary file for processing (preserve original extension)
        if '.' in original_filename and len(original_filename.split('.')) > 1:
            file_ext = '.' + original_filename.split('.')[-1].lower()
        else:
            # Default to .pdf if no extension detected
            file_ext = '.pdf'
        temp_path = UPLOAD_DIR / f"temp_{os.urandom(4).hex()}{file_ext}"
        
        with temp_path.open("wb") as buffer:
            content = file.file.read()
            buffer.write(content)
        
        # Also save with original name for side-by-side viewing
        with original_path.open("wb") as buffer:
            buffer.write(content)
        
        if progress_callback:
            progress_tracker.update_progress(
                session_id, 
                ProgressStage.UPLOAD, 
                0.1, 
                "File saved, initializing processing pipeline"
            )
        
        logger.info(f"🚀 Starting complete modular pipeline: method={method}, output={output_format}, enhanced={enhanced}")
        
        if PIPELINE_AVAILABLE:
            # Use modular pipeline for complete processing
            config = PipelineConfig(
                extraction_method=method.lower(),
                output_format=output_format.lower(),
                enhanced_filling=enhanced,
                save_intermediate=True,
                output_directory=str(OUTPUT_DIR),
                include_metadata=True
            )
            
            # Use optimized processor if enabled
            if use_optimized:
                try:
                    from optimized_processor import process_optimized
                    
                    # Read file content from temp file
                    with open(temp_path, 'rb') as f:
                        file_content = f.read()
                    
                    # Process with optimization and custom progress tracking
                    logger.info("⚡ Using optimized processor with caching and parallel processing")
                    
                    # Track extraction phase start
                    if progress_callback:
                        progress_callback.on_extraction_start(method)
                    
                    result = await process_optimized(
                        file_content,
                        method.lower(),
                        output_format.lower(),
                        config.to_dict(),
                        progress_callback  # Pass progress callback to avoid duplicate updates
                    )
                    
                    # Update progress for final stages only
                    if progress_callback and result.success:
                        # Mark PDF generation complete
                        progress_callback.on_pdf_generation_complete(
                            result.fields_filled or 0,
                            result.output_pdf or ""
                        )
                        
                        # Finalization
                        progress_callback.on_finalization_start()
                        
                except Exception as e:
                    logger.warning(f"⚠️ Optimized processing failed, falling back: {e}")
                    use_optimized = False  # Fall back to standard processing
            
            # Standard processing (fallback or if not using optimized)
            if not use_optimized:
                # Start processing with progress tracking for standard path
                if progress_callback:
                    progress_callback.on_extraction_start(method)
                
                # Process with modular pipeline
                if output_format.lower() == "both":
                    # Generate both MNR and ASH forms with SHARED extraction
                    logger.info("📄 Extracting once, then generating both MNR and ASH forms")
                    
                    # Step 1: Extract data ONCE
                    config_extract = copy.deepcopy(config)
                    config_extract.output_format = "mnr"  # Use MNR for extraction
                    
                    result = process_medical_form(
                        pdf_path=str(temp_path),
                        output_format="mnr",
                        extraction_method=method.lower(),
                        config=config_extract.to_dict()
                    )
                    
                    # Step 2: If extraction successful, generate ASH form using same data
                    if result.success and result.extraction_result:
                        logger.info("📄 Using extracted data to generate ASH form")
                        
                        # Generate ASH PDF using the already extracted data
                        from pipeline.json_processor import JSONProcessorOrchestrator
                        from pipeline.ash_pdf_filler import ASHPDFFiller
                        import copy as copy_module
                        
                        try:
                            # Process data for ASH format
                            json_processor = JSONProcessorOrchestrator()
                            ash_processing = json_processor.full_pipeline(
                                raw_data=result.extraction_result.data,
                                output_format="ash"
                            )
                            
                            if ash_processing.success:
                                # Generate ASH PDF
                                ash_filler = ASHPDFFiller()
                                ash_template = os.path.join(os.path.dirname(__file__), "templates", "ash_medical_form.pdf")
                                ash_output = os.path.join(config.output_directory, f"ash_form_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
                                
                                ash_result = ash_filler.fill_pdf(ash_processing.data, ash_template, ash_output)
                                
                                if ash_result.success:
                                    # Add ASH info to result
                                    result.ash_pdf = ash_output
                                    result.ash_filename = os.path.basename(ash_output)
                                    result.mnr_filename = os.path.basename(result.output_pdf) if result.output_pdf else None
                                    logger.info(f"✅ Both forms generated successfully")
                        except Exception as e:
                            logger.warning(f"⚠️ ASH generation failed: {e}")
                            # Continue with just MNR form
                else:
                    # Single format generation
                    result = process_medical_form(
                        pdf_path=str(temp_path),
                        output_format=output_format.lower(),
                        extraction_method=method.lower(),
                        config=config.to_dict()
                    )
            
            # Update progress based on result
            if progress_callback:
                if result.extraction_result:
                    progress_callback.on_extraction_complete(
                        result.fields_extracted or 0,
                        result.total_cost or 0.0,
                        result.total_processing_time or 0.0
                    )
                    progress_callback.on_processing_start(output_format)
                    progress_callback.on_processing_complete()
                    progress_callback.on_pdf_generation_start(output_format)
                    
                if result.success:
                    progress_callback.on_pdf_generation_complete(
                        result.fields_filled or 0,
                        result.output_pdf or ""
                    )
                    
                    # Start finalization process
                    progress_callback.on_finalization_start()
            
            # Clean up temp file
            temp_path.unlink()
            
            if result.success:
                # Get the output filename for download
                output_filename = os.path.basename(result.output_pdf) if result.output_pdf else None
                
                # Progress update for response preparation
                if progress_callback:
                    progress_callback.on_finalization_progress(0.3, "Preparing download URLs")
                
                # Progress update for metadata preparation
                if progress_callback:
                    progress_callback.on_finalization_progress(0.7, "Preparing metadata")
                
                # Final progress update
                if progress_callback:
                    progress_callback.on_finalization_progress(1.0, "Finalizing response data")
                
                    response_data = {
                        "success": True,
                        "message": f"Processing complete - {output_format.upper()} PDF generated",
                        "extracted_data": result.extraction_result.data if result.extraction_result else None,
                        "method_used": result.extraction_result.method_used if result.extraction_result else "unknown",
                        "output_format": output_format,
                        "enhanced_filling": enhanced,
                        "pdf_url": f"/api/download/{urllib.parse.quote(output_filename)}" if output_filename else None,
                        "original_file_url": f"/api/uploads/{urllib.parse.quote(original_filename)}",
                        "original_filename": original_filename,
                        "metadata": result.pipeline_metadata,
                        "processing_time": result.total_processing_time,
                        "fields_extracted": result.fields_extracted,
                        "fields_filled": result.fields_filled,
                        "cost": result.total_cost
                    }
                    progress_callback.on_finalization_complete()
                    progress_callback.on_pipeline_complete(response_data)
                
                response = {
                    "success": True,
                    "message": f"Processing complete - {output_format.upper()} PDF generated with modular pipeline",
                    "extracted_data": result.extraction_result.data if result.extraction_result else None,
                    "method_used": result.extraction_result.method_used if result.extraction_result else "unknown",
                    "output_format": output_format,
                    "enhanced_filling": enhanced,
                    "pdf_url": f"/api/download/{urllib.parse.quote(output_filename)}" if output_filename else None,
                    "original_file_url": f"/api/uploads/{urllib.parse.quote(original_filename)}",
                    "original_filename": original_filename,
                    "metadata": result.pipeline_metadata,
                    "processing_time": result.total_processing_time,
                    "fields_extracted": result.fields_extracted,
                    "fields_filled": result.fields_filled,
                    "cost": result.total_cost,
                    "session_id": session_id
                }
                
                # Add both PDF URLs if both forms were generated
                if output_format.lower() == "both" and hasattr(result, 'ash_filename') and hasattr(result, 'mnr_filename'):
                    response["mnr_pdf_url"] = f"/api/download/{urllib.parse.quote(result.mnr_filename)}" if result.mnr_filename else None
                    response["ash_pdf_url"] = f"/api/download/{urllib.parse.quote(result.ash_filename)}" if result.ash_filename else None
                    response["pdf_url"] = response["mnr_pdf_url"]  # Keep MNR as default
                
                return response
            else:
                # Pipeline failed - update progress
                if progress_callback:
                    progress_callback.on_pipeline_error(
                        result.error or "Unknown pipeline error",
                        result.stage_reached.value if result.stage_reached else "unknown"
                    )
                
                raise HTTPException(
                    status_code=500, 
                    detail=f"Pipeline failed at {result.stage_reached.value}: {result.error}"
                )
        
        # Fallback to legacy processing if pipeline not available
        elif LEGACY_AVAILABLE:
            logger.info("🔧 Fallback to legacy complete pipeline")
            
            # Legacy extraction
            ocr_text = extract_text_from_pdf(str(temp_path))
            
            if ocr_text:
                extracted_data = parse_ocr_output(ocr_text)
                
                # Load template if available
                template_path_json = CONFIG_DIR / "patience_mnr_form_fields.json"
                if template_path_json.exists():
                    template = load_json(str(template_path_json))
                    extracted_data = merge_into_template(template, extracted_data)
                
                extracted_data['_metadata'] = {
                    'extraction_method': 'Legacy OCR',
                    'accuracy_expected': '52%'
                }
                method_used = "legacy"
            else:
                # Use sample data if OCR fails
                extracted_data = {
                    "Height": {"feet": 5, "inches": 8},
                    "Weight_lbs": 175,
                    "Primary_Care_Physician": "Dr. Smith",
                    "Current_Health_Problems": "Lower back pain",
                    "When_Began": "2024-01",
                    "Pain_Level": {"Current": 6},
                    "_metadata": {
                        "extraction_method": "Sample Data (OCR Failed)",
                        "accuracy_expected": "N/A"
                    }
                }
                method_used = "sample"
            
            # Prepare data for PDF generation
            if output_format.lower() == "ash":
                # Map to ASH format
                ash_mapped = map_mnr_to_ash(extracted_data)
                form_data = create_ash_from_mnr_only(ash_mapped)
                template_name = "ASH"
            else:
                # Use MNR format (default)
                form_data = extracted_data
                template_name = "MNR"
                output_format = "mnr"
            
            # Generate PDF
            if output_format.lower() == "ash":
                template_path = TEMPLATE_DIR / "ash_medical_form.pdf"
                output_filename = f"ash_complete_{os.urandom(4).hex()}.pdf"
            else:
                template_path = TEMPLATE_DIR / "mnr_form.pdf"
                output_filename = f"mnr_complete_{os.urandom(4).hex()}.pdf"
            
            output_path = OUTPUT_DIR / output_filename
            
            # Fill PDF - Use modular pipeline fillers if available
            if PIPELINE_AVAILABLE:
                if output_format.lower() == "ash":
                    from pipeline import fill_ash_pdf as pipeline_fill_ash
                    result = pipeline_fill_ash(form_data, str(template_path), str(output_path))
                    success = result.success
                else:
                    from pipeline import fill_mnr_pdf as pipeline_fill_mnr
                    result = pipeline_fill_mnr(form_data, str(template_path), str(output_path))
                    success = result.success
            else:
                # No legacy filling available
                success = False
                logger.error("No PDF filling methods available")
            
            # Clean up temp file
            temp_path.unlink()
            
            if not success:
                raise HTTPException(status_code=500, detail=f"Failed to generate {template_name} PDF")
            
            return {
                "success": True,
                "message": f"Processing complete - {template_name} PDF generated with legacy pipeline",
                "extracted_data": extracted_data,
                "method_used": method_used,
                "output_format": output_format,
                "enhanced_filling": enhanced,
                "pdf_url": f"/api/download/{urllib.parse.quote(output_filename)}",
                "metadata": extracted_data.get('_metadata') if extracted_data else None
            }
        else:
            raise HTTPException(status_code=500, detail="No processing methods available")
        
    except Exception as e:
        # Clean up on error
        if 'temp_path' in locals() and temp_path.exists():
            temp_path.unlink()
        
        # Update progress on error
        if progress_callback:
            progress_callback.on_pipeline_error(str(e), "unknown")
        
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/download/{filename}")
async def download_pdf(filename: str):
    """Download generated PDF"""
    file_path = OUTPUT_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/pdf",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET",
            "Access-Control-Allow-Headers": "*",
            "Cross-Origin-Resource-Policy": "cross-origin"
        }
    )

@app.get("/api/uploads/{filename}")
async def get_uploaded_file(filename: str):
    """Serve uploaded files (PDFs and images)"""
    file_path = UPLOAD_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Original file not found")
    
    # Determine media type based on file extension
    file_ext = filename.lower().split('.')[-1] if '.' in filename else ''
    
    media_type_map = {
        'pdf': 'application/pdf',
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'gif': 'image/gif',
        'bmp': 'image/bmp',
        'tiff': 'image/tiff',
        'tif': 'image/tiff',
        'webp': 'image/webp'
    }
    
    media_type = media_type_map.get(file_ext, 'application/octet-stream')
    
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type=media_type,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET",
            "Access-Control-Allow-Headers": "*",
            "Cross-Origin-Resource-Policy": "cross-origin"
        }
    )

@app.get("/api/forms")
async def list_forms():
    """List available form templates and processed forms"""
    try:
        templates = list(TEMPLATE_DIR.glob("*.pdf"))
        processed = list(OUTPUT_DIR.glob("*.pdf"))
        
        # Get pipeline capabilities if available
        if PIPELINE_AVAILABLE:
            pipeline_capabilities = get_pipeline_capabilities()
        else:
            pipeline_capabilities = {"pipeline_ready": False, "error": "Pipeline not available"}
        
        return {
            "templates": [f.name for f in templates],
            "processed": [f.name for f in processed],
            "system_status": {
                "pipeline_available": PIPELINE_AVAILABLE,
                "legacy_available": LEGACY_AVAILABLE,
                "pipeline_capabilities": pipeline_capabilities
            },
            "processing_methods": pipeline_capabilities.get("capabilities", {}).get("extraction_methods", {}) if PIPELINE_AVAILABLE else {
                "legacy": {
                    "available": LEGACY_AVAILABLE,
                    "accuracy": "52%", 
                    "description": "Traditional OCR with regex parsing"
                }
            },
            "architecture": "Modular Pipeline" if PIPELINE_AVAILABLE else "Legacy"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/processor-stats")
async def get_processor_stats():
    """Get pipeline and processor statistics"""
    try:
        if PIPELINE_AVAILABLE:
            # Get pipeline statistics
            pipeline = create_pipeline()
            stats = pipeline.get_statistics()
            
            return {
                "success": True,
                "stats": stats,
                "pipeline_status": pipeline.get_pipeline_status(),
                "message": "Pipeline statistics retrieved",
                "architecture": "Modular Pipeline"
            }
        else:
            return {
                "success": False,
                "error": "Pipeline not available",
                "architecture": "Legacy",
                "legacy_available": LEGACY_AVAILABLE
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def convert_frontend_to_backend_format(frontend_data: dict) -> dict:
    """Convert flat frontend form data to backend format expected by PDF filler"""
    backend_data = {}
    
    # Detect form type based on field names
    has_ash_fields = any(key.startswith(('patient_', 'pcp_', 'clinic_', 'condition_', 'subscriber_')) for key in frontend_data.keys())
    has_mnr_fields = any(key in ['primary_care_physician', 'physician_phone', 'pain_level_average'] for key in frontend_data.keys())
    
    if has_ash_fields and not has_mnr_fields:
        logger.info("🔍 Detected ASH form data - using direct mapping")
        # ASH forms use a flat structure - copy most fields directly
        # Only process phone field parsing
        for key, value in frontend_data.items():
            if key.endswith('_combined'):
                # Handle combined phone fields by parsing them
                if value:
                    # Parse phone number
                    digits = ''.join(filter(str.isdigit, str(value)))
                    if len(digits) >= 10:
                        # Full 10+ digit number
                        area_code = digits[:3]
                        phone = digits[3:10]
                    elif len(digits) >= 7:
                        # 7+ digit number without area code
                        area_code = ''
                        phone = digits[:7]
                    else:
                        # Less than 7 digits
                        area_code = ''
                        phone = digits
                    
                    # Map to separate fields based on combined field name
                    if key == 'patient_phone_combined':
                        backend_data['patient_area_code'] = area_code
                        backend_data['patient_phone'] = phone
                    elif key == 'pcp_phone_combined':
                        backend_data['pcp_area_code'] = area_code
                        backend_data['pcp_phone'] = phone
                    elif key == 'clinic_phone_combined':
                        backend_data['clinic_area_code'] = area_code
                        backend_data['clinic_phone'] = phone
                    elif key == 'fax_combined':
                        backend_data['fax_area_code'] = area_code
                        backend_data['fax_number'] = phone
            elif not key.endswith('_combined'):
                # Copy all non-combined fields directly
                backend_data[key] = value
        
        return backend_data
    
    logger.info("🔍 Detected MNR form data - using nested structure mapping")
    # MNR form fields (nested structure conversion)
    string_field_mapping = {
        'primary_care_physician': 'Primary_Care_Physician',
        'physician_phone': 'Physician_Phone',
        'employer': 'Employer',
        'job_description': 'Job_Description',
        'current_health_problems': 'Current_Health_Problems',
        'when_began': 'When_Began',
        'how_happened': 'How_Happened',
        'pain_medication': 'Pain_Medication',
        'health_history': 'Health_History',
        'todays_date': 'Date',
        'signature': 'Signature'
    }
    
    for frontend_key, backend_key in string_field_mapping.items():
        if frontend_data.get(frontend_key):
            backend_data[backend_key] = frontend_data[frontend_key]
    
    # Under physician care (convert string to nested object)
    if frontend_data.get('under_physician_care'):
        under_care_value = frontend_data['under_physician_care']
        backend_data['Under_Physician_Care'] = {
            'Yes': under_care_value == 'Yes',
            'No': under_care_value == 'No',
            'Conditions': frontend_data.get('conditions', '') if under_care_value == 'Yes' else None
        }
    
    # Pain levels (convert flat to nested with /10 format)
    pain_fields = ['pain_level_average', 'pain_level_worst', 'pain_level_current']
    if any(frontend_data.get(field) for field in pain_fields):
        backend_data['Pain_Level'] = {}
        
        if frontend_data.get('pain_level_average'):
            backend_data['Pain_Level']['Average_Past_Week'] = f"{frontend_data['pain_level_average']}/10"
        
        if frontend_data.get('pain_level_worst'):
            backend_data['Pain_Level']['Worst_Past_Week'] = f"{frontend_data['pain_level_worst']}/10"
        
        if frontend_data.get('pain_level_current'):
            backend_data['Pain_Level']['Current'] = f"{frontend_data['pain_level_current']}/10"
    
    # Daily activity interference (convert to string)
    if frontend_data.get('daily_activity_interference'):
        backend_data['Daily_Activity_Interference'] = str(frontend_data['daily_activity_interference'])
    
    # Symptoms past week (convert string to object)
    if frontend_data.get('symptoms_past_week'):
        backend_data['Symptoms_Past_Week_Percentage'] = {
            frontend_data['symptoms_past_week']: True
        }
    
    # Treatment received (convert array to object)
    if frontend_data.get('treatments_received'):
        backend_data['Treatment_Received'] = {}
        treatment_mapping = {
            'Surgery': 'Surgery',
            'Medications': 'Medications', 
            'Physical Therapy': 'Physical_Therapy',
            'Chiropractic': 'Chiropractic',
            'Massage': 'Massage',
            'Injections': 'Injections'
        }
        
        for treatment in frontend_data['treatments_received']:
            backend_key = treatment_mapping.get(treatment, treatment.replace(' ', '_'))
            backend_data['Treatment_Received'][backend_key] = True
        
        # Handle other treatment text
        if frontend_data.get('treatment_other_text'):
            backend_data['Treatment_Received']['Other'] = frontend_data['treatment_other_text']
    
    # New complaints (convert string + text to object)
    if frontend_data.get('new_complaints'):
        backend_data['New_Complaints'] = {
            'Yes': frontend_data['new_complaints'] == 'Yes',
            'No': frontend_data['new_complaints'] == 'No',
            'Explain': frontend_data.get('new_complaints_text', '') if frontend_data['new_complaints'] == 'Yes' else None
        }
    
    # Re-injuries (convert string + text to object)
    if frontend_data.get('re_injuries'):
        backend_data['Re_Injuries'] = {
            'Yes': frontend_data['re_injuries'] == 'Yes',
            'No': frontend_data['re_injuries'] == 'No',
            'Explain': frontend_data.get('re_injuries_text', '') if frontend_data['re_injuries'] == 'Yes' else None
        }
    
    # Type of treatments (convert array to object)
    if frontend_data.get('type_of_treatments'):
        backend_data['Helpful_Treatments'] = {}
        treatment_mapping = {
            'Acupuncture': 'Acupuncture',
            'Chinese Herbs': 'Chinese_Herbs',
            'Massage Therapy': 'Massage_Therapy',
            'Nutritional Supplements': 'Nutritional_Supplements',
            'Prescription Medication(s)': 'Prescription_Medications',
            'Physical Therapy': 'Physical_Therapy',
            'Rehab / Home Care': 'Rehab_Home_Care',
            'Spinal Adjustment / Manipulation': 'Spinal_Adjustment_Manipulation'
        }
        
        for treatment in frontend_data['type_of_treatments']:
            backend_key = treatment_mapping.get(treatment, treatment.replace(' ', '_').replace('/', '_'))
            backend_data['Helpful_Treatments'][backend_key] = True
        
        if frontend_data.get('type_of_treatments_other_text'):
            backend_data['Helpful_Treatments']['Other'] = frontend_data['type_of_treatments_other_text']
    
    # Activities (convert flat fields to array of objects)
    activities = []
    for i in range(1, 4):  # activities 1-3
        activity = frontend_data.get(f'activity_{i}')
        measurement = frontend_data.get(f'measurement_{i}')
        change = frontend_data.get(f'change_{i}')
        
        if activity or measurement or change:
            activities.append({
                'Activity': activity or '',
                'Measurement': measurement or '',
                'How_has_changed': change or ''
            })
    
    if activities:
        backend_data['Activities_Monitored'] = activities
    
    # Pain quality (convert array to object)
    if frontend_data.get('pain_quality'):
        backend_data['Pain_Quality'] = {}
        for quality in frontend_data['pain_quality']:
            backend_data['Pain_Quality'][quality] = True
    
    # Progress since acupuncture (convert array to object)
    if frontend_data.get('progress_acupuncture'):
        backend_data['Progress_Since_Acupuncture'] = {}
        for progress in frontend_data['progress_acupuncture']:
            backend_data['Progress_Since_Acupuncture'][progress] = True
    
    # Relief duration (convert flat fields to object)
    relief_fields = ['relief_duration_hours', 'relief_duration_days', 'relief_duration_hours_number', 'relief_duration_days_number']
    if any(frontend_data.get(field) for field in relief_fields):
        backend_data['Relief_Duration'] = {}
        
        if frontend_data.get('relief_duration_hours'):
            backend_data['Relief_Duration']['Hours'] = True
            if frontend_data.get('relief_duration_hours_number'):
                backend_data['Relief_Duration']['Hours_Number'] = int(frontend_data['relief_duration_hours_number'])
        
        if frontend_data.get('relief_duration_days'):
            backend_data['Relief_Duration']['Days'] = True
            if frontend_data.get('relief_duration_days_number'):
                backend_data['Relief_Duration']['Days_Number'] = int(frontend_data['relief_duration_days_number'])
    
    # Treatment course (convert array to object)
    if frontend_data.get('treatment_course'):
        backend_data['Upcoming_Treatment_Course'] = {}
        course_mapping = {
            '1/week': '1_per_week',
            '2/week': '2_per_week'
        }
        
        for course in frontend_data['treatment_course']:
            backend_key = course_mapping.get(course, course.replace('/', '_per_'))
            backend_data['Upcoming_Treatment_Course'][backend_key] = True
    
    # Height (convert flat fields to object)
    if frontend_data.get('height_feet') or frontend_data.get('height_inches'):
        backend_data['Height'] = {
            'feet': int(frontend_data['height_feet']) if frontend_data.get('height_feet') else None,
            'inches': int(frontend_data['height_inches']) if frontend_data.get('height_inches') else None
        }
    
    # Weight (convert to number)
    if frontend_data.get('weight'):
        try:
            backend_data['Weight_lbs'] = int(frontend_data['weight'])
        except (ValueError, TypeError):
            pass
    
    # Blood pressure (convert flat fields to object)
    if frontend_data.get('blood_pressure_systolic') or frontend_data.get('blood_pressure_diastolic'):
        backend_data['Blood_Pressure'] = {}
        if frontend_data.get('blood_pressure_systolic'):
            try:
                backend_data['Blood_Pressure']['systolic'] = int(frontend_data['blood_pressure_systolic'])
            except (ValueError, TypeError):
                pass
        if frontend_data.get('blood_pressure_diastolic'):
            try:
                backend_data['Blood_Pressure']['diastolic'] = int(frontend_data['blood_pressure_diastolic'])
            except (ValueError, TypeError):
                pass
    
    # Pregnant (convert string to object)
    if frontend_data.get('pregnant'):
        backend_data['Pregnant'] = {
            'Yes': frontend_data['pregnant'] == 'Yes',
            'No': frontend_data['pregnant'] == 'No'
        }
        
        if frontend_data.get('pregnancy_physician') and frontend_data['pregnant'] == 'Yes':
            backend_data['Pregnant']['Physician'] = frontend_data['pregnancy_physician']
    
    return backend_data

@app.post("/api/update-pdf")
async def update_pdf_with_corrections(
    corrected_data: dict,
    output_format: str = Query("both", description="Output format: 'mnr', 'ash', or 'both'"),
    enhanced: bool = Query(True, description="Use enhanced PDF filler")
):
    """Update and regenerate PDF with user corrections"""
    try:
        logger.info(f"🔄 Regenerating PDF with user corrections: format={output_format}, enhanced={enhanced}")
        logger.info(f"📥 Received frontend data keys: {list(corrected_data.keys())}")
        
        if not PIPELINE_AVAILABLE:
            raise HTTPException(status_code=503, detail="Pipeline not available")
        
        # Import pipeline components
        from pipeline.mnr_pdf_filler import fill_mnr_pdf
        from pipeline.ash_pdf_filler import fill_ash_pdf
        
        # Convert frontend flat structure to backend nested structure
        backend_format_data = convert_frontend_to_backend_format(corrected_data)
        logger.info(f"🔄 Converted to backend format with keys: {list(backend_format_data.keys())}")
        
        response = {
            "success": True,
            "output_format": output_format,
            "enhanced_filling": enhanced,
            "corrected_data": backend_format_data  # Return the converted data structure
        }
        
        if output_format.lower() == "both":
            # Generate both MNR and ASH forms
            logger.info("📄 Generating both MNR and ASH forms with corrections")
            
            # Generate MNR
            mnr_filename = f"corrected_{os.urandom(4).hex()}_mnr_filled_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            mnr_path = OUTPUT_DIR / mnr_filename
            mnr_template = TEMPLATE_DIR / "mnr_form.pdf"
            
            mnr_result = fill_mnr_pdf(
                data=backend_format_data,
                template_path=str(mnr_template),
                output_path=str(mnr_path)
            )
            
            # Generate ASH (map data to ASH format first)
            from pipeline.json_processor import ASHJSONMapper
            ash_mapper = ASHJSONMapper()
            ash_data_result = ash_mapper.process(backend_format_data)
            
            ash_filename = f"corrected_{os.urandom(4).hex()}_ash_filled_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            ash_path = OUTPUT_DIR / ash_filename
            ash_template = TEMPLATE_DIR / "ash_medical_form.pdf"
            
            if ash_data_result.success:
                ash_result = fill_ash_pdf(
                    data=ash_data_result.data,
                    template_path=str(ash_template),
                    output_path=str(ash_path)
                )
            else:
                ash_result = None
            
            if mnr_result.success and ash_result and ash_result.success:
                logger.info(f"✅ Both PDFs regenerated successfully")
                logger.info(f"📊 MNR fields filled: {mnr_result.fields_filled}, ASH fields filled: {ash_result.fields_filled}")
                
                response.update({
                    "message": "Both MNR and ASH PDFs updated successfully with corrections",
                    "mnr_pdf_url": f"/api/download/{urllib.parse.quote(mnr_filename)}",
                    "ash_pdf_url": f"/api/download/{urllib.parse.quote(ash_filename)}",
                    "pdf_url": f"/api/download/{urllib.parse.quote(mnr_filename)}",  # Default to MNR
                    "mnr_fields_filled": mnr_result.fields_filled,
                    "ash_fields_filled": ash_result.fields_filled,
                    "fields_filled": mnr_result.fields_filled  # Default to MNR
                })
            else:
                raise HTTPException(status_code=500, detail="Failed to generate one or both PDFs")
                
        elif output_format == "mnr":
            # Generate MNR only
            output_filename = f"corrected_{os.urandom(4).hex()}_mnr_filled_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            output_path = OUTPUT_DIR / output_filename
            template_path = TEMPLATE_DIR / "mnr_form.pdf"
            
            result = fill_mnr_pdf(
                data=backend_format_data,
                template_path=str(template_path),
                output_path=str(output_path)
            )
            
            if result.success:
                logger.info(f"✅ MNR PDF regenerated successfully: {output_filename}")
                logger.info(f"📊 Fields filled: {result.fields_filled}")
                response.update({
                    "message": "MNR PDF updated successfully with corrections",
                    "pdf_url": f"/api/download/{urllib.parse.quote(output_filename)}",
                    "fields_filled": result.fields_filled
                })
            else:
                raise HTTPException(status_code=500, detail=f"PDF generation failed: {result.error}")
                
        else:  # ASH format
            # Map data to ASH format
            from pipeline.json_processor import ASHJSONMapper
            ash_mapper = ASHJSONMapper()
            ash_data_result = ash_mapper.process(backend_format_data)
            
            if not ash_data_result.success:
                raise HTTPException(status_code=500, detail="Failed to map data to ASH format")
            
            output_filename = f"corrected_{os.urandom(4).hex()}_ash_filled_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            output_path = OUTPUT_DIR / output_filename
            template_path = TEMPLATE_DIR / "ash_medical_form.pdf"
            
            result = fill_ash_pdf(
                data=ash_data_result.data,
                template_path=str(template_path),
                output_path=str(output_path)
            )
            
            if result.success:
                logger.info(f"✅ ASH PDF regenerated successfully: {output_filename}")
                logger.info(f"📊 Fields filled: {result.fields_filled}")
                response.update({
                    "message": "ASH PDF updated successfully with corrections",
                    "pdf_url": f"/api/download/{urllib.parse.quote(output_filename)}",
                    "fields_filled": result.fields_filled
                })
            else:
                raise HTTPException(status_code=500, detail=f"PDF generation failed: {result.error}")
        
        return response
            
    except Exception as e:
        logger.error(f"❌ PDF update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint for Docker containers"""
    try:
        # Check if pipeline is available
        pipeline_status = "available" if PIPELINE_AVAILABLE else "unavailable"
        
        # Check directories exist
        directories_ok = all([
            UPLOAD_DIR.exists(),
            OUTPUT_DIR.exists(),
            TEMPLATE_DIR.exists()
        ])
        
        return {
            "status": "healthy",
            "pipeline_available": PIPELINE_AVAILABLE,
            "legacy_available": LEGACY_AVAILABLE,
            "directories_ok": directories_ok,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")

@app.delete("/api/cleanup")
async def cleanup_files():
    """Clean up temporary files"""
    try:
        # Clean upload directory
        for file in UPLOAD_DIR.glob("temp_*.pdf"):
            file.unlink()
        
        # Clean old output files (older than 1 hour)
        import time
        current_time = time.time()
        for file in OUTPUT_DIR.glob("*.pdf"):
            if current_time - file.stat().st_mtime > 3600:  # 1 hour
                file.unlink()
        
        return {"success": True, "message": "Cleanup completed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, reload=False)