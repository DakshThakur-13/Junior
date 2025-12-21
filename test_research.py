import requests
import json
import time

print("Waiting 3 seconds for server to be ready...")
time.sleep(3)

try:
    # Test research search endpoint
    print("\n" + "="*60)
    print("Testing Research Search Endpoint")
    print("="*60)
    
    url = "http://localhost:8000/api/v1/research/sources/search"
    data = {
        "query": "contract law",
        "language": "en"
    }
    
    print(f"\nPOST {url}")
    print(f"Payload: {json.dumps(data, indent=2)}")
    
    response = requests.post(url, json=data, timeout=30)
    
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response:")
    print(json.dumps(response.json(), indent=2)[:2000])
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
