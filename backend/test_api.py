#!/usr/bin/env python3
"""
Simple test script for the Crogia FastAPI backend
"""

import asyncio
import aiohttp
import json
from typing import Dict, Any

BASE_URL = "http://localhost:8000"

async def test_health():
    """Test the health endpoint"""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/api/health") as response:
            data = await response.json()
            print(f"Health check: {data}")
            return response.status == 200

async def test_sessions():
    """Test session management endpoints"""
    async with aiohttp.ClientSession() as session:
        # List sessions (should be empty initially)
        async with session.get(f"{BASE_URL}/api/sessions") as response:
            sessions = await response.json()
            print(f"Initial sessions: {sessions}")
        
        # Create a new session
        task_data = {"task": "Test task for API verification"}
        async with session.post(f"{BASE_URL}/api/sessions", json=task_data) as response:
            if response.status == 200:
                new_session = await response.json()
                print(f"Created session: {new_session}")
                return new_session["session_id"]
            else:
                print(f"Failed to create session: {response.status}")
                return None

async def test_websocket():
    """Test WebSocket connection"""
    import websockets
    
    try:
        uri = "ws://localhost:8000/ws/test-session"
        async with websockets.connect(uri) as websocket:
            # Send a test message
            await websocket.send("Hello WebSocket!")
            
            # Receive response
            response = await websocket.recv()
            print(f"WebSocket response: {response}")
            return True
    except Exception as e:
        print(f"WebSocket test failed: {e}")
        return False

async def main():
    """Run all tests"""
    print("🧪 Testing Crogia FastAPI Backend")
    print("=" * 40)
    
    # Test health endpoint
    print("\n1. Testing health endpoint...")
    health_ok = await test_health()
    
    if not health_ok:
        print("❌ Health check failed - is the server running?")
        return
    
    print("✅ Health check passed")
    
    # Test session endpoints
    print("\n2. Testing session endpoints...")
    session_id = await test_sessions()
    
    if session_id:
        print(f"✅ Session management works - created session {session_id}")
    else:
        print("❌ Session management failed")
    
    # Test WebSocket (optional - might fail if no session exists)
    print("\n3. Testing WebSocket connection...")
    ws_ok = await test_websocket()
    
    if ws_ok:
        print("✅ WebSocket connection works")
    else:
        print("⚠️  WebSocket test failed (this might be expected)")
    
    print("\n🎉 API testing complete!")

if __name__ == "__main__":
    asyncio.run(main()) 