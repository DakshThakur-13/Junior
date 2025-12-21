"""Test streaming chat endpoint"""
import time
time.sleep(8)  # Wait for server to start

import requests

print("Testing streaming chat endpoint...")
print("URL: http://localhost:8000/api/v1/chat/stream")

response = requests.post(
    'http://localhost:8000/api/v1/chat/stream',
    json={'message': 'hi', 'language': 'en'},
    stream=True
)

print(f"\nStatus: {response.status_code}")

if response.status_code == 200:
    print("✅ SUCCESS - Streaming chat is working!\n")
    print("Response chunks:")
    for i, line in enumerate(response.iter_lines()):
        if line:
            print(line.decode('utf-8'))
            if i > 10:  # Show first 10 lines
                print("... (truncated)")
                break
else:
    print(f"❌ FAILED: {response.status_code}")
    print(f"Response: {response.text}")
