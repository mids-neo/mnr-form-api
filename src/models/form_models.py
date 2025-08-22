"""
Form data models for MNR and ASH medical forms
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, date
from enum import Enum

# Base form field types
class FormFieldType(str, Enum):
    """Types of form fields"""
    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    SELECT = "select"
    TEXTAREA = "textarea"
    SIGNATURE = "signature"

class FormField(BaseModel):
    """Generic form field"""
    name: str
    value: Optional[Union[str, int, float, bool, List[str]]] = None
    field_type: FormFieldType
    required: bool = False
    options: Optional[List[str]] = None  # For select/radio fields
    validation_pattern: Optional[str] = None
    description: Optional[str] = None

# MNR Form Models
class MNRPatientInfo(BaseModel):
    """MNR form patient information section"""
    patient_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    member_id: Optional[str] = None
    group_number: Optional[str] = None
    phone_number: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None

class MNRProviderInfo(BaseModel):
    """MNR form provider information"""
    provider_name: Optional[str] = None
    clinic_name: Optional[str] = None
    provider_phone: Optional[str] = None
    provider_fax: Optional[str] = None
    provider_npi: Optional[str] = None
    provider_address: Optional[str] = None
    specialty: Optional[str] = None
    contact_person: Optional[str] = None

class MNRDiagnosisInfo(BaseModel):
    """MNR diagnosis and condition information"""
    primary_diagnosis: Optional[str] = None
    icd10_codes: List[str] = []
    secondary_diagnosis: Optional[str] = None
    onset_date: Optional[str] = None
    symptom_description: Optional[str] = None
    functional_limitations: Optional[str] = None
    pain_level: Optional[str] = None  # 0-10 scale
    pain_frequency: Optional[str] = None

class MNRTreatmentHistory(BaseModel):
    """MNR treatment history"""
    previous_treatments: List[str] = []
    current_medications: List[str] = []
    allergies: List[str] = []
    contraindications: List[str] = []
    treatment_outcomes: Optional[str] = None
    treatment_duration: Optional[str] = None

class MNRRequestedServices(BaseModel):
    """MNR requested services and treatments"""
    physical_therapy: Optional[bool] = None
    occupational_therapy: Optional[bool] = None
    speech_therapy: Optional[bool] = None
    chiropractic_care: Optional[bool] = None
    acupuncture: Optional[bool] = None
    massage_therapy: Optional[bool] = None
    other_services: List[str] = []
    frequency_requested: Optional[str] = None
    duration_requested: Optional[str] = None
    goals_objectives: Optional[str] = None

class MNRForm(BaseModel):
    """Complete MNR form data structure"""
    form_id: Optional[str] = None
    submission_date: Optional[datetime] = None
    patient_info: MNRPatientInfo = MNRPatientInfo()
    provider_info: MNRProviderInfo = MNRProviderInfo()
    diagnosis_info: MNRDiagnosisInfo = MNRDiagnosisInfo()
    treatment_history: MNRTreatmentHistory = MNRTreatmentHistory()
    requested_services: MNRRequestedServices = MNRRequestedServices()
    additional_fields: Dict[str, Any] = {}

# ASH Form Models
class ASHPatientInfo(BaseModel):
    """ASH form patient information (flattened structure)"""
    name: Optional[str] = None
    dob: Optional[str] = None
    gender: Optional[str] = None
    member_id: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None

class ASHProviderInfo(BaseModel):
    """ASH form provider information (flattened structure)"""
    provider_name: Optional[str] = None
    clinic_name: Optional[str] = None
    phone: Optional[str] = None
    fax: Optional[str] = None
    npi: Optional[str] = None

class ASHDiagnosisInfo(BaseModel):
    """ASH diagnosis information (flattened structure)"""
    diagnosis: Optional[str] = None
    icd10: Optional[str] = None
    onset_date: Optional[str] = None
    pain_level: Optional[str] = None

class ASHServices(BaseModel):
    """ASH services (flattened checkboxes)"""
    pt: Optional[bool] = None  # Physical Therapy
    ot: Optional[bool] = None  # Occupational Therapy
    st: Optional[bool] = None  # Speech Therapy
    chiro: Optional[bool] = None  # Chiropractic
    acupuncture: Optional[bool] = None
    massage: Optional[bool] = None

class ASHForm(BaseModel):
    """Complete ASH form data structure (flattened for PDF filling)"""
    patient: ASHPatientInfo = ASHPatientInfo()
    provider: ASHProviderInfo = ASHProviderInfo()
    diagnosis: ASHDiagnosisInfo = ASHDiagnosisInfo()
    services: ASHServices = ASHServices()
    additional_fields: Dict[str, Any] = {}

# Form Processing Models
class ProcessingConfig(BaseModel):
    """Configuration for form processing pipeline"""
    extraction_method: str = "auto"  # "auto", "openai", "legacy"
    output_format: str = "ash"  # "mnr", "ash", "both"
    enhanced_filling: bool = True
    save_intermediate: bool = True
    confidence_threshold: float = 0.7

class ExtractionResult(BaseModel):
    """Result from OCR/extraction process"""
    method_used: str
    confidence_score: Optional[float] = None
    extracted_text: Optional[str] = None
    extracted_fields: Dict[str, Any] = {}
    processing_time_ms: int
    warnings: List[str] = []
    errors: List[str] = []

class MappingResult(BaseModel):
    """Result from MNR to ASH mapping process"""
    source_format: str = "mnr"
    target_format: str = "ash"
    mapped_fields: Dict[str, Any] = {}
    unmapped_fields: List[str] = []
    confidence_scores: Dict[str, float] = {}
    mapping_warnings: List[str] = []

class PDFFillingResult(BaseModel):
    """Result from PDF filling process"""
    method_used: str  # "pymupdf", "pypdf2", "reportlab"
    fields_filled: int
    total_fields: int
    output_file_path: str
    file_size: int
    filling_warnings: List[str] = []
    filling_errors: List[str] = []

class ProcessingSession(BaseModel):
    """Complete processing session data"""
    session_id: str
    user_id: int
    original_filename: str
    file_hash: str
    upload_timestamp: datetime
    processing_config: ProcessingConfig
    extraction_result: Optional[ExtractionResult] = None
    mapping_result: Optional[MappingResult] = None
    pdf_filling_result: Optional[PDFFillingResult] = None
    final_output_files: List[str] = []
    total_processing_time_ms: int = 0
    status: str = "pending"  # "pending", "processing", "completed", "failed"
    error_message: Optional[str] = None

# Field Mapping Configuration
class FieldMapping(BaseModel):
    """Field mapping configuration between forms"""
    source_field: str
    target_field: str
    transformation: Optional[str] = None  # "uppercase", "lowercase", "date_format", etc.
    default_value: Optional[str] = None
    required: bool = False
    validation_rule: Optional[str] = None

class FormMappingConfig(BaseModel):
    """Complete mapping configuration between form types"""
    source_form: str  # "mnr"
    target_form: str  # "ash"
    field_mappings: List[FieldMapping]
    global_transformations: Dict[str, Any] = {}
    validation_rules: Dict[str, Any] = {}

# Form Templates
class FormTemplate(BaseModel):
    """Template definition for form types"""
    form_type: str  # "mnr", "ash"
    version: str
    fields: List[FormField]
    validation_schema: Dict[str, Any] = {}
    ui_layout: Dict[str, Any] = {}
    pdf_field_mappings: Dict[str, str] = {}  # Maps form fields to PDF field names

# Validation Models
class ValidationError(BaseModel):
    """Form validation error"""
    field_name: str
    error_type: str  # "required", "format", "range", etc.
    error_message: str
    suggested_value: Optional[str] = None

class ValidationResult(BaseModel):
    """Form validation result"""
    is_valid: bool
    errors: List[ValidationError] = []
    warnings: List[str] = []
    completeness_score: float = Field(..., ge=0, le=1)
    validated_fields: int
    total_fields: int