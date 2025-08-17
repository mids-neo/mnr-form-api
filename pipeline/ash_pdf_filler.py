#!/usr/bin/env python3
"""
ash_pdf_filler.py
=================

ASH PDF Form Filling Pipeline Module
Handles filling ASH (Acupuncture and Shiatsu Health) Medical forms with comprehensive field mapping
"""

import json
import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from abc import ABC, abstractmethod

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

try:
    from PyPDF2 import PdfReader, PdfWriter
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class ASHFillingResult:
    """Result of ASH PDF filling operation"""
    success: bool
    output_path: Optional[str] = None
    fields_filled: int = 0
    total_fields: int = 0
    error: Optional[str] = None
    processing_time: float = 0.0
    method_used: str = "unknown"
    warnings: Optional[List[str]] = None

class BaseASHPDFFiller(ABC):
    """Base class for ASH PDF filling operations"""
    
    @abstractmethod
    def fill_pdf(self, data: Dict[str, Any], template_path: str, output_path: str) -> ASHFillingResult:
        """Fill ASH PDF with data"""
        pass
    
    @abstractmethod
    def is_available(self) -> Tuple[bool, str]:
        """Check if filler is available"""
        pass

class ASHPDFFiller(BaseASHPDFFiller):
    """ASH PDF form filler with comprehensive field mapping"""
    
    def __init__(self):
        """Initialize ASH PDF filler"""
        self.blue = (0, 0, 1)  # Blue color for text
        self.ash_field_mapping = self._build_ash_field_mapping()
        
        # Determine best available method
        self.available_methods = []
        if PYMUPDF_AVAILABLE:
            self.available_methods.append('pymupdf')
        if PYPDF2_AVAILABLE:
            self.available_methods.append('pypdf2')
        if REPORTLAB_AVAILABLE:
            self.available_methods.append('reportlab')
        
        if not self.available_methods:
            raise ImportError("No PDF processing libraries available. Install PyMuPDF, PyPDF2, or ReportLab")
        
        logger.info(f"📄 ASH PDF Filler initialized with methods: {', '.join(self.available_methods)}")
    
    def _build_direct_field_mapping(self) -> Dict[str, List[str]]:
        """Build direct mapping from ASH data fields to form field names"""
        return {
            # Patient information
            'patient_name': ['Patient Name'],
            'patient_dob': ['Birthdate'],
            'patient_phone': ['Patient Phone number'],
            'patient_address': ['Address'],
            'employer': ['Employer'],
            'job_description': ['Group'],  # Map to available field
            
            # Physician information
            'primary_care_physician': ['PCP Name'],
            'physician_phone': ['PCP Phone number', 'Area code for PCP phone number'],
            
            # Health information
            'health_problems': ['Chief Complaint(s)', 'Condition 1', 'Chief Complaint(s) 2', 'Chief Complaint(s) 3'],
            'current_pain': ['Pain Level'],
            'average_pain': ['Pain Level 2'],
            'worst_pain': ['Pain Level 3'],
            'when_began': ['Date', 'Date 2', 'Date 3'],
            'how_happened': ['Cause of Condition/Injury', 'Cause of Condition/Injury 2', 'Cause of Condition/Injury 3'],
            
            # Physical measurements
            'height': ['Height'],
            'weight': ['Weight'],
            'blood_pressure': ['Blood Pressure', 'Blood Pressure 2'],
            
            # Medication and treatments
            'pain_medication': ['Changes in Pain Medication Use eg name frequency amount dosage'],
            'treatments_received': ['Other Comments eg Responses to Care Barriers to Progress Patient Health History 1'],
            'helpful_treatments': ['Other Comments eg Responses to Care Barriers to Progress Patient Health History 2'],
            
            # Activities (parse the activities_monitored field)
            'activities_monitored': ['Activity#0', 'Activity#1', 'Measurements', 'Measurements#1', 'How has it changed?', 'How has it changed?#1'],
            
            # Additional health information
            'daily_activity_interference': ['Frequency'],
            'pain_quality': ['Observation', 'Observation 2', 'Observation 3'],
            'progress_since_acupuncture': ['Response to most recent Treatment Plan'],
            'relief_duration': ['How long does relief last?', 'How long does relief last? 2', 'How long does relief last? 3'],
            'symptoms_percentage': ['Frequency 2', 'Frequency 3'],
            'pregnant': ['# of weeks pregnant'],
            'new_complaints': ['Treatment Goals'],
            're_injuries': ['How will you measure progress toward these goals'],
            'upcoming_treatment_course': ['Total  of Therapies for Requested Dates'],
            
            # Date and signature information  
            'date': ['Date of Signature'],
            
            # Additional clinic information
            'clinic_name': ['Clinic Name'],
            'treating_practitioner': ['Treating Practitioner'],
        }
    
    def _build_ash_field_mapping(self) -> Dict[str, Dict]:
        """Build comprehensive field mapping for ASH forms"""
        return {
            # Patient information
            'patient_name': {
                'search_terms': ['Patient Name', 'Name'],
                'type': 'text',
                'offset': 10,
                'fontsize': 10
            },
            'patient_dob': {
                'search_terms': ['Date of Birth', 'DOB', 'Birth Date'],
                'type': 'text',
                'offset': 10,
                'fontsize': 10
            },
            'patient_age': {
                'search_terms': ['Age'],
                'type': 'text',
                'offset': 10,
                'fontsize': 10
            },
            'patient_gender': {
                'search_terms': ['Gender', 'Sex'],
                'type': 'text',
                'offset': 10,
                'fontsize': 10
            },
            
            # Contact information
            'patient_address': {
                'search_terms': ['Address', 'Street Address'],
                'type': 'text',
                'offset': 10,
                'fontsize': 9,
                'multiline': True
            },
            'patient_phone': {
                'search_terms': ['Phone', 'Telephone', 'Phone Number'],
                'type': 'text',
                'offset': 10,
                'fontsize': 10
            },
            'patient_email': {
                'search_terms': ['Email', 'E-mail'],
                'type': 'text',
                'offset': 10,
                'fontsize': 9
            },
            
            # Medical information
            'primary_care_physician': {
                'search_terms': ['Primary Care Physician', 'PCP', 'Doctor'],
                'type': 'text',
                'offset': 10,
                'fontsize': 10
            },
            'physician_phone': {
                'search_terms': ['Physician Phone', 'Doctor Phone'],
                'type': 'text',
                'offset': 10,
                'fontsize': 10
            },
            'health_problems': {
                'search_terms': ['Health Problems', 'Medical Conditions', 'Diagnosis'],
                'type': 'text',
                'offset': 10,
                'fontsize': 9,
                'multiline': True
            },
            'when_began': {
                'search_terms': ['When began', 'Date started', 'Onset'],
                'type': 'text',
                'offset': 10,
                'fontsize': 10
            },
            'how_happened': {
                'search_terms': ['How happened', 'Cause', 'How occurred'],
                'type': 'text',
                'offset': 10,
                'fontsize': 9,
                'multiline': True
            },
            
            # Pain information
            'current_pain': {
                'search_terms': ['Current Pain', 'Pain Level', 'Pain Rating'],
                'type': 'text',
                'offset': 10,
                'fontsize': 10
            },
            'average_pain': {
                'search_terms': ['Average Pain', 'Typical Pain'],
                'type': 'text',
                'offset': 10,
                'fontsize': 10
            },
            'worst_pain': {
                'search_terms': ['Worst Pain', 'Maximum Pain'],
                'type': 'text',
                'offset': 10,
                'fontsize': 10
            },
            
            # Treatment information
            'treatments_received': {
                'search_terms': ['Treatments Received', 'Previous Treatment', 'Therapies'],
                'type': 'text',
                'offset': 10,
                'fontsize': 9,
                'multiline': True
            },
            'pain_medication': {
                'search_terms': ['Pain Medication', 'Medications', 'Drugs'],
                'type': 'text',
                'offset': 10,
                'fontsize': 9
            },
            'health_history': {
                'search_terms': ['Health History', 'Medical History'],
                'type': 'text',
                'offset': 10,
                'fontsize': 9,
                'multiline': True
            },
            
            # Physical measurements
            'height': {
                'search_terms': ['Height'],
                'type': 'text',
                'offset': 10,
                'fontsize': 10
            },
            'weight': {
                'search_terms': ['Weight'],
                'type': 'text',
                'offset': 10,
                'fontsize': 10
            },
            'blood_pressure': {
                'search_terms': ['Blood Pressure', 'BP'],
                'type': 'text',
                'offset': 10,
                'fontsize': 10
            },
            
            # Activities and monitoring
            'activities_monitored': {
                'search_terms': ['Activities', 'Activity Monitoring', 'Daily Activities'],
                'type': 'text',
                'offset': 10,
                'fontsize': 9,
                'multiline': True
            },
            
            # Date and signature
            'date': {
                'search_terms': ['Date', "Today's Date"],
                'type': 'text',
                'offset': 10,
                'fontsize': 10
            },
            'signature': {
                'search_terms': ['Signature', 'Patient Signature'],
                'type': 'text',
                'offset': 10,
                'fontsize': 10
            }
        }
    
    def fill_pdf(self, data: Dict[str, Any], template_path: str, output_path: str) -> ASHFillingResult:
        """Fill ASH PDF using best available method"""
        start_time = datetime.now()
        warnings = []
        
        try:
            logger.info(f"📄 Filling ASH PDF: {os.path.basename(template_path)}")
            logger.info(f"💾 Output: {os.path.basename(output_path)}")
            
            # Validate template exists
            if not os.path.exists(template_path):
                return ASHFillingResult(
                    success=False,
                    error=f"Template not found: {template_path}",
                    method_used="ash_filler"
                )
            
            # Try methods in order of preference
            for method in self.available_methods:
                try:
                    if method == 'pymupdf':
                        result = self._fill_with_pymupdf(data, template_path, output_path, warnings)
                    elif method == 'pypdf2':
                        result = self._fill_with_pypdf2(data, template_path, output_path, warnings)
                    elif method == 'reportlab':
                        result = self._fill_with_reportlab(data, template_path, output_path, warnings)
                    else:
                        continue
                    
                    if result.success:
                        processing_time = (datetime.now() - start_time).total_seconds()
                        result.processing_time = processing_time
                        result.warnings = warnings if warnings else None
                        
                        logger.info(f"✅ ASH PDF filled successfully with {method}: {output_path}")
                        logger.info(f"📊 Fields filled: {result.fields_filled}")
                        logger.info(f"⏱️ Processing time: {processing_time:.2f}s")
                        
                        return result
                    else:
                        logger.warning(f"⚠️ Method {method} failed: {result.error}")
                        warnings.append(f"Method {method} failed: {result.error}")
                        
                except Exception as e:
                    logger.warning(f"⚠️ Method {method} error: {e}")
                    warnings.append(f"Method {method} error: {e}")
                    continue
            
            # All methods failed
            processing_time = (datetime.now() - start_time).total_seconds()
            return ASHFillingResult(
                success=False,
                error="All PDF filling methods failed",
                processing_time=processing_time,
                method_used="all_failed",
                warnings=warnings
            )
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"❌ ASH PDF filling failed: {e}")
            
            return ASHFillingResult(
                success=False,
                error=str(e),
                processing_time=processing_time,
                method_used="ash_filler_failed"
            )
    
    def _fill_with_pymupdf(self, data: Dict[str, Any], template_path: str, 
                          output_path: str, warnings: List[str]) -> ASHFillingResult:
        """Fill PDF using PyMuPDF with actual form fields (preferred method)"""
        if not PYMUPDF_AVAILABLE:
            return ASHFillingResult(
                success=False,
                error="PyMuPDF not available",
                method_used="pymupdf_unavailable"
            )
        
        try:
            logger.info("🔧 Using PyMuPDF form field method")
            
            # Open template PDF
            doc = fitz.open(template_path)
            page = doc[0]  # Work with first page
            
            fields_filled = 0
            
            # Get all form widgets
            widgets = list(page.widgets())
            logger.info(f"📋 Found {len(widgets)} form fields")
            
            # Create direct field mapping
            direct_field_mapping = self._build_direct_field_mapping()
            
            # Fill form fields directly
            for widget in widgets:
                field_name = widget.field_name
                field_type = widget.field_type
                
                # Check if we have data for this field
                value = None
                for data_key, form_field_names in direct_field_mapping.items():
                    if field_name in form_field_names and data_key in data and data[data_key]:
                        # Special handling for activities_monitored field
                        if data_key == 'activities_monitored' and data[data_key]:
                            value = self._extract_activity_value(data[data_key], field_name)
                        else:
                            value = str(data[data_key])
                        break
                
                if value:
                    try:
                        # Fill the field based on type
                        if field_type == 7:  # Text field
                            widget.field_value = value
                            widget.update()
                            fields_filled += 1
                            logger.debug(f"   ✅ {field_name}: {value[:50]}...")
                        elif field_type == 5:  # Checkbox
                            # Handle checkbox values
                            if value.lower() in ['true', 'yes', '1', 'on', 'checked']:
                                widget.field_value = "Yes"
                            else:
                                widget.field_value = "Off"
                            widget.update()
                            fields_filled += 1
                            logger.debug(f"   ✅ {field_name}: {widget.field_value}")
                        elif field_type == 2:  # Button/Radio
                            widget.field_value = value
                            widget.update()
                            fields_filled += 1
                            logger.debug(f"   ✅ {field_name}: {value}")
                    except Exception as field_error:
                        logger.warning(f"   ⚠️ Failed to fill {field_name}: {field_error}")
                        warnings.append(f"Failed to fill field {field_name}: {field_error}")
            
            # Save the filled PDF
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            doc.save(output_path)
            doc.close()
            
            logger.info(f"✅ Form field filling completed: {fields_filled} fields filled")
            
            return ASHFillingResult(
                success=True,
                output_path=output_path,
                fields_filled=fields_filled,
                total_fields=len(data),
                method_used="pymupdf_form_fields"
            )
            
        except Exception as e:
            return ASHFillingResult(
                success=False,
                error=str(e),
                method_used="pymupdf_failed"
            )
    
    def _place_text_pymupdf(self, page, search_terms: List[str], value: str, 
                           offset: float = 10, fontsize: float = 10, multiline: bool = False) -> bool:
        """Place text using PyMuPDF"""
        if not value or value in ['None', 'null', '']:
            return False
        
        for term in search_terms:
            rects = page.search_for(term)
            if rects:
                rect = rects[0]
                x = rect.x1 + offset
                y = (rect.y0 + rect.y1) / 2
                
                # Handle multiline text
                if multiline and len(str(value)) > 50:
                    lines = self._wrap_text(str(value), 50)
                    for i, line in enumerate(lines[:3]):  # Limit to 3 lines
                        page.insert_text((x, y + i * 12), line, fontsize=fontsize, color=self.blue)
                else:
                    # Truncate if too long for single line
                    display_value = str(value)
                    if len(display_value) > 60:
                        display_value = display_value[:57] + "..."
                    
                    page.insert_text((x, y), display_value, fontsize=fontsize, color=self.blue)
                
                return True
        
        return False
    
    def _fill_with_pypdf2(self, data: Dict[str, Any], template_path: str, 
                         output_path: str, warnings: List[str]) -> ASHFillingResult:
        """Fill PDF using PyPDF2 (form field method)"""
        if not PYPDF2_AVAILABLE:
            return ASHFillingResult(
                success=False,
                error="PyPDF2 not available",
                method_used="pypdf2_unavailable"
            )
        
        try:
            logger.info("🔧 Using PyPDF2 method")
            
            # Read template PDF
            with open(template_path, 'rb') as template_file:
                reader = PdfReader(template_file)
                writer = PdfWriter()
                
                # Check if PDF has form fields
                if reader.get_form_text_fields():
                    fields_filled = 0
                    
                    # Fill form fields
                    form_fields = reader.get_form_text_fields()
                    field_updates = {}
                    
                    # Map data to form fields
                    for field_name, field_config in self.ash_field_mapping.items():
                        if field_name in data and data[field_name]:
                            value = str(data[field_name])
                            
                            # Try to find matching form field
                            for form_field_name in form_fields.keys():
                                if any(term.lower() in form_field_name.lower() 
                                      for term in field_config['search_terms']):
                                    field_updates[form_field_name] = value
                                    fields_filled += 1
                                    logger.debug(f"   ✅ {field_name} -> {form_field_name}: {value[:50]}...")
                                    break
                    
                    # Update form fields
                    for page in reader.pages:
                        writer.add_page(page)
                    
                    writer.update_page_form_field_values(writer.pages[0], field_updates)
                    
                    # Save filled PDF
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    with open(output_path, 'wb') as output_file:
                        writer.write(output_file)
                    
                    return ASHFillingResult(
                        success=True,
                        output_path=output_path,
                        fields_filled=fields_filled,
                        total_fields=len(data),
                        method_used="pypdf2_forms"
                    )
                else:
                    # No form fields found
                    warnings.append("No form fields found in PDF")
                    return ASHFillingResult(
                        success=False,
                        error="No fillable form fields found",
                        method_used="pypdf2_no_fields"
                    )
                    
        except Exception as e:
            return ASHFillingResult(
                success=False,
                error=str(e),
                method_used="pypdf2_failed"
            )
    
    def _fill_with_reportlab(self, data: Dict[str, Any], template_path: str, 
                            output_path: str, warnings: List[str]) -> ASHFillingResult:
        """Fill PDF using ReportLab (overlay method)"""
        if not REPORTLAB_AVAILABLE:
            return ASHFillingResult(
                success=False,
                error="ReportLab not available",
                method_used="reportlab_unavailable"
            )
        
        try:
            logger.info("🔧 Using ReportLab overlay method")
            
            # Create overlay with data
            overlay_path = output_path.replace('.pdf', '_overlay.pdf')
            
            # Create overlay PDF
            c = canvas.Canvas(overlay_path, pagesize=letter)
            width, height = letter
            
            fields_filled = 0
            y_position = height - 100  # Start near top
            
            # Add data as text overlay
            for field_name, field_config in self.ash_field_mapping.items():
                if field_name in data and data[field_name]:
                    value = str(data[field_name])
                    
                    # Format field label and value
                    display_text = f"{field_name.replace('_', ' ').title()}: {value}"
                    
                    # Truncate if too long
                    if len(display_text) > 80:
                        display_text = display_text[:77] + "..."
                    
                    c.drawString(50, y_position, display_text)
                    y_position -= 20
                    fields_filled += 1
                    
                    logger.debug(f"   ✅ {field_name}: {value[:50]}...")
                    
                    # Prevent overflow
                    if y_position < 50:
                        break
            
            c.save()
            
            # Merge overlay with template (if PyPDF2 is available)
            if PYPDF2_AVAILABLE:
                try:
                    from PyPDF2 import PdfReader, PdfWriter
                    
                    template_reader = PdfReader(template_path)
                    overlay_reader = PdfReader(overlay_path)
                    writer = PdfWriter()
                    
                    # Merge first page
                    template_page = template_reader.pages[0]
                    overlay_page = overlay_reader.pages[0]
                    template_page.merge_page(overlay_page)
                    
                    writer.add_page(template_page)
                    
                    # Add remaining pages from template
                    for i in range(1, len(template_reader.pages)):
                        writer.add_page(template_reader.pages[i])
                    
                    # Save merged PDF
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    with open(output_path, 'wb') as output_file:
                        writer.write(output_file)
                    
                    # Clean up overlay file
                    os.remove(overlay_path)
                    
                except Exception as merge_error:
                    warnings.append(f"Merge failed: {merge_error}")
                    # Use overlay as final output
                    os.rename(overlay_path, output_path)
            else:
                # Use overlay as final output
                os.rename(overlay_path, output_path)
            
            return ASHFillingResult(
                success=True,
                output_path=output_path,
                fields_filled=fields_filled,
                total_fields=len(data),
                method_used="reportlab_overlay"
            )
            
        except Exception as e:
            return ASHFillingResult(
                success=False,
                error=str(e),
                method_used="reportlab_failed"
            )
    
    def _wrap_text(self, text: str, width: int) -> List[str]:
        """Wrap text to specified width"""
        words = text.split()
        lines = []
        current_line = []
        current_length = 0
        
        for word in words:
            if current_length + len(word) + 1 <= width:
                current_line.append(word)
                current_length += len(word) + 1
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
                current_length = len(word)
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines
    
    def _extract_activity_value(self, activities_data: str, field_name: str) -> str:
        """Extract specific activity values from activities_monitored data"""
        try:
            # Parse the activities string: "Activity: Sleep | Measurement: 4 hours | Change: none; Activity: Recreation | ..."
            activities = activities_data.split(';')
            
            if field_name == 'Activity#0' and len(activities) > 0:
                # Extract first activity name
                first_activity = activities[0].strip()
                if 'Activity:' in first_activity:
                    return first_activity.split('Activity:')[1].split('|')[0].strip()
            elif field_name == 'Activity#1' and len(activities) > 1:
                # Extract second activity name
                second_activity = activities[1].strip()
                if 'Activity:' in second_activity:
                    return second_activity.split('Activity:')[1].split('|')[0].strip()
            elif field_name == 'Measurements' and len(activities) > 0:
                # Extract first measurement
                first_activity = activities[0].strip()
                if 'Measurement:' in first_activity:
                    return first_activity.split('Measurement:')[1].split('|')[0].strip()
            elif field_name == 'Measurements#1' and len(activities) > 1:
                # Extract second measurement
                second_activity = activities[1].strip()
                if 'Measurement:' in second_activity:
                    return second_activity.split('Measurement:')[1].split('|')[0].strip()
            elif field_name == 'How has it changed?' and len(activities) > 0:
                # Extract first change
                first_activity = activities[0].strip()
                if 'Change:' in first_activity:
                    return first_activity.split('Change:')[1].strip()
            elif field_name == 'How has it changed?#1' and len(activities) > 1:
                # Extract second change
                second_activity = activities[1].strip()
                if 'Change:' in second_activity:
                    return second_activity.split('Change:')[1].strip()
            
            return ""
        except Exception as e:
            logger.warning(f"Error parsing activities data for {field_name}: {e}")
            return ""
    
    def is_available(self) -> Tuple[bool, str]:
        """Check if ASH PDF filler is available"""
        if not self.available_methods:
            return False, "No PDF processing libraries available"
        
        return True, f"ASH PDF filler ready with methods: {', '.join(self.available_methods)}"

