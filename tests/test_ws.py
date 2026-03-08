import asyncio
import websockets
import json
import subprocess
import time

async def test_websocket():
    url = "ws://localhost:8000/ws/events"
    print(f"Connecting to {url}...")
    
    try:
        async with websockets.connect(url) as websocket:
            print("Connected! Waiting for progress events...")
            
            # Start the app in a separate process or assume it's running
            # For this test, we just listen. 
            # In a real scenario, you'd trigger a connection through the UI.
            
            async for message in websocket:
                data = json.loads(message)
                print(f"Received: {data}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket())
