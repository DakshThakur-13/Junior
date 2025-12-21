"""Test official sources search directly"""
import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from junior.services.official_sources import search_sources, CATALOG

async def main():
    print("="*60)
    print("Testing Official Sources Search")
    print("="*60)
    
    print(f"\nTotal items in CATALOG: {len(CATALOG)}")
    
    # Test 1: Empty query (should return all)
    print("\n--- Test 1: Empty query ---")
    results = await search_sources("", category=None, authority=None, limit=25)
    print(f"Results: {len(results)}")
    for i, r in enumerate(results[:3], 1):
        print(f"{i}. {r.title}")
    
    # Test 2: Query "contract law"
    print("\n--- Test 2: Query 'contract law' ---")
    results = await search_sources("contract law", category=None, authority=None, limit=25)
    print(f"Results: {len(results)}")
    for i, r in enumerate(results[:5], 1):
        print(f"{i}. {r.title}")
    
    # Test 3: Query "supreme court"
    print("\n--- Test 3: Query 'supreme court' ---")
    results = await search_sources("supreme court", category=None, authority=None, limit=25)
    print(f"Results: {len(results)}")
    for i, r in enumerate(results[:5], 1):
        print(f"{i}. {r.title}")
    
    # Test 4: Check first few catalog items
    print("\n--- First 5 catalog items ---")
    for i, item in enumerate(CATALOG[:5], 1):
        print(f"{i}. {item.title} (type={item.type}, authority={item.authority})")

if __name__ == "__main__":
    asyncio.run(main())
