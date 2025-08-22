#!/usr/bin/env python3
"""Test frontend-backend connection and CORS"""

import requests
import json

def test_frontend_backend_connection():
    """Test basic frontend-backend connectivity and CORS"""
    
    print("🌐 Testing Frontend-Backend Connection")
    print("=" * 40)
    
    # Test 1: Basic health check
    print("1️⃣ Testing basic backend connectivity...")
    try:
        health_response = requests.get('http://localhost:8000/health', timeout=5)
        if health_response.status_code == 200:
            print("   ✅ Backend is accessible")
            print(f"   📋 Response: {health_response.json()}")
        else:
            print(f"   ❌ Backend health check failed: {health_response.status_code}")
    except Exception as e:
        print(f"   ❌ Backend not accessible: {e}")
        return
    
    # Test 2: Test CORS preflight for auth endpoints
    print("\n2️⃣ Testing CORS configuration...")
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
            cors_methods = preflight_response.headers.get('Access-Control-Allow-Methods')
            cors_headers = preflight_response.headers.get('Access-Control-Allow-Headers')
            
            print(f"   📋 CORS Origin: {cors_origin}")
            print(f"   📋 CORS Methods: {cors_methods}")
            print(f"   📋 CORS Headers: {cors_headers}")
        else:
            print(f"   ⚠️  CORS preflight returned: {preflight_response.status_code}")
        
    except Exception as e:
        print(f"   ❌ CORS preflight failed: {e}")
    
    # Test 3: Test user registration to create a test user
    print("\n3️⃣ Creating test user...")
    
    test_user_data = {
        "email": "test@example.com",
        "password": "TestPassword123!",
        "full_name": "Test User",
        "role": "physician"
    }
    
    try:
        register_response = requests.post(
            'http://localhost:8000/auth/register',
            json=test_user_data,
            headers={'Origin': 'http://localhost:8080'},
            timeout=10
        )
        
        if register_response.status_code == 201:
            print("   ✅ Test user created successfully")
            user_data = register_response.json()
            print(f"   👤 User: {user_data['user']['full_name']}")
        elif register_response.status_code == 400:
            # User already exists
            print("   ✅ Test user already exists")
        else:
            print(f"   ❌ User creation failed: {register_response.status_code}")
            try:
                error_data = register_response.json()
                print(f"   📋 Error: {error_data}")
            except:
                print(f"   📋 Error: {register_response.text}")
        
    except Exception as e:
        print(f"   ❌ User registration failed: {e}")
    
    # Test 4: Test login with the test user
    print("\n4️⃣ Testing login...")
    
    login_data = {
        "email": "test@example.com",
        "password": "TestPassword123!"
    }
    
    try:
        login_response = requests.post(
            'http://localhost:8000/auth/login',
            json=login_data,
            headers={'Origin': 'http://localhost:8080'},
            timeout=10
        )
        
        if login_response.status_code == 200:
            auth_data = login_response.json()
            print("   ✅ Login successful!")
            print(f"   👤 Logged in as: {auth_data['user']['full_name']}")
            
            # Test 5: Test secure endpoint access
            print("\n5️⃣ Testing secure endpoint access...")
            
            auth_headers = {
                'Authorization': f"Bearer {auth_data['access_token']}",
                'Origin': 'http://localhost:8080'
            }
            
            session_response = requests.post(
                'http://localhost:8000/api/secure/create-progress-session',
                headers=auth_headers,
                timeout=5
            )
            
            if session_response.status_code == 200:
                session_data = session_response.json()
                print("   ✅ Secure endpoints accessible")
                print(f"   📋 Session: {session_data['session_id'][:8]}...")
                
                # Check CORS headers in secure response
                cors_origin = session_response.headers.get('Access-Control-Allow-Origin')
                if cors_origin:
                    print(f"   🌐 CORS working: {cors_origin}")
                else:
                    print("   ⚠️  No CORS headers in secure response")
            else:
                print(f"   ❌ Secure endpoint failed: {session_response.status_code}")
                
        else:
            print(f"   ❌ Login failed: {login_response.status_code}")
            try:
                error_data = login_response.json()
                print(f"   📋 Error: {error_data}")
            except:
                print(f"   📋 Error: {login_response.text}")
        
    except Exception as e:
        print(f"   ❌ Login request failed: {e}")
    
    print(f"\n🎯 Connection Test Complete")
    print(f"   Frontend URL: http://localhost:8080")
    print(f"   Backend URL: http://localhost:8000")
    print(f"   Ready for browser testing! 🚀")

if __name__ == "__main__":
    test_frontend_backend_connection()