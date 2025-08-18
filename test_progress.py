#!/usr/bin/env python3
"""
Test script for real-time progress tracking
"""

import asyncio
import websockets
import json
import requests
import time
from pathlib import Path

API_BASE_URL = "http://localhost:8000"

async def test_progress_tracking():
    """Test the complete progress tracking workflow"""
    
    print("🧪 Testing Real-Time Progress Tracking System")
    print("=" * 50)
    
    try:
        # Step 1: Create progress session
        print("1. Creating progress session...")
        session_response = requests.post(f"{API_BASE_URL}/api/create-progress-session")
        session_data = session_response.json()
        session_id = session_data["session_id"]
        print(f"   ✅ Session created: {session_id}")
        
        # Step 2: Connect to WebSocket
        print("2. Connecting to WebSocket...")
        ws_url = f"ws://localhost:8000/ws/progress/{session_id}"
        
        async with websockets.connect(ws_url) as websocket:
            print(f"   ✅ WebSocket connected: {ws_url}")
            
            # Step 3: Start processing in background
            print("3. Starting file processing...")
            
            # Use existing test file
            test_file_path = Path("uploads/Patient C.S..pdf")
            if not test_file_path.exists():
                print(f"   ❌ Test file not found: {test_file_path}")
                return
                
            # Start processing
            def start_processing():
                with open(test_file_path, 'rb') as f:
                    files = {'file': ('Patient C.S..pdf', f, 'application/pdf')}
                    params = {
                        'method': 'openai',
                        'output_format': 'mnr',
                        'enhanced': 'true',
                        'session_id': session_id
                    }
                    response = requests.post(
                        f"{API_BASE_URL}/api/process-complete",
                        files=files,
                        params=params
                    )
                    return response
            
            # Start processing in background
            import threading
            processing_thread = threading.Thread(target=start_processing)
            processing_thread.start()
            
            print("   ✅ Processing started")
            
            # Step 4: Listen for progress updates
            print("4. Listening for progress updates...")
            print("   " + "-" * 40)
            
            start_time = time.time()
            update_count = 0
            
            try:
                while True:
                    # Set timeout to avoid hanging
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=60.0)
                        update = json.loads(message)
                        update_count += 1
                        
                        elapsed = time.time() - start_time
                        progress_percent = int(update['progress'] * 100)
                        
                        print(f"   📊 Update #{update_count} ({elapsed:.1f}s)")
                        print(f"      Stage: {update['stage']}")
                        print(f"      Progress: {progress_percent}%")
                        print(f"      Message: {update['message']}")
                        
                        if update.get('details'):
                            details = update['details']
                            if 'fields_extracted' in details:
                                print(f"      Fields Extracted: {details['fields_extracted']}")
                            if 'cost' in details:
                                print(f"      Cost: ${details['cost']:.4f}")
                        
                        print("   " + "-" * 40)
                        
                        # Check if completed or failed
                        if update['stage'] in ['completed', 'failed']:
                            print(f"   🏁 Processing {update['stage']}")
                            break
                            
                    except asyncio.TimeoutError:
                        print("   ⏰ Timeout waiting for updates")
                        break
                        
            except websockets.ConnectionClosed:
                print("   🔌 WebSocket connection closed")
            
            # Wait for processing thread to complete
            processing_thread.join(timeout=10)
            
            print(f"\n📈 Summary:")
            print(f"   Total updates received: {update_count}")
            print(f"   Total time: {time.time() - start_time:.1f}s")
            print(f"   Session ID: {session_id}")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Starting progress tracking test...")
    asyncio.run(test_progress_tracking())