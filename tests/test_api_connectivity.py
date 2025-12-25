"""
Test all API endpoints to ensure frontend-backend connectivity
"""
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

def test_endpoint(method, endpoint, data=None, description=""):
    """Test a single endpoint"""
    url = f"{BASE_URL}{endpoint}"
    print(f"\n{'='*60}")
    print(f"Testing: {description or endpoint}")
    print(f"Method: {method.upper()}")
    print(f"URL: {url}")
    
    try:
        if method.lower() == "get":
            response = requests.get(url, timeout=5)
        elif method.lower() == "post":
            response = requests.post(url, json=data, timeout=5)
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ SUCCESS")
            if response.headers.get('content-type', '').startswith('application/json'):
                print(f"Response: {json.dumps(response.json(), indent=2)[:200]}...")
        elif response.status_code == 422:
            print("⚠️  VALIDATION ERROR (expected for missing data)")
        else:
            print(f"❌ FAILED: {response.status_code}")
            print(f"Response: {response.text[:200]}")
    except requests.exceptions.ConnectionError:
        print("❌ CONNECTION FAILED - Server not running")
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")

print("\n" + "="*60)
print("JUNIOR API CONNECTIVITY TEST")
print("="*60)

# Test all endpoints that the frontend uses
tests = [
    ("GET", "/health", None, "Health Check"),
    ("POST", "/research/sources/search", {"query": "test", "language": "en"}, "Research - Search Sources"),
    ("POST", "/research/devils-advocate", {"query": "test"}, "Research - Devils Advocate"),
    ("POST", "/format/preview", {"content": "test", "template": "petition"}, "Format - Preview Document"),
    ("GET", "/format/templates", None, "Format - Get Templates"),
    ("POST", "/judges/analyze", {"judge_name": "Test Judge", "judgments": ["This is a sample judgment excerpt."]}, "Judges - Analyze"),
    ("POST", "/wall/analyze", {"content": "test case"}, "DetectiveWall - Analyze"),
    ("POST", "/audio/transcribe", {}, "Audio - Transcribe (will fail - needs file)"),
    ("POST", "/chat/stream", {"message": "hi", "language": "en"}, "Chat - Streaming"),
]

for method, endpoint, data, description in tests:
    test_endpoint(method, endpoint, data, description)

print("\n" + "="*60)
print("TEST COMPLETE")
print("="*60)
