#!/usr/bin/env python3
"""Test actual medical form processing with real PDF"""

import requests
import os

def test_real_processing():
    """Test processing with an actual MNR form PDF"""
    
    print("🏥 Testing Real Medical Form Processing")
    print("=" * 50)
    
    # Step 1: Find a real PDF file to test with
    test_files = [
        "Patient C.S..pdf",  # From the original samples
        "mnr_form.pdf",     # Template file
        "ash_medical_form.pdf"  # ASH template
    ]
    
    test_file = None
    for filename in test_files:
        if os.path.exists(filename):
            test_file = filename
            break
        # Check in common directories
        for dir_path in [".", "templates", "../"]:
            full_path = os.path.join(dir_path, filename)
            if os.path.exists(full_path):
                test_file = full_path
                break
        if test_file:
            break
    
    if not test_file:
        print("❌ No test PDF files found. Available files:")
        for item in os.listdir('.'):
            if item.endswith('.pdf'):
                print(f"   📄 {item}")
        return
    
    print(f"📄 Using test file: {test_file}")
    file_size = os.path.getsize(test_file)
    print(f"📊 File size: {file_size:,} bytes")
    
    # Step 2: Login
    print("\n1️⃣ Authenticating...")
    
    login_data = {
        "email": "test@example.com",
        "password": "TestPassword123!"
    }
    
    login_response = requests.post('http://localhost:8000/auth/login', json=login_data)
    
    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.status_code}")
        return
    
    auth_data = login_response.json()
    token = auth_data['access_token']
    print(f"✅ Authenticated as: {auth_data['user']['full_name']}")
    
    # Step 3: Create session
    print("\n2️⃣ Creating processing session...")
    
    headers = {'Authorization': f'Bearer {token}'}
    
    session_response = requests.post('http://localhost:8000/api/secure/create-progress-session', 
                                   headers=headers)
    
    if session_response.status_code != 200:
        print(f"❌ Session creation failed: {session_response.status_code}")
        return
    
    session_data = session_response.json()
    session_id = session_data['session_id']
    print(f"✅ Session created: {session_id[:8]}...")
    
    # Step 4: Process the real PDF
    print(f"\n3️⃣ Processing real medical form: {os.path.basename(test_file)}")
    
    with open(test_file, 'rb') as f:
        files = {
            'file': (os.path.basename(test_file), f, 'application/pdf')
        }
        
        params = {
            'method': 'auto',      # Try OpenAI first, fallback to legacy
            'output_format': 'mnr', # Start with MNR format
            'enhanced': 'true',
            'use_optimized': 'false',
            'session_id': session_id
        }
        
        processing_headers = {
            'Authorization': f'Bearer {token}',
            'Origin': 'http://localhost:8080'
        }
        
        print("   📤 Uploading and processing...")
        print(f"   📊 Method: {params['method']}")
        print(f"   📄 Output format: {params['output_format']}")
        
        try:
            processing_response = requests.post(
                'http://localhost:8000/api/secure/process-complete',
                files=files,
                params=params,
                headers=processing_headers,
                timeout=60  # Longer timeout for real processing
            )
            
            print(f"   📋 Response status: {processing_response.status_code}")
            
            if processing_response.status_code == 200:
                result = processing_response.json()
                print("   ✅ Processing successful!")
                print(f"   👤 Processed by: {result['processed_by']['email']}")
                print(f"   📊 Method used: {result['method_used']}")
                print(f"   ⏱️  Processing time: {result['processing_time']}ms")
                print(f"   💰 Cost: ${result['cost']}")
                print(f"   📄 Fields extracted: {result['fields_extracted']}")
                print(f"   📝 Fields filled: {result['fields_filled']}")
                print(f"   🎯 Success: {result['success']}")
                
                # Show extracted data summary
                if result.get('extracted_data'):
                    data = result['extracted_data']
                    print(f"   📋 Extracted data summary:")
                    for key, value in list(data.items())[:5]:  # Show first 5 fields
                        if key.startswith('_'):
                            continue
                        if isinstance(value, str) and len(value) > 50:
                            value = value[:50] + "..."
                        print(f"      • {key}: {value}")
                    
                    if len(data) > 5:
                        print(f"      ... and {len(data) - 5} more fields")
                
                # Check for download URL
                if result.get('mnr_pdf_url'):
                    print(f"   📥 Download URL: {result['mnr_pdf_url']}")
                
            else:
                print(f"   ❌ Processing failed: {processing_response.status_code}")
                try:
                    error_data = processing_response.json()
                    print(f"   📋 Error: {error_data}")
                except:
                    print(f"   📋 Error text: {processing_response.text[:200]}")
        
        except Exception as e:
            print(f"   ❌ Request failed: {e}")
    
    print(f"\n🎯 Real Processing Test Complete")

if __name__ == "__main__":
    test_real_processing()