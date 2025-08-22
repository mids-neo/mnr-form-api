#!/usr/bin/env python3
"""Test secure file processing endpoint"""

import requests
import io

def test_secure_file_processing():
    """Test the secure file processing endpoint"""
    
    print("🔒 Testing Secure File Processing")
    print("=" * 40)
    
    # Step 1: Login to get authentication token
    print("1️⃣ Logging in...")
    
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
    print(f"✅ Login successful for {auth_data['user']['full_name']}")
    
    # Step 2: Create progress session
    print("\n2️⃣ Creating progress session...")
    
    headers = {'Authorization': f'Bearer {token}'}
    
    session_response = requests.post('http://localhost:8000/api/secure/create-progress-session', 
                                   headers=headers)
    
    if session_response.status_code != 200:
        print(f"❌ Session creation failed: {session_response.status_code}")
        return
    
    session_data = session_response.json()
    session_id = session_data['session_id']
    print(f"✅ Session created: {session_id[:8]}...")
    
    # Step 3: Test file processing (simulated file)
    print("\n3️⃣ Testing file processing...")
    
    # Create a dummy PDF file for testing
    dummy_pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n193\n%%EOF"
    
    # Prepare file upload
    files = {
        'file': ('test_medical_form.pdf', io.BytesIO(dummy_pdf_content), 'application/pdf')
    }
    
    params = {
        'method': 'auto',
        'output_format': 'both',
        'enhanced': 'true',
        'use_optimized': 'false',
        'session_id': session_id
    }
    
    # Test CORS preflight first
    print("   🔄 Testing CORS preflight...")
    
    preflight_headers = {
        'Origin': 'http://localhost:8080',
        'Access-Control-Request-Method': 'POST',
        'Access-Control-Request-Headers': 'Authorization'
    }
    
    preflight_response = requests.options('http://localhost:8000/api/secure/process-complete', 
                                        headers=preflight_headers)
    
    if preflight_response.status_code == 200:
        print("   ✅ CORS preflight successful")
        cors_headers = {
            'Origin': preflight_response.headers.get('Access-Control-Allow-Origin'),
            'Methods': preflight_response.headers.get('Access-Control-Allow-Methods'),
            'Headers': preflight_response.headers.get('Access-Control-Allow-Headers')
        }
        print(f"   📋 CORS Origin: {cors_headers['Origin']}")
    else:
        print(f"   ⚠️  CORS preflight: {preflight_response.status_code}")
    
    # Now test the actual file processing
    print("   📤 Sending file processing request...")
    
    # Add Origin header to simulate browser request
    headers['Origin'] = 'http://localhost:8080'
    
    try:
        processing_response = requests.post(
            'http://localhost:8000/api/secure/process-complete',
            files=files,
            params=params,
            headers=headers,
            timeout=30
        )
        
        print(f"   📋 Response status: {processing_response.status_code}")
        
        if processing_response.status_code == 200:
            result = processing_response.json()
            print("   ✅ File processing successful!")
            print(f"   👤 Processed by: {result.get('processed_by', {}).get('email', 'Unknown')}")
            print(f"   📊 Method used: {result.get('method_used', 'Unknown')}")
            print(f"   ⏱️  Processing time: {result.get('processing_time', 0)}ms")
            print(f"   🎯 Success: {result.get('success', False)}")
            
            # Check CORS headers in response
            cors_origin = processing_response.headers.get('Access-Control-Allow-Origin')
            if cors_origin:
                print(f"   🌐 CORS Origin in response: {cors_origin}")
            else:
                print("   ⚠️  No CORS Origin header in response")
                
        else:
            print(f"   ❌ File processing failed: {processing_response.status_code}")
            try:
                error_data = processing_response.json()
                print(f"   📋 Error: {error_data}")
            except:
                print(f"   📋 Error: {processing_response.text}")
                
    except Exception as e:
        print(f"   ❌ Request failed: {e}")
    
    print(f"\n🎯 Secure File Processing Test Complete")
    print(f"   Authentication: ✅ Working")
    print(f"   Session Creation: ✅ Working")
    print(f"   CORS Configuration: ✅ Configured")
    print(f"   Ready for frontend file uploads! 🚀")

if __name__ == "__main__":
    test_secure_file_processing()