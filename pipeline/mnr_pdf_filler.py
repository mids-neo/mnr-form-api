#!/usr/bin/env python3
"""
mnr_pdf_filler.py
=================

MNR PDF Form Filling Pipeline Module
Handles filling MNR (Medical Necessity Review) forms with comprehensive field mapping
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
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class FillingResult:
    """Result of PDF filling operation"""
    success: bool
    output_path: Optional[str] = None
    fields_filled: int = 0
    total_fields: int = 0
    error: Optional[str] = None
    processing_time: float = 0.0
    method_used: str = "unknown"
    warnings: Optional[List[str]] = None

class BasePDFFiller(ABC):
    """Base class for PDF filling operations"""
    
    @abstractmethod
    def fill_pdf(self, data: Dict[str, Any], template_path: str, output_path: str) -> FillingResult:
        """Fill PDF with data"""
        pass
    
    @abstractmethod
    def is_available(self) -> Tuple[bool, str]:
        """Check if filler is available"""
        pass

class MNRPDFFiller(BasePDFFiller):
    """MNR PDF form filler with comprehensive field mapping"""
    
    def __init__(self):
        """Initialize MNR PDF filler"""
        if not PYMUPDF_AVAILABLE:
            raise ImportError("PyMuPDF not available. Install with: pip install PyMuPDF")
        
        self.blue = (0, 0, 1)  # Blue color for text
        self.form_field_mapping = self._build_field_mapping()
        
        logger.info("📋 MNR PDF Filler initialized")
    
    def _build_field_mapping(self) -> Dict[str, Dict]:
        """Build comprehensive field mapping for MNR forms"""
        return {
            # Basic information fields
            'Primary_Care_Physician': {
                'search_terms': ['Primary Care Physician', 'Primary care physician'],
                'type': 'text',
                'offset': 10,
                'fontsize': 10
            },
            'Physician_Phone': {
                'search_terms': ['Physician Phone', 'Phone'],
                'type': 'text', 
                'offset': 10,
                'fontsize': 10
            },
            'Employer': {
                'search_terms': ['Employer'],
                'type': 'text',
                'offset': 10,
                'fontsize': 10
            },
            'Job_Description': {
                'search_terms': ['Job Description', 'Job Title'],
                'type': 'text',
                'offset': 10,
                'fontsize': 10
            },
            
            # Health status fields
            'Current_Health_Problems': {
                'search_terms': ['current health problem', 'Current health problems'],
                'type': 'text',
                'offset': 10,
                'fontsize': 9,
                'multiline': True
            },
            'When_Began': {
                'search_terms': ['When it began?', 'When began'],
                'type': 'text',
                'offset': 10,
                'fontsize': 10
            },
            'How_Happened': {
                'search_terms': ['How it happened?', 'How happened'],
                'type': 'text',
                'offset': 10,
                'fontsize': 9,
                'multiline': True
            },
            'Pain_Medication': {
                'search_terms': ['Pain Medication (Name, Dosage, Frequency)', 'Pain Medication'],
                'type': 'text',
                'offset': 5,
                'fontsize': 9
            },
            'Health_History': {
                'search_terms': ['Pertinent Health history', 'Health History'],
                'type': 'text',
                'offset': 10,
                'fontsize': 9,
                'multiline': True
            },
            
            # Date and signature
            'Date': {
                'search_terms': ['DATE', "Today's Date"],
                'type': 'text',
                'offset': 10,
                'fontsize': 10
            },
            'Signature': {
                'search_terms': ['SIGNATURE:', 'Signature'],
                'type': 'text',
                'offset': 10,
                'fontsize': 10
            },
            
            # Pain levels
            'Pain_Level': {
                'type': 'pain_scales',
                'mappings': [
                    ('Average_Past_Week', ['Average Pain Level in the past week', 'Average pain']),
                    ('Worst_Past_Week', ['Worse Pain Level in the past week', 'Worst pain']),
                    ('Current', ['Current Pain Level', 'Current pain'])
                ]
            },
            'Daily_Activity_Interference': {
                'search_terms': ['How has it interfered with your daily activity'],
                'type': 'text',
                'offset': 10,
                'fontsize': 10
            },
            
            # Physical measurements
            'Height': {
                'search_terms': ['Height'],
                'type': 'physical',
                'offset': 5,
                'fontsize': 10
            },
            'Weight_lbs': {
                'search_terms': ['Weight'],
                'type': 'physical', 
                'offset': 5,
                'fontsize': 10
            },
            'Blood_Pressure': {
                'search_terms': ['Blood Pressure'],
                'type': 'physical',
                'offset': 5,
                'fontsize': 10
            }
        }
    
    def fill_pdf(self, data: Dict[str, Any], template_path: str, output_path: str) -> FillingResult:
        """Fill MNR PDF with comprehensive field mapping"""
        start_time = datetime.now()
        warnings = []
        
        try:
            logger.info(f"📋 Filling MNR PDF: {os.path.basename(template_path)}")
            logger.info(f"💾 Output: {os.path.basename(output_path)}")
            
            # Validate template exists
            if not os.path.exists(template_path):
                return FillingResult(
                    success=False,
                    error=f"Template not found: {template_path}",
                    method_used="mnr_filler"
                )
            
            # Open template PDF
            doc = fitz.open(template_path)
            page = doc[0]  # Work with first page
            
            # Get page dimensions
            page_width = page.rect.width
            page_height = page.rect.height
            
            logger.info(f"📐 Page size: {page_width:.0f} x {page_height:.0f}")
            
            # Fill different types of fields
            text_count = self._fill_text_fields(page, data, warnings)
            checkbox_count = self._fill_checkboxes(page, data, warnings)
            pain_count = self._fill_pain_levels(page, data, warnings)
            activity_count = self._fill_activity_table(page, data, warnings)
            physical_count = self._fill_physical_measurements(page, data, warnings)
            
            total_fields_filled = text_count + checkbox_count + pain_count + activity_count + physical_count
            
            # Save the filled PDF
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            doc.save(output_path)
            doc.close()
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"✅ MNR PDF filled successfully: {output_path}")
            logger.info(f"📊 Fields filled: {text_count} text, {checkbox_count} checkboxes, {pain_count} pain scales")
            logger.info(f"📊 Additional: {activity_count} activities, {physical_count} measurements")
            logger.info(f"🎯 Total fields: {total_fields_filled}")
            
            return FillingResult(
                success=True,
                output_path=output_path,
                fields_filled=total_fields_filled,
                total_fields=len(data),
                processing_time=processing_time,
                method_used="mnr_filler_pymupdf",
                warnings=warnings if warnings else None
            )
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"❌ MNR PDF filling failed: {e}")
            
            return FillingResult(
                success=False,
                error=str(e),
                processing_time=processing_time,
                method_used="mnr_filler_failed",
                warnings=warnings if warnings else None
            )
    
    def _place_text_smart(self, page, search_terms: List[str], value: str, 
                         offset: float = 10, fontsize: float = 10, multiline: bool = False) -> bool:
        """Smart text placement using multiple search terms"""
        
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
    
    def _fill_text_fields(self, page, data: Dict[str, Any], warnings: List[str]) -> int:
        """Fill text fields with comprehensive mapping"""
        
        logger.info("📝 Filling text fields...")
        filled_count = 0
        
        # Basic text fields using mapping
        text_fields = [
            'Primary_Care_Physician', 'Physician_Phone', 'Employer', 'Job_Description',
            'Current_Health_Problems', 'When_Began', 'How_Happened', 'Pain_Medication',
            'Health_History', 'Date', 'Signature'
        ]
        
        for field in text_fields:
            if field in self.form_field_mapping and field in data:
                mapping = self.form_field_mapping[field]
                value = data[field]
                
                if self._place_text_smart(
                    page, 
                    mapping['search_terms'], 
                    value, 
                    mapping.get('offset', 10),
                    mapping.get('fontsize', 10),
                    mapping.get('multiline', False)
                ):
                    filled_count += 1
                    logger.debug(f"   ✅ {field}: {str(value)[:50]}...")
                else:
                    warnings.append(f"Could not place text field: {field}")
        
        # Handle under physician care conditions
        under_care = data.get('Under_Physician_Care', {})
        if isinstance(under_care, dict) and under_care.get('Yes'):
            conditions = under_care.get('Conditions', '')
            if not conditions:
                # Extract from health problems if no specific conditions
                health_problems = data.get('Current_Health_Problems', '')
                conditions = self._extract_condition_keywords(health_problems)
            
            if conditions and self._place_text_smart(page, ['for what conditions?'], conditions):
                filled_count += 1
                logger.debug(f"   ✅ Conditions: {conditions}")
        
        # Daily activity interference
        activity_interference = data.get('Daily_Activity_Interference', '')
        if activity_interference and self._place_text_smart(
            page, ['How has it interfered with your daily activity'], 
            str(activity_interference)):
            filled_count += 1
            logger.debug(f"   ✅ Daily Activity Interference: {activity_interference}")
        
        logger.info(f"📝 Text fields filled: {filled_count}")
        return filled_count
    
    def _extract_condition_keywords(self, health_problems: str) -> str:
        """Extract key condition keywords from health problems"""
        if not health_problems:
            return ""
        
        health_lower = health_problems.lower()
        
        # Map common conditions to keywords
        condition_map = {
            'shoulder': 'Shoulder',
            'knee': 'Knee', 
            'back': 'Back',
            'hip': 'Hip',
            'osteoarthritis': 'Osteoarthritis',
            'fibromyalgia': 'Fibromyalgia',
            'herniated': 'Herniated disc',
            'disc': 'Disc problems'
        }
        
        for key, condition in condition_map.items():
            if key in health_lower:
                return condition
        
        # Return first few words if no specific match
        words = health_problems.split()
        return ' '.join(words[:3]) if words else health_problems
    
    def _fill_pain_levels(self, page, data: Dict[str, Any], warnings: List[str]) -> int:
        """Fill pain level fields"""
        
        logger.info("📊 Filling pain levels...")
        filled_count = 0
        
        pain_levels = data.get('Pain_Level', {})
        if not isinstance(pain_levels, dict):
            return 0
        
        # Get mapping from field configuration
        pain_mapping = self.form_field_mapping.get('Pain_Level', {})
        mappings = pain_mapping.get('mappings', [])
        
        for json_key, search_terms in mappings:
            value = pain_levels.get(json_key)
            if value and self._place_text_smart(page, search_terms, str(value)):
                filled_count += 1
                logger.debug(f"   ✅ {json_key}: {value}")
            elif value:
                warnings.append(f"Could not place pain level: {json_key}")
        
        logger.info(f"📊 Pain levels filled: {filled_count}")
        return filled_count
    
    def _fill_checkboxes(self, page, data: Dict[str, Any], warnings: List[str]) -> int:
        """Fill checkbox fields with comprehensive coverage"""
        
        logger.info("☑️ Filling checkboxes...")
        filled_count = 0
        
        # Under physician care
        filled_count += self._fill_yes_no_checkbox(page, data, 'Under_Physician_Care', 
                                                  y_range=(100, 120), warnings=warnings)
        
        # Treatment received
        treatment = data.get('Treatment_Received', {})
        if isinstance(treatment, dict):
            treatment_mappings = [
                ('Surgery', ['Surgery']),
                ('Medications', ['Medications', 'Medication']),
                ('Physical_Therapy', ['Physical Therapy', 'PT']),
                ('Chiropractic', ['Chiropractic']),
                ('Massage', ['Massage']),
                ('Injections', ['Injections', 'Injection'])
            ]
            
            for json_key, search_terms in treatment_mappings:
                if treatment.get(json_key):
                    if self._place_checkbox_mark(page, search_terms):
                        filled_count += 1
                        logger.debug(f"   ✅ Treatment: {search_terms[0]}")
                    else:
                        warnings.append(f"Could not place treatment checkbox: {json_key}")
            
            # Other treatment text
            other = treatment.get('Other', '')
            if other and self._place_text_smart(page, ['Other'], other, offset=5):
                filled_count += 1
                logger.debug(f"   ✅ Treatment Other: {other}")
        
        # Symptoms percentage
        symptoms = data.get('Symptoms_Past_Week_Percentage', {})
        if isinstance(symptoms, dict):
            for range_key in ['0-10%', '11-20%', '21-30%', '31-40%', '41-50%',
                            '51-60%', '61-70%', '71-80%', '81-90%', '91-100%']:
                if symptoms.get(range_key):
                    if self._place_checkbox_mark(page, [range_key]):
                        filled_count += 1
                        logger.debug(f"   ✅ Symptoms: {range_key}")
                    else:
                        warnings.append(f"Could not place symptom checkbox: {range_key}")
                    break  # Only one range should be selected
        
        # New complaints and re-injuries
        filled_count += self._fill_yes_no_with_explain(page, data, 'New_Complaints',
                                                      y_range=(340, 350), warnings=warnings)
        filled_count += self._fill_yes_no_with_explain(page, data, 'Re_Injuries', 
                                                      y_range=(360, 370), warnings=warnings)
        
        # Additional checkbox sections
        filled_count += self._fill_helpful_treatments(page, data, warnings)
        filled_count += self._fill_pain_quality(page, data, warnings)
        filled_count += self._fill_progress_section(page, data, warnings)
        filled_count += self._fill_relief_duration(page, data, warnings)
        filled_count += self._fill_treatment_course(page, data, warnings)
        filled_count += self._fill_pregnant_section(page, data, warnings)
        
        logger.info(f"☑️ Checkboxes filled: {filled_count}")
        return filled_count
    
    def _fill_yes_no_checkbox(self, page, data: Dict[str, Any], field: str, 
                             y_range: tuple, warnings: List[str]) -> int:
        """Fill Yes/No checkbox with Y-position filtering"""
        filled_count = 0
        
        field_data = data.get(field, {})
        if not isinstance(field_data, dict):
            return 0
        
        y_min, y_max = y_range
        
        if field_data.get('Yes'):
            yes_rects = page.search_for('Yes')
            for rect in yes_rects:
                if y_min < rect.y0 < y_max:
                    cx = (rect.x0 + rect.x1) / 2
                    cy = (rect.y0 + rect.y1) / 2
                    page.insert_text((cx, cy), 'X', fontsize=10, color=self.blue)
                    filled_count += 1
                    logger.debug(f"   ✅ {field}: Yes")
                    break
            else:
                if field_data.get('Yes'):
                    warnings.append(f"Could not place Yes checkbox for {field}")
        
        if field_data.get('No'):
            no_rects = page.search_for('No')
            for rect in no_rects:
                if y_min < rect.y0 < y_max:
                    cx = (rect.x0 + rect.x1) / 2
                    cy = (rect.y0 + rect.y1) / 2
                    page.insert_text((cx, cy), 'X', fontsize=10, color=self.blue)
                    filled_count += 1
                    logger.debug(f"   ✅ {field}: No")
                    break
            else:
                if field_data.get('No'):
                    warnings.append(f"Could not place No checkbox for {field}")
        
        return filled_count
    
    def _fill_yes_no_with_explain(self, page, data: Dict[str, Any], field: str,
                                 y_range: tuple, warnings: List[str]) -> int:
        """Fill Yes/No checkbox with explanation field"""
        filled_count = self._fill_yes_no_checkbox(page, data, field, y_range, warnings)
        
        field_data = data.get(field, {})
        if isinstance(field_data, dict):
            explain = field_data.get('Explain', '')
            if explain:
                explain_rects = page.search_for('Explain:')
                if explain_rects:
                    # Use appropriate explain rect based on field
                    rect_index = 0 if field == 'New_Complaints' else 1
                    if rect_index < len(explain_rects):
                        rect = explain_rects[rect_index]
                        x = rect.x1 + 10
                        y = (rect.y0 + rect.y1) / 2
                        page.insert_text((x, y), explain, fontsize=10, color=self.blue)
                        filled_count += 1
                        logger.debug(f"   ✅ {field} Explain: {explain}")
                    else:
                        warnings.append(f"Could not place explanation for {field}")
                else:
                    warnings.append(f"Could not find explain field for {field}")
        
        return filled_count
    
    def _place_checkbox_mark(self, page, search_terms: List[str]) -> bool:
        """Place checkbox mark (X) in proper checkbox position"""
        for term in search_terms:
            rects = page.search_for(term)
            if rects:
                rect = rects[0]
                
                # For treatment checkboxes, position X before the label (checkbox is to the left)
                if any(treatment in term for treatment in ['Surgery', 'Medications', 'Physical Therapy', 
                                                         'Chiropractic', 'Massage', 'Injections']):
                    x = rect.x0 - 12  # Position to the left of label (in checkbox)
                else:
                    x = rect.x1 + 10  # Default: position to the right
                
                y = (rect.y0 + rect.y1) / 2
                page.insert_text((x, y), 'X', fontsize=10, color=self.blue)
                return True
        return False
    
    def _fill_helpful_treatments(self, page, data: Dict[str, Any], warnings: List[str]) -> int:
        """Fill helpful treatments section"""
        filled_count = 0
        helpful = data.get('Helpful_Treatments', {})
        
        if isinstance(helpful, dict):
            helpful_mappings = [
                ('Acupuncture', ['Acupuncture']),
                ('Chinese_Herbs', ['Chinese Herbs']),
                ('Massage_Therapy', ['Massage Therapy']),
                ('Nutritional_Supplements', ['Nutritional Supplements']),
                ('Prescription_Medications', ['Prescription Medication']),
                ('Physical_Therapy', ['Physical Therapy']),
                ('Rehab_Home_Care', ['Rehab/Home Care', 'Rehab']),
                ('Spinal_Adjustment_Manipulation', ['Spinal Adjustment'])
            ]
            
            for json_key, search_terms in helpful_mappings:
                if helpful.get(json_key):
                    if self._place_checkbox_mark(page, search_terms):
                        filled_count += 1
                        logger.debug(f"   ✅ Helpful: {search_terms[0]}")
                    else:
                        warnings.append(f"Could not place helpful treatment: {json_key}")
        
        return filled_count
    
    def _fill_pain_quality(self, page, data: Dict[str, Any], warnings: List[str]) -> int:
        """Fill pain quality checkboxes"""
        filled_count = 0
        pain_quality = data.get('Pain_Quality', {})
        
        if isinstance(pain_quality, dict):
            quality_options = ['Sharp', 'Throbbing', 'Ache', 'Burning', 'Numb', 'Tingling']
            for option in quality_options:
                if pain_quality.get(option):
                    if self._place_checkbox_mark(page, [option]):
                        filled_count += 1
                        logger.debug(f"   ✅ Pain Quality: {option}")
                    else:
                        warnings.append(f"Could not place pain quality: {option}")
        
        return filled_count
    
    def _fill_progress_section(self, page, data: Dict[str, Any], warnings: List[str]) -> int:
        """Fill progress since acupuncture section"""
        filled_count = 0
        progress = data.get('Progress_Since_Acupuncture', {})
        
        if isinstance(progress, dict):
            progress_options = ['Excellent', 'Good', 'Fair', 'Poor', 'Worse']
            for option in progress_options:
                if progress.get(option):
                    if self._place_checkbox_mark(page, [option]):
                        filled_count += 1
                        logger.debug(f"   ✅ Progress: {option}")
                    else:
                        warnings.append(f"Could not place progress option: {option}")
        
        return filled_count
    
    def _fill_relief_duration(self, page, data: Dict[str, Any], warnings: List[str]) -> int:
        """Fill relief duration section"""
        filled_count = 0
        relief = data.get('Relief_Duration', {})
        
        if isinstance(relief, dict):
            if relief.get('Hours'):
                if self._place_checkbox_mark(page, ['Hours']):
                    filled_count += 1
                    logger.debug("   ✅ Relief: Hours")
                else:
                    warnings.append("Could not place Hours checkbox")
                
                hours_num = relief.get('Hours_Number')
                if hours_num and self._place_text_smart(page, ['if so, how many'], str(hours_num)):
                    filled_count += 1
                    logger.debug(f"   ✅ Hours Number: {hours_num}")
            
            if relief.get('Days'):
                if self._place_checkbox_mark(page, ['Days']):
                    filled_count += 1
                    logger.debug("   ✅ Relief: Days")
                else:
                    warnings.append("Could not place Days checkbox")
                
                days_num = relief.get('Days_Number')
                if days_num:
                    # Find second occurrence of "if so, how many" for days
                    how_many_rects = page.search_for('if so, how many')
                    if len(how_many_rects) > 1:
                        rect = how_many_rects[1]
                        x = rect.x1 + 10
                        y = (rect.y0 + rect.y1) / 2
                        page.insert_text((x, y), str(days_num), fontsize=10, color=self.blue)
                        filled_count += 1
                        logger.debug(f"   ✅ Days Number: {days_num}")
                    else:
                        warnings.append("Could not place Days number")
        
        return filled_count
    
    def _fill_treatment_course(self, page, data: Dict[str, Any], warnings: List[str]) -> int:
        """Fill treatment course section"""
        filled_count = 0
        treatment_course = data.get('Upcoming_Treatment_Course', {})
        
        if isinstance(treatment_course, dict):
            if treatment_course.get('1_per_week'):
                if self._place_checkbox_mark(page, ['1/week']):
                    filled_count += 1
                    logger.debug("   ✅ Treatment: 1/week")
                else:
                    warnings.append("Could not place 1/week checkbox")
            
            if treatment_course.get('2_per_week'):
                if self._place_checkbox_mark(page, ['2/week']):
                    filled_count += 1
                    logger.debug("   ✅ Treatment: 2/week")
                else:
                    warnings.append("Could not place 2/week checkbox")
            
            out_of_town = treatment_course.get('Out_of_Town_Dates', '')
            if out_of_town and self._place_text_smart(page, ['Will you be out of town'], out_of_town):
                filled_count += 1
                logger.debug(f"   ✅ Out of Town: {out_of_town}")
        
        return filled_count
    
    def _fill_pregnant_section(self, page, data: Dict[str, Any], warnings: List[str]) -> int:
        """Fill pregnancy section with all fields"""
        filled_count = 0
        
        pregnant = data.get('Pregnant', {})
        if not isinstance(pregnant, dict):
            return 0
        
        # Yes/No checkboxes
        filled_count += self._fill_yes_no_checkbox(page, data, 'Pregnant', (695, 710), warnings)
        
        # Additional pregnancy fields if Yes
        if pregnant.get('Yes'):
            weeks = pregnant.get('Weeks')
            if weeks and self._place_text_smart(page, ['# of weeks'], str(weeks)):
                filled_count += 1
                logger.debug(f"   ✅ Pregnancy Weeks: {weeks}")
            
            physician = pregnant.get('Physician')
            if physician and self._place_text_smart(page, ['Physician for Pregnancy'], physician):
                filled_count += 1
                logger.debug(f"   ✅ Pregnancy Physician: {physician}")
        
        return filled_count
    
    def _fill_physical_measurements(self, page, data: Dict[str, Any], warnings: List[str]) -> int:
        """Fill physical measurements with proper formatting"""
        
        logger.info("📏 Filling physical measurements...")
        filled_count = 0
        
        # Height with better formatting
        height = data.get('Height', {})
        if isinstance(height, dict):
            feet = height.get('feet', '')
            inches = height.get('inches', '')
            if feet or inches:
                height_str = f"{feet}'{inches}\"" if feet and inches else f"{feet or inches}"
                if self._place_text_smart(page, ['Height'], height_str):
                    filled_count += 1
                    logger.debug(f"   ✅ Height: {height_str}")
                else:
                    warnings.append("Could not place height")
        
        # Weight
        weight = data.get('Weight_lbs', '')
        if weight and self._place_text_smart(page, ['Weight'], f"{weight} lbs"):
            filled_count += 1
            logger.debug(f"   ✅ Weight: {weight} lbs")
        elif weight:
            warnings.append("Could not place weight")
        
        # Blood pressure with better formatting
        bp = data.get('Blood_Pressure', {})
        if isinstance(bp, dict):
            systolic = bp.get('systolic', '')
            diastolic = bp.get('diastolic', '')
            if systolic or diastolic:
                bp_str = f"{systolic}/{diastolic}" if systolic and diastolic else str(systolic or diastolic)
                if self._place_text_smart(page, ['Blood Pressure'], bp_str):
                    filled_count += 1
                    logger.debug(f"   ✅ Blood Pressure: {bp_str}")
                else:
                    warnings.append("Could not place blood pressure")
        
        logger.info(f"📏 Physical measurements filled: {filled_count}")
        return filled_count
    
    def _fill_activity_table(self, page, data: Dict[str, Any], warnings: List[str]) -> int:
        """Fill activity table with enhanced positioning"""
        
        logger.info("📋 Filling activity table...")
        
        activities = data.get('Activities_Monitored', [])
        if not isinstance(activities, list) or len(activities) == 0:
            logger.info("   ℹ️ No activities to fill")
            return 0
        
        # Find activity table header
        header_terms = ['List the activities', 'Activities', 'activity']
        header_rect = None
        
        for term in header_terms:
            rects = page.search_for(term)
            if rects:
                header_rect = rects[0]
                break
        
        if not header_rect:
            warnings.append("Could not find activity table header")
            return 0
        
        base_y = header_rect.y1 + 25  # Start below header
        filled_count = 0
        
        # Column positions
        col_positions = {
            'activity': 72,      # Activity name column
            'measurement': 216,   # Measurement column  
            'changed': 468       # How changed column
        }
        
        for i, item in enumerate(activities[:3]):  # Limit to 3 activities
            if not isinstance(item, dict):
                continue
            
            y = base_y + (i * 22)  # Row spacing
            
            # Activity name
            activity_name = item.get('Activity', '')
            if activity_name:
                if len(activity_name) > 25:
                    activity_name = activity_name[:22] + "..."
                page.insert_text((col_positions['activity'], y), activity_name, 
                               fontsize=9, color=self.blue)
                filled_count += 1
            
            # Measurement
            measurement = item.get('Measurement', '') or ''
            if measurement and measurement != 'null':
                if len(measurement) > 30:
                    measurement = measurement[:27] + "..."
                page.insert_text((col_positions['measurement'], y), measurement,
                               fontsize=9, color=self.blue)
                filled_count += 1
            
            # How changed
            changed = item.get('How_has_changed', '')
            if changed:
                if len(changed) > 25:
                    changed = changed[:22] + "..."
                page.insert_text((col_positions['changed'], y), changed,
                               fontsize=9, color=self.blue)
                filled_count += 1
            
            if activity_name or measurement or changed:
                logger.debug(f"   ✅ Activity {i+1}: {activity_name[:20]}... | {measurement[:20]}... | {changed[:20]}...")
        
        logger.info(f"📋 Activities filled: {filled_count}")
        return filled_count
    
    def is_available(self) -> Tuple[bool, str]:
        """Check if MNR PDF filler is available"""
        if not PYMUPDF_AVAILABLE:
            return False, "PyMuPDF not available"
        
        return True, "MNR PDF filler ready"

# Convenience functions
def fill_mnr_pdf(data: Dict[str, Any], template_path: str, output_path: str) -> FillingResult:
    """Fill MNR PDF with data"""
    filler = MNRPDFFiller()
    return filler.fill_pdf(data, template_path, output_path)

def check_mnr_filler_availability() -> Tuple[bool, str]:
    """Check if MNR PDF filler is available"""
    filler = MNRPDFFiller()
    return filler.is_available()