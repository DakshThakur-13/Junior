"""Quick endpoint tests for Junior API"""
import requests
import time

BASE_URL = "http://localhost:8000/api/v1"

def test_endpoint(name: str, method: str, url: str, **kwargs):
    """Test a single endpoint"""
    try:
        if method == "GET":
            r = requests.get(url, timeout=10, **kwargs)
        elif method == "POST":
            r = requests.post(url, timeout=10, **kwargs)
        
        print(f"✅ {name}: {r.status_code}")
        if r.status_code == 200:
            return r.json()
        return None
    except Exception as e:
        print(f"❌ {name}: {str(e)}")
        return None

print("=" * 60)
print("🧪 Testing Junior API Endpoints")
print("=" * 60)
print()

# 1. Health Check
print("1️⃣  Basic Health Check")
result = test_endpoint("Health", "GET", f"{BASE_URL}/health")
if result:
    print(f"   Status: {result.get('status')}")
print()

# 2. Translation - Get Languages
print("2️⃣  Translation - Supported Languages")
result = test_endpoint("Languages", "GET", f"{BASE_URL}/translate/languages")
if result:
    print(f"   Languages: {len(result)} supported")
print()

# 3. Translation - Translate Text
print("3️⃣  Translation - English to Hindi")
result = test_endpoint(
    "Translate", 
    "POST", 
    f"{BASE_URL}/translate/",
    json={
        "text": "The court granted bail to the accused.",
        "target_language": "hi",
        "preserve_legal_terms": True
    }
)
if result:
    print(f"   Original: The court granted bail to the accused.")
    print(f"   Translated: {result.get('translated_text')}")
    print(f"   Preserved: {result.get('preserved_terms')}")
print()

# 4. Glossary Lookup
print("4️⃣  Legal Glossary - Bail Definition")
result = test_endpoint("Glossary", "GET", f"{BASE_URL}/translate/glossary/Bail")
if result:
    print(f"   Term: {result.get('term')}")
    print(f"   Definition: {result.get('definition', '')[:100]}...")
print()

# 5. Search Sources
print("5️⃣  Research - Search Legal Sources")
result = test_endpoint(
    "Search", 
    "POST", 
    f"{BASE_URL}/research/sources/search",
    json={"query": "supreme court", "limit": 5}
)
if result:
    print(f"   Results: {len(result)} sources found")
    if result:
        print(f"   First: {result[0].get('name', 'N/A')}")
print()

# 6. Admin Health (Development Mode - No Key Required)
print("6️⃣  Admin - Detailed Health Check")
result = test_endpoint("Admin Health", "GET", f"{BASE_URL}/admin/health-detailed")
if result:
    services = result.get('services', {})
    print(f"   Services Status:")
    for svc, status in services.items():
        emoji = "✅" if status == "ok" else "⚠️"
        print(f"      {emoji} {svc}: {status}")
print()

print("=" * 60)
print("✅ Testing Complete!")
print("=" * 60)
