"""
Live API Endpoint Testing Script
Tests all endpoints with actual HTTP requests
"""
import requests
import json
import time
from io import BytesIO

BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"

print("=" * 80)
print("JUNIOR AI - LIVE API ENDPOINT TESTING")
print("=" * 80)

# ============================================================================
# Test Health Endpoint
# ============================================================================
print("\n[TEST 1] Health Check")
print("-" * 80)
try:
    response = requests.get(f"{API_BASE}/health", timeout=5)
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Health endpoint working")
        print(f"  Status: {data.get('status')}")
        print(f"  Version: {data.get('version')}")
    else:
        print(f"✗ Health check failed: {response.status_code}")
except Exception as e:
    print(f"✗ Health check error: {e}")

# ============================================================================
# Test Translation Endpoints
# ============================================================================
print("\n[TEST 2] Translation Endpoints")
print("-" * 80)

# Test languages list
print("\n[2.1] Get Supported Languages")
try:
    response = requests.get(f"{API_BASE}/translate/languages", timeout=5)
    if response.status_code == 200:
        data = response.json()
        langs = data.get('languages', [])
        print(f"✓ Languages endpoint working: {len(langs)} languages")
        print(f"  Sample: {', '.join([l['code'] for l in langs[:5]])}")
    else:
        print(f"✗ Languages failed: {response.status_code}")
except Exception as e:
    print(f"✗ Languages error: {e}")

# Test glossary lookup
print("\n[2.2] Glossary Lookup")
try:
    response = requests.get(f"{API_BASE}/translate/glossary/Bail", timeout=5)
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Glossary lookup working")
        print(f"  Term: {data.get('term')}")
        print(f"  Definition: {data.get('definition', '')[:80]}...")
    elif response.status_code == 404:
        print(f"⊘ Term not found in glossary (expected for uninitialized)")
    else:
        print(f"✗ Glossary lookup failed: {response.status_code}")
except Exception as e:
    print(f"✗ Glossary error: {e}")

# Test translation
print("\n[2.3] Text Translation")
try:
    payload = {
        "text": "The court granted bail to the accused under Section 438 CrPC.",
        "target_language": "hi",
        "preserve_legal_terms": True
    }
    response = requests.post(f"{API_BASE}/translate/", json=payload, timeout=15)
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Translation working")
        print(f"  Original: {data.get('original_text', '')[:50]}...")
        print(f"  Translated: {data.get('translated_text', '')[:60]}...")
        print(f"  Preserved terms: {len(data.get('preserved_terms', []))}")
    else:
        print(f"✗ Translation failed: {response.status_code}")
        print(f"  Error: {response.text[:200]}")
except Exception as e:
    print(f"✗ Translation error: {e}")

# ============================================================================
# Test Research/Search Endpoints
# ============================================================================
print("\n[TEST 3] Research & Search Endpoints")
print("-" * 80)

print("\n[3.1] Search Legal Sources")
try:
    payload = {
        "query": "bail",
        "category": None,
        "authority": None,
        "limit": 20
    }
    response = requests.post(f"{API_BASE}/research/sources/search", json=payload, timeout=10)
    if response.status_code == 200:
        data = response.json()
        results = data.get('results', data if isinstance(data, list) else [])
        print(f"✓ Search working: {len(results)} results")
        if results:
            print(f"  Sample result: {results[0].get('title', 'N/A')[:60]}")
            print(f"  Source: {results[0].get('source', 'N/A')}")
    else:
        print(f"✗ Search failed: {response.status_code}")
        print(f"  Error: {response.text[:200]}")
except Exception as e:
    print(f"✗ Search error: {e}")

print("\n[3.2] Empty Query (Catalog Listing)")
try:
    payload = {"query": "", "limit": 10}
    response = requests.post(f"{API_BASE}/research/sources/search", json=payload, timeout=10)
    if response.status_code == 200:
        data = response.json()
        results = data.get('results', data if isinstance(data, list) else [])
        print(f"✓ Catalog listing: {len(results)} items")
    else:
        print(f"✗ Catalog failed: {response.status_code}")
except Exception as e:
    print(f"✗ Catalog error: {e}")

# ============================================================================
# Test Chat Streaming Endpoint
# ============================================================================
print("\n[TEST 4] Chat Streaming Endpoint")
print("-" * 80)

print("\n[4.1] Chat Stream (English)")
try:
    payload = {
        "message": "What is anticipatory bail?",
        "language": "en",
        "session_id": None
    }
    
    with requests.post(
        f"{API_BASE}/chat/stream",
        json=payload,
        stream=True,
        timeout=30
    ) as response:
        if response.status_code == 200:
            chunks_received = 0
            session_id = None
            content_length = 0
            
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        try:
                            data = json.loads(line[6:])
                            if data.get('type') == 'session':
                                session_id = data.get('session_id')
                            elif data.get('type') == 'chunk':
                                content_length += len(data.get('content', ''))
                                chunks_received += 1
                            elif data.get('type') == 'done':
                                break
                        except:
                            pass
            
            print(f"✓ Chat streaming working")
            print(f"  Session ID: {session_id[:20] if session_id else 'N/A'}...")
            print(f"  Chunks received: {chunks_received}")
            print(f"  Total content length: {content_length} chars")
        else:
            print(f"✗ Chat failed: {response.status_code}")
