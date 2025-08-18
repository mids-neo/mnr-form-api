#!/usr/bin/env python3
"""
ASH Filler Wrapper - Convenience functions for ASH PDF filling
Provides backward compatibility while using optimized filler by default
"""

import logging
from typing import Dict, Any, Optional
from .optimized_ash_filler import OptimizedASHPDFFiller, OptimizedASHFillingResult
from .ash_pdf_filler import ASHPDFFiller, ASHFillingResult

logger = logging.getLogger(__name__)

def fill_ash_pdf_optimized(data: Dict[str, Any], template_path: str, output_path: str, 
                          method: str = "auto", use_optimized: bool = True) -> OptimizedASHFillingResult:
    """
    Fill ASH PDF using optimized filler (preferred method)
    
    Args:
        data: ASH form data dictionary
        template_path: Path to ASH PDF template
        output_path: Path for output PDF
        method: PDF filling method ("auto", "pymupdf", "pypdf2", "reportlab")
        use_optimized: Whether to use optimized filler (True by default)
    
    Returns:
        OptimizedASHFillingResult with success status and metrics
    """
    try:
        if use_optimized:
            logger.info("🚀 Using optimized ASH PDF filler")
            filler = OptimizedASHPDFFiller(template_path)
            return filler.fill_pdf(data, output_path, method)
        else:
            logger.info("⚙️  Using legacy ASH PDF filler")
            # Fallback to legacy filler
            filler = ASHPDFFiller()
            legacy_result = filler.fill_pdf(data, template_path, output_path)
            
            # Convert legacy result to optimized format for consistency
            return OptimizedASHFillingResult(
                success=legacy_result.success,
                output_path=legacy_result.output_path,
                fields_filled=legacy_result.fields_filled,
                total_fields=legacy_result.total_fields,
                error=legacy_result.error,
                processing_time=legacy_result.processing_time,
                method_used=f"legacy-{legacy_result.method_used}",
                warnings=legacy_result.warnings,
                mapping_result=None,  # Not available in legacy
                performance_metrics={
                    'total_time': legacy_result.processing_time,
                    'legacy_mode': True
                }
            )
    except Exception as e:
        logger.error(f"❌ ASH PDF filling failed: {e}")
        return OptimizedASHFillingResult(
            success=False,
            error=str(e),
            processing_time=0.0
        )

def get_ash_filler_capabilities() -> Dict[str, Any]:
    """Get capabilities of available ASH PDF fillers"""
    try:
        # Test optimized filler
        optimized_filler = OptimizedASHPDFFiller("templates/ash_medical_form.pdf")
        is_available, status = optimized_filler.is_available()
        
        coverage_stats = optimized_filler.get_field_coverage_stats() if is_available else {}
        
        return {
            'optimized_filler': {
                'available': is_available,
                'status': status,
                'template_coverage': coverage_stats.get('coverage_percentage', 0),
                'mapped_fields': coverage_stats.get('mapped_data_fields', 0),
                'total_template_fields': coverage_stats.get('total_template_fields', 0)
            },
            'performance_mode': 'optimized' if is_available else 'legacy',
            'recommended_method': 'fill_ash_pdf_optimized'
        }
    except Exception as e:
        return {
            'optimized_filler': {
                'available': False,
                'status': f"Error: {e}",
                'template_coverage': 0
            },
            'performance_mode': 'error',
            'recommended_method': 'legacy_fallback'
        }

# Backward compatibility function
def fill_ash_pdf(data: Dict[str, Any], template_path: str, output_path: str) -> OptimizedASHFillingResult:
    """
    Backward compatibility wrapper for fill_ash_pdf
    Now uses optimized filler by default
    """
    return fill_ash_pdf_optimized(data, template_path, output_path, use_optimized=True)