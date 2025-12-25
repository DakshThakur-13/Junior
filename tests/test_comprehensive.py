"""
Comprehensive Testing Script for Junior AI Legal Assistant
Tests all endpoints, services, and functionality
"""
import sys
import os
import asyncio
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

print("=" * 80)
print("JUNIOR AI - COMPREHENSIVE TESTING & DEBUGGING")
print("=" * 80)

# ============================================================================
# PHASE 1: DEPENDENCY & CONFIGURATION CHECK
# ============================================================================
print("\n[PHASE 1] Dependency & Configuration Check")
print("-" * 80)

dependencies = {
    "langchain": "LangChain Core",
    "langchain_groq": "Groq Integration",
    "langchain_perplexity": "Perplexity Integration",
    "langchain_huggingface": "HuggingFace Integration",
    "faster_whisper": "Speech-to-Text",
    "supabase": "Database Client",
    "ddgs": "Web Search",
    "indic_transliteration": "Indic Transliteration",
    "diskcache": "Disk Cache",
    "fastapi": "API Framework",
    "uvicorn": "ASGI Server",
}

failed_imports = []
for module, name in dependencies.items():
    try:
        __import__(module)
        print(f"✓ {name:.<40} OK")
    except ImportError as e:
        print(f"✗ {name:.<40} MISSING")
        failed_imports.append((module, str(e)))

if failed_imports:
    print(f"\n⚠️  {len(failed_imports)} dependencies missing!")
    for mod, err in failed_imports:
        print(f"  - {mod}: {err}")
else:
    print("\n✓ All dependencies installed")

# Check configuration
print("\n[Configuration Check]")
try:
    from junior.core import settings
    
    configs = {
        "GROQ_API_KEY": settings.groq_api_key,
        "PERPLEXITY_API_KEY": settings.perplexity_api_key,
        "HUGGINGFACE_API_KEY": settings.huggingface_api_key,
        "SUPABASE_URL": settings.supabase_url,
        "SUPABASE_KEY": settings.supabase_key,
    }
    
    for key, value in configs.items():
        status = "✓" if value else "✗"
        masked = f"{value[:10]}..." if value else "NOT SET"
        print(f"{status} {key:.<30} {masked}")
    
    configured_count = sum(1 for v in configs.values() if v)
    print(f"\n{configured_count}/{len(configs)} configurations set")
    
except Exception as e:
    print(f"✗ Configuration load failed: {e}")

# ============================================================================
# PHASE 2: SERVICE INITIALIZATION TEST
# ============================================================================
print("\n\n[PHASE 2] Service Initialization Test")
print("-" * 80)

services = []

# Translation Service
print("\n[Translation Service]")
try:
    from junior.services.translator import TranslationService
    translator = TranslationService()
    print(f"✓ TranslationService initialized")
    print(f"  - Preserved terms: {len(translator.PRESERVE_TERMS)}")
    print(f"  - Supported languages: {len(translator.LANGUAGE_NAMES)}")
    services.append(("TranslationService", True, None))
except Exception as e:
    print(f"✗ TranslationService failed: {e}")
    services.append(("TranslationService", False, str(e)))

# Transcriber Service
print("\n[Transcriber Service]")
try:
    from junior.services.transcriber import TranscriberService
    transcriber = TranscriberService()
    print(f"✓ TranscriberService initialized (lazy-loading)")
    services.append(("TranscriberService", True, None))
except Exception as e:
    print(f"✗ TranscriberService failed: {e}")
    services.append(("TranscriberService", False, str(e)))

# Official Sources Service
print("\n[Official Sources Service]")
try:
    from junior.services.official_sources import OfficialSourcesService
    sources = OfficialSourcesService()
    print(f"✓ OfficialSourcesService initialized")
    print(f"  - Catalog size: {len(sources.CATALOG)}")
    services.append(("OfficialSourcesService", True, None))
except Exception as e:
    print(f"✗ OfficialSourcesService failed: {e}")
    services.append(("OfficialSourcesService", False, str(e)))

# Conversational Chat Service
print("\n[Conversational Chat Service]")
try:
    from junior.services.conversational_chat import ConversationalChat
    chat = ConversationalChat()
    print(f"✓ ConversationalChat initialized")
    services.append(("ConversationalChat", True, None))
except Exception as e:
    print(f"✗ ConversationalChat failed: {e}")
    services.append(("ConversationalChat", False, str(e)))

