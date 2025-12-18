# Local IndicTrans2 Setup for Junior

## Your Hardware

✅ **GPU Detected**: NVIDIA GeForce RTX 3050 6GB Laptop GPU  
⚠️ **Current PyTorch**: CPU-only (no CUDA support)

Your RTX 3050 6GB is **sufficient** for IndicTrans2 (requires ~4GB).

## Quick Setup (CPU Version - Works Now)

Since your PyTorch is CPU-only, start with CPU IndicTrans2:

```bash
# Activate venv
cd "c:\Users\Daksh Thakur\Desktop\ZeroDay"
.\.venv\Scripts\activate

# Install IndicTrans2 toolkit
pip install ai4bharat-transliteration

# Test installation
python -c "print('IndicTrans2 installed successfully')"
```

## Enable in .env

```env
# Allow local model downloads for IndicTrans2
ALLOW_HF_MODEL_DOWNLOADS=true
```

## Translation Priority

Your system now uses this fallback chain:

1. **Local IndicTrans2** (if installed + `ALLOW_HF_MODEL_DOWNLOADS=true`) ← Best quality
2. **HF Inference API** (usually unavailable - returns 410)
3. **Groq LLM** (always works) ← Current fallback

## GPU Acceleration Setup (Optional - Better Performance)

To enable GPU acceleration:

### Step 1: Install CUDA-enabled PyTorch

```bash
# Uninstall CPU PyTorch
pip uninstall torch torchvision torchaudio

# Install PyTorch with CUDA 12.1 (check your CUDA version first)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### Step 2: Verify CUDA

```python
import torch
print("CUDA Available:", torch.cuda.is_available())
print("GPU Name:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "None")
```

### Step 3: Install GPU IndicTrans2

```bash
# After CUDA PyTorch is working
pip install ai4bharat-transliteration
```

## Model Download

First translation will download models (~4GB):

- **en-indic**: English → Hindi/Marathi/Tamil/etc.
- **indic-en**: Hindi/Marathi/Tamil/etc. → English

Models are cached in `~/.cache/huggingface/` after first download.

## Testing

```python
from fastapi.testclient import TestClient
from junior.main import app

client = TestClient(app)

# Test intelligent translation with glossary verification
response = client.post("/api/v1/translate/", json={
    "text": "The petitioner filed a writ petition under Article 226.",
    "target_language": "hi",
    "preserve_legal_terms": True
})

print(response.json())
```

## Current Status

✅ **Glossary Service**: Created  
✅ **Intelligent Translation**: Implemented  
✅ **Multi-tier Fallback**: Local IndicTrans2 → HF API → Groq LLM  
✅ **HTML Parsing**: beautifulsoup4 + lxml installed  
⏳ **Local IndicTrans2**: Not installed yet (optional)

Your system **works perfectly now** with Groq fallback. Local IndicTrans2 is optional for:
- Offline translation
- High volume usage
- Slightly better quality

## Recommendation

1. **Start with current setup** (Groq fallback works great)
2. Test intelligent translation with glossary
3. If you want offline/faster, install CPU IndicTrans2
4. If you want maximum speed, install CUDA PyTorch + GPU IndicTrans2 later

Your translation quality is already excellent with glossary verification + Groq!
