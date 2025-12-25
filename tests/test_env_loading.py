import os
from pathlib import Path
from dotenv import load_dotenv

# Test .env loading
repo_root = Path(__file__).parent
env_file = repo_root / '.env'

print(f"Repo root: {repo_root}")
print(f".env path: {env_file}")
print(f".env exists: {env_file.exists()}")

if env_file.exists():
    load_dotenv(env_file)
    
    groq = os.getenv('GROQ_API_KEY', '')
    perplexity = os.getenv('PERPLEXITY_API_KEY', '')
    supabase = os.getenv('SUPABASE_URL', '')
    
    print(f"\nGROQ_API_KEY: {'✅ SET (' + str(len(groq)) + ' chars)' if groq.startswith('gsk_') else '❌ NOT SET'}")
    print(f"PERPLEXITY_API_KEY: {'✅ SET (' + str(len(perplexity)) + ' chars)' if perplexity.startswith('pplx-') else '❌ NOT SET'}")
    print(f"SUPABASE_URL: {'✅ SET' if supabase.startswith('https://') else '❌ NOT SET'}")
else:
    print("❌ .env file not found!")
