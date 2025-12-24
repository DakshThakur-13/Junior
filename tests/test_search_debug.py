"""Test search functionality to debug issues"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

from junior.services.official_sources import search_sources

async def test_searches():
    print("=" * 60)
    print("SEARCH DEBUG TEST")
    print("=" * 60)
    
    # Test 1: Empty query (should return catalog items)
    print("\n1. Testing EMPTY query (should show catalog)...")
    results = await search_sources(query="", limit=10)
    print(f"   Results: {len(results)}")
    for r in results[:3]:
        print(f"   - {r.title} ({r.type}) - {r.source}")
    
    # Test 2: Simple query
    print("\n2. Testing 'IPC' query...")
    results = await search_sources(query="IPC", limit=10)
    print(f"   Results: {len(results)}")
    for r in results[:3]:
        print(f"   - {r.title} ({r.type}) - {r.source}")
    
    # Test 3: Specific query
    print("\n3. Testing 'Section 302' query...")
    results = await search_sources(query="Section 302", limit=10)
    print(f"   Results: {len(results)}")
    for r in results[:5]:
        print(f"   - {r.title} ({r.type}) - {r.source}")
    
    # Test 4: Check if DDGS is working
    print("\n4. Testing live search capability...")
    try:
        from ddgs import DDGS
        print("   ✅ DDGS is installed")
        with DDGS() as ddgs:
            test_results = list(ddgs.text("test india", max_results=2))
            print(f"   ✅ DDGS is working ({len(test_results)} results)")
    except Exception as e:
        print(f"   ❌ DDGS issue: {e}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(test_searches())
