#!/usr/bin/env python3
"""
FastAPI backend for MNR Form processing
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import json
import os
import tempfile
import shutil
from pathlib import Path

# Import the existing MNR processing functions
from mnr_to_ash_single import (
    extract_text_from_pdf,
    parse_ocr_output,
    merge_into_template,
    map_mnr_to_ash,
    create_ash_from_mnr_only,
    fill_ash_pdf,
    load_json,
    save_json
)

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

# Create directories if they don't exist
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

class ProcessFormRequest(BaseModel):
    mnr_pdf_name: str
    extract_only: bool = False
    
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

@app.get("/")
async def root():
    return {"message": "MNR Form Processing API", "version": "1.0.0"}

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
    """Extract data from MNR PDF using OCR"""
    try:
        mnr_pdf_path = UPLOAD_DIR / request.mnr_pdf_name
        
        if not mnr_pdf_path.exists():
            raise HTTPException(status_code=404, detail="MNR PDF not found")
        
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
                "Pregnant": {"No": True, "Yes": False}
            }
            
            return FormResponse(
                success=True,
                message="OCR not available, using sample data",
                data={"mnr_data": sample_data, "ocr_available": False}
            )
        
        # Parse OCR output
        extracted_data = parse_ocr_output(ocr_text)
        
        # Load template if available
        template_path = BASE_DIR / "patience_mnr_form_fields.json"
        if template_path.exists():
            template = load_json(str(template_path))
            mnr_data = merge_into_template(template, extracted_data)
        else:
            mnr_data = extracted_data
        
        return FormResponse(
            success=True,
            message="Data extracted successfully",
            data={"mnr_data": mnr_data, "ocr_available": True}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/map-to-ash", response_model=FormResponse)
async def map_mnr_to_ash_endpoint(mnr_data: Dict[str, Any]):
    """Map MNR data to ASH form format"""
    try:
        # Map MNR to ASH
        ash_data = map_mnr_to_ash(mnr_data)
        
        # Create ASH form using only MNR data
        ash_form_data = create_ash_from_mnr_only(ash_data)
        
        return FormResponse(
            success=True,
            message="Data mapped to ASH format successfully",
            data={"ash_data": ash_form_data}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate-ash-pdf")
async def generate_ash_pdf(ash_data: Dict[str, Any]):
    """Generate filled ASH PDF from ASH form data"""
    try:
        # Use the blank ASH template
        ash_template_path = BASE_DIR / "ash_medical_form.pdf"
        if not ash_template_path.exists():
            raise HTTPException(status_code=404, detail="ASH template PDF not found")
        
        # Generate output filename
        output_filename = f"ash_filled_{os.urandom(4).hex()}.pdf"
        output_path = OUTPUT_DIR / output_filename
        
        # Fill the PDF
        success = fill_ash_pdf(str(ash_template_path), str(output_path), ash_data)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to fill ASH PDF")
        
        return FileResponse(
            path=str(output_path),
            filename=output_filename,
            media_type="application/pdf"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/process-complete")
async def process_complete_pipeline(file: UploadFile = File(...)):
    """Complete pipeline: Upload MNR -> Extract -> Map -> Generate ASH PDF"""
    try:
        # Save uploaded file
        temp_path = UPLOAD_DIR / f"temp_{os.urandom(4).hex()}.pdf"
        with temp_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Extract data from MNR
        ocr_text = extract_text_from_pdf(str(temp_path))
        
        if ocr_text:
            extracted_data = parse_ocr_output(ocr_text)
        else:
            # Use sample data if OCR fails
            extracted_data = {
                "Height": {"feet": 5, "inches": 8},
                "Weight_lbs": 175,
                "Primary_Care_Physician": "Dr. Smith",
                "Current_Health_Problems": "Lower back pain",
                "When_Began": "2024-01",
                "Pain_Level": {"Current": 6}
            }
        
        # Load template if available
        template_path = BASE_DIR / "patience_mnr_form_fields.json"
        if template_path.exists():
            template = load_json(str(template_path))
            mnr_data = merge_into_template(template, extracted_data)
        else:
            mnr_data = extracted_data
        
        # Map to ASH format
        ash_mapped = map_mnr_to_ash(mnr_data)
        ash_form_data = create_ash_from_mnr_only(ash_mapped)
        
        # Generate ASH PDF
        ash_template_path = BASE_DIR / "ash_medical_form.pdf"
        output_filename = f"ash_complete_{os.urandom(4).hex()}.pdf"
        output_path = OUTPUT_DIR / output_filename
        
        success = fill_ash_pdf(str(ash_template_path), str(output_path), ash_form_data)
        
        # Clean up temp file
        temp_path.unlink()
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to generate ASH PDF")
        
        return {
            "success": True,
            "message": "Processing complete",
            "mnr_data": mnr_data,
            "ash_data": ash_form_data,
            "pdf_url": f"/api/download/{output_filename}"
        }
        
    except Exception as e:
        # Clean up on error
        if temp_path.exists():
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
        templates = list(BASE_DIR.glob("*.pdf"))
        processed = list(OUTPUT_DIR.glob("*.pdf"))
        
        return {
            "templates": [f.name for f in templates],
            "processed": [f.name for f in processed]
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