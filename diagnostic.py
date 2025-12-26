"""
Comprehensive Diagnostic Script for Junior Search System
Checks all modules, dependencies, connectivity, and configurations
"""

import sys
import os
sys.path.insert(0, "src")

print("=" * 80)
print("JUNIOR SEARCH SYSTEM - COMPREHENSIVE DIAGNOSTIC")
print("=" * 80)

# 1. Python Environment
print("\n[1] PYTHON ENVIRONMENT")
print("-" * 80)
print(f"Python Version: {sys.version}")
print(f"Python Executable: {sys.executable}")
print(f"Working Directory: {os.getcwd()}")

# 2. Check Required Packages
print("\n[2] REQUIRED PACKAGES")
print("-" * 80)
required_packages = [
    'ddgs',
    'duckduckgo_search', 
    'diskcache',
    'langchain_groq',
    'langchain_core',
    'fastapi',
    'httpx',
    'uvicorn'
]

installed = {}
for pkg in required_packages:
    try:
        mod = __import__(pkg)
        version = getattr(mod, '__version__', 'unknown')
        installed[pkg] = version
        print(f"  [OK] {pkg}: {version}")
    except ImportError:
        installed[pkg] = None
        print(f"  [MISSING] {pkg}: NOT INSTALLED")

# 3. Check Search Libraries
print("\n[3] SEARCH LIBRARY CHECK")
print("-" * 80)
ddgs_available = False
try:
    from ddgs import DDGS
    ddgs_available = True
    print("  [OK] ddgs library imported successfully")
except ImportError:
    try:
        from duckduckgo_search import DDGS
        ddgs_available = True
        print("  [OK] duckduckgo_search library imported successfully")
    except ImportError:
        print("  [ERROR] No search library available!")

# 4. Check official_sources Module
print("\n[4] OFFICIAL_SOURCES MODULE")
print("-" * 80)
try:
    from junior.services.official_sources import (
        search_sources,
        search_live,
        CATALOG,
        TRUSTED_DOMAINS,
        HAS_DDGS,
        SEARCH_CACHE_VERSION,
        SEARCH_CACHE
    )
    print(f"  [OK] Module imported successfully")
    print(f"  - HAS_DDGS: {HAS_DDGS}")
    print(f"  - SEARCH_CACHE_VERSION: {SEARCH_CACHE_VERSION}")
    print(f"  - CATALOG entries: {len(CATALOG)}")
    print(f"  - TRUSTED_DOMAINS: {len(TRUSTED_DOMAINS)} domains")
    print(f"  - Cache type: {type(SEARCH_CACHE)}")
except Exception as e:
    print(f"  [ERROR] Failed to import: {e}")
    import traceback
    traceback.print_exc()

# 5. Check Core Settings
print("\n[5] CORE SETTINGS")
print("-" * 80)
try:
    from junior.core import settings
    print(f"  [OK] Settings imported")
    print(f"  - GROQ API Key: {'SET' if settings.groq_api_key else 'NOT SET'}")
    print(f"  - Environment: {getattr(settings, 'environment', 'unknown')}")
except Exception as e:
    print(f"  [ERROR] Settings import failed: {e}")

# 6. Test Direct Search
print("\n[6] DIRECT SEARCH TEST")
print("-" * 80)
try:
    import asyncio
    
    async def test_search():
        results = await search_sources("rape", limit=200)
        return results
    
    results = asyncio.run(test_search())
    print(f"  [OK] Search executed successfully")
    print(f"  - Total results: {len(results)}")
    print(f"  - Result types:")
    type_counts = {}
    for r in results:
        type_counts[r.type] = type_counts.get(r.type, 0) + 1
    for t, count in type_counts.items():
        print(f"    * {t}: {count}")
    
    print(f"\n  First 5 results:")
    for i, r in enumerate(results[:5], 1):
        print(f"    {i}. [{r.type}] {r.title[:60]}")
        print(f"       URL: {r.url}")
        print(f"       Authority: {r.authority}")
        
except Exception as e:
    print(f"  [ERROR] Search failed: {e}")
    import traceback
    traceback.print_exc()

# 7. Check API Endpoint
print("\n[7] API ENDPOINT CHECK")
print("-" * 80)
try:
    from junior.api.endpoints.research import search_official_sources
    print(f"  [OK] API endpoint imported")
    print(f"  - Function: {search_official_sources}")
except Exception as e:
    print(f"  [ERROR] API endpoint import failed: {e}")

# 8. Check Schemas
print("\n[8] API SCHEMAS")
print("-" * 80)
try:
    from junior.api.schemas import (
        OfficialSourcesSearchRequest,
        OfficialSourcesSearchResponse,
        OfficialSourceItem
    )
    print(f"  [OK] All schemas imported successfully")
except Exception as e:
    print(f"  [ERROR] Schema import failed: {e}")

# 9. Check Cache
print("\n[9] CACHE STATUS")
print("-" * 80)
try:
    cache_dir = ".cache/search_results"
    if os.path.exists(cache_dir):
        print(f"  [OK] Cache directory exists: {cache_dir}")
        # Try to list cache keys
        try:
            cache_keys = list(SEARCH_CACHE.iterkeys())
            print(f"  - Cached queries: {len(cache_keys)}")
            if cache_keys:
                print(f"  - Sample keys:")
                for key in list(cache_keys)[:3]:
                    print(f"    * {key}")
        except:
            print(f"  - Unable to list cache keys")
    else:
        print(f"  [WARN] Cache directory does not exist")
except Exception as e:
    print(f"  [ERROR] Cache check failed: {e}")

# 10. File System Check
print("\n[10] FILE SYSTEM CHECK")
print("-" * 80)
critical_files = [
    "src/junior/services/official_sources.py",
    "src/junior/api/endpoints/research.py",
    "src/junior/api/schemas.py",
    "frontend/src/components/ResearchPanel.tsx"
]

for filepath in critical_files:
    if os.path.exists(filepath):
        size = os.path.getsize(filepath)
        print(f"  [OK] {filepath} ({size:,} bytes)")
    else:
        print(f"  [MISSING] {filepath}")

# 11. Test Live Search
print("\n[11] LIVE SEARCH TEST")
print("-" * 80)
if ddgs_available:
    try:
        import asyncio
        
        async def test_live():
            live_results = await search_live("rape", limit=50)
            return live_results
        
        live_results = asyncio.run(test_live())
        print(f"  [OK] Live search executed")
        print(f"  - Results from web: {len(live_results)}")
        if live_results:
            print(f"  - Sample results:")
            for i, r in enumerate(live_results[:3], 1):
                print(f"    {i}. {r.title[:60]}")
    except Exception as e:
        print(f"  [ERROR] Live search failed: {e}")
else:
    print(f"  [SKIP] No search library available")

# 12. Summary
print("\n" + "=" * 80)
print("DIAGNOSTIC SUMMARY")
print("=" * 80)

issues = []

if not ddgs_available:
    issues.append("No search library (ddgs/duckduckgo_search) available")

if not installed.get('diskcache'):
    issues.append("diskcache not installed - caching disabled")

if not installed.get('langchain_groq') or not installed.get('langchain_core'):
    issues.append("LangChain not fully installed - query expansion disabled")

if issues:
    print("\n[ISSUES FOUND]")
    for i, issue in enumerate(issues, 1):
        print(f"  {i}. {issue}")
else:
    print("\n[OK] No critical issues detected")

print("\n" + "=" * 80)
