#!/usr/bin/env python3
"""
Extract all form fields from ASH PDF template to establish source of truth
"""

import fitz  # PyMuPDF
import json
from typing import List, Dict, Any
import os

def extract_ash_pdf_fields(pdf_path: str) -> Dict[str, Any]:
    """Extract all form fields from ASH PDF template"""
    
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"ASH PDF template not found at: {pdf_path}")
    
    doc = fitz.open(pdf_path)
    
    # Get all form fields
    field_data = {}
    all_fields = []
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        
        # Get form fields on this page
        page_fields = page.widgets()
        
        for field in page_fields:
            field_info = {
                'name': field.field_name,
                'type': field.field_type_string,
                'page': page_num + 1,
                'rect': field.rect,
                'text_color': field.text_color,
                'fill_color': field.fill_color,
                'border_color': field.border_color,
                'max_length': getattr(field, 'text_maxlen', None),
                'multiline': getattr(field, 'text_multiline', False),
                'value': field.field_value if field.field_value else "",
                'options': getattr(field, 'choice_values', []) if hasattr(field, 'choice_values') else []
            }
            
            all_fields.append(field_info)
    
    # Organize fields by type and section
    field_data = {
        'total_fields': len(all_fields),
        'fields_by_type': {},
        'fields_by_page': {},
        'all_fields': all_fields,
        'field_names': [field['name'] for field in all_fields],
        'unique_field_names': sorted(list(set(field['name'] for field in all_fields if field['name'])))
    }
    
    # Group by field type
    for field in all_fields:
        field_type = field['type']
        if field_type not in field_data['fields_by_type']:
            field_data['fields_by_type'][field_type] = []
        field_data['fields_by_type'][field_type].append(field)
    
    # Group by page
    for field in all_fields:
        page_num = field['page']
        if page_num not in field_data['fields_by_page']:
            field_data['fields_by_page'][page_num] = []
        field_data['fields_by_page'][page_num].append(field)
    
    doc.close()
    return field_data

if __name__ == "__main__":
    # Path to ASH PDF template
    ash_template_path = "templates/ash_medical_form.pdf"
    
    print("🔍 Extracting form fields from ASH PDF template...")
    
    try:
        field_data = extract_ash_pdf_fields(ash_template_path)
        
        print(f"✅ Successfully extracted {field_data['total_fields']} form fields")
        print(f"📄 Found {len(field_data['unique_field_names'])} unique field names")
        
        # Print field types summary
        print("\n📊 Fields by Type:")
        for field_type, fields in field_data['fields_by_type'].items():
            print(f"  {field_type}: {len(fields)} fields")
        
        # Print pages summary
        print("\n📄 Fields by Page:")
        for page_num, fields in field_data['fields_by_page'].items():
            print(f"  Page {page_num}: {len(fields)} fields")
        
        # Print unique field names
        print(f"\n📝 Unique Field Names ({len(field_data['unique_field_names'])}):")
        for i, name in enumerate(field_data['unique_field_names'], 1):
            print(f"  {i:3d}. '{name}'")
        
        # Save detailed field data to JSON
        output_file = "ash_pdf_fields_analysis.json"
        with open(output_file, 'w') as f:
            json.dump(field_data, f, indent=2, default=str)
        
        print(f"\n💾 Detailed field analysis saved to: {output_file}")
        
        # Save just the field names for easy reference
        field_names_file = "ash_pdf_field_names.json"
        with open(field_names_file, 'w') as f:
            json.dump(field_data['unique_field_names'], f, indent=2)
        
        print(f"📝 Field names list saved to: {field_names_file}")
        
    except Exception as e:
        print(f"❌ Error extracting fields: {e}")