class ASHFormFieldMapper:
    """Maps various data formats to ASH form fields"""
    
    def __init__(self):
        """Initialize ASH form field mapper"""
        logger.info("🗂️ ASH Form Field Mapper initialized")
    
    def map_mnr_to_ash(self, mnr_data: Dict[str, Any]) -> Dict[str, Any]:
        """Map MNR data to ASH format"""
        ash_data = {}
        
        # Direct field mappings
        direct_mappings = {
            'Primary_Care_Physician': 'primary_care_physician',
            'Physician_Phone': 'physician_phone',
            'Current_Health_Problems': 'health_problems',
            'When_Began': 'when_began',
            'How_Happened': 'how_happened',
            'Pain_Medication': 'pain_medication',
            'Health_History': 'health_history',
            'Date': 'date',
            'Signature': 'signature',
            'Employer': 'employer',
            'Job_Description': 'job_description'
        }
        
        for mnr_field, ash_field in direct_mappings.items():
            if mnr_field in mnr_data and mnr_data[mnr_field]:
                ash_data[ash_field] = mnr_data[mnr_field]
        
        # Complex field mappings
        
        # Height formatting
        height = mnr_data.get('Height', {})
        if isinstance(height, dict):
            feet = height.get('feet', '')
            inches = height.get('inches', '')
            if feet or inches:
                ash_data['height'] = f"{feet}'{inches}\"" if feet and inches else f"{feet or inches}"
        
        # Weight formatting
        weight = mnr_data.get('Weight_lbs')
        if weight:
            ash_data['weight'] = f"{weight} lbs"
        
        # Blood pressure formatting
        bp = mnr_data.get('Blood_Pressure', {})
        if isinstance(bp, dict):
            systolic = bp.get('systolic', '')
            diastolic = bp.get('diastolic', '')
            if systolic or diastolic:
                ash_data['blood_pressure'] = f"{systolic}/{diastolic}" if systolic and diastolic else str(systolic or diastolic)
        
        # Pain levels
        pain_levels = mnr_data.get('Pain_Level', {})
        if isinstance(pain_levels, dict):
            pain_mappings = {
                'Average_Past_Week': 'average_pain',
                'Worst_Past_Week': 'worst_pain',
                'Current': 'current_pain'
            }
            
            for mnr_key, ash_key in pain_mappings.items():
                if mnr_key in pain_levels:
                    ash_data[ash_key] = pain_levels[mnr_key]
        
        # Treatment received (flatten to text)
        treatment = mnr_data.get('Treatment_Received', {})
        if isinstance(treatment, dict):
            treatment_list = []
            for key, value in treatment.items():
                if value is True:
                    treatment_list.append(key.replace('_', ' '))
            
            other = treatment.get('Other')
            if other:
                treatment_list.append(f"Other: {other}")
            
            if treatment_list:
                ash_data['treatments_received'] = ', '.join(treatment_list)
        
        # Activities (flatten structure)
        activities = mnr_data.get('Activities_Monitored', [])
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
        
        # Daily Activity Interference
        daily_interference = mnr_data.get('Daily_Activity_Interference')
        if daily_interference:
            ash_data['daily_activity_interference'] = str(daily_interference)
        
        # Pain Quality (flatten to text)
        pain_quality = mnr_data.get('Pain_Quality', {})
        if isinstance(pain_quality, dict):
            quality_list = []
            for key, value in pain_quality.items():
                if value is True:
                    quality_list.append(key.replace('_', ' '))
            if quality_list:
                ash_data['pain_quality'] = ', '.join(quality_list)
        
        # Helpful Treatments (flatten to text)
        helpful_treatments = mnr_data.get('Helpful_Treatments', {})
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
        
        # Progress Since Acupuncture
        progress = mnr_data.get('Progress_Since_Acupuncture', {})
        if isinstance(progress, dict):
            progress_list = []
            for key, value in progress.items():
                if value is True:
                    progress_list.append(key.replace('_', ' '))
            if progress_list:
                ash_data['progress_since_acupuncture'] = ', '.join(progress_list)
        
        # Relief Duration
        relief = mnr_data.get('Relief_Duration', {})
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
        
        # Symptoms Past Week Percentage (flatten to text)
        symptoms = mnr_data.get('Symptoms_Past_Week_Percentage', {})
        if isinstance(symptoms, dict):
            symptom_list = []
            for key, value in symptoms.items():
                if value is True:
                    symptom_list.append(key)
            if symptom_list:
                ash_data['symptoms_percentage'] = ', '.join(symptom_list)
        
        # Pregnant status
        pregnant = mnr_data.get('Pregnant', {})
        if isinstance(pregnant, dict):
            if pregnant.get('Yes'):
                weeks = pregnant.get('Weeks', '')
                physician = pregnant.get('Physician', '')
                ash_data['pregnant'] = f"Yes{f', {weeks} weeks' if weeks else ''}{f', Physician: {physician}' if physician else ''}"
            elif pregnant.get('No'):
                ash_data['pregnant'] = "No"
        
        # New Complaints
        new_complaints = mnr_data.get('New_Complaints', {})
        if isinstance(new_complaints, dict):
            if new_complaints.get('Yes'):
                explain = new_complaints.get('Explain', '')
                ash_data['new_complaints'] = f"Yes{f': {explain}' if explain else ''}"
            elif new_complaints.get('No'):
                ash_data['new_complaints'] = "No"
        
        # Re-Injuries
        re_injuries = mnr_data.get('Re_Injuries', {})
        if isinstance(re_injuries, dict):
            if re_injuries.get('Yes'):
                explain = re_injuries.get('Explain', '')
                ash_data['re_injuries'] = f"Yes{f': {explain}' if explain else ''}"
            elif re_injuries.get('No'):
                ash_data['re_injuries'] = "No"
        
        # Upcoming Treatment Course
        treatment_course = mnr_data.get('Upcoming_Treatment_Course', {})
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
        
        # Add mapping metadata
        ash_data['_mapping_info'] = {
            'mapped_from': 'MNR',
            'mapper': 'ASH Form Field Mapper',
            'mapped_at': datetime.now().isoformat(),
            'original_fields': len(mnr_data),
            'mapped_fields': len([k for k in ash_data.keys() if not k.startswith('_')])
        }
        
        logger.info(f"🗂️ Mapped {len(mnr_data)} MNR fields to {len(ash_data)} ASH fields")
        
        return ash_data
    
    def validate_ash_data(self, ash_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate ASH form data"""
        errors = []
        
        # Check required fields
        required_fields = ['patient_name', 'health_problems']
        for field in required_fields:
            if field not in ash_data or not ash_data[field]:
                errors.append(f"Missing required field: {field}")
        
        # Validate data types and formats
        if 'current_pain' in ash_data:
            pain_value = ash_data['current_pain']
            if not str(pain_value).endswith('/10'):
                errors.append(f"Pain level should be in 'X/10' format: {pain_value}")
        
        return len(errors) == 0, errors

# Convenience functions
def fill_ash_pdf(data: Dict[str, Any], template_path: str, output_path: str) -> ASHFillingResult:
    """Fill ASH PDF with data"""
    filler = ASHPDFFiller()
    return filler.fill_pdf(data, template_path, output_path)

def map_mnr_to_ash_format(mnr_data: Dict[str, Any]) -> Dict[str, Any]:
    """Map MNR data to ASH format"""
    mapper = ASHFormFieldMapper()
    return mapper.map_mnr_to_ash(mnr_data)

def check_ash_filler_availability() -> Tuple[bool, str]:
    """Check if ASH PDF filler is available"""
    try:
        filler = ASHPDFFiller()
        return filler.is_available()
    except Exception as e:
        return False, str(e)