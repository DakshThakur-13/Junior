import sys
sys.path.insert(0, "src")

print("Testing if API can import the module...")
try:
    # Simulate what the API does
    from junior.services.official_sources import search_sources
    print("✅ Import successful in simulated API context")
    
    # Try calling it
    import asyncio
    async def test():
        results = await search_sources("rape", limit=200)
        return len(results)
    
    count = asyncio.run(test())
    print(f"✅ Search returned {count} results")
    
except Exception as e:
    print(f"❌ IMPORT/CALL FAILED: {e}")
    import traceback
    traceback.print_exc()
