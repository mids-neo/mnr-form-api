#!/usr/bin/env python3
"""
json_processor.py
=================

JSON Processing and Validation Pipeline Module
Handles data validation, transformation, and mapping between different form formats
"""

import json
import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from abc import ABC, abstractmethod

try:
    from pydantic import BaseModel, ValidationError, Field
    from pydantic.types import constr, conint, confloat
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class ProcessingResult:
    """Result of JSON processing"""
    success: bool
    data: Optional[Dict[str, Any]]
    error: Optional[str] = None
    validation_errors: Optional[List[str]] = None
    processing_time: float = 0.0
    method_used: str = "unknown"

# Pydantic models for validation (if available)
if PYDANTIC_AVAILABLE:
    class HeightModel(BaseModel):
        feet: Optional[conint(ge=0, le=10)] = None
        inches: Optional[conint(ge=0, le=11)] = None
    
    class BloodPressureModel(BaseModel):
        systolic: Optional[conint(ge=0, le=300)] = None
        diastolic: Optional[conint(ge=0, le=200)] = None
    
    class PainLevelModel(BaseModel):
        Average_Past_Week: Optional[constr(pattern=r'^\d+/10$')] = None
        Worst_Past_Week: Optional[constr(pattern=r'^\d+/10$')] = None
        Current: Optional[constr(pattern=r'^\d+/10$')] = None
    
    class YesNoModel(BaseModel):
        No: Optional[bool] = False
        Yes: Optional[bool] = False
    
    class UnderPhysicianCareModel(YesNoModel):
        Conditions: Optional[str] = None
    
    class TreatmentReceivedModel(BaseModel):
        Surgery: Optional[bool] = False
        Medications: Optional[bool] = False
        Physical_Therapy: Optional[bool] = False
        Chiropractic: Optional[bool] = False
        Massage: Optional[bool] = False
        Injections: Optional[bool] = False
        Other: Optional[str] = None
    
    class ActivityModel(BaseModel):
        Activity: Optional[str] = None
        Measurement: Optional[str] = None
        How_has_changed: Optional[str] = None
    
    class PercentageModel(BaseModel):
        """Model for percentage fields like symptoms"""
        pass  # Will be dynamically populated
    
    class HelpfulTreatmentsModel(BaseModel):
        Acupuncture: Optional[bool] = False
        Chinese_Herbs: Optional[bool] = False
        Massage_Therapy: Optional[bool] = False
        Nutritional_Supplements: Optional[bool] = False
        Prescription_Medications: Optional[bool] = False
        Physical_Therapy: Optional[bool] = False
        Rehab_Home_Care: Optional[bool] = False
        Spinal_Adjustment_Manipulation: Optional[bool] = False
        Other: Optional[str] = None
    
    class PainQualityModel(BaseModel):
        Sharp: Optional[bool] = False
        Throbbing: Optional[bool] = False
        Ache: Optional[bool] = False
        Burning: Optional[bool] = False
        Numb: Optional[bool] = False
        Tingling: Optional[bool] = False
    
    class ProgressModel(BaseModel):
        Excellent: Optional[bool] = False
        Good: Optional[bool] = False
        Fair: Optional[bool] = False
        Poor: Optional[bool] = False
        Worse: Optional[bool] = False
    
    class ReliefDurationModel(BaseModel):
        Hours: Optional[bool] = False
        Hours_Number: Optional[int] = None
        Days: Optional[bool] = False
        Days_Number: Optional[int] = None
    
    class TreatmentCourseModel(BaseModel):
        pass  # Will be dynamically populated
    
    class PregnantModel(YesNoModel):
        Weeks: Optional[int] = None
        Physician: Optional[str] = None
    
    class MNRFormModel(BaseModel):
        """Complete MNR form validation model"""
        # Core patient information
        Primary_Care_Physician: Optional[str] = None
        Physician_Phone: Optional[str] = None
        Employer: Optional[str] = None
        Job_Description: Optional[str] = None
        Under_Physician_Care: Optional[UnderPhysicianCareModel] = None
        
        # Health problems and history
        Current_Health_Problems: Optional[str] = None
        When_Began: Optional[str] = None
        How_Happened: Optional[str] = None
        Health_History: Optional[str] = None
        
        # Treatment information
        Treatment_Received: Optional[TreatmentReceivedModel] = None
        Helpful_Treatments: Optional[HelpfulTreatmentsModel] = None
        Progress_Since_Acupuncture: Optional[ProgressModel] = None
        Relief_Duration: Optional[ReliefDurationModel] = None
        Upcoming_Treatment_Course: Optional[Dict] = None
        
        # Pain information
        Pain_Level: Optional[PainLevelModel] = None
        Pain_Medication: Optional[str] = None
        Pain_Quality: Optional[PainQualityModel] = None
        Daily_Activity_Interference: Optional[str] = None
        
        # Physical measurements
        Height: Optional[HeightModel] = None
        Weight_lbs: Optional[conint(ge=0, le=1000)] = None
        Blood_Pressure: Optional[BloodPressureModel] = None
        
        # Activities and monitoring
        Activities_Monitored: Optional[List[ActivityModel]] = None
        Symptoms_Past_Week_Percentage: Optional[Dict] = None
        
        # Medical conditions
        Pregnant: Optional[PregnantModel] = None
        New_Complaints: Optional[YesNoModel] = None
        Re_Injuries: Optional[YesNoModel] = None
        
        # Form completion
        Date: Optional[str] = None
        Signature: Optional[str] = None

