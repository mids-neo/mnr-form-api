"""
Validation dependencies for FastAPI routes
"""

from typing import Dict, Any
from fastapi import HTTPException, UploadFile, status

def validate_file_upload(file: UploadFile) -> UploadFile:
    """Validate uploaded file"""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided"
        )
    
    # Check file extension
    allowed_extensions = {'.pdf', '.jpg', '.jpeg', '.png'}
    file_ext = '.' + file.filename.split('.')[-1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {file_ext} not allowed. Allowed types: {allowed_extensions}"
        )
    
    return file

def validate_form_data(form_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate form data structure"""
    if not isinstance(form_data, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Form data must be a JSON object"
        )
    
    return form_data