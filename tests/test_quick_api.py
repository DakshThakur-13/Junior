"""Quick endpoint tests for Junior API"""
import requests

BASE_URL = "http://localhost:8000/api/v1"

def call_endpoint(name: str, method: str, url: str, **kwargs):
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





def main() -> None:
    print("=" * 60)
    print("🧪 Testing Junior API Endpoints")
    print("=" * 60)
    print()

    # 1. Health Check
    print("1️⃣  Basic Health Check")
    result = call_endpoint("Health", "GET", f"{BASE_URL}/health")
    if result:
        print(f"   Status: {result.get('status')}")
    print()

    # 2. Translation - Get Languages
    print("2️⃣  Translation - Supported Languages")
    result = call_endpoint("Languages", "GET", f"{BASE_URL}/translate/languages")
    if result:
        try:
            print(f"   Languages: {len(result)} supported")
        except Exception:
            pass
    print()

    # 3. Translation - Translate Text
    print("3️⃣  Translation - English to Hindi")
    result = call_endpoint(
        "Translate",
        "POST",
        f"{BASE_URL}/translate/",
        json={
            "text": "The court granted bail to the accused.",
            "target_language": "hi",
            "preserve_legal_terms": True,
        },
    )
    if result:
        print("   Original: The court granted bail to the accused.")
        print(f"   Translated: {result.get('translated_text')}")
        print(f"   Preserved: {result.get('preserved_terms')}")
    print()

    # 4. Glossary Lookup
    print("4️⃣  Legal Glossary - Bail Definition")
    result = call_endpoint("Glossary", "GET", f"{BASE_URL}/translate/glossary/Bail")
    if result:
        print(f"   Term: {result.get('term')}")
        print(f"   Definition: {result.get('definition', '')[:100]}...")
    print()

    # 5. Search Sources
    print("5️⃣  Research - Search Legal Sources")
    result = call_endpoint(
        "Search",
        "POST",
        f"{BASE_URL}/research/sources/search",
        json={"query": "supreme court", "limit": 5},
    )
    if isinstance(result, dict) and "results" in result:
        results = result.get("results") or []
        print(f"   Results: {len(results)} sources found")
        if results:
            first = results[0]
            if isinstance(first, dict):
                print(f"   First: {first.get('title', 'N/A')}")
    elif isinstance(result, list):
        print(f"   Results: {len(result)} sources found")
    print()

    # 6. Admin Health (Development Mode - No Key Required)
    print("6️⃣  Admin - Detailed Health Check")
    result = call_endpoint("Admin Health", "GET", f"{BASE_URL}/admin/health-detailed")
    if isinstance(result, dict):
        services = result.get("services", {})
        print("   Services Status:")
        if isinstance(services, dict):
            for svc, status in services.items():
                emoji = "✅" if status == "ok" else "⚠️"
                print(f"      {emoji} {svc}: {status}")
    print()

    print("=" * 60)
    print("✅ Testing Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
