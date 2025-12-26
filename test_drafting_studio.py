"""
Test Drafting Studio APIs
"""
import asyncio
import httpx

async def test_format_apis():
    """Test all format endpoints"""
    base_url = "http://localhost:8000/api/v1"
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        print("🧪 Testing Drafting Studio APIs\n")
        
        # Test 1: Get court rules
        print("1️⃣ Testing GET /format/rules/{court}")
        try:
            resp = await client.get(f"{base_url}/format/rules/high_court")
            if resp.status_code == 200:
                data = resp.json()
                print(f"   ✅ Court rules loaded: {data.get('font_family')} {data.get('font_size')}")
            else:
                print(f"   ❌ Failed: {resp.status_code} - {resp.text}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print()
        
        # Test 2: Get templates
        print("2️⃣ Testing GET /format/templates")
        try:
            resp = await client.get(f"{base_url}/format/templates")
            if resp.status_code == 200:
                data = resp.json()
                templates = data.get('templates', [])
                print(f"   ✅ Templates loaded: {len(templates)} templates")
                for t in templates[:3]:
                    print(f"      - {t.get('name')}")
            else:
                print(f"   ❌ Failed: {resp.status_code} - {resp.text}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print()
        
        # Test 3: Format document
        print("3️⃣ Testing POST /format/document")
        try:
            resp = await client.post(
                f"{base_url}/format/document",
                json={
                    "content": "JURISDICTION\n\nThat this Hon'ble Court has jurisdiction...",
                    "document_type": "writ_petition",
                    "court": "high_court",
                    "case_number": "WP(C) 123/2024",
                    "petitioner": "Test Petitioner",
                    "respondent": "Test Respondent"
                }
            )
            if resp.status_code == 200:
                data = resp.json()
                formatted_len = len(data.get('formatted_text', ''))
                print(f"   ✅ Document formatted: {formatted_len} chars")
            else:
                print(f"   ❌ Failed: {resp.status_code} - {resp.text}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print()
        
        # Test 4: Preview
        print("4️⃣ Testing POST /format/preview")
        try:
            resp = await client.post(
                f"{base_url}/format/preview",
                json={
                    "content": "JURISDICTION\n\nThat this Hon'ble Court has jurisdiction...",
                    "document_type": "writ_petition",
                    "court": "high_court",
                    "case_number": "WP(C) 123/2024",
                    "petitioner": "Test Petitioner",
                    "respondent": "Test Respondent"
                }
            )
            if resp.status_code == 200:
                html = resp.text
                print(f"   ✅ Preview generated: {len(html)} chars HTML")
                if '<html>' in html.lower():
                    print("      - Contains valid HTML structure")
            else:
                print(f"   ❌ Failed: {resp.status_code} - {resp.text}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print("\n" + "="*50)
        print("✅ API Testing Complete!")

if __name__ == "__main__":
    asyncio.run(test_format_apis())
