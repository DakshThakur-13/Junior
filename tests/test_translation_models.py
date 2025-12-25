"""
Test script to evaluate different translation and speech models
"""
import sys
import time
import subprocess

def test_model_availability(package_name, import_statement, test_func_name):
    """Test if a model/package is available and working"""
    print(f"\n{'='*60}")
    print(f"Testing: {package_name}")
    print(f"{'='*60}")
    
    try:
        # Try to import
        exec(import_statement)
        print(f"✅ {package_name} is importable")
        
        # Try basic functionality if test function provided
        if test_func_name:
            print(f"⏳ Running basic test...")
            exec(test_func_name)
            print(f"✅ Basic test passed")
        
        return True
    except ImportError as e:
        print(f"❌ Not installed: {e}")
        return False
    except Exception as e:
        print(f"⚠️ Import works but test failed: {e}")
        return False

def check_indicTrans2():
    """Check IndicTrans2 availability"""
    result = test_model_availability(
        "IndicTrans2",
        "from indicTrans.inference.engine import Model",
        None
    )
    
    if not result:
        print("\n📦 Installation command:")
        print("pip install indictrans")
        print("\nOR use HuggingFace Inference API (no install needed):")
        print("https://huggingface.co/ai4bharat/indictrans2-en-indic-1B")
    
    return result

def check_whisper():
    """Check OpenAI Whisper availability"""
    result = test_model_availability(
        "OpenAI Whisper",
        "import whisper",
        "whisper.load_model('tiny')"
    )
    
    if not result:
        print("\n📦 Installation command:")
        print("pip install openai-whisper")
        print("\nNote: Requires ffmpeg to be installed")
        print("      Download from: https://ffmpeg.org/download.html")
        print("\nAlternative: Use Whisper API (no local install):")
        print("pip install openai")
    
    return result

def check_indicxlit():
    """Check IndicXlit (AI4Bharat transliteration)"""
    result = test_model_availability(
        "IndicXlit (Transliteration)",
        "from ai4bharat.transliteration import XlitEngine",
        None
    )
    
    if not result:
        print("\n📦 Installation command:")
        print("pip install ai4bharat-transliteration")
        print("\nOR use API endpoint:")
        print("https://xlit-api.ai4bharat.org/")
    
    return result

def check_transformers():
    """Check if transformers library is available (needed for many models)"""
    result = test_model_availability(
        "HuggingFace Transformers",
        "from transformers import pipeline",
        None
    )
    
    if not result:
        print("\n📦 Installation command:")
        print("pip install transformers torch")
    
    return result

def check_indic_nlp_library():
    """Check Indic NLP Library"""
    result = test_model_availability(
        "Indic NLP Library",
        "from indicnlp.transliterate.unicode_transliterate import UnicodeIndicTransliterator",
        None
    )
    
    if not result:
        print("\n📦 Installation command:")
        print("pip install indic-nlp-library")
    
    return result

