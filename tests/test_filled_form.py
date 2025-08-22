#!/usr/bin/env python3
"""Test processing with a filled medical form"""

import requests
import os

def test_filled_form():
    """Test processing with what appears to be a filled medical form"""
    
    print("📄 Testing Filled Medical Form Processing")
    print("=" * 50)
    
    test_file = "uploads/PAU.pdf"
    
    if not os.path.exists(test_file):
        print(f"❌ Test file not found: {test_file}")
        return
    
    file_size = os.path.getsize(test_file)
    print(f"📄 Using test file: {test_file}")
    print(f"📊 File size: {file_size:,} bytes")
    
    # Step 1: Login
    print("\n1️⃣ Authenticating...")
    
    login_data = {
        "email": "physician@medicaldocai.com",  # Use the expected frontend credentials
        "password": "Physician123!"
    }
    
    login_response = requests.post('http://localhost:8000/auth/login', json=login_data)
    
    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.status_code}")
        return
    
    auth_data = login_response.json()
    token = auth_data['access_token']
    print(f"✅ Authenticated as: {auth_data['user']['full_name']}")
    
    # Step 2: Create session
    print("\n2️⃣ Creating processing session...")
    
    headers = {'Authorization': f'Bearer {token}'}
    
    session_response = requests.post('http://localhost:8000/api/secure/create-progress-session', 
                                   headers=headers)
    
    session_data = session_response.json()
    session_id = session_data['session_id']
    print(f"✅ Session created: {session_id[:8]}...")
    
    # Step 3: Process with different methods and formats
    test_configs = [
        {"method": "openai", "format": "mnr", "name": "OpenAI → MNR"},
        {"method": "legacy", "format": "mnr", "name": "Legacy OCR → MNR"},
        {"method": "auto", "format": "ash", "name": "Auto → ASH"},
    ]
    
    for i, config in enumerate(test_configs, 1):
        print(f"\n{i+2}️⃣ Test {i}: {config['name']}")
        
        with open(test_file, 'rb') as f:
            files = {
                'file': (os.path.basename(test_file), f, 'application/pdf')
            }
            
            params = {
                'method': config['method'],
                'output_format': config['format'],
                'enhanced': 'true',
                'use_optimized': 'false',
                'session_id': session_id
            }
            
            processing_headers = {
                'Authorization': f'Bearer {token}',
                'Origin': 'http://localhost:8080'
            }
            
            print(f"   📤 Processing with {config['method']} → {config['format']}")
            
            try:
                processing_response = requests.post(
                    'http://localhost:8000/api/secure/process-complete',
                    files=files,
                    params=params,
                    headers=processing_headers,
                    timeout=90
                )
                
                print(f"   📋 Response: {processing_response.status_code}")
                
                if processing_response.status_code == 200:
                    result = processing_response.json()
                    print(f"   ✅ Success: {result['success']}")
                    print(f"   📊 Method used: {result['method_used']}")
                    print(f"   ⏱️  Time: {result['processing_time']}ms")
                    print(f"   💰 Cost: ${result['cost']}")
                    print(f"   📄 Fields extracted: {result['fields_extracted']}")
                    print(f"   📝 Fields filled: {result['fields_filled']}")
                    
                    # Show sample extracted data
                    if result.get('extracted_data'):
                        data = result['extracted_data']
                        filled_fields = {k: v for k, v in data.items() 
                                       if v and not k.startswith('_') and v != "None" 
                                       and v != "" and v is not None}
                        
                        print(f"   📋 Non-empty fields: {len(filled_fields)}")
                        
                        # Show first few filled fields
                        for key, value in list(filled_fields.items())[:3]:
                            if isinstance(value, str) and len(value) > 40:
                                value = value[:40] + "..."
                            print(f"      • {key}: {value}")
                    
                    if result.get('mnr_pdf_url') or result.get('ash_pdf_url'):
                        url = result.get('mnr_pdf_url') or result.get('ash_pdf_url')
                        print(f"   📥 Download: {url}")
                
                else:
                    print(f"   ❌ Failed: {processing_response.status_code}")
                    try:
                        error = processing_response.json()
                        print(f"   📋 Error: {error.get('detail', 'Unknown error')}")
                    except:
                        pass
            
            except Exception as e:
                print(f"   ❌ Exception: {e}")
    
    print(f"\n🎯 Filled Form Processing Test Complete")

if __name__ == "__main__":
    test_filled_form()