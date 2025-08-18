#!/usr/bin/env python3
"""
optimized_ash_mapper.py
=======================

Optimized ASH Form Field Mapper - Template-Driven Architecture
Uses the ASH PDF template as the single source of truth for field mappings
"""

import json
import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple, Set
from dataclasses import dataclass

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class FieldMappingResult:
    """Result of field mapping operation"""
    success: bool
    mapped_fields: Dict[str, Any]
    total_data_fields: int
    mapped_count: int
    unmapped_fields: List[str]
    invalid_pdf_fields: List[str]
    warnings: List[str]
    processing_time: float = 0.0

class OptimizedASHFormFieldMapper:
    """Template-driven ASH form field mapper for maximum performance and accuracy"""
    
    def __init__(self, template_path: str):
        """Initialize with PDF template as source of truth"""
        self.template_path = template_path
        self.template_fields: Set[str] = set()
        self.field_mapping: Dict[str, str] = {}
        self.reverse_mapping: Dict[str, str] = {}
        
        # Load template fields and build mappings
        self._load_template_fields()
        self._build_optimized_mapping()
        
        logger.info(f"🚀 Optimized ASH Mapper initialized with {len(self.field_mapping)} field mappings")
    
    def _load_template_fields(self) -> None:
        """Load all field names from PDF template"""
        if not PYMUPDF_AVAILABLE:
            raise ImportError("PyMuPDF is required for template field extraction")
        
        if not os.path.exists(self.template_path):
            raise FileNotFoundError(f"ASH PDF template not found: {self.template_path}")
        
        try:
            doc = fitz.open(self.template_path)
            
            # Extract all field names from template
            for page_num in range(len(doc)):
                page = doc[page_num]
                for field in page.widgets():
                    if field.field_name:
                        self.template_fields.add(field.field_name)
            
            doc.close()
            logger.info(f"📄 Loaded {len(self.template_fields)} template fields from PDF")
            
        except Exception as e:
            logger.error(f"❌ Failed to load template fields: {e}")
            raise
    
    def _build_optimized_mapping(self) -> None:
        """Build optimized 1:1 field mapping from data fields to PDF field names"""
        
        # Direct mapping from standardized data field names to exact PDF field names
        self.field_mapping = {
            # Patient Information Section
            'patient_name': 'Patient Name',
            'patient_dob': 'Birthdate', 
            'patient_id': 'Patient ID',
            'patient_phone': 'Patient Phone number',
            'patient_area_code': 'Patient Area code',
            'patient_address': 'Address',
            'patient_city_state_zip': 'CityStateZip',
            'patient_gender': 'Gender',
            
            # Insurance/Subscriber Section
            'subscriber_name': 'Subscriber Name',
            'subscriber_id': 'Subscriber ID',
            'health_plan': 'Health Plan',
            'employer': 'Employer',
            'group_number': 'Group',
            'primary_insurance': 'Primary',
            'secondary_insurance': 'Secondary',
            'work_related': 'Work Related',
            'auto_related': 'Auto Related',
            
            # Provider Information Section
            'pcp_name': 'PCP Name',
            'pcp_phone': 'PCP Phone number',
            'pcp_area_code': 'Area code for PCP phone number',
            'clinic_name': 'Clinic Name',
            'clinic_phone': 'Clinic Phone Number',
            'clinic_area_code': 'Area code for Clinic phone number',
            'treating_practitioner': 'Treating Practitioner',
            'clinic_address': 'Address_2',
            'clinic_city_state_zip': 'CityStateZip_2',
            'fax_area_code': 'Fax Area code',
            'fax_number': 'Fax number',
            
            # Condition Information Section
            'condition_1': 'Condition 1',
            'condition_2': 'Condition 2', 
            'condition_3': 'Condition 3',
            'condition_4': 'Condition 4',
            'icd_code_1': 'ICD CODE 1',
            'icd_code_2': 'ICD CODE 2',
            'icd_code_3': 'ICD CODE 3',
            'icd_code_4': 'ICD CODE 4',
            'office_visit_date': 'Office Visit date mmddyyyy',
            'last_office_visit': 'Last Office Visit date',
            'total_visits': 'Total number of Visits',
            
            # Chief Complaints Section - Set 1
            'chief_complaint_1': 'Chief Complaint(s)',
            'chief_complaint_1_location': 'Location',
            'chief_complaint_1_date': 'Date',
            'chief_complaint_1_pain_level': 'Pain Level',
            'chief_complaint_1_frequency': 'Frequency',
            'chief_complaint_1_cause': 'Cause of Condition/Injury',
            'chief_complaint_1_relief_duration': 'How long does relief last?',
            'chief_complaint_1_observation': 'Observation',
            'chief_complaint_1_tenderness': 'Tenderness to palpation 1-4',
            'chief_complaint_1_range_of_motion': 'Range of Motion',
            
            # Chief Complaints Section - Set 2
            'chief_complaint_2': 'Chief Complaint(s) 2',
            'chief_complaint_2_location': 'Location 2',
            'chief_complaint_2_date': 'Date 2',
            'chief_complaint_2_pain_level': 'Pain Level 2',
            'chief_complaint_2_frequency': 'Frequency 2',
            'chief_complaint_2_cause': 'Cause of Condition/Injury 2',
            'chief_complaint_2_relief_duration': 'How long does relief last? 2',
            'chief_complaint_2_observation': 'Observation 2',
            'chief_complaint_2_tenderness': 'Tenderness to palpation 2',
            'chief_complaint_2_range_of_motion': 'Range of Motion 2',
            
            # Chief Complaints Section - Set 3
            'chief_complaint_3': 'Chief Complaint(s) 3',
            'chief_complaint_3_location': 'Location 3',
            'chief_complaint_3_date': 'Date 3',
            'chief_complaint_3_pain_level': 'Pain Level 3',
            'chief_complaint_3_frequency': 'Frequency 3',
            'chief_complaint_3_cause': 'Cause of Condition/Injury 3',
            'chief_complaint_3_relief_duration': 'How long does relief last? 3',
            'chief_complaint_3_observation': 'Observation 3',
            'chief_complaint_3_tenderness': 'Tenderness to palpation 3',
            'chief_complaint_3_range_of_motion': 'Range of Motion 3',
            
            # Treatment Plan Section
            'new_pt_exam': 'New Pt Exam',
            'est_pt_exam': 'Est Pt Exam Date of Exam Findings for Chief Complaints Listed Below required',
            'exam_day': 'Date of Exam Findings for Chief Complaints Day',
            'exam_month': 'Date of Exam Findings for Chief Complaints Month', 
            'exam_year': 'Date of Exam Findings for Chief Complaints Year',
            'from_day': 'Day From',
            'from_month': 'Month',
            'from_year': 'Year From',
            'through_day': 'Through Day',
            'through_month': 'Through Month',
            'through_year': 'Through Year',
            'total_office_visits': 'Total  Office Visits',
            'total_therapies': 'Total  of Therapies for Requested Dates',
            'nj_acu_units': 'New Jersey Only  Acu CPT units requested per date of service',
            'nj_therapy_units': 'New Jersey Only Therapy units requested per date of service',
            
            # Therapy Types Section
            'hot_cold_packs': 'HotCold Packs 97010',
            'infrared': 'Infrared 97026',
            'massage': 'Massage 97124',
            'therapeutic_exercise': 'Therapeutic Exercise 97110',
            'ultrasound': 'Ultrasound 97035',
            'other_therapy': 'Other',
            'other_therapy_description': 'Other Do not enter acupuncture CPT codes 9781097814 as they are part of OVAcu above',
            'special_services': 'Other Special Services  Lab  Xray List CPT codes',
            
            # Treatment Response & Goals Section
            'response_to_treatment': 'Response to most recent Treatment Plan',
            'treatment_goals': 'Treatment Goals',
            'progress_measurement': 'How will you measure progress toward these goals',
            
            # Activities and Functional Outcomes Section
            'activity_1': 'Activity#0',
            'measurements_1': 'Measurements',
            'how_changed_1': 'How has it changed?',
            'activity_2': 'Activity#1',
            'measurements_2': 'Measurements#1',
            'how_changed_2': 'How has it changed?#1',
            
            # Functional Assessment Section
            'functional_tool_name_1': 'Functional Tool Name',
            'functional_body_area_1': 'Body Area/Condition',
            'functional_date_1': 'Body Area/Condition Date',
            'functional_score_1': 'Score',
            'functional_tool_name_2': 'Functional Tool Name 2',
            'functional_body_area_2': 'Body Area/Condition 2',
            'functional_date_2': 'Body Area/Condition Date#2',
            'functional_score_2': 'Score#2',
            
            # Medical Information Section
            'pain_medication_changes': 'Changes in Pain Medication Use eg name frequency amount dosage',
            'other_comments_1': 'Other Comments eg Responses to Care Barriers to Progress Patient Health History 1',
            'other_comments_2': 'Other Comments eg Responses to Care Barriers to Progress Patient Health History 2',
            'conditions': 'Conditions',
            
            # Medical Care Questions (Yes/No)
            'physician_care_yes': 'Yes Being Cared for By a Medical Physician',
            'physician_care_no': 'No Not Being Cared for By a Medical Physician',
            'pregnant_yes': 'Yes',
            'pregnant_no': 'No',
            'pregnant_weeks': '# of weeks pregnant',
            'physician_aware_pediatric': 'If patient is between 3 and 11 years old is their medical physician aware that they are receiving acupuncture for this condition',
            'pregnancy_practitioner_yes': 'Yes patient does have medical practitioner for pregnancy care',
            'pregnancy_practitioner_no': 'No patient does not have medical practitioner for pregnancy care',
            'required_pregnant': 'Required Is this patient pregnant',
            
            # Vital Signs Section
            'height': 'Height',
            'weight': 'Weight',
            'blood_pressure_1': 'Blood Pressure',
            'blood_pressure_2': 'Blood Pressure 2',
            'temperature': 'Temp',
            'bmi': 'BMI',
            'tobacco_use': 'Tobacco Use',
            
            # Traditional Medicine Section
            'tongue_signs': 'Tongue Signs',
            'pulse_signs_right': 'Rt',
            'pulse_signs_left': 'Lt',
            
            # Form Completion Section
            'signature_date': 'Date of Signature',
            'chronic_back_pain_attestation': 'I hereby attest this member meets the requirements for Chronic Low Back Pain as outlined'
        }
        
        # Build reverse mapping for lookup optimization
        self.reverse_mapping = {pdf_field: data_field for data_field, pdf_field in self.field_mapping.items()}
        
        # Validate mapping against template
        self._validate_mapping()
        
        logger.info(f"🔗 Built optimized mapping with {len(self.field_mapping)} field pairs")
    
    def _validate_mapping(self) -> None:
        """Validate that all mapped PDF fields exist in template"""
        invalid_fields = []
        valid_fields = []
        
        for data_field, pdf_field in self.field_mapping.items():
            if pdf_field in self.template_fields:
                valid_fields.append(pdf_field)
            else:
                invalid_fields.append(pdf_field)
        
        if invalid_fields:
            logger.warning(f"⚠️  {len(invalid_fields)} mapped PDF fields not found in template:")
            for field in invalid_fields[:10]:  # Show first 10
                logger.warning(f"   - '{field}'")
            if len(invalid_fields) > 10:
                logger.warning(f"   ... and {len(invalid_fields) - 10} more")
        
        coverage = len(valid_fields) / len(self.template_fields) * 100
        logger.info(f"📊 Template coverage: {len(valid_fields)}/{len(self.template_fields)} ({coverage:.1f}%)")
    
    def map_data_to_pdf_fields(self, input_data: Dict[str, Any]) -> FieldMappingResult:
        """Map input data to PDF field format with optimized performance"""
        start_time = datetime.now()
        
        mapped_fields = {}
        unmapped_fields = []
        warnings = []
        
        # Direct O(1) field mapping
        for data_field, value in input_data.items():
            # Skip metadata fields
            if data_field.startswith('_'):
                continue
            
            # Check if we have a mapping for this field
            if data_field in self.field_mapping:
                pdf_field = self.field_mapping[data_field]
                
                # Validate PDF field exists in template
                if pdf_field in self.template_fields:
                    # Convert value to string for PDF compatibility
                    pdf_value = self._format_value_for_pdf(value)
                    if pdf_value:  # Only include non-empty values
                        mapped_fields[pdf_field] = pdf_value
                else:
                    warnings.append(f"PDF field '{pdf_field}' not found in template")
            else:
                unmapped_fields.append(data_field)
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Validate for any PDF fields that don't exist
        invalid_pdf_fields = [pdf_field for pdf_field in mapped_fields.keys() 
                             if pdf_field not in self.template_fields]
        
        return FieldMappingResult(
            success=len(mapped_fields) > 0,
            mapped_fields=mapped_fields,
            total_data_fields=len([k for k in input_data.keys() if not k.startswith('_')]),
            mapped_count=len(mapped_fields),
            unmapped_fields=unmapped_fields,
            invalid_pdf_fields=invalid_pdf_fields,
            warnings=warnings,
            processing_time=processing_time
        )
    
    def _format_value_for_pdf(self, value: Any) -> str:
        """Format value for PDF field compatibility"""
        if value is None:
            return ""
        
        # Handle boolean values
        if isinstance(value, bool):
            return "Yes" if value else "No"
        
        # Handle string values
        if isinstance(value, str):
            return value.strip()
        
        # Handle numeric values
        if isinstance(value, (int, float)):
            return str(value)
        
        # Handle lists/arrays
        if isinstance(value, (list, tuple)):
            return ", ".join(str(v) for v in value if v)
        
        # Handle dictionaries
        if isinstance(value, dict):
            # For complex objects, try to extract meaningful values
            if 'value' in value:
                return str(value['value'])
            elif 'text' in value:
                return str(value['text'])
            else:
                return str(value)
        
        # Default conversion
        return str(value)
    
    def get_mapping_coverage_report(self) -> Dict[str, Any]:
        """Generate comprehensive mapping coverage report"""
        unmapped_template_fields = self.template_fields - set(self.field_mapping.values())
        
        return {
            'total_template_fields': len(self.template_fields),
            'mapped_fields': len(self.field_mapping),
            'coverage_percentage': len(self.field_mapping) / len(self.template_fields) * 100,
            'unmapped_template_fields': sorted(list(unmapped_template_fields)),
            'mapped_data_fields': sorted(list(self.field_mapping.keys())),
            'mapped_pdf_fields': sorted(list(self.field_mapping.values())),
            'template_path': self.template_path
        }
    
    def get_field_suggestions(self, data_field: str) -> List[str]:
        """Get suggestions for unmapped data fields"""
        suggestions = []
        data_field_lower = data_field.lower()
        
        # Find similar template fields
        for template_field in self.template_fields:
            template_lower = template_field.lower()
            
            # Exact substring match
            if data_field_lower in template_lower or template_lower in data_field_lower:
                suggestions.append(template_field)
            
            # Word-based similarity
            data_words = set(data_field_lower.replace('_', ' ').split())
            template_words = set(template_lower.replace('_', ' ').split())
            
            # If they share 50% of words, suggest it
            if data_words and template_words:
                intersection = data_words & template_words
                if len(intersection) / max(len(data_words), len(template_words)) >= 0.5:
                    suggestions.append(template_field)
        
        return sorted(list(set(suggestions)))

# Convenience function for external use
def create_optimized_ash_mapper(template_path: str = "templates/ash_medical_form.pdf") -> OptimizedASHFormFieldMapper:
    """Create an optimized ASH form field mapper"""
    return OptimizedASHFormFieldMapper(template_path)