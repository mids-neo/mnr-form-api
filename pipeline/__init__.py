#!/usr/bin/env python3
"""
Pipeline Package
================

Modular medical form processing pipeline with separate components for:
- OCR Extraction (OpenAI GPT-4o + Legacy OCR)
- JSON Processing and Validation
- MNR PDF Form Filling
- ASH PDF Form Filling
- Pipeline Orchestration
"""

from .ocr_extraction import (
    ExtractionResult,
    OpenAIExtractor,
    LegacyOCRExtractor, 
    ExtractionOrchestrator,
    extract_from_pdf,
    check_extraction_availability
)

from .json_processor import (
    ProcessingResult,
    MNRJSONValidator,
    ASHJSONMapper,
    JSONProcessorOrchestrator,
    validate_mnr_json,
    process_mnr_json,
    map_mnr_to_ash,
    load_json_file,
    save_json_file
)

from .mnr_pdf_filler import (
    FillingResult,
    MNRPDFFiller,
    fill_mnr_pdf,
    check_mnr_filler_availability
)

from .ash_pdf_filler import (
    ASHFillingResult,
    ASHPDFFiller,
    ASHFormFieldMapper,
    fill_ash_pdf,
    map_mnr_to_ash_format,
    check_ash_filler_availability
)

from .orchestrator import (
    PipelineResult,
    MedicalFormPipeline,
    PipelineConfig,
    create_pipeline,
    process_medical_form,
    get_pipeline_capabilities
)

__version__ = "1.0.0"
__author__ = "Medical Form Processing Team"

__all__ = [
    # OCR Extraction
    'ExtractionResult',
    'OpenAIExtractor',
    'LegacyOCRExtractor', 
    'ExtractionOrchestrator',
    'extract_from_pdf',
    'check_extraction_availability',
    
    # JSON Processing
    'ProcessingResult',
    'MNRJSONValidator',
    'ASHJSONMapper',
    'JSONProcessorOrchestrator',
    'validate_mnr_json',
    'process_mnr_json',
    'map_mnr_to_ash',
    'load_json_file',
    'save_json_file',
    
    # MNR PDF Filling
    'FillingResult',
    'MNRPDFFiller',
    'fill_mnr_pdf',
    'check_mnr_filler_availability',
    
    # ASH PDF Filling
    'ASHFillingResult',
    'ASHPDFFiller',
    'ASHFormFieldMapper',
    'fill_ash_pdf',
    'map_mnr_to_ash_format',
    'check_ash_filler_availability',
    
    # Pipeline Orchestration
    'PipelineResult',
    'MedicalFormPipeline',
    'PipelineConfig',
    'create_pipeline',
    'process_medical_form',
    'get_pipeline_capabilities'
]