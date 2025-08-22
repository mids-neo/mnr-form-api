#!/usr/bin/env python3
"""
Comprehensive test for the optimized ASH PDF filler
"""

import json
import time
import os
from pipeline.optimized_ash_filler import OptimizedASHPDFFiller, create_optimized_ash_filler
from typing import Dict, Any

def create_comprehensive_ash_data() -> Dict[str, Any]:
    """Create comprehensive ASH data for testing"""
    return {
        # Patient Information Section
        'patient_name': 'Johnson, Sarah M',
        'patient_dob': '03/22/1985',
        'patient_id': 'ASH001234',
        'patient_phone': '555-0199',
        'patient_area_code': '555',
        'patient_address': '456 Oak Avenue',
        'patient_city_state_zip': 'Springfield, IL 62701',
        'patient_gender': 'F',
        
        # Insurance/Subscriber Section
        'subscriber_name': 'Sarah M Johnson',
        'subscriber_id': 'SUB456789',
        'health_plan': 'Aetna Better Health',
        'employer': 'Springfield Medical Center',
        'group_number': 'GRP789',
        'primary_insurance': True,
        'secondary_insurance': False,
        'work_related': False,
        'auto_related': False,
        
        # Provider Information Section
        'pcp_name': 'Dr. Robert Kim',
        'pcp_phone': '555-0234',
        'pcp_area_code': '555',
        'clinic_name': 'Healing Arts Acupuncture',
        'clinic_phone': '555-0345',
        'clinic_area_code': '555',
        'treating_practitioner': 'Dr. Lisa Chang, LAc',
        'clinic_address': '789 Wellness Blvd',
        'clinic_city_state_zip': 'Springfield, IL 62702',
        'fax_area_code': '555',
        'fax_number': '555-0346',
        
        # Condition Information Section
        'condition_1': 'Fibromyalgia',
        'condition_2': 'Chronic Fatigue Syndrome',
        'condition_3': 'Tension Headaches',
        'condition_4': 'Sleep Disorders',
        'icd_code_1': 'M79.3',
        'icd_code_2': 'R53.82',
        'icd_code_3': 'G44.209',
        'icd_code_4': 'G47.9',
        'office_visit_date': '01/15/2025',
        'last_office_visit': '01/01/2025',
        'total_visits': '15',
        
        # Chief Complaints Section - Set 1
        'chief_complaint_1': 'Widespread muscle pain and stiffness',
        'chief_complaint_1_location': 'Bilateral shoulders, neck, lower back',
        'chief_complaint_1_date': '09/15/2024',
        'chief_complaint_1_pain_level': '8',
        'chief_complaint_1_frequency': 'Constant',
        'chief_complaint_1_cause': 'Unknown onset, gradual progression',
        'chief_complaint_1_relief_duration': '4-6 hours post treatment',
        'chief_complaint_1_observation': 'Visible muscle tension, guarded movement',
        'chief_complaint_1_tenderness': '4',
        'chief_complaint_1_range_of_motion': 'Limited neck rotation 40%',
        
        # Chief Complaints Section - Set 2
        'chief_complaint_2': 'Chronic fatigue and brain fog',
        'chief_complaint_2_location': 'Systemic',
        'chief_complaint_2_date': '09/15/2024',
        'chief_complaint_2_pain_level': 'N/A',
        'chief_complaint_2_frequency': 'Daily',
        'chief_complaint_2_cause': 'Associated with fibromyalgia',
        'chief_complaint_2_relief_duration': 'Temporary improvement with treatment',
        'chief_complaint_2_observation': 'Appears fatigued, difficulty concentrating',
        'chief_complaint_2_tenderness': 'N/A',
        'chief_complaint_2_range_of_motion': 'Normal',
        
        # Chief Complaints Section - Set 3
        'chief_complaint_3': 'Tension headaches',
        'chief_complaint_3_location': 'Bilateral temporal and occipital regions',
        'chief_complaint_3_date': '10/01/2024',
        'chief_complaint_3_pain_level': '6',
        'chief_complaint_3_frequency': '3-4 times per week',
        'chief_complaint_3_cause': 'Stress and muscle tension',
        'chief_complaint_3_relief_duration': '2-3 hours post treatment',
        'chief_complaint_3_observation': 'Tense facial muscles, light sensitivity',
        'chief_complaint_3_tenderness': '2',
        'chief_complaint_3_range_of_motion': 'Limited neck extension',
        
        # Treatment Plan Section
        'new_pt_exam': False,
        'est_pt_exam': True,
        'exam_day': '15',
        'exam_month': '01',
        'exam_year': '2025',
        'from_day': '15',
        'from_month': '01',
        'from_year': '2025',
        'through_day': '15',
        'through_month': '03',
        'through_year': '2025',
        'total_office_visits': '16',
        'total_therapies': '32',
        'nj_acu_units': 'N/A',
        'nj_therapy_units': 'N/A',
        
        # Therapy Types Section
        'hot_cold_packs': True,
        'infrared': True,
        'massage': True,
        'therapeutic_exercise': False,
        'ultrasound': False,
        'other_therapy': True,
        'other_therapy_description': 'Electro-acupuncture with 2Hz frequency',
        'special_services': 'None',
        
        # Treatment Response & Goals Section
        'response_to_treatment': 'Patient reports 70% improvement in pain levels and 50% improvement in energy levels since beginning comprehensive treatment plan',
        'treatment_goals': 'Reduce fibromyalgia pain to manageable levels (≤4/10), improve energy and sleep quality, reduce headache frequency by 75%',
        'progress_measurement': 'Bi-weekly pain and fatigue assessments using validated scales, sleep quality tracking, functional capacity evaluations',
        
        # Activities and Functional Outcomes Section
        'activity_1': 'Light exercise/yoga',
        'measurements_1': '20 minutes, 3x per week',
        'how_changed_1': 'Increased from 10 minutes 1x per week',
        'activity_2': 'Household tasks',
        'measurements_2': '2-3 hours daily',
        'how_changed_2': 'Increased from 30 minutes daily',
        
        # Functional Assessment Section
        'functional_tool_name_1': 'Fibromyalgia Impact Questionnaire',
        'functional_body_area_1': 'Whole body functional assessment',
        'functional_date_1': '01/01/2025',
        'functional_score_1': '45/100',
        'functional_tool_name_2': 'Multidimensional Fatigue Inventory',
        'functional_body_area_2': 'General fatigue assessment',
        'functional_date_2': '01/01/2025',
        'functional_score_2': '65/100',
        
        # Medical Information Section
        'pain_medication_changes': 'Reduced gabapentin from 300mg 3x daily to 100mg 2x daily. Added magnesium supplement 400mg daily.',
        'other_comments_1': 'Patient shows excellent compliance with treatment plan and home care recommendations. Reports improved sleep quality.',
        'other_comments_2': 'Family support system is strong. Patient actively participates in fibromyalgia support group.',
        'conditions': 'Fibromyalgia, CFS, tension headaches, sleep disorders',
        
        # Medical Care Questions (Yes/No)
        'physician_care_yes': True,
        'physician_care_no': False,
        'pregnant_yes': False,
        'pregnant_no': True,
        'pregnant_weeks': '',
        'physician_aware_pediatric': '',  # Not applicable
        'pregnancy_practitioner_yes': False,
        'pregnancy_practitioner_no': True,
        'required_pregnant': 'No',
        
        # Vital Signs Section
        'height': '5\'6"',
        'weight': '145 lbs',
        'blood_pressure_1': '118/75',
        'blood_pressure_2': '',
        'temperature': '98.4°F',
        'bmi': '23.4',
        'tobacco_use': 'No',
        
        # Traditional Medicine Section
        'tongue_signs': 'Slightly pale with thin white coating on root',
        'pulse_signs_right': 'Deep, slightly weak',
        'pulse_signs_left': 'Wiry in liver position',
        
        # Form Completion Section
        'signature_date': '01/15/2025',
        'chronic_back_pain_attestation': False,  # Not applicable for fibromyalgia
        
        # Additional metadata
        '_processing_method': 'optimized_ash_filler',
        '_test_data': True
    }

