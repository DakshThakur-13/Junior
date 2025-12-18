import sys
import os

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

try:
    from duckduckgo_search import DDGS
    print("SUCCESS: duckduckgo_search imported successfully.")
    
    print("Attempting search...")
    with DDGS() as ddgs:
        results = list(ddgs.text("test legal query", max_results=1))
        print(f"SUCCESS: Search returned {len(results)} results.")
        if results:
            print(f"Sample: {results[0]['title']}")

except ImportError as e:
    print(f"ERROR: Could not import duckduckgo_search. {e}")
except Exception as e:
    print(f"ERROR: Search failed. {e}")

print("-" * 20)
print("Checking service integration...")
try:
    from junior.services.official_sources import search_sources, HAS_DDGS
    print(f"HAS_DDGS flag is: {HAS_DDGS}")
    
    results = search_sources("Supreme Court", limit=5)
    print(f"Service returned {len(results)} results.")
    for r in results:
        print(f" - [{r.type}] {r.title} ({r.url})")

except Exception as e:
    print(f"ERROR: Service check failed. {e}")
