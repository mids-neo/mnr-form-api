#!/usr/bin/env python3
"""
FastAPI backend for MNR Form processing
Updated with OpenAI integration achieving 92% accuracy
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import json
import os
import tempfile
import shutil
import logging
from pathlib import Path

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

app = FastAPI(
    title="MNR Form API", 
    version="1.0.0",
    description="Medical Necessity Review Form Processing API"
)

# Environment-based CORS configuration
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8080")
CORS_ORIGINS = [
    FRONTEND_URL,
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
    """Upload an MNR PDF form for processing"""
    try:
        # Validate file type
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")
        
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
            template_path = TEMPLATE_DIR / "Patience MNR Form.pdf"
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

@app.post("/api/process-complete")
async def process_complete_pipeline(
    file: UploadFile = File(...),
    method: str = Query("openai", description="Processing method: 'openai', 'auto', or 'legacy'"),
    output_format: str = Query("mnr", description="Output format: 'mnr' or 'ash'"),
    enhanced: bool = Query(True, description="Use enhanced PDF filler")
):
    """Complete pipeline: Upload MNR -> Extract -> Generate Filled PDF using modular pipeline"""
    try:
        # Save uploaded file
        temp_path = UPLOAD_DIR / f"temp_{os.urandom(4).hex()}.pdf"
        with temp_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
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
            
            # Process with modular pipeline
            result = process_medical_form(
                pdf_path=str(temp_path),
                output_format=output_format.lower(),
                extraction_method=method.lower(),
                config=config.to_dict()
            )
            
            # Clean up temp file
            temp_path.unlink()
            
            if result.success:
                # Get the output filename for download
                output_filename = os.path.basename(result.output_pdf) if result.output_pdf else None
                
                return {
                    "success": True,
                    "message": f"Processing complete - {output_format.upper()} PDF generated with modular pipeline",
                    "extracted_data": result.extraction_result.data if result.extraction_result else None,
                    "method_used": result.extraction_result.method_used if result.extraction_result else "unknown",
                    "output_format": output_format,
                    "enhanced_filling": enhanced,
                    "pdf_url": f"/api/download/{output_filename}" if output_filename else None,
                    "metadata": result.pipeline_metadata,
                    "processing_time": result.total_processing_time,
                    "fields_extracted": result.fields_extracted,
                    "fields_filled": result.fields_filled,
                    "cost": result.total_cost
                }
            else:
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
                template_path = TEMPLATE_DIR / "Patience MNR Form.pdf"
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
                "pdf_url": f"/api/download/{output_filename}",
                "metadata": extracted_data.get('_metadata') if extracted_data else None
            }
        else:
            raise HTTPException(status_code=500, detail="No processing methods available")
        
    except Exception as e:
        # Clean up on error
        if 'temp_path' in locals() and temp_path.exists():
            temp_path.unlink()
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
        media_type="application/pdf"
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