# Legal Glossary Service
print("\n[Legal Glossary Service]")
try:
    from junior.services.legal_glossary import get_glossary_service
    glossary = get_glossary_service()
    print(f"✓ LegalGlossaryService initialized")
    services.append(("LegalGlossaryService", True, None))
except Exception as e:
    print(f"✗ LegalGlossaryService failed: {e}")
    services.append(("LegalGlossaryService", False, str(e)))

success_count = sum(1 for _, success, _ in services if success)
print(f"\n{success_count}/{len(services)} services initialized successfully")

# ============================================================================
# PHASE 3: TRANSLATION FUNCTIONALITY TEST
# ============================================================================
print("\n\n[PHASE 3] Translation Functionality Test")
print("-" * 80)

async def test_translation():
    from junior.services.translator import TranslationService
    from junior.core.types import Language
    
    translator = TranslationService()
    
    # Test 1: Language Detection
    print("\n[Test 1: Language Detection]")
    test_texts = {
        "Hello, how are you?": Language.ENGLISH,
        "नमस्ते, आप कैसे हैं?": Language.HINDI,
        "नमस्कार, तुम्ही कसे आहात?": Language.HINDI,  # Marathi uses Devanagari too
    }
    
    for text, expected in test_texts.items():
        detected = translator.detect_language(text)
        status = "✓" if detected == expected or (expected == Language.HINDI and detected in [Language.HINDI, Language.MARATHI]) else "✗"
        print(f"{status} '{text[:30]}...' → {detected.value}")
    
    # Test 2: Preserved Terms Detection
    print("\n[Test 2: Preserved Terms Detection]")
    test_text = "The petitioner filed a Writ Petition seeking Anticipatory Bail under Section 438 CrPC."
    found_terms = translator._find_preserved_terms(test_text)
    print(f"Found {len(found_terms)} preserved terms:")
    for term in found_terms:
        print(f"  - {term}")
    
    # Test 3: Translation (requires API key)
    print("\n[Test 3: Translation]")
    if settings.groq_api_key or settings.huggingface_api_key:
        try:
            result = await translator.translate_response(
                text="The court granted bail to the accused.",
                target_lang=Language.HINDI,
                preserve_legal_terms=True
            )
            print(f"✓ Translation successful")
            print(f"  Original: {result.source_text}")
            print(f"  Translated: {result.translated_text}")
            print(f"  Preserved: {result.preserved_terms}")
        except Exception as e:
            print(f"✗ Translation failed: {e}")
    else:
        print("⊘ Skipped (no API key configured)")

try:
    asyncio.run(test_translation())
except Exception as e:
    print(f"✗ Translation tests failed: {e}")

# ============================================================================
# PHASE 4: SEARCH FUNCTIONALITY TEST
# ============================================================================
print("\n\n[PHASE 4] Search Functionality Test")
print("-" * 80)

async def test_search():
    from junior.services.official_sources import OfficialSourcesService
    
    service = OfficialSourcesService()
    
    # Test 1: Empty Query (should return catalog)
    print("\n[Test 1: Empty Query - Catalog Listing]")
    try:
        results = await service.search_sources("", limit=10)
        print(f"✓ Empty query returned {len(results)} catalog items")
        if results:
            print(f"  Sample: {results[0].get('title', 'N/A')[:60]}")
    except Exception as e:
        print(f"✗ Empty query failed: {e}")
    
    # Test 2: Specific Legal Query
    print("\n[Test 2: Legal Query - 'bail']")
    try:
        results = await service.search_sources("bail", limit=20)
        print(f"✓ Query returned {len(results)} results")
        
        # Check for duplicates
        titles = [r.get('title', '') for r in results]
        unique_titles = set(titles)
        print(f"  Unique results: {len(unique_titles)}/{len(results)}")
        
        # Show sample results
        if results:
            for i, r in enumerate(results[:3], 1):
                print(f"  {i}. {r.get('title', 'N/A')[:60]}")
                print(f"     Source: {r.get('source', 'N/A')}")
    except Exception as e:
        print(f"✗ Query failed: {e}")
    
    # Test 3: Live Web Search
    print("\n[Test 3: Live Web Search]")
    try:
        results = await service.search_live("Supreme Court bail judgment", max_results=5)
        print(f"✓ Live search returned {len(results)} results")
        if results:
            print(f"  Sample: {results[0].get('title', 'N/A')[:60]}")
    except Exception as e:
        print(f"✗ Live search failed: {e}")

try:
    asyncio.run(test_search())
except Exception as e:
    print(f"✗ Search tests failed: {e}")