class BaseJSONProcessor(ABC):
    """Base class for JSON processors"""
    
    @abstractmethod
    def process(self, data: Dict[str, Any]) -> ProcessingResult:
        """Process JSON data"""
        pass
    
    @abstractmethod
    def validate(self, data: Dict[str, Any]) -> ProcessingResult:
        """Validate JSON data"""
        pass

class MNRJSONValidator(BaseJSONProcessor):
    """Validates MNR form JSON data"""
    
    def __init__(self):
        """Initialize MNR validator"""
        self.required_fields = [
            'Primary_Care_Physician',
            'Current_Health_Problems',
            'Pain_Level'
        ]
        
        self.field_types = {
            # Core patient information
            'Primary_Care_Physician': str,
            'Physician_Phone': str,
            'Employer': str,
            'Job_Description': str,
            'Under_Physician_Care': dict,
            
            # Health problems and history
            'Current_Health_Problems': str,
            'When_Began': str,
            'How_Happened': str,
            'Health_History': str,
            
            # Treatment information
            'Treatment_Received': dict,
            'Helpful_Treatments': dict,
            'Progress_Since_Acupuncture': dict,
            'Relief_Duration': dict,
            'Upcoming_Treatment_Course': dict,
            
            # Pain information
            'Pain_Level': dict,
            'Pain_Medication': str,
            'Pain_Quality': dict,
            'Daily_Activity_Interference': (str, int, float),
            
            # Physical measurements
            'Height': dict,
            'Weight_lbs': (int, float),
            'Blood_Pressure': dict,
            
            # Activities and monitoring
            'Activities_Monitored': list,
            'Symptoms_Past_Week_Percentage': dict,
            
            # Medical conditions
            'Pregnant': dict,
            'New_Complaints': dict,
            'Re_Injuries': dict,
            
            # Form completion
            'Date': str,
            'Signature': str
        }
        
        logger.info("🔍 MNR JSON Validator initialized")
    
    def validate(self, data: Dict[str, Any]) -> ProcessingResult:
        """Validate MNR JSON data"""
        start_time = datetime.now()
        errors = []
        
        try:
            logger.info("🔍 Validating MNR JSON data...")
            
            # Check if data is a dictionary
            if not isinstance(data, dict):
                return ProcessingResult(
                    success=False,
                    data=None,
                    error="Data must be a dictionary",
                    method_used="mnr_validator"
                )
            
            # Use Pydantic validation if available
            if PYDANTIC_AVAILABLE:
                try:
                    validated_data = MNRFormModel(**data)
                    validated_dict = validated_data.dict(exclude_none=False)
                    
                    processing_time = (datetime.now() - start_time).total_seconds()
                    
                    logger.info("✅ MNR JSON validation successful (Pydantic)")
                    return ProcessingResult(
                        success=True,
                        data=validated_dict,
                        processing_time=processing_time,
                        method_used="mnr_validator_pydantic"
                    )
                    
                except ValidationError as e:
                    errors.extend([f"Pydantic validation: {error['msg']} for field '{error['loc'][0]}'" for error in e.errors()])
            
            # Manual validation fallback
            self._validate_required_fields(data, errors)
            self._validate_field_types(data, errors)
            self._validate_pain_levels(data, errors)
            self._validate_height_weight(data, errors)
            self._validate_activities(data, errors)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            if errors:
                logger.warning(f"⚠️ MNR JSON validation completed with {len(errors)} errors")
                return ProcessingResult(
                    success=False,
                    data=data,
                    validation_errors=errors,
                    processing_time=processing_time,
                    method_used="mnr_validator_manual"
                )
            else:
                logger.info("✅ MNR JSON validation successful (Manual)")
                return ProcessingResult(
                    success=True,
                    data=data,
                    processing_time=processing_time,
                    method_used="mnr_validator_manual"
                )
                
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"❌ MNR JSON validation failed: {e}")
            
            return ProcessingResult(
                success=False,
                data=None,
                error=str(e),
                processing_time=processing_time,
                method_used="mnr_validator_failed"
            )
    
    def _validate_required_fields(self, data: Dict[str, Any], errors: List[str]):
        """Validate required fields"""
        for field in self.required_fields:
            if field not in data or not data[field]:
                errors.append(f"Missing required field: {field}")
    
    def _validate_field_types(self, data: Dict[str, Any], errors: List[str]):
        """Validate field types"""
        for field, expected_type in self.field_types.items():
            if field in data and data[field] is not None:
                if not isinstance(data[field], expected_type):
                    errors.append(f"Invalid type for {field}: expected {expected_type}, got {type(data[field])}")
    
    def _validate_pain_levels(self, data: Dict[str, Any], errors: List[str]):
        """Validate pain level formats"""
        pain_levels = data.get('Pain_Level', {})
        if isinstance(pain_levels, dict):
            for key, value in pain_levels.items():
                if value and not str(value).endswith('/10'):
                    errors.append(f"Pain level {key} should be in 'X/10' format, got: {value}")
    
    def _validate_height_weight(self, data: Dict[str, Any], errors: List[str]):
        """Validate height and weight data"""
        height = data.get('Height', {})
        if isinstance(height, dict):
            feet = height.get('feet')
            inches = height.get('inches')
            
            if feet is not None and (not isinstance(feet, int) or feet < 0 or feet > 10):
                errors.append(f"Invalid height feet: {feet} (should be 0-10)")
            
            if inches is not None and (not isinstance(inches, int) or inches < 0 or inches > 11):
                errors.append(f"Invalid height inches: {inches} (should be 0-11)")
        
        weight = data.get('Weight_lbs')
        if weight is not None and (not isinstance(weight, (int, float)) or weight < 0 or weight > 1000):
            errors.append(f"Invalid weight: {weight} (should be 0-1000 lbs)")
    
    def _validate_activities(self, data: Dict[str, Any], errors: List[str]):
        """Validate activities monitored"""
        activities = data.get('Activities_Monitored', [])
        if isinstance(activities, list):
            for i, activity in enumerate(activities):
                if not isinstance(activity, dict):
                    errors.append(f"Activity {i} should be a dictionary")
                    continue
                
                required_activity_fields = ['Activity', 'Measurement', 'How_has_changed']
                for field in required_activity_fields:
                    if field not in activity:
                        errors.append(f"Activity {i} missing field: {field}")
    
    def process(self, data: Dict[str, Any]) -> ProcessingResult:
        """Process and clean MNR JSON data"""
        # First validate
        validation_result = self.validate(data)
        
        if not validation_result.success:
            return validation_result
        
        try:
            # Clean and standardize data
            cleaned_data = self._clean_data(validation_result.data)
            
            # Add processing metadata
            cleaned_data['_processing_metadata'] = {
                'processor': 'MNR JSON Validator',
                'validation_method': validation_result.method_used,
                'processed_at': datetime.now().isoformat(),
                'validation_errors': validation_result.validation_errors or []
            }
            
            logger.info("✅ MNR JSON processing completed")
            
            return ProcessingResult(
                success=True,
                data=cleaned_data,
                processing_time=validation_result.processing_time,
                method_used="mnr_processor"
            )
            
        except Exception as e:
            logger.error(f"❌ MNR JSON processing failed: {e}")
            
            return ProcessingResult(
                success=False,
                data=None,
                error=str(e),
                method_used="mnr_processor_failed"
            )
    
    def _clean_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and standardize JSON data"""
        cleaned = data.copy()
        
        # Standardize pain levels
        pain_levels = cleaned.get('Pain_Level', {})
        if isinstance(pain_levels, dict):
            for key, value in pain_levels.items():
                if value and not str(value).endswith('/10'):
                    # Try to extract number and add /10
                    try:
                        number = int(str(value).split('/')[0])
                        pain_levels[key] = f"{number}/10"
                    except:
                        pass
        
        # Clean string fields
        string_fields = ['Primary_Care_Physician', 'Physician_Phone', 'Employer', 
                        'Current_Health_Problems', 'When_Began', 'How_Happened', 
                        'Pain_Medication', 'Health_History']
        
        for field in string_fields:
            if field in cleaned and cleaned[field]:
                cleaned[field] = str(cleaned[field]).strip()
        
        # Ensure boolean fields are proper booleans
        self._clean_boolean_structures(cleaned)
        
        return cleaned
    
    def _clean_boolean_structures(self, data: Dict[str, Any]):
        """Clean boolean structures like Yes/No fields"""
        boolean_structures = ['Under_Physician_Care', 'Treatment_Received', 'New_Complaints', 
                             'Re_Injuries', 'Helpful_Treatments', 'Pain_Quality', 
                             'Progress_Since_Acupuncture', 'Relief_Duration', 
                             'Upcoming_Treatment_Course', 'Pregnant']
        
        for structure in boolean_structures:
            if structure in data and isinstance(data[structure], dict):
                for key, value in data[structure].items():
                    if isinstance(value, bool):
                        continue
                    elif value in ['true', 'True', '1', 1]:
                        data[structure][key] = True
                    elif value in ['false', 'False', '0', 0]:
                        data[structure][key] = False

class ASHJSONMapper(BaseJSONProcessor):
    """Maps MNR JSON data to ASH format"""
    
    def __init__(self):
        """Initialize ASH mapper"""
        self.mnr_to_ash_mapping = {
            # Basic info mapping
            'Primary_Care_Physician': 'primary_care_physician',
            'Physician_Phone': 'physician_phone',
            'Current_Health_Problems': 'health_problems',
            'When_Began': 'when_began',
            'How_Happened': 'how_happened',
            'Pain_Medication': 'pain_medication',
            'Health_History': 'health_history',
            'Employer': 'employer',
            'Job_Description': 'job_description',
            'Date': 'date',
            'Signature': 'signature'
        }
        
        logger.info("🔄 ASH JSON Mapper initialized")
    
    def validate(self, data: Dict[str, Any]) -> ProcessingResult:
        """Validate that data can be mapped to ASH format"""
        if not isinstance(data, dict):
            return ProcessingResult(
                success=False,
                data=None,
                error="Data must be a dictionary",
                method_used="ash_mapper_validator"
            )
        
        return ProcessingResult(
            success=True,
            data=data,
            method_used="ash_mapper_validator"
        )
    
    def process(self, data: Dict[str, Any]) -> ProcessingResult:
        """Map MNR data to ASH format"""
        start_time = datetime.now()
        
        try:
            logger.info("🔄 Mapping MNR data to ASH format...")
            
            ash_data = {}
            
            # Map basic fields
            for mnr_field, ash_field in self.mnr_to_ash_mapping.items():
                if mnr_field in data and data[mnr_field]:
                    ash_data[ash_field] = data[mnr_field]
            
            # Map height
            height = data.get('Height', {})
            if isinstance(height, dict):
                feet = height.get('feet', '')
                inches = height.get('inches', '')
                if feet or inches:
                    ash_data['height'] = f"{feet}'{inches}\""
            
            # Map weight
            weight = data.get('Weight_lbs')
            if weight:
                ash_data['weight'] = f"{weight} lbs"
            
            # Map blood pressure
            bp = data.get('Blood_Pressure', {})
            if isinstance(bp, dict):
                systolic = bp.get('systolic', '')
                diastolic = bp.get('diastolic', '')
                if systolic or diastolic:
                    ash_data['blood_pressure'] = f"{systolic}/{diastolic}"
            
            # Map pain levels
            pain_levels = data.get('Pain_Level', {})
            if isinstance(pain_levels, dict):
                for mnr_key, ash_key in [
                    ('Average_Past_Week', 'average_pain'),
                    ('Worst_Past_Week', 'worst_pain'),
                    ('Current', 'current_pain')
                ]:
                    if mnr_key in pain_levels:
                        ash_data[ash_key] = pain_levels[mnr_key]
            
            # Map treatment received
            treatment = data.get('Treatment_Received', {})
            if isinstance(treatment, dict):
                treatment_list = []
                for key, value in treatment.items():
                    if value is True:
                        treatment_list.append(key.replace('_', ' '))
                if treatment_list:
                    ash_data['treatments_received'] = ', '.join(treatment_list)
            
            # Map activities (flatten structure)
            activities = data.get('Activities_Monitored', [])
            if isinstance(activities, list) and activities:
                activity_descriptions = []
                for activity in activities:
                    if isinstance(activity, dict):
                        desc_parts = []
                        if activity.get('Activity'):
                            desc_parts.append(f"Activity: {activity['Activity']}")
                        if activity.get('Measurement'):
                            desc_parts.append(f"Measurement: {activity['Measurement']}")
                        if activity.get('How_has_changed'):
                            desc_parts.append(f"Change: {activity['How_has_changed']}")
                        
                        if desc_parts:
                            activity_descriptions.append(' | '.join(desc_parts))
                
                if activity_descriptions:
                    ash_data['activities_monitored'] = '; '.join(activity_descriptions)
            
            # Map Daily Activity Interference
            daily_interference = data.get('Daily_Activity_Interference')
            if daily_interference:
                ash_data['daily_activity_interference'] = str(daily_interference)
            
            # Map Pain Quality (flatten to text)
            pain_quality = data.get('Pain_Quality', {})
            if isinstance(pain_quality, dict):
                quality_list = []
                for key, value in pain_quality.items():
                    if value is True:
                        quality_list.append(key.replace('_', ' '))
                if quality_list:
                    ash_data['pain_quality'] = ', '.join(quality_list)
            
            # Map Helpful Treatments (flatten to text)
            helpful_treatments = data.get('Helpful_Treatments', {})
            if isinstance(helpful_treatments, dict):
                helpful_list = []
                for key, value in helpful_treatments.items():
                    if value is True:
                        helpful_list.append(key.replace('_', ' '))
                
                other = helpful_treatments.get('Other')
                if other:
                    helpful_list.append(f"Other: {other}")
                
                if helpful_list:
                    ash_data['helpful_treatments'] = ', '.join(helpful_list)
            
            # Map Progress Since Acupuncture
            progress = data.get('Progress_Since_Acupuncture', {})
            if isinstance(progress, dict):
                progress_list = []
                for key, value in progress.items():
                    if value is True:
                        progress_list.append(key.replace('_', ' '))
                if progress_list:
                    ash_data['progress_since_acupuncture'] = ', '.join(progress_list)
            
            # Map Relief Duration
            relief = data.get('Relief_Duration', {})
            if isinstance(relief, dict):
                relief_parts = []
                if relief.get('Hours') and relief.get('Hours_Number'):
                    relief_parts.append(f"{relief['Hours_Number']} hours")
                elif relief.get('Hours'):
                    relief_parts.append("Hours")
                
                if relief.get('Days') and relief.get('Days_Number'):
                    relief_parts.append(f"{relief['Days_Number']} days")
                elif relief.get('Days'):
                    relief_parts.append("Days")
                
                if relief_parts:
                    ash_data['relief_duration'] = ', '.join(relief_parts)
            
            # Map Symptoms Past Week Percentage (flatten to text)
            symptoms = data.get('Symptoms_Past_Week_Percentage', {})
            if isinstance(symptoms, dict):
                symptom_list = []
                for key, value in symptoms.items():
                    if value is True:
                        symptom_list.append(key)
                if symptom_list:
                    ash_data['symptoms_percentage'] = ', '.join(symptom_list)
            
            # Map Pregnant status
            pregnant = data.get('Pregnant', {})
            if isinstance(pregnant, dict):
                if pregnant.get('Yes'):
                    weeks = pregnant.get('Weeks', '')
                    physician = pregnant.get('Physician', '')
                    ash_data['pregnant'] = f"Yes{f', {weeks} weeks' if weeks else ''}{f', Physician: {physician}' if physician else ''}"
                elif pregnant.get('No'):
                    ash_data['pregnant'] = "No"
            
            # Map New Complaints
            new_complaints = data.get('New_Complaints', {})
            if isinstance(new_complaints, dict):
                if new_complaints.get('Yes'):
                    explain = new_complaints.get('Explain', '')
                    ash_data['new_complaints'] = f"Yes{f': {explain}' if explain else ''}"
                elif new_complaints.get('No'):
                    ash_data['new_complaints'] = "No"
            
            # Map Re-Injuries
            re_injuries = data.get('Re_Injuries', {})
            if isinstance(re_injuries, dict):
                if re_injuries.get('Yes'):
                    explain = re_injuries.get('Explain', '')
                    ash_data['re_injuries'] = f"Yes{f': {explain}' if explain else ''}"
                elif re_injuries.get('No'):
                    ash_data['re_injuries'] = "No"
            
            # Map Upcoming Treatment Course
            treatment_course = data.get('Upcoming_Treatment_Course', {})
            if isinstance(treatment_course, dict):
                course_list = []
                for key, value in treatment_course.items():
                    if value is True:
                        course_list.append(key.replace('_', ' '))
                
                out_of_town = treatment_course.get('Out_of_Town_Dates')
                if out_of_town:
                    course_list.append(f"Out of town: {out_of_town}")
                
                if course_list:
                    ash_data['upcoming_treatment_course'] = ', '.join(course_list)
            
            # Map Under Physician Care
            under_care = data.get('Under_Physician_Care', {})
            if isinstance(under_care, dict):
                if under_care.get('Yes'):
                    conditions = under_care.get('Conditions', '')
                    ash_data['under_physician_care'] = f"Yes{f': {conditions}' if conditions else ''}"
                elif under_care.get('No'):
                    ash_data['under_physician_care'] = "No"
            
            # Add processing metadata
            ash_data['_mapping_metadata'] = {
                'mapped_from': 'MNR',
                'mapper': 'ASH JSON Mapper',
                'mapped_at': datetime.now().isoformat(),
                'original_fields_count': len(data),
                'mapped_fields_count': len([k for k in ash_data.keys() if not k.startswith('_')])
            }
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"✅ ASH mapping completed: {len(ash_data)} fields mapped")
            
            return ProcessingResult(
                success=True,
                data=ash_data,
                processing_time=processing_time,
                method_used="ash_mapper"
            )
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"❌ ASH mapping failed: {e}")
            
            return ProcessingResult(
                success=False,
                data=None,
                error=str(e),
                processing_time=processing_time,
                method_used="ash_mapper_failed"
            )

class JSONProcessorOrchestrator:
    """Orchestrates JSON processing operations"""
    
    def __init__(self):
        """Initialize JSON processor orchestrator"""
        self.processors = {
            'mnr_validator': MNRJSONValidator(),
            'ash_mapper': ASHJSONMapper()
        }
        
        logger.info("🎛️ JSON Processor Orchestrator initialized")
    
    def validate_mnr(self, data: Dict[str, Any]) -> ProcessingResult:
        """Validate MNR JSON data"""
        return self.processors['mnr_validator'].validate(data)
    
    def process_mnr(self, data: Dict[str, Any]) -> ProcessingResult:
        """Process and clean MNR JSON data"""
        return self.processors['mnr_validator'].process(data)
    
    def map_to_ash(self, mnr_data: Dict[str, Any]) -> ProcessingResult:
        """Map MNR data to ASH format"""
        return self.processors['ash_mapper'].process(mnr_data)
    
    def full_pipeline(self, raw_data: Dict[str, Any], output_format: str = "mnr") -> ProcessingResult:
        """Full JSON processing pipeline"""
        try:
            logger.info(f"🔄 Starting full JSON pipeline (output: {output_format})")
            
            # Step 1: Process MNR data
            mnr_result = self.process_mnr(raw_data)
            
            if not mnr_result.success:
                return mnr_result
            
            # Step 2: Map to ASH if requested
            if output_format.lower() == "ash":
                ash_result = self.map_to_ash(mnr_result.data)
                
                if not ash_result.success:
                    return ash_result
                
                # Combine metadata
                final_data = ash_result.data
                final_data['_pipeline_metadata'] = {
                    'steps_completed': ['mnr_processing', 'ash_mapping'],
                    'mnr_processing': mnr_result.data.get('_processing_metadata'),
                    'ash_mapping': ash_result.data.get('_mapping_metadata'),
                    'total_processing_time': mnr_result.processing_time + ash_result.processing_time
                }
                
                return ProcessingResult(
                    success=True,
                    data=final_data,
                    processing_time=mnr_result.processing_time + ash_result.processing_time,
                    method_used="full_pipeline_ash"
                )
            else:
                # Return processed MNR data
                mnr_result.data['_pipeline_metadata'] = {
                    'steps_completed': ['mnr_processing'],
                    'mnr_processing': mnr_result.data.get('_processing_metadata'),
                    'total_processing_time': mnr_result.processing_time
                }
                
                mnr_result.method_used = "full_pipeline_mnr"
                return mnr_result
                
        except Exception as e:
            logger.error(f"❌ Full JSON pipeline failed: {e}")
            
            return ProcessingResult(
                success=False,
                data=None,
                error=str(e),
                method_used="full_pipeline_failed"
            )

# Utility functions
def load_json_file(file_path: str) -> ProcessingResult:
    """Load and validate JSON from file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return ProcessingResult(
            success=True,
            data=data,
            method_used="json_file_loader"
        )
        
    except FileNotFoundError:
        return ProcessingResult(
            success=False,
            data=None,
            error=f"File not found: {file_path}",
            method_used="json_file_loader"
        )
    except json.JSONDecodeError as e:
        return ProcessingResult(
            success=False,
            data=None,
            error=f"Invalid JSON: {e}",
            method_used="json_file_loader"
        )
    except Exception as e:
        return ProcessingResult(
            success=False,
            data=None,
            error=str(e),
            method_used="json_file_loader"
        )

def save_json_file(data: Dict[str, Any], file_path: str) -> ProcessingResult:
    """Save JSON data to file"""
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return ProcessingResult(
            success=True,
            data={"file_path": file_path, "size": os.path.getsize(file_path)},
            method_used="json_file_saver"
        )
        
    except Exception as e:
        return ProcessingResult(
            success=False,
            data=None,
            error=str(e),
            method_used="json_file_saver"
        )

# Convenience functions
def validate_mnr_json(data: Dict[str, Any]) -> ProcessingResult:
    """Validate MNR JSON data"""
    validator = MNRJSONValidator()
    return validator.validate(data)

def process_mnr_json(data: Dict[str, Any]) -> ProcessingResult:
    """Process MNR JSON data"""
    validator = MNRJSONValidator()
    return validator.process(data)

def map_mnr_to_ash(data: Dict[str, Any]) -> ProcessingResult:
    """Map MNR data to ASH format"""
    mapper = ASHJSONMapper()
    return mapper.process(data)