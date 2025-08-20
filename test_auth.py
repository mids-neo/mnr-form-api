#!/usr/bin/env python3
"""Test authentication endpoints"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_login_and_secure_endpoint():
    # Test login
    login_data = {
        "email": "physician@medicaldocai.com",
        "password": "Physician123!"
    }
    
    print("🔐 Testing login...")
    response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    print(f"Login status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        token = data['access_token']
        user = data['user']
        print(f"✅ Login successful for {user['full_name']} ({user['role']})")
        print(f"Token: {token[:50]}...")
        
        # Test secure endpoint
        headers = {"Authorization": f"Bearer {token}"}
        print("\n📋 Testing secure endpoint...")
        
        response = requests.post(f"{BASE_URL}/api/secure/create-progress-session", headers=headers)
        print(f"Secure endpoint status: {response.status_code}")
        
        if response.status_code == 200:
            session_data = response.json()
            print(f"✅ Secure endpoint successful: {session_data}")
        else:
            print(f"❌ Secure endpoint failed: {response.text}")
            
    else:
        print(f"❌ Login failed: {response.text}")

def test_admin_endpoints():
    # Test admin login
    login_data = {
        "email": "admin@medicaldocai.com",
        "password": "Admin123!"
    }
    
    print("\n👑 Testing admin login...")
    response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    
    if response.status_code == 200:
        data = response.json()
        token = data['access_token']
        user = data['user']
        print(f"✅ Admin login successful for {user['full_name']}")
        
        # Test admin endpoint
        headers = {"Authorization": f"Bearer {token}"}
        print("\n👥 Testing admin users endpoint...")
        
        response = requests.get(f"{BASE_URL}/auth/users", headers=headers)
        print(f"Admin users endpoint status: {response.status_code}")
        
        if response.status_code == 200:
            users = response.json()
            print(f"✅ Found {len(users)} users in system")
            for user in users:
                print(f"  - {user['email']} ({user['role']})")
        else:
            print(f"❌ Admin endpoint failed: {response.text}")
    else:
        print(f"❌ Admin login failed: {response.text}")

if __name__ == "__main__":
    test_login_and_secure_endpoint()
    test_admin_endpoints()