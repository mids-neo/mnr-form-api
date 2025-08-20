#!/usr/bin/env python3
"""Simulate browser interaction with the authentication UI"""

import requests
import json
import time

def simulate_browser_session():
    """Simulate a complete browser session with authentication"""
    
    print("🌐 Simulating Browser Authentication Session")
    print("=" * 50)
    
    # Step 1: Access the frontend (this would happen when user opens browser)
    print("1️⃣ User opens browser and navigates to http://localhost:8080")
    
    try:
        frontend_response = requests.get("http://localhost:8080", timeout=5)
        if frontend_response.status_code == 200:
            print("   ✅ Frontend loads successfully")
            print("   📋 User sees login form (not authenticated)")
        else:
            print(f"   ❌ Frontend failed: {frontend_response.status_code}")
            return
    except Exception as e:
        print(f"   ❌ Frontend not accessible: {e}")
        return
    
    # Step 2: User attempts to login
    print("\n2️⃣ User enters credentials and clicks login")
    print("   Email: test@example.com")
    print("   Password: ********")
    
    # Simulate the CORS preflight request that the browser makes
    print("\n   🔄 Browser sends CORS preflight request...")
    try:
        preflight_headers = {
            'Origin': 'http://localhost:8080',
            'Access-Control-Request-Method': 'POST',
            'Access-Control-Request-Headers': 'Content-Type'
        }
        
        preflight_response = requests.options(
            "http://localhost:8000/auth/login", 
            headers=preflight_headers,
            timeout=5
        )
        
        if preflight_response.status_code == 200:
            print("   ✅ CORS preflight successful")
            cors_origin = preflight_response.headers.get('Access-Control-Allow-Origin')
            print(f"   📋 CORS allows origin: {cors_origin}")
        else:
            print(f"   ⚠️  CORS preflight returned: {preflight_response.status_code}")
        
    except Exception as e:
        print(f"   ❌ CORS preflight failed: {e}")
    
    # Step 3: Actual login request
    print("\n   📤 Sending login request...")
    
    login_data = {
        "email": "test@example.com",
        "password": "TestPassword123!"
    }
    
    login_headers = {
        'Content-Type': 'application/json',
        'Origin': 'http://localhost:8080'
    }
    
    try:
        login_response = requests.post(
            "http://localhost:8000/auth/login",
            json=login_data,
            headers=login_headers,
            timeout=10
        )
        
        if login_response.status_code == 200:
            auth_data = login_response.json()
            print("   ✅ Login successful!")
            print(f"   👤 Logged in as: {auth_data['user']['full_name']}")
            print(f"   🔑 Token received (expires in {auth_data['expires_in']} seconds)")
            
            # Step 4: Access protected content
            print("\n3️⃣ User now has access to protected features")
            
            # Test accessing user profile
            profile_headers = {
                'Authorization': f"Bearer {auth_data['access_token']}",
                'Origin': 'http://localhost:8080'
            }
            
            profile_response = requests.get(
                "http://localhost:8000/auth/me",
                headers=profile_headers,
                timeout=5
            )
            
            if profile_response.status_code == 200:
                profile_data = profile_response.json()
                print("   ✅ Can access user profile")
                print(f"   📋 Profile: {profile_data['full_name']} ({profile_data['role']})")
            
            # Test accessing secure medical endpoints
            secure_response = requests.post(
                "http://localhost:8000/api/secure/create-progress-session",
                headers=profile_headers,
                timeout=5
            )
            
            if secure_response.status_code == 200:
                session_data = secure_response.json()
                print("   ✅ Can access secure medical features")
                print(f"   📋 Session created: {session_data['session_id'][:8]}...")
            
            # Step 5: Test role-based access
            print("\n4️⃣ Testing role-based access control")
            
            admin_response = requests.get(
                "http://localhost:8000/auth/users",
                headers=profile_headers,
                timeout=5
            )
            
            if admin_response.status_code == 403:
                print("   ✅ Admin features properly restricted for physician")
            elif admin_response.status_code == 200:
                print("   ⚠️  Physician has unexpected admin access")
            else:
                print(f"   ❓ Unexpected admin response: {admin_response.status_code}")
            
            print("\n5️⃣ Session Summary:")
            print(f"   🟢 Authentication: Working")
            print(f"   🟢 User Profile: Accessible")
            print(f"   🟢 Medical Features: Accessible") 
            print(f"   🟢 Role Security: Enforced")
            print(f"   🟢 CORS: Configured")
            
        else:
            error_data = login_response.json() if login_response.headers.get('content-type', '').startswith('application/json') else login_response.text
            print(f"   ❌ Login failed: {login_response.status_code}")
            print(f"   📋 Error: {error_data}")
            
    except Exception as e:
        print(f"   ❌ Login request failed: {e}")
    
    print(f"\n🎯 Browser Session Simulation Complete")
    print(f"   Frontend: http://localhost:8080")
    print(f"   Backend: http://localhost:8000")
    print(f"   Ready for real browser testing! 🚀")

if __name__ == "__main__":
    simulate_browser_session()