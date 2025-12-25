"""Quick test script for research search API"""
import requests
import json

BASE_URL = "http://localhost:8000/api/v1/research/sources/search"

def test_search(query="", category=None, limit=200):
    """Test the search API"""
    payload = {
        "query": query,
        "category": category,
        "authority": None,
        "limit": limit
    }
    
    print(f"\n{'='*60}")
    print(f"Testing: query='{query}', category={category}, limit={limit}")
    print(f"{'='*60}")
    
    try:
        response = requests.post(BASE_URL, json=payload)
        response.raise_for_status()
        data = response.json()
        
        results = data.get("results", [])
        print(f"✅ Got {len(results)} results")
        
        if results:
            print(f"\nFirst 5 results:")
            for i, item in enumerate(results[:5], 1):
                print(f"  {i}. [{item['type']}] {item['title'][:70]}")
        
        # Count by type
        types = {}
        for item in results:
            t = item['type']
            types[t] = types.get(t, 0) + 1
        
        if types:
            print(f"\nResults by type:")
            for t, count in sorted(types.items()):
                print(f"  {t}: {count}")
                
        return len(results)
    except Exception as e:
        print(f"❌ Error: {e}")
        return 0

if __name__ == "__main__":
    print("Testing Junior Research Search API")
    print("=" * 60)
    
    # Test 1: Empty query (should return all catalog items)
    count1 = test_search(query="", category=None)
    
    # Test 2: Search for "dowry"
    count2 = test_search(query="dowry", category=None)
    
    # Test 3: Filter by Act category
    count3 = test_search(query="", category="Act")
    
    # Test 4: Filter by Precedent category
    count4 = test_search(query="", category="Precedent")
    
    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"  Empty query: {count1} results")
    print(f"  'dowry' query: {count2} results")
    print(f"  Acts only: {count3} results")
    print(f"  Precedents only: {count4} results")
    print(f"{'='*60}")
