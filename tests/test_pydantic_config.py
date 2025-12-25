"""Test if pydantic-settings can load the config from .env"""

import sys
from pathlib import Path

# Add src to path like the app does
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from junior.core.config import Settings
    
    print("Testing pydantic-settings configuration loading...")
    print("=" * 60)
    
    settings = Settings()
    
    print(f"\nApp Name: {settings.app_name}")
    print(f"App Version: {settings.app_version}")
    print(f"Environment: {settings.app_env}")
    
    print("\n" + "=" * 60)
    print("API KEYS STATUS:")
    print("=" * 60)
    
    # GROQ
    if settings.groq_api_key:
        print(f"✅ GROQ_API_KEY: SET ({len(settings.groq_api_key)} chars, starts with '{settings.groq_api_key[:4]}')")
    else:
        print("❌ GROQ_API_KEY: NOT SET")
    
    # Perplexity
    if settings.perplexity_api_key:
        print(f"✅ PERPLEXITY_API_KEY: SET ({len(settings.perplexity_api_key)} chars, starts with '{settings.perplexity_api_key[:5]}')")
    else:
        print("❌ PERPLEXITY_API_KEY: NOT SET")
    
    # Supabase
    if settings.supabase_url:
        print(f"✅ SUPABASE_URL: SET ({settings.supabase_url})")
    else:
        print("❌ SUPABASE_URL: NOT SET")
        
    if settings.supabase_key:
        print(f"✅ SUPABASE_KEY: SET ({len(settings.supabase_key)} chars)")
    else:
        print("❌ SUPABASE_KEY: NOT SET")
        
    print("\n" + "=" * 60)
    print("MODELS CONFIGURATION:")
    print("=" * 60)
    print(f"Researcher: {settings.researcher_model} ({settings.researcher_provider})")
    print(f"Critic: {settings.critic_model} ({settings.critic_provider})")
    print(f"Writer: {settings.writer_model} ({settings.writer_provider})")
    
except Exception as e:
    print(f"❌ ERROR loading settings: {e}")
    import traceback
    traceback.print_exc()
