import sys
sys.path.insert(0, "src")

print("Testing import...")
try:
    from junior.services.official_sources import search_sources, HAS_DDGS, SEARCH_CACHE_VERSION
    print(f"✅ Import successful")
    print(f"   HAS_DDGS: {HAS_DDGS}")
    print(f"   VERSION: {SEARCH_CACHE_VERSION}")
    print(f"   search_sources: {search_sources}")
except Exception as e:
    print(f"❌ Import failed: {e}")
    import traceback
    traceback.print_exc()

print("\nTesting search...")
import asyncio
async def test():
    results = await search_sources("rape", limit=200)
    print(f"✅ Got {len(results)} results")
    for i, r in enumerate(results[:5], 1):
        print(f"   {i}. [{r.type}] {r.title}")

try:
    asyncio.run(test())
except Exception as e:
    print(f"❌ Search failed: {e}")
    import traceback
    traceback.print_exc()