# ============================================================================
# PHASE 5: API ENDPOINTS STRUCTURE CHECK
# ============================================================================
print("\n\n[PHASE 5] API Endpoints Structure Check")
print("-" * 80)

try:
    from junior.main import app
    from fastapi.routing import APIRoute
    
    print("\n[Registered API Routes]")
    routes = []
    for route in app.routes:
        if isinstance(route, APIRoute):
            routes.append((route.path, list(route.methods)))
    
    # Group by category
    categories = {
        "Health": [],
        "Audio": [],
        "Research": [],
        "Documents": [],
        "Chat": [],
        "Translation": [],
        "Format": [],
        "Judges": [],
        "Cases": [],
        "Wall": [],
        "WebSocket": [],
        "Frontend": [],
    }
    
    for path, methods in routes:
        if "/health" in path:
            categories["Health"].append((path, methods))
        elif "/audio" in path:
            categories["Audio"].append((path, methods))
        elif "/research" in path:
            categories["Research"].append((path, methods))
        elif "/documents" in path:
            categories["Documents"].append((path, methods))
        elif "/chat" in path:
            categories["Chat"].append((path, methods))
        elif "/translate" in path:
            categories["Translation"].append((path, methods))
        elif "/format" in path:
            categories["Format"].append((path, methods))
        elif "/judges" in path:
            categories["Judges"].append((path, methods))
        elif "/cases" in path:
            categories["Cases"].append((path, methods))
        elif "/wall" in path:
            categories["Wall"].append((path, methods))
        elif "/ws" in path:
            categories["WebSocket"].append((path, methods))
        else:
            categories["Frontend"].append((path, methods))
    
    total_endpoints = 0
    for category, endpoints in categories.items():
        if endpoints:
            print(f"\n{category} ({len(endpoints)} endpoints):")
            for path, methods in endpoints:
                print(f"  {', '.join(methods):6} {path}")
                total_endpoints += 1
    
    print(f"\n✓ Total API endpoints: {total_endpoints}")
    
except Exception as e:
    print(f"✗ API structure check failed: {e}")

# ============================================================================
# PHASE 6: FRONTEND BUILD CHECK
# ============================================================================
print("\n\n[PHASE 6] Frontend Build Check")
print("-" * 80)

frontend_dist = Path(__file__).parent / "frontend" / "dist"
if frontend_dist.exists():
    files = list(frontend_dist.rglob("*"))
    print(f"✓ Frontend build exists")
    print(f"  Total files: {len([f for f in files if f.is_file()])}")
    
    # Check key files
    key_files = ["index.html", "assets"]
    for kf in key_files:
        path = frontend_dist / kf
        if path.exists():
            print(f"  ✓ {kf}")
        else:
            print(f"  ✗ {kf} missing")
else:
    print(f"✗ Frontend build not found at {frontend_dist}")
    print("  Run: cd frontend && npm run build")

# ============================================================================
# SUMMARY & RECOMMENDATIONS
# ============================================================================
print("\n\n" + "=" * 80)
print("SUMMARY & RECOMMENDATIONS")
print("=" * 80)

issues = []
recommendations = []

# Check for failed imports
if failed_imports:
    issues.append(f"{len(failed_imports)} missing dependencies")
    recommendations.append("Install missing dependencies: pip install " + " ".join([m for m, _ in failed_imports]))

# Check for missing API keys
unconfigured = [k for k, v in configs.items() if not v]
if unconfigured:
    issues.append(f"{len(unconfigured)} API keys not configured")
    recommendations.append("Configure missing API keys in .env file")

# Check service initialization
failed_services = [name for name, success, _ in services if not success]
if failed_services:
    issues.append(f"{len(failed_services)} services failed to initialize")
    recommendations.append(f"Debug service initialization: {', '.join(failed_services)}")

# Check frontend build
if not frontend_dist.exists():
    issues.append("Frontend build missing")
    recommendations.append("Build frontend: cd frontend && npm run build")

print(f"\n[Issues Found: {len(issues)}]")
if issues:
    for i, issue in enumerate(issues, 1):
        print(f"  {i}. {issue}")
else:
    print("  ✓ No critical issues found")

print(f"\n[Recommendations: {len(recommendations)}]")
if recommendations:
    for i, rec in enumerate(recommendations, 1):
        print(f"  {i}. {rec}")
else:
    print("  ✓ System is ready for testing")

print("\n" + "=" * 80)
print("Next Step: Start servers and run live endpoint tests")
print("Command: python start.py")
print("=" * 80)