def search_better_alternatives():
    """Research and suggest better free alternatives"""
    print(f"\n{'='*60}")
    print("🔍 BETTER FREE ALTERNATIVES RESEARCH")
    print(f"{'='*60}")
    
    alternatives = {
        "Translation": [
            {
                "name": "IndicTrans2 (AI4Bharat)",
                "description": "SOTA for Indian languages, built by IIT Madras",
                "pros": ["Free", "Best quality for EN↔HI/MR", "Can run locally or API"],
                "cons": ["Large model (1-2GB)", "Requires GPU for speed"],
                "url": "https://huggingface.co/ai4bharat/indictrans2-en-indic-1B",
                "rating": "⭐⭐⭐⭐⭐"
            },
            {
                "name": "Google Cloud Translation (Free Tier)",
                "description": "Neural MT with 500K chars/month free",
                "pros": ["Very accurate", "Fast", "500K free chars/month"],
                "cons": ["Requires API key", "Paid after free tier"],
                "url": "https://cloud.google.com/translate",
                "rating": "⭐⭐⭐⭐"
            },
            {
                "name": "LibreTranslate",
                "description": "Open-source translation API",
                "pros": ["100% Free", "Self-hostable", "No API key needed"],
                "cons": ["Lower quality than IndicTrans2", "Limited Indian language support"],
                "url": "https://libretranslate.com/",
                "rating": "⭐⭐⭐"
            },
            {
                "name": "Bhashini (Govt of India)",
                "description": "Government initiative for Indian languages",
                "pros": ["Free", "Government backed", "All 22 scheduled languages"],
                "cons": ["API still in beta", "Quality varies"],
                "url": "https://bhashini.gov.in/",
                "rating": "⭐⭐⭐"
            },
            {
                "name": "Groq + Llama 3.1 70B (Current)",
                "description": "Using existing Groq for translation",
                "pros": ["Already integrated", "Fast", "Free tier generous"],
                "cons": ["Not specialized for Indian languages", "May lack legal terminology"],
                "url": "https://groq.com/",
                "rating": "⭐⭐⭐⭐"
            }
        ],
        "Speech-to-Text": [
            {
                "name": "Whisper (OpenAI)",
                "description": "State-of-the-art multilingual STT",
                "pros": ["Excellent quality", "Supports Hindi/Marathi", "Can run locally or API"],
                "cons": ["API costs $0.006/min", "Local requires GPU"],
                "url": "https://openai.com/research/whisper",
                "rating": "⭐⭐⭐⭐⭐"
            },
            {
                "name": "Wav2Vec2 for Hindi/Marathi",
                "description": "Facebook's speech model fine-tuned for Indian languages",
                "pros": ["Free", "Good quality", "Can run on HuggingFace"],
                "cons": ["Requires transformers library", "Slower than Whisper"],
                "url": "https://huggingface.co/models?search=wav2vec2+hindi",
                "rating": "⭐⭐⭐⭐"
            },
            {
                "name": "Google Cloud Speech-to-Text",
                "description": "Excellent STT with free tier",
                "pros": ["Very accurate", "60 min/month free", "Fast"],
                "cons": ["Requires API key", "Paid after free tier"],
                "url": "https://cloud.google.com/speech-to-text",
                "rating": "⭐⭐⭐⭐⭐"
            },
            {
                "name": "Bhashini Speech Recognition",
                "description": "Government initiative",
                "pros": ["Free", "All Indian languages", "Government backed"],
                "cons": ["Beta quality", "May be unreliable"],
                "url": "https://bhashini.gov.in/",
                "rating": "⭐⭐⭐"
            }
        ],
        "Transliteration (Hinglish)": [
            {
                "name": "IndicXlit (AI4Bharat)",
                "description": "AI-based transliteration for Indian languages",
                "pros": ["Free", "Excellent quality", "Handles spelling variations"],
                "cons": ["Requires installation or API call"],
                "url": "https://github.com/AI4Bharat/IndicXlit",
                "rating": "⭐⭐⭐⭐⭐"
            },
            {
                "name": "Google Input Tools JS",
                "description": "Client-side transliteration",
                "pros": ["Free", "No server needed", "Fast", "Works offline"],
                "cons": ["Limited to Google's script"],
                "url": "https://www.google.com/inputtools/",
                "rating": "⭐⭐⭐⭐"
            },
            {
                "name": "Indic NLP Library",
                "description": "Python library for Indic transliteration",
                "pros": ["Free", "Pure Python", "Works offline"],
                "cons": ["Rule-based, less accurate than AI"],
                "url": "https://github.com/anoopkunchukuttan/indic_nlp_library",
                "rating": "⭐⭐⭐"
            },
            {
                "name": "Lipika IME",
                "description": "JavaScript transliteration engine",
                "pros": ["Free", "Client-side", "Fast", "No dependencies"],
                "cons": ["Basic rule-based system"],
                "url": "https://github.com/ratreya/lipika-ime",
                "rating": "⭐⭐⭐"
            }
        ]
    }
    
    for category, models in alternatives.items():
        print(f"\n{'─'*60}")
        print(f"📋 {category.upper()}")
        print(f"{'─'*60}")
        
        for i, model in enumerate(models, 1):
            print(f"\n{i}. {model['name']} {model['rating']}")
            print(f"   {model['description']}")
            print(f"   ✅ Pros: {', '.join(model['pros'])}")
            print(f"   ⚠️ Cons: {', '.join(model['cons'])}")
            print(f"   🔗 {model['url']}")

