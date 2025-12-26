"""Test API endpoint while server is running"""
import httpx
import asyncio
import json

async def test_api():
    print("Testing API endpoint at http://localhost:8000...")
    print("="*80)
    
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            'http://localhost:8000/api/v1/research/sources/search',
            json={'query': 'rape', 'limit': 200}
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response type: {type(response.json())}")
        
        data = response.json()
        results = data.get('results', [])
        
        print(f"\nTotal Results: {len(results)}")
        print(f"Query: {data.get('query', 'N/A')}")
        
        if results:
            print(f"\nFirst 10 results:")
            for i, item in enumerate(results[:10], 1):
                print(f"\n{i}. {item['title'][:80]}")
                print(f"   URL: {item['url']}")
                print(f"   Type: {item['item_type']}")
                print(f"   Authority: {item['authority_level']}")
        else:
            print("\n❌ NO RESULTS RETURNED!")
            
        # Analyze results by type
        types = {}
        for item in results:
            t = item['item_type']
            types[t] = types.get(t, 0) + 1
        
        print(f"\n\nResults by type:")
        for t, count in types.items():
            print(f"  {t}: {count}")

if __name__ == "__main__":
    asyncio.run(test_api())
