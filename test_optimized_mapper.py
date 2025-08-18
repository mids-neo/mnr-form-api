#!/usr/bin/env python3
"""
Test script for the optimized ASH form field mapper
"""

import json
import time
from pipeline.optimized_ash_mapper import OptimizedASHFormFieldMapper, create_optimized_ash_mapper
from typing import Dict, Any

def create_sample_ash_data() -> Dict[str, Any]:
    """Create sample ASH data for testing"""
    return {
        # Patient Information
        'patient_name': 'Smith, John A',
        'patient_dob': '01/15/1980',
        'patient_id': 'P123456',
        'patient_phone': '555-0123',
        'patient_area_code': '555',
        'patient_address': '123 Main Street',
        'patient_city_state_zip': 'Anytown, NY 12345',
        'patient_gender': 'M',
        
        # Insurance Information
        'subscriber_name': 'John A Smith',
        'subscriber_id': 'SUB789012',
        'health_plan': 'Blue Cross Blue Shield',
        'employer': 'Tech Company Inc',
        'group_number': 'GRP456',
        'primary_insurance': True,
        'work_related': False,
        'auto_related': False,
        
        # Provider Information
        'pcp_name': 'Dr. Jane Wilson',
        'pcp_phone': '555-0456',
        'pcp_area_code': '555',
        'clinic_name': 'Wellness Acupuncture Clinic',
        'treating_practitioner': 'Dr. Michael Chen, LAc',
        
        # Conditions
        'condition_1': 'Chronic Lower Back Pain',
        'condition_2': 'Sciatica',
        'icd_code_1': 'M54.5',
        'icd_code_2': 'M54.3',
        'office_visit_date': '12/01/2024',
        'last_office_visit': '11/15/2024',
        'total_visits': '8',
        
        # Chief Complaints
        'chief_complaint_1': 'Lower back pain',
        'chief_complaint_1_location': 'Lumbar spine L4-L5',
        'chief_complaint_1_date': '08/01/2024',
        'chief_complaint_1_pain_level': '7',
        'chief_complaint_1_frequency': 'Daily',
        'chief_complaint_1_cause': 'Work-related repetitive motion',
        'chief_complaint_1_relief_duration': '2-3 hours after treatment',
        'chief_complaint_1_observation': 'Limited range of motion',
        'chief_complaint_1_tenderness': '3',
        'chief_complaint_1_range_of_motion': 'Reduced flexion 50%',
        
        # Treatment Plan
        'new_pt_exam': True,
        'exam_day': '01',
        'exam_month': '12',
        'exam_year': '2024',
        'from_day': '01',
        'from_month': '12',
        'from_year': '2024',
        'through_day': '31',
        'through_month': '01',
        'through_year': '2025',
        'total_office_visits': '12',
        'total_therapies': '24',
        
        # Therapies
        'hot_cold_packs': True,
        'infrared': False,
        'massage': True,
        'therapeutic_exercise': True,
        'ultrasound': False,
        
        # Treatment Response
        'response_to_treatment': 'Patient reports 60% improvement in pain levels since beginning treatment',
        'treatment_goals': 'Reduce pain to 3/10, restore full range of motion, return to normal activities',
        'progress_measurement': 'Weekly pain scale assessments, ROM measurements, functional capacity evaluation',
        
        # Activities
        'activity_1': 'Walking',
        'measurements_1': '30 minutes daily',
        'how_changed_1': 'Increased from 10 minutes to 30 minutes',
        'activity_2': 'Lifting',
        'measurements_2': '15 lbs maximum',
        'how_changed_2': 'Increased from 5 lbs to 15 lbs',
        
        # Medical Information
        'pain_medication_changes': 'Reduced ibuprofen from 800mg 3x daily to 400mg 2x daily',
        'other_comments_1': 'Patient is highly compliant with treatment recommendations',
        'other_comments_2': 'Shows good progress with home exercise program',
        
        # Yes/No Questions
        'physician_care_yes': True,
        'physician_care_no': False,
        'pregnant_no': True,
        'pregnant_yes': False,
        
        # Vital Signs
        'height': '5\'10"',
        'weight': '185 lbs',
        'blood_pressure_1': '120/80',
        'temperature': '98.6°F',
        'bmi': '26.5',
        'tobacco_use': 'No',
        
        # Traditional Medicine
        'tongue_signs': 'Pale with thick white coating',
        'pulse_signs_right': 'Slow, deep',
        'pulse_signs_left': 'Weak, thready',
        
        # Form Completion
        'signature_date': '12/15/2024',
        'chronic_back_pain_attestation': True,
        
        # Test unmapped fields
        'unmapped_field_1': 'This should not be mapped',
        'unmapped_field_2': 'Neither should this',
        
        # Metadata (should be ignored)
        '_original_data': 'some metadata',
        '_processing_timestamp': '2024-12-15T10:30:00Z'
    }

