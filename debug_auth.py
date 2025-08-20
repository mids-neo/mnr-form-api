#!/usr/bin/env python3
"""Debug authentication issues"""

import requests
import jwt
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

def debug_token():
    # Login to get token
    login_data = {
        "email": "physician@medicaldocai.com",
        "password": "Physician123!"
    }
    
    response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    if response.status_code != 200:
        print(f"Login failed: {response.text}")
        return
    
    data = response.json()
    token = data['access_token']
    
    print("📋 Token Analysis:")
    print(f"Token: {token}")
    print(f"User: {data['user']['email']} (ID: {data['user']['id']})")
    
    # Decode token without verification to see contents
    try:
        decoded = jwt.decode(token, options={"verify_signature": False})
        print(f"Decoded payload: {json.dumps(decoded, indent=2)}")
        
        # Check expiration
        exp = decoded.get('exp')
        if exp:
            exp_date = datetime.fromtimestamp(exp)
            print(f"Token expires: {exp_date}")
            print(f"Current time: {datetime.now()}")
            
    except Exception as e:
        print(f"Error decoding token: {e}")
    
    # Test the secure endpoint with detailed error
    print("\n🔐 Testing secure endpoint...")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(f"{BASE_URL}/api/secure/create-progress-session", headers=headers)
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    # Also test a direct database check
    print("\n💾 Testing database session...")
    
    # Check sessions endpoint if it exists
    try:
        response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
        print(f"Me endpoint status: {response.status_code}")
        print(f"Me endpoint response: {response.text}")
    except Exception as e:
        print(f"Me endpoint error: {e}")

if __name__ == "__main__":
    debug_token()