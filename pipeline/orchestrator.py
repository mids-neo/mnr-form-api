#!/usr/bin/env python3
"""
orchestrator.py
===============

Pipeline Orchestrator Module
Coordinates the entire medical form processing pipeline with configurable stages
"""

import json
import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, asdict
from enum import Enum

from .ocr_extraction import ExtractionOrchestrator, ExtractionResult
from .json_processor import JSONProcessorOrchestrator, ProcessingResult
from .mnr_pdf_filler import MNRPDFFiller, FillingResult
from .ash_pdf_filler import ASHPDFFiller, ASHFormFieldMapper, ASHFillingResult
from .optimized_ash_filler import OptimizedASHPDFFiller, OptimizedASHFillingResult

logger = logging.getLogger(__name__)

class PipelineStage(Enum):
    """Pipeline stages"""
    EXTRACTION = "extraction"
    JSON_PROCESSING = "json_processing"
    PDF_GENERATION = "pdf_generation"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class PipelineConfig:
    """Configuration for pipeline execution with HIPAA compliance"""
    # Extraction settings
    extraction_method: str = "auto"  # "auto", "openai", "legacy"
    extraction_fallback: bool = True
    
    # Processing settings
    output_format: str = "mnr"  # "mnr", "ash"
    validate_json: bool = True
    
    # PDF generation settings
    enhanced_filling: bool = True
    
    # Output settings
    save_intermediate: bool = True
    output_directory: str = "outputs"
    
    # Metadata settings
    include_metadata: bool = True
    
    # HIPAA Compliance settings
    user_id: Optional[int] = None
    session_id: Optional[str] = None
    user_email: Optional[str] = None
    user_role: Optional[str] = None
    processing_session: Optional[str] = None
    audit_enabled: bool = True
    phi_encryption: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return asdict(self)

@dataclass 
class PipelineResult:
    """Comprehensive result of pipeline execution"""
    success: bool
    stage_reached: PipelineStage
    
    # Input information
    input_pdf: Optional[str] = None
    
    # Stage results
    extraction_result: Optional[ExtractionResult] = None
    processing_result: Optional[ProcessingResult] = None
    filling_result: Optional[Union[FillingResult, ASHFillingResult]] = None
    
    # Output information
    output_pdf: Optional[str] = None
    intermediate_json: Optional[str] = None
    
    # Metrics
    total_processing_time: float = 0.0
    total_cost: float = 0.0
    fields_extracted: int = 0
    fields_filled: int = 0
    
    # Error information
    error: Optional[str] = None
    warnings: Optional[List[str]] = None
    
    # Configuration used
    config: Optional[PipelineConfig] = None
    
    # Metadata
    pipeline_metadata: Optional[Dict[str, Any]] = None

