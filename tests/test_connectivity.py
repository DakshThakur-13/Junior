"""Comprehensive API connectivity test"""
import requests
import json
import sys

BASE_URL = "http://localhost:8000/api/v1"

def print_header(text):
    print(f"\n{'='*60}")
    print(f" {text}")
    print(f"{'='*60}\n")

def test_health():
    """Test health endpoint"""
    print("1️⃣  Testing Health Endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        response.raise_for_status()
        data = response.json()
        print("   ✅ Health Check: PASSED")
        print(f"   Status: {data.get('status')}")
        print(f"   Version: {data.get('version')}")
        print(f"   Environment: {data.get('environment')}")
        print("\n   📊 Services Status:")
        services = data.get('services', {})
        print(f"   Groq API: {services.get('groq')}")
        print(f"   Supabase: {services.get('supabase')}")
        print(f"   PII Redaction: {services.get('pii_redaction')}\n")
        return True
    except Exception as e:
        print(f"   ❌ Health Check: FAILED - {e}\n")
        return False

def test_cases():
    """Test cases endpoint"""
    print("2️⃣  Testing Cases Endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/cases", timeout=5)
        response.raise_for_status()
        data = response.json()
        print(f"   ✅ Cases Endpoint: PASSED")
        print(f"   Found {len(data)} cases\n")
        return True
    except Exception as e:
        print(f"   ⚠️  Cases Endpoint: {e}\n")
        return False

def test_groq_api():
    """Test Groq API directly"""
    print("3️⃣  Testing Groq API Key...")
    try:
        with open('.env', 'r') as f:
            for line in f:
                if line.startswith('GROQ_API_KEY='):
                    groq_key = line.strip().split('=', 1)[1]
                    break
        
        headers = {
            "Authorization": f"Bearer {groq_key}",
            "Content-Type": "application/json"
        }
        response = requests.get(
            "https://api.groq.com/openai/v1/models",
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        print(f"   ✅ Groq API Key: VALID")
        print(f"   Available models: {len(data.get('data', []))}\n")
        return True
    except Exception as e:
        print(f"   ❌ Groq API Key: INVALID - {e}\n")
        return False

def test_perplexity_api():
    """Test Perplexity API directly"""
    print("4️⃣  Testing Perplexity API Key...")
    try:
        with open('.env', 'r') as f:
            for line in f:
                if line.startswith('PERPLEXITY_API_KEY='):
                    pplx_key = line.strip().split('=', 1)[1]
                    break
        
        headers = {
            "Authorization": f"Bearer {pplx_key}",
            "Content-Type": "application/json"
        }
        body = {
            "model": "llama-3.1-sonar-small-128k-online",
            "messages": [
                {"role": "user", "content": "Hello"}
            ],
            "max_tokens": 10
        }
        response = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers=headers,
            json=body,
            timeout=15
        )
        response.raise_for_status()
        print(f"   ✅ Perplexity API Key: VALID")
        print(f"   Test completion successful\n")
        return True
    except Exception as e:
        print(f"   ⚠️  Perplexity API: {e}\n")
        return False

def test_supabase():
    """Test Supabase connectivity"""
    print("5️⃣  Testing Supabase Connectivity...")
    try:
        with open('.env', 'r') as f:
            env_vars = {}
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    env_vars[key] = value
        
        supabase_url = env_vars.get('SUPABASE_URL')
        supabase_key = env_vars.get('SUPABASE_KEY')
        
        headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}"
        }
        response = requests.get(
            f"{supabase_url}/rest/v1/",
            headers=headers,
            timeout=10
        )
        # Supabase returns 404 for root, but that means it's accessible
        if response.status_code in [200, 404]:
            print(f"   ✅ Supabase: CONNECTED")
            print(f"   URL: {supabase_url}\n")
            return True
        else:
            print(f"   ⚠️  Supabase: Unexpected status {response.status_code}\n")
            return False
    except Exception as e:
        print(f"   ⚠️  Supabase: {e}\n")
        return False

if __name__ == "__main__":
    print_header("🔍 TESTING BACKEND API CONNECTIVITY")
    
    results = {
        "Health Endpoint": test_health(),
        "Cases Endpoint": test_cases(),
        "Groq API Key": test_groq_api(),
        "Perplexity API Key": test_perplexity_api(),
        "Supabase": test_supabase()
    }
    
    print_header("📊 TEST SUMMARY")
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"   {test_name}: {status}")
    
    print(f"\n{'='*60}")
    print(f" {passed}/{total} tests passed")
    print(f"{'='*60}\n")
    
    sys.exit(0 if passed == total else 1)
