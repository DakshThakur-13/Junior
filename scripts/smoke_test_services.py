
import sys
from fastapi.testclient import TestClient
from junior.main import app
from junior.core.config import settings

def test_services():
    client = TestClient(app)
    
    print("=== 1. Health Check ===")
    r = client.get("/api/v1/health")
    print(f"Status: {r.status_code}")
    print(f"Response: {r.json()}")
    
    print("\n=== 2. Chat (Groq) ===")
    try:
        # Simple chat to verify Groq key
        payload = {
            "message": "Say 'Groq is working' and nothing else.",
            "language": "en",
            "stream": False
        }
        # Note: Trailing slash might be required depending on router include
        r = client.post("/api/v1/chat/", json=payload)
        if r.status_code == 200:
            print(f"Success! Response: {r.json().get('response', '')[:50]}...")
        else:
            print(f"Failed: {r.status_code} - {r.text}")
    except Exception as e:
        print(f"Error: {e}")

    print("\n=== 3. Translation (NLLB via HF) ===")
    try:
        # Translate with legal term preservation
        payload = {
            "text": "The petitioner filed a writ petition under Article 226.",
            "target_language": "hi",
            "preserve_legal_terms": True
        }
        r = client.post("/api/v1/translate/", json=payload)
        if r.status_code == 200:
            resp = r.json()
            print(f"Success!")
            print(f"Original: {resp.get('original_text')}")
            print(f"Translated: {resp.get('translated_text')}")
            print(f"Preserved terms: {resp.get('preserved_terms')}")
        else:
            print(f"Failed: {r.status_code} - {r.text}")
    except Exception as e:
        print(f"Error: {e}")

    print("\n=== 4. Vector Search (Supabase) ===")
    try:
        # Search for something generic
        payload = {
            "query": "legal",
            "limit": 1,
            "threshold": 0.0
        }
        r = client.post("/api/v1/documents/search", json=payload)
        if r.status_code == 200:
            results = r.json()
            print(f"Success! Found {len(results)} results.")
        else:
            print(f"Failed: {r.status_code} - {r.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_services()