class MedicalFormPipeline:
    """Orchestrates the complete medical form processing pipeline with HIPAA compliance"""
    
    def __init__(self, config: Optional[PipelineConfig] = None):
        """Initialize pipeline with configuration"""
        self.config = config or PipelineConfig()
        
        # Initialize pipeline components
        self.extraction_orchestrator = ExtractionOrchestrator()
        self.json_orchestrator = JSONProcessorOrchestrator()
        self.mnr_filler = MNRPDFFiller()
        self.ash_filler = ASHPDFFiller()
        self.ash_mapper = ASHFormFieldMapper()
        
        # Pipeline state
        self.current_stage = PipelineStage.EXTRACTION
        self.warnings = []
        
        # HIPAA compliance validation
        if self.config.audit_enabled:
            self._validate_hipaa_config()
        
        logger.info("🎭 Medical Form Pipeline initialized with HIPAA compliance")
        logger.info(f"📋 User: {self.config.user_email or 'Unknown'} ({self.config.user_role or 'Unknown'})")
        logger.info(f"📋 Session: {self.config.session_id or 'None'}")
        
        # Only log non-sensitive config details
        safe_config = {k: v for k, v in self.config.to_dict().items() 
                      if k not in ['user_id', 'user_email', 'session_id']}
        logger.info(f"📋 Config: {safe_config}")
    
    def _validate_hipaa_config(self):
        """Validate HIPAA compliance requirements"""
        if not self.config.user_id:
            logger.warning("⚠️ HIPAA Warning: No user_id provided for PHI processing")
        if not self.config.session_id:
            logger.warning("⚠️ HIPAA Warning: No session_id provided for audit trail")
        if not self.config.user_email:
            logger.warning("⚠️ HIPAA Warning: No user_email provided for accountability")
        
        # Log HIPAA compliance status
        logger.info(f"🔒 HIPAA Compliance: User tracking {'✅' if self.config.user_id else '❌'}, "
                   f"Session tracking {'✅' if self.config.session_id else '❌'}, "
                   f"Audit logging {'✅' if self.config.audit_enabled else '❌'}")
    
    def _log_hipaa_audit(self, stage: str, action: str, details: Optional[Dict[str, Any]] = None):
        """Log HIPAA-compliant audit entry"""
        if not self.config.audit_enabled:
            return
            
        audit_entry = {
            'timestamp': datetime.now().isoformat(),
            'user_id': self.config.user_id,
            'user_email': self.config.user_email,
            'user_role': self.config.user_role,
            'session_id': self.config.session_id,
            'processing_session': self.config.processing_session,
            'pipeline_stage': stage,
            'action': action,
            'details': details or {}
        }
        
        # Log without sensitive data
        safe_audit = {k: v for k, v in audit_entry.items() 
                     if k not in ['user_id', 'user_email']}
        logger.info(f"🔒 HIPAA Audit: {safe_audit}")
    
    def process(self, pdf_path: str, template_path: Optional[str] = None) -> PipelineResult:
        """Execute the complete pipeline with HIPAA compliance"""
        start_time = datetime.now()
        
        # HIPAA Audit: Pipeline initiation
        self._log_hipaa_audit(
            "pipeline_start", 
            "initiated_phi_processing",
            {
                "input_file": os.path.basename(pdf_path),
                "output_format": self.config.output_format,
                "extraction_method": self.config.extraction_method
            }
        )
        
        try:
            logger.info(f"🚀 Starting HIPAA-compliant pipeline for: {os.path.basename(pdf_path)}")
            logger.info(f"🎯 Output format: {self.config.output_format}")
            logger.info(f"⚙️ Method: {self.config.extraction_method}")
            
            # Validate input
            if not os.path.exists(pdf_path):
                self._log_hipaa_audit("validation", "input_file_not_found", {"file": pdf_path})
                return PipelineResult(
                    success=False,
                    stage_reached=PipelineStage.FAILED,
                    input_pdf=pdf_path,
                    error=f"Input PDF not found: {pdf_path}",
                    config=self.config
                )
            
            # Initialize result
            result = PipelineResult(
                success=False,
                stage_reached=PipelineStage.EXTRACTION,
                input_pdf=pdf_path,
                config=self.config
            )
            
            # Stage 1: Extraction
            self._log_hipaa_audit("extraction", "started_phi_extraction", {"method": self.config.extraction_method})
            extraction_result = self._execute_extraction(pdf_path)
            result.extraction_result = extraction_result
            result.total_cost += extraction_result.cost
            
            if not extraction_result.success:
                self._log_hipaa_audit("extraction", "phi_extraction_failed", {"error": extraction_result.error})
                result.error = f"Extraction failed: {extraction_result.error}"
                result.stage_reached = PipelineStage.FAILED
                return self._finalize_result(result, start_time)
            
            result.fields_extracted = len(extraction_result.data) if extraction_result.data else 0
            self._log_hipaa_audit("extraction", "phi_extraction_completed", {
                "fields_extracted": result.fields_extracted,
                "cost": extraction_result.cost
            })
            logger.info(f"✅ Extraction completed: {result.fields_extracted} fields")
            
            # Stage 2: JSON Processing
            self.current_stage = PipelineStage.JSON_PROCESSING
            result.stage_reached = PipelineStage.JSON_PROCESSING
            
            processing_result = self._execute_json_processing(extraction_result.data)
            result.processing_result = processing_result
            
            if not processing_result.success:
                result.error = f"JSON processing failed: {processing_result.error}"
                result.stage_reached = PipelineStage.FAILED
                return self._finalize_result(result, start_time)
            
            logger.info("✅ JSON processing completed")
            
            # Save intermediate JSON if requested
            if self.config.save_intermediate:
                intermediate_path = self._save_intermediate_json(
                    processing_result.data, 
                    pdf_path
                )
                result.intermediate_json = intermediate_path
            
            # Stage 3: PDF Generation
            self.current_stage = PipelineStage.PDF_GENERATION
            result.stage_reached = PipelineStage.PDF_GENERATION
            
            filling_result = self._execute_pdf_generation(
                processing_result.data, 
                pdf_path, 
                template_path
            )
            result.filling_result = filling_result
            
            if not filling_result.success:
                result.error = f"PDF generation failed: {filling_result.error}"
                result.stage_reached = PipelineStage.FAILED
                return self._finalize_result(result, start_time)
            
            result.output_pdf = filling_result.output_path
            result.fields_filled = filling_result.fields_filled
            
            logger.info(f"✅ PDF generation completed: {result.fields_filled} fields filled")
            
            # Pipeline completed successfully
            result.success = True
            result.stage_reached = PipelineStage.COMPLETED
            result.warnings = self.warnings if self.warnings else None
            
            return self._finalize_result(result, start_time)
            
        except Exception as e:
            logger.error(f"❌ Pipeline execution failed: {e}")
            
            return PipelineResult(
                success=False,
                stage_reached=PipelineStage.FAILED,
                input_pdf=pdf_path,
                error=str(e),
                total_processing_time=(datetime.now() - start_time).total_seconds(),
                config=self.config,
                warnings=self.warnings if self.warnings else None
            )
    
    def _execute_extraction(self, pdf_path: str) -> ExtractionResult:
        """Execute OCR extraction stage"""
        logger.info(f"🔍 Stage 1: Extraction ({self.config.extraction_method})")
        
        return self.extraction_orchestrator.extract(
            pdf_path=pdf_path,
            method=self.config.extraction_method,
            fallback=self.config.extraction_fallback
        )
    
    def _execute_json_processing(self, raw_data: Dict[str, Any]) -> ProcessingResult:
        """Execute JSON processing and validation stage"""
        logger.info(f"📋 Stage 2: JSON Processing ({self.config.output_format})")
        
        return self.json_orchestrator.full_pipeline(
            raw_data=raw_data,
            output_format=self.config.output_format
        )
    
    def _execute_pdf_generation(self, processed_data: Dict[str, Any], 
                               pdf_path: str, template_path: Optional[str]) -> Union[FillingResult, ASHFillingResult]:
        """Execute PDF generation stage"""
        logger.info(f"📄 Stage 3: PDF Generation ({self.config.output_format})")
        
        # Determine template path
        if not template_path:
            if self.config.output_format.lower() == "ash":
                template_path = self._find_template("ash_medical_form.pdf")
            else:
                template_path = self._find_template("mnr_form.pdf")
        
        if not template_path or not os.path.exists(template_path):
            raise FileNotFoundError(f"Template not found for {self.config.output_format} format")
        
        # Generate output path
        output_path = self._generate_output_path(pdf_path)
        
        # Fill PDF based on format
        if self.config.output_format.lower() == "ash":
            return self.ash_filler.fill_pdf(processed_data, template_path, output_path)
        else:
            return self.mnr_filler.fill_pdf(processed_data, template_path, output_path)
    
    def _find_template(self, template_name: str) -> Optional[str]:
        """Find template file in various locations"""
        search_paths = [
            os.path.join(os.path.dirname(__file__), "..", "templates", template_name),
            os.path.join(os.getcwd(), "templates", template_name),
            os.path.join(os.path.dirname(__file__), "..", template_name),
            os.path.join(os.getcwd(), template_name),
            template_name  # Absolute path
        ]
        
        for path in search_paths:
            if os.path.exists(path):
                return os.path.abspath(path)
        
        self.warnings.append(f"Template not found: {template_name}")
        return None
    
    def _generate_output_path(self, input_path: str) -> str:
        """Generate output PDF path"""
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        output_filename = f"{base_name}_{self.config.output_format}_filled_{timestamp}.pdf"
        
        # Ensure output directory exists
        os.makedirs(self.config.output_directory, exist_ok=True)
        
        return os.path.join(self.config.output_directory, output_filename)
    
    def _save_intermediate_json(self, data: Dict[str, Any], input_path: str) -> str:
        """Save intermediate JSON data"""
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        json_filename = f"{base_name}_processed_{timestamp}.json"
        json_path = os.path.join(self.config.output_directory, json_filename)
        
        os.makedirs(self.config.output_directory, exist_ok=True)
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"💾 Intermediate JSON saved: {json_path}")
        return json_path
    
    def _finalize_result(self, result: PipelineResult, start_time: datetime) -> PipelineResult:
        """Finalize pipeline result with metadata"""
        result.total_processing_time = (datetime.now() - start_time).total_seconds()
        
        # Add pipeline metadata
        if self.config.include_metadata:
            result.pipeline_metadata = {
                'pipeline_version': '1.0.0',
                'execution_timestamp': datetime.now().isoformat(),
                'stages_completed': [
                    stage.value for stage in PipelineStage 
                    if stage.value != 'failed' and (
                        stage == result.stage_reached or 
                        list(PipelineStage).index(stage) < list(PipelineStage).index(result.stage_reached)
                    )
                ],
                'configuration': result.config.to_dict() if result.config else None,
                'system_info': {
                    'extraction_methods_available': list(self.extraction_orchestrator.extractors.keys()),
                    'pdf_filling_methods_available': {
                        'mnr': self.mnr_filler.is_available()[0],
                        'ash': self.ash_filler.is_available()[0]
                    }
                }
            }
        
        # Log final result
        if result.success:
            logger.info(f"🎉 Pipeline completed successfully!")
            logger.info(f"📊 Fields: {result.fields_extracted} extracted → {result.fields_filled} filled")
            logger.info(f"💰 Cost: ${result.total_cost:.4f}")
            logger.info(f"⏱️ Time: {result.total_processing_time:.2f}s")
            logger.info(f"📄 Output: {result.output_pdf}")
        else:
            logger.error(f"❌ Pipeline failed at {result.stage_reached.value}: {result.error}")
        
        return result
    
    def get_pipeline_status(self) -> Dict[str, Any]:
        """Get current pipeline status and capabilities"""
        extraction_methods = self.extraction_orchestrator.get_available_methods()
        
        return {
            'pipeline_ready': True,
            'current_stage': self.current_stage.value,
            'configuration': self.config.to_dict(),
            'capabilities': {
                'extraction_methods': extraction_methods,
                'output_formats': ['mnr', 'ash'],
                'pdf_filling_available': {
                    'mnr': self.mnr_filler.is_available()[0],
                    'ash': self.ash_filler.is_available()[0]
                }
            },
            'warnings': self.warnings if self.warnings else None
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get pipeline component statistics"""
        stats = {
            'extraction_stats': self.extraction_orchestrator.get_stats(),
            'pipeline_info': {
                'version': '1.0.0',
                'components': ['OCR Extraction', 'JSON Processing', 'PDF Filling'],
                'supported_formats': ['MNR', 'ASH']
            }
        }
        
        return stats

# Convenience functions
def create_pipeline(config: Optional[Dict[str, Any]] = None) -> MedicalFormPipeline:
    """Create a pipeline with optional configuration"""
    if config:
        pipeline_config = PipelineConfig(**config)
    else:
        pipeline_config = PipelineConfig()
    
    return MedicalFormPipeline(pipeline_config)

def process_medical_form(pdf_path: str, 
                        output_format: str = "mnr",
                        extraction_method: str = "auto",
                        template_path: Optional[str] = None,
                        config: Optional[Dict[str, Any]] = None) -> PipelineResult:
    """Process a medical form with simple interface"""
    
    # Create configuration
    if config:
        pipeline_config = PipelineConfig(**config)
    else:
        pipeline_config = PipelineConfig(
            output_format=output_format,
            extraction_method=extraction_method
        )
    
    # Create and run pipeline
    pipeline = MedicalFormPipeline(pipeline_config)
    return pipeline.process(pdf_path, template_path)

def get_pipeline_capabilities() -> Dict[str, Any]:
    """Get information about pipeline capabilities"""
    try:
        pipeline = create_pipeline()
        return pipeline.get_pipeline_status()
    except Exception as e:
        return {
            'pipeline_ready': False,
            'error': str(e)
        }