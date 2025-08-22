#!/usr/bin/env python3
"""
Test integration of optimized ASH filler with pipeline
"""

import json
from pipeline import (
    create_optimized_ash_filler,
    OptimizedASHPDFFiller,
    fill_ash_pdf,  # Should now use optimized version
    get_pipeline_capabilities
)

def test_integration():
    """Test that optimized filler integrates properly"""
    print("🧪 Testing Optimized ASH Filler Integration")
    print("=" * 50)
    
    # Test 1: Direct optimized filler creation
    try:
        filler = create_optimized_ash_filler()
        print("✅ Direct optimized filler creation: SUCCESS")
        
        coverage = filler.get_field_coverage_stats()
        print(f"   - Template coverage: {coverage['coverage_percentage']:.1f}%")
        print(f"   - Mapped fields: {coverage['mapped_data_fields']}")
    except Exception as e:
        print(f"❌ Direct optimized filler creation: FAILED - {e}")
    
    # Test 2: Pipeline integration
    try:
        capabilities = get_pipeline_capabilities()
        print("\n✅ Pipeline capabilities access: SUCCESS")
        print(f"   - Available stages: {list(capabilities.keys()) if capabilities else 'None'}")
    except Exception as e:
        print(f"\n❌ Pipeline capabilities access: FAILED - {e}")
    
    # Test 3: fill_ash_pdf function (should use optimized version)
    try:
        # Create minimal test data
        test_data = {
            'patient_name': 'Integration Test Patient',
            'patient_dob': '01/01/1990',
            'patient_phone': '555-TEST'
        }
        
        template_path = "templates/ash_medical_form.pdf"
        output_path = "test_integration_ash.pdf"
        
        result = fill_ash_pdf(test_data, template_path, output_path)
        
        print(f"\n✅ fill_ash_pdf integration: SUCCESS")
        print(f"   - Method used: {result.method_used}")
        print(f"   - Fields filled: {result.fields_filled}")
        print(f"   - Processing time: {result.processing_time:.3f}s")
        print(f"   - Uses optimized: {'optimized' in result.method_used}")
        
        # Clean up test file
        import os
        if os.path.exists(output_path):
            os.remove(output_path)
            
    except Exception as e:
        print(f"\n❌ fill_ash_pdf integration: FAILED - {e}")
    
    print(f"\n🎉 Integration testing complete!")

if __name__ == "__main__":
    test_integration()