def test_mapper_performance():
    """Test the performance of the optimized mapper"""
    print("🚀 Testing Optimized ASH Form Field Mapper")
    print("=" * 60)
    
    # Initialize mapper
    try:
        start_init = time.time()
        mapper = create_optimized_ash_mapper()
        init_time = time.time() - start_init
        print(f"✅ Mapper initialized in {init_time:.3f}s")
    except Exception as e:
        print(f"❌ Failed to initialize mapper: {e}")
        return
    
    # Test mapping
    sample_data = create_sample_ash_data()
    print(f"\n📊 Testing with {len(sample_data)} data fields")
    
    start_mapping = time.time()
    result = mapper.map_data_to_pdf_fields(sample_data)
    mapping_time = time.time() - start_mapping
    
    # Display results
    print(f"\n🔍 Mapping Results:")
    print(f"   Success: {result.success}")
    print(f"   Processing Time: {result.processing_time:.3f}s")
    print(f"   Total Time: {mapping_time:.3f}s")
    print(f"   Data Fields: {result.total_data_fields}")
    print(f"   Mapped Fields: {result.mapped_count}")
    print(f"   Mapping Rate: {result.mapped_count/result.total_data_fields*100:.1f}%")
    print(f"   Unmapped Fields: {len(result.unmapped_fields)}")
    print(f"   Warnings: {len(result.warnings)}")
    
    if result.unmapped_fields:
        print(f"\n⚠️  Unmapped Fields ({len(result.unmapped_fields)}):")
        for field in result.unmapped_fields[:10]:
            suggestions = mapper.get_field_suggestions(field)
            if suggestions:
                print(f"   - {field} → Suggestions: {suggestions[:3]}")
            else:
                print(f"   - {field}")
        if len(result.unmapped_fields) > 10:
            print(f"   ... and {len(result.unmapped_fields) - 10} more")
    
    if result.warnings:
        print(f"\n⚠️  Warnings ({len(result.warnings)}):")
        for warning in result.warnings[:5]:
            print(f"   - {warning}")
        if len(result.warnings) > 5:
            print(f"   ... and {len(result.warnings) - 5} more")
    
    # Show sample mapped fields
    print(f"\n📝 Sample Mapped Fields ({min(10, len(result.mapped_fields))}):")
    for i, (pdf_field, value) in enumerate(list(result.mapped_fields.items())[:10]):
        print(f"   {i+1:2d}. '{pdf_field}' = '{value}'")
    
    if len(result.mapped_fields) > 10:
        print(f"   ... and {len(result.mapped_fields) - 10} more")
    
    return result

def test_coverage_report():
    """Test the coverage reporting functionality"""
    print(f"\n📊 Testing Coverage Report")
    print("-" * 40)
    
    try:
        mapper = create_optimized_ash_mapper()
        coverage = mapper.get_mapping_coverage_report()
        
        print(f"Template Fields: {coverage['total_template_fields']}")
        print(f"Mapped Fields: {coverage['mapped_fields']}")
        print(f"Coverage: {coverage['coverage_percentage']:.1f}%")
        print(f"Unmapped Template Fields: {len(coverage['unmapped_template_fields'])}")
        
        if coverage['unmapped_template_fields']:
            print(f"\n🔍 Unmapped Template Fields ({len(coverage['unmapped_template_fields'])}):")
            for field in coverage['unmapped_template_fields'][:10]:
                print(f"   - '{field}'")
            if len(coverage['unmapped_template_fields']) > 10:
                print(f"   ... and {len(coverage['unmapped_template_fields']) - 10} more")
        
        # Save coverage report
        with open('ash_mapper_coverage_report.json', 'w') as f:
            json.dump(coverage, f, indent=2)
        print(f"\n💾 Coverage report saved to: ash_mapper_coverage_report.json")
        
    except Exception as e:
        print(f"❌ Coverage test failed: {e}")

if __name__ == "__main__":
    # Run performance test
    result = test_mapper_performance()
    
    # Run coverage test
    test_coverage_report()
    
    print(f"\n✅ Testing complete!")
    
    if result and result.success:
        print(f"🎉 Mapper is working correctly with {result.mapped_count} fields mapped")
    else:
        print("⚠️  Some issues were found - check the output above")