"""Quick API test"""
import httpx
import asyncio

async def test():
    r = await httpx.AsyncClient().post(
        'http://localhost:8000/api/v1/research/sources/search',
        json={'query': 'rape', 'limit': 200}
    )
    data = r.json()
    print(f"Status: {r.status_code}")
    print(f"Results: {len(data['results'])}")
    if data['results']:
        print("First 3 titles:")
        for i in data['results'][:3]:
            print(f"  - {i['title'][:70]}")
        print(f"\nTypes: {set(i['type'] for i in data['results'])}")
    else:
        print("NO RESULTS")

asyncio.run(test())
