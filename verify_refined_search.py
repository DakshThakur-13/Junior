
import asyncio
import sys
import os

print("Starting verification script...")

# Add src to path
sys.path.insert(0, os.path.abspath("src"))

from junior.services.official_sources import search_sources, HAS_DDGS

async def main():
    print(f"HAS_DDGS: {HAS_DDGS}")
    print("Searching for 'robbery'...")
    results = await search_sources("robbery", limit=5)
    print(f"Found {len(results)} results.")
    for r in results:
        print(f"- [{r.type}] {r.title} ({r.url})")

if __name__ == "__main__":
    asyncio.run(main())
