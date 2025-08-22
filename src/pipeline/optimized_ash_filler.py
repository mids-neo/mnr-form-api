#!/usr/bin/env python3
"""
optimized_ash_filler.py
=======================

Optimized ASH PDF Form Filler using template-driven field mapping
Integrates with the OptimizedASHFormFieldMapper for maximum performance and accuracy
"""

import json
import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass

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
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

from .optimized_ash_mapper import OptimizedASHFormFieldMapper, FieldMappingResult

logger = logging.getLogger(__name__)

@dataclass
class OptimizedASHFillingResult:
    """Result of optimized ASH PDF filling operation"""
    success: bool
    output_path: Optional[str] = None
    fields_filled: int = 0
    total_fields: int = 0
    error: Optional[str] = None
    processing_time: float = 0.0
    method_used: str = "optimized"
    warnings: Optional[List[str]] = None
    mapping_result: Optional[FieldMappingResult] = None
    performance_metrics: Optional[Dict[str, float]] = None

class OptimizedASHPDFFiller:
    """Optimized ASH PDF form filler with template-driven field mapping"""
    
    def __init__(self, template_path: str = "templates/ash_medical_form.pdf"):
        """Initialize optimized ASH PDF filler"""
        self.template_path = template_path
        self.blue = (0, 0, 1)  # Blue color for text
        
        # Initialize optimized mapper
        self.mapper = OptimizedASHFormFieldMapper(template_path)
        
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
        
        logger.info(f"🚀 Optimized ASH PDF Filler initialized with methods: {', '.join(self.available_methods)}")
        logger.info(f"📊 Template coverage: {len(self.mapper.field_mapping)} mapped fields")
    
    def fill_pdf(self, data: Dict[str, Any], output_path: str, 
                 method: str = "auto") -> OptimizedASHFillingResult:
        """Fill ASH PDF with data using optimized field mapping"""
        start_time = datetime.now()
        performance_metrics = {}
        
        try:
            # Step 1: Map data to PDF fields using optimized mapper
            mapping_start = datetime.now()
            mapping_result = self.mapper.map_data_to_pdf_fields(data)
            mapping_time = (datetime.now() - mapping_start).total_seconds()
            performance_metrics['mapping_time'] = mapping_time
            
            logger.info(f"📊 Mapped {mapping_result.mapped_count}/{mapping_result.total_data_fields} fields in {mapping_time:.3f}s")
            
            if not mapping_result.success or not mapping_result.mapped_fields:
                return OptimizedASHFillingResult(
                    success=False,
                    error="No fields could be mapped to PDF template",
                    mapping_result=mapping_result,
                    performance_metrics=performance_metrics,
                    processing_time=(datetime.now() - start_time).total_seconds()
                )
            
            # Step 2: Fill PDF using the best available method
            filling_start = datetime.now()
            
            if method == "auto":
                # Try methods in order of preference
                for fill_method in self.available_methods:
                    try:
                        result = self._fill_pdf_with_method(
                            mapping_result.mapped_fields, 
                            output_path, 
                            fill_method
                        )
                        if result.success:
                            result.method_used = f"optimized-{fill_method}"
                            break
                    except Exception as e:
                        logger.warning(f"Method {fill_method} failed: {e}")
                        continue
            else:
                result = self._fill_pdf_with_method(
                    mapping_result.mapped_fields, 
                    output_path, 
                    method
                )
                result.method_used = f"optimized-{method}"
            
            filling_time = (datetime.now() - filling_start).total_seconds()
            performance_metrics['filling_time'] = filling_time
            
            # Step 3: Finalize result
            total_time = (datetime.now() - start_time).total_seconds()
            performance_metrics['total_time'] = total_time
            
            result.mapping_result = mapping_result
            result.performance_metrics = performance_metrics
            result.processing_time = total_time
            
            if result.success:
                logger.info(f"✅ ASH PDF filled successfully: {result.fields_filled} fields in {total_time:.3f}s")
            else:
                logger.error(f"❌ ASH PDF filling failed: {result.error}")
            
            return result
            
        except Exception as e:
            error_msg = f"Optimized ASH PDF filling failed: {str(e)}"
            logger.error(error_msg)
            
            return OptimizedASHFillingResult(
                success=False,
                error=error_msg,
                processing_time=(datetime.now() - start_time).total_seconds(),
                performance_metrics=performance_metrics
            )
    
    def _fill_pdf_with_method(self, mapped_fields: Dict[str, Any], 
                             output_path: str, method: str) -> OptimizedASHFillingResult:
        """Fill PDF using specified method"""
        
        if method == "pymupdf" and PYMUPDF_AVAILABLE:
            return self._fill_with_pymupdf(mapped_fields, output_path)
        elif method == "pypdf2" and PYPDF2_AVAILABLE:
            return self._fill_with_pypdf2(mapped_fields, output_path)
        elif method == "reportlab" and REPORTLAB_AVAILABLE:
            return self._fill_with_reportlab(mapped_fields, output_path)
        else:
            return OptimizedASHFillingResult(
                success=False,
                error=f"Method '{method}' not available or not supported"
            )
    
    def _fill_with_pymupdf(self, mapped_fields: Dict[str, Any], 
                          output_path: str) -> OptimizedASHFillingResult:
        """Fill PDF using PyMuPDF (preferred method)"""
        try:
            doc = fitz.open(self.template_path)
            fields_filled = 0
            total_fields = 0
            warnings = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Get all form fields on this page
                for field in page.widgets():
                    total_fields += 1
                    field_name = field.field_name
                    
                    if field_name in mapped_fields:
                        try:
                            value = str(mapped_fields[field_name])
                            
                            # Handle different field types
                            if field.field_type == fitz.PDF_WIDGET_TYPE_TEXT:
                                field.field_value = value
                                field.update()
                                fields_filled += 1
                                
                            elif field.field_type == fitz.PDF_WIDGET_TYPE_CHECKBOX:
                                # Handle checkbox values
                                if value.lower() in ['yes', 'true', '1', 'on']:
                                    field.field_value = True
                                    field.update()
                                    fields_filled += 1
                                elif value.lower() in ['no', 'false', '0', 'off']:
                                    field.field_value = False
                                    field.update()
                                    fields_filled += 1
                                
                            elif field.field_type == fitz.PDF_WIDGET_TYPE_RADIOBUTTON:
                                # Handle radio button values
                                if value.lower() in ['yes', 'true', '1', 'on']:
                                    field.field_value = True
                                    field.update()
                                    fields_filled += 1
                                    
                        except Exception as e:
                            warnings.append(f"Failed to set field '{field_name}': {str(e)}")
            
            # Save the filled PDF
            doc.save(output_path)
            doc.close()
            
            return OptimizedASHFillingResult(
                success=True,
                output_path=output_path,
                fields_filled=fields_filled,
                total_fields=total_fields,
                method_used="pymupdf",
                warnings=warnings if warnings else None
            )
            
        except Exception as e:
            return OptimizedASHFillingResult(
                success=False,
                error=f"PyMuPDF filling failed: {str(e)}"
            )
    
    def _fill_with_pypdf2(self, mapped_fields: Dict[str, Any], 
                         output_path: str) -> OptimizedASHFillingResult:
        """Fill PDF using PyPDF2 (fallback method)"""
        try:
            reader = PdfReader(self.template_path)
            writer = PdfWriter()
            
            fields_filled = 0
            total_fields = 0
            warnings = []
            
            # Update form fields
            if reader.get_form_text_fields():
                total_fields = len(reader.get_form_text_fields())
                
                for field_name, current_value in reader.get_form_text_fields().items():
                    if field_name in mapped_fields:
                        try:
                            # PyPDF2 field update
                            writer.update_page_form_field_values(
                                reader.pages[0], 
                                {field_name: str(mapped_fields[field_name])}
                            )
                            fields_filled += 1
                        except Exception as e:
                            warnings.append(f"Failed to set field '{field_name}': {str(e)}")
            
            # Add all pages
            for page in reader.pages:
                writer.add_page(page)
            
            # Write output
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)
            
            return OptimizedASHFillingResult(
                success=True,
                output_path=output_path,
                fields_filled=fields_filled,
                total_fields=total_fields,
                method_used="pypdf2",
                warnings=warnings if warnings else None
            )
            
        except Exception as e:
            return OptimizedASHFillingResult(
                success=False,
                error=f"PyPDF2 filling failed: {str(e)}"
            )
    
    def _fill_with_reportlab(self, mapped_fields: Dict[str, Any], 
                            output_path: str) -> OptimizedASHFillingResult:
        """Fill PDF using ReportLab overlay (last resort method)"""
        try:
            # This is a simplified implementation
            # In practice, you'd need to position text based on field locations
            from reportlab.pdfgen import canvas
            
            c = canvas.Canvas(output_path, pagesize=letter)
            
            # Add mapped fields as text overlay (simplified)
            y_position = 750
            fields_filled = 0
            
            for field_name, value in mapped_fields.items():
                c.drawString(50, y_position, f"{field_name}: {value}")
                y_position -= 20
                fields_filled += 1
                
                if y_position < 50:  # Start new page if needed
                    c.showPage()
                    y_position = 750
            
            c.save()
            
            return OptimizedASHFillingResult(
                success=True,
                output_path=output_path,
                fields_filled=fields_filled,
                total_fields=len(mapped_fields),
                method_used="reportlab",
                warnings=["ReportLab overlay method used - field positioning may not be accurate"]
            )
            
        except Exception as e:
            return OptimizedASHFillingResult(
                success=False,
                error=f"ReportLab filling failed: {str(e)}"
            )
    
    def is_available(self) -> Tuple[bool, str]:
        """Check if optimized filler is available"""
        if not self.available_methods:
            return False, "No PDF processing libraries available"
        
        if not os.path.exists(self.template_path):
            return False, f"Template not found: {self.template_path}"
        
        return True, f"Available with methods: {', '.join(self.available_methods)}"
    
    def get_field_coverage_stats(self) -> Dict[str, Any]:
        """Get field coverage statistics"""
        coverage = self.mapper.get_mapping_coverage_report()
        return {
            'total_template_fields': coverage['total_template_fields'],
            'mapped_data_fields': coverage['mapped_fields'],
            'coverage_percentage': coverage['coverage_percentage'],
            'unmapped_template_fields_count': len(coverage['unmapped_template_fields']),
            'template_path': self.template_path
        }

# Convenience function for external use
def create_optimized_ash_filler(template_path: str = "templates/ash_medical_form.pdf") -> OptimizedASHPDFFiller:
    """Create an optimized ASH PDF filler"""
    return OptimizedASHPDFFiller(template_path)