def test_optimized_filler_performance():
    """Test the performance of the optimized ASH PDF filler"""
    print("🚀 Testing Optimized ASH PDF Filler")
    print("=" * 60)
    
    # Initialize filler
    try:
        start_init = time.time()
        filler = create_optimized_ash_filler()
        init_time = time.time() - start_init
        print(f"✅ Filler initialized in {init_time:.3f}s")
        
        # Check availability
        is_available, status_msg = filler.is_available()
        print(f"📊 Status: {status_msg}")
        
        if not is_available:
            print(f"❌ Filler not available: {status_msg}")
            return None
            
    except Exception as e:
        print(f"❌ Failed to initialize filler: {e}")
        return None
    
    # Get field coverage stats
    coverage_stats = filler.get_field_coverage_stats()
    print(f"\n📈 Field Coverage Statistics:")
    print(f"   Template Fields: {coverage_stats['total_template_fields']}")
    print(f"   Mapped Fields: {coverage_stats['mapped_data_fields']}")
    print(f"   Coverage: {coverage_stats['coverage_percentage']:.1f}%")
    
    # Test PDF filling
    sample_data = create_comprehensive_ash_data()
    output_path = "test_filled_ash_form.pdf"
    
    print(f"\n🔧 Testing PDF filling with {len([k for k in sample_data.keys() if not k.startswith('_')])} data fields")
    
    start_filling = time.time()
    result = filler.fill_pdf(sample_data, output_path)
    filling_time = time.time() - start_filling
    
    # Display results
    print(f"\n📊 Filling Results:")
    print(f"   Success: {'✅' if result.success else '❌'} {result.success}")
    print(f"   Total Time: {filling_time:.3f}s")
    print(f"   Processing Time: {result.processing_time:.3f}s")
    print(f"   Method Used: {result.method_used}")
    print(f"   Fields Filled: {result.fields_filled}")
    print(f"   Total PDF Fields: {result.total_fields}")
    
    if result.total_fields > 0:
        fill_rate = result.fields_filled / result.total_fields * 100
        print(f"   Fill Rate: {fill_rate:.1f}%")
    
    # Display performance metrics
    if result.performance_metrics:
        print(f"\n⚡ Performance Metrics:")
        for metric, value in result.performance_metrics.items():
            print(f"   {metric.replace('_', ' ').title()}: {value:.3f}s")
    
    # Display mapping results
    if result.mapping_result:
        mapping = result.mapping_result
        print(f"\n🔗 Mapping Results:")
        print(f"   Data Fields: {mapping.total_data_fields}")
        print(f"   Mapped Fields: {mapping.mapped_count}")
        print(f"   Mapping Rate: {mapping.mapped_count/mapping.total_data_fields*100:.1f}%")
        print(f"   Unmapped Fields: {len(mapping.unmapped_fields)}")
        print(f"   Processing Time: {mapping.processing_time:.3f}s")
        
        if mapping.unmapped_fields:
            print(f"   Unmapped: {', '.join(mapping.unmapped_fields[:5])}")
            if len(mapping.unmapped_fields) > 5:
                print(f"   ... and {len(mapping.unmapped_fields) - 5} more")
    
    # Display warnings
    if result.warnings:
        print(f"\n⚠️  Warnings ({len(result.warnings)}):")
        for warning in result.warnings[:5]:
            print(f"   - {warning}")
        if len(result.warnings) > 5:
            print(f"   ... and {len(result.warnings) - 5} more")
    
    # Check if output file was created
    if result.success and os.path.exists(output_path):
        file_size = os.path.getsize(output_path)
        print(f"\n📄 Output file created: {output_path} ({file_size:,} bytes)")
    elif result.success:
        print(f"\n⚠️  Success reported but output file not found: {output_path}")
    
    if not result.success:
        print(f"\n❌ Error: {result.error}")
    
    return result

def benchmark_performance():
    """Benchmark the performance improvements"""
    print(f"\n🏁 Performance Benchmark")
    print("-" * 40)
    
    try:
        filler = create_optimized_ash_filler()
        sample_data = create_comprehensive_ash_data()
        
        # Run multiple iterations for average performance
        iterations = 3
        total_time = 0
        total_fields = 0
        
        for i in range(iterations):
            output_path = f"benchmark_test_{i+1}.pdf"
            start_time = time.time()
            
            result = filler.fill_pdf(sample_data, output_path)
            
            iteration_time = time.time() - start_time
            total_time += iteration_time
            
            if result.success:
                total_fields += result.fields_filled
            
            # Clean up test files
            if os.path.exists(output_path):
                os.remove(output_path)
            
            print(f"   Iteration {i+1}: {iteration_time:.3f}s ({result.fields_filled} fields)")
        
        avg_time = total_time / iterations
        avg_fields = total_fields / iterations
        
        print(f"\n📊 Benchmark Results:")
        print(f"   Iterations: {iterations}")
        print(f"   Average Time: {avg_time:.3f}s")
        print(f"   Average Fields Filled: {avg_fields:.0f}")
        print(f"   Fields per Second: {avg_fields/avg_time:.0f}")
        
    except Exception as e:
        print(f"❌ Benchmark failed: {e}")

if __name__ == "__main__":
    # Run comprehensive test
    result = test_optimized_filler_performance()
    
    # Run performance benchmark
    if result and result.success:
        benchmark_performance()
    
    print(f"\n✅ Testing complete!")
    
    if result and result.success:
        print(f"🎉 Optimized ASH PDF filler is working correctly!")
        print(f"📈 Performance: {result.fields_filled} fields filled in {result.processing_time:.3f}s")
    else:
        print("⚠️  Some issues were found - check the output above")