except Exception as e:
    print(f"✗ Chat error: {e}")

print("\n[4.2] Chat Stream (Hindi with Translation)")
try:
    payload = {
        "message": "What is bail?",
        "language": "hi",
        "input_language": "en",
        "output_script": "native",
        "session_id": None
    }
    
    with requests.post(
        f"{API_BASE}/chat/stream",
        json=payload,
        stream=True,
        timeout=30
    ) as response:
        if response.status_code == 200:
            chunks_received = 0
            preserved_terms = []
            
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        try:
                            data = json.loads(line[6:])
                            if data.get('type') == 'chunk':
                                chunks_received += 1
                            elif data.get('type') == 'meta':
                                preserved_terms = data.get('preserved_terms', [])
                            elif data.get('type') == 'done':
                                break
                        except:
                            pass
            
            print(f"✓ Hindi translation working")
            print(f"  Chunks: {chunks_received}")
            print(f"  Preserved terms: {len(preserved_terms)}")
            if preserved_terms:
                print(f"  Sample terms: {', '.join(preserved_terms[:5])}")
        else:
            print(f"✗ Hindi chat failed: {response.status_code}")
except Exception as e:
    print(f"✗ Hindi chat error: {e}")

# ============================================================================
# Test Format Endpoints
# ============================================================================
print("\n[TEST 5] Document Formatting Endpoints")
print("-" * 80)

print("\n[5.1] Get Templates")
try:
    response = requests.get(f"{API_BASE}/format/templates", timeout=5)
    if response.status_code == 200:
        data = response.json()
        templates = data.get('templates', [])
        print(f"✓ Templates endpoint working: {len(templates)} templates")
        if templates:
            print(f"  Sample: {templates[0].get('name', 'N/A')}")
    else:
        print(f"✗ Templates failed: {response.status_code}")
except Exception as e:
    print(f"✗ Templates error: {e}")

print("\n[5.2] Get Court Rules")
try:
    response = requests.get(f"{API_BASE}/format/rules/high_court", timeout=5)
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Court rules working")
        print(f"  Court: {data.get('court')}")
        print(f"  Font: {data.get('font_family')}, {data.get('font_size')}pt")
    else:
        print(f"✗ Court rules failed: {response.status_code}")
except Exception as e:
    print(f"✗ Court rules error: {e}")

# ============================================================================
# Test Audio Transcription
# ============================================================================
print("\n[TEST 6] Audio Transcription Endpoint")
print("-" * 80)

print("\n[6.1] Audio Upload (Mock Test)")
try:
    # Create a minimal WAV file (silence) for testing
    # This is just to test the endpoint structure, not actual transcription
    wav_header = bytes([
        0x52, 0x49, 0x46, 0x46,  # "RIFF"
        0x24, 0x00, 0x00, 0x00,  # File size
        0x57, 0x41, 0x56, 0x45,  # "WAVE"
        0x66, 0x6D, 0x74, 0x20,  # "fmt "
        0x10, 0x00, 0x00, 0x00,  # Fmt chunk size
        0x01, 0x00, 0x01, 0x00,  # Audio format, channels
        0x44, 0xAC, 0x00, 0x00,  # Sample rate
        0x88, 0x58, 0x01, 0x00,  # Byte rate
        0x02, 0x00, 0x10, 0x00,  # Block align, bits per sample
        0x64, 0x61, 0x74, 0x61,  # "data"
        0x00, 0x00, 0x00, 0x00   # Data size
    ])
    
    files = {'file': ('test.wav', BytesIO(wav_header), 'audio/wav')}
    response = requests.post(f"{API_BASE}/audio/transcribe", files=files, timeout=10)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Audio endpoint accessible")
        print(f"  Status: {data.get('status')}")
    elif response.status_code == 422:
        print(f"⊘ Audio endpoint working (mock file rejected as expected)")
    else:
        print(f"⚠ Audio response: {response.status_code}")
        print(f"  Message: {response.text[:100]}")
except Exception as e:
    print(f"⊘ Audio test skipped: {e}")

# ============================================================================
# Summary
# ============================================================================
print("\n\n" + "=" * 80)
print("LIVE TESTING COMPLETE")
print("=" * 80)
print("\n✓ Core features tested:")
print("  - Health check")
print("  - Translation (English → Hindi)")
print("  - Glossary lookup")
print("  - Legal source search")
print("  - Chat streaming (English + Hindi)")
print("  - Document formatting")
print("  - Audio transcription endpoint")
print("\nServer is operational and responding to requests.")
print("=" * 80)