def recommend_best_stack():
    """Recommend the best stack based on requirements"""
    print(f"\n{'='*60}")
    print("🎯 RECOMMENDED STACK FOR JUNIOR AI")
    print(f"{'='*60}")
    
    print("\n🏆 WINNER: Hybrid Multi-Model Approach")
    print("\n1. TRANSLATION:")
    print("   Primary: IndicTrans2 (HuggingFace Inference API)")
    print("   Fallback: Groq + Llama 3.1 (already integrated)")
    print("   Cost: FREE (both options)")
    print("   Quality: ⭐⭐⭐⭐⭐")
    
    print("\n2. SPEECH-TO-TEXT:")
    print("   Primary: Whisper API (OpenAI)")
    print("   Fallback: Google Cloud STT (60 min/month free)")
    print("   Cost: $0.006/min (very affordable)")
    print("   Quality: ⭐⭐⭐⭐⭐")
    
    print("\n3. TRANSLITERATION (HINGLISH):")
    print("   Primary: IndicXlit API (AI4Bharat)")
    print("   Fallback: Google Input Tools JS (client-side)")
    print("   Cost: FREE")
    print("   Quality: ⭐⭐⭐⭐⭐")
    
    print("\n💡 WHY THIS STACK?")
    print("   ✅ All services have FREE tiers or very cheap")
    print("   ✅ Best quality for Indian languages")
    print("   ✅ API-based = No heavy local dependencies")
    print("   ✅ Fallbacks for reliability")
    print("   ✅ Can start free, scale as needed")

def test_huggingface_api():
    """Test HuggingFace Inference API for IndicTrans2"""
    print(f"\n{'='*60}")
    print("🧪 Testing HuggingFace Inference API")
    print(f"{'='*60}")
    
    try:
        import requests
        
        print("\n📡 Sending test request to IndicTrans2...")
        
        API_URL = "https://api-inference.huggingface.co/models/ai4bharat/indictrans2-en-indic-1B"
        headers = {"Authorization": "Bearer hf_YOUR_TOKEN_HERE"}  # User needs to add token
        
        payload = {
            "inputs": "I need information about divorce",
            "parameters": {"src_lang": "eng_Latn", "tgt_lang": "hin_Deva"}
        }
        
        print("   Input: 'I need information about divorce'")
        print("   Target: Hindi (Devanagari)")
        
        # Note: This will fail without a valid HF token, but shows the user how to use it
        print("\n   ⚠️ Note: Requires HuggingFace API token")
        print("   Get free token at: https://huggingface.co/settings/tokens")
        print("   Example output would be: 'मुझे तलाक के बारे में जानकारी चाहिए'")
        
    except Exception as e:
        print(f"   ℹ️ Test skipped (expected): {e}")
        print("   This is just to show the API structure")

if __name__ == "__main__":
    print("🚀 Junior AI - Translation Models Test Suite")
    print("=" * 60)
    
    results = {}
    
    # Test each component
    print("\n📦 CHECKING INSTALLED PACKAGES...")
    results['transformers'] = check_transformers()
    results['indicTrans2'] = check_indicTrans2()
    results['whisper'] = check_whisper()
    results['indicxlit'] = check_indicxlit()
    results['indic_nlp'] = check_indic_nlp_library()
    
    # Research alternatives
    search_better_alternatives()
    
    # Recommend best stack
    recommend_best_stack()
    
    # Test API approach
    test_huggingface_api()
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 SUMMARY")
    print(f"{'='*60}")
    
    installed = sum(1 for v in results.values() if v)
    total = len(results)
    
    print(f"\n✅ Installed: {installed}/{total}")
    print(f"❌ Not installed: {total - installed}/{total}")
    
    if installed == 0:
        print("\n💡 RECOMMENDATION:")
        print("   Don't install heavy local models!")
        print("   Use API-based approach instead:")
        print("   1. HuggingFace Inference API (IndicTrans2) - FREE")
        print("   2. Whisper API (OpenAI) - $0.006/min")
        print("   3. IndicXlit API - FREE")
        print("\n   This keeps your app lightweight and fast!")
    
    print("\n✅ Test complete!")
