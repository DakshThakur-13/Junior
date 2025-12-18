# Junior - Your Trusted AI Legal Assistant 🧑‍⚖️

> An Agentic AI Workflow Platform designed as a hyper-efficient Legal Assistant for Indian lawyers.

## 🎯 Overview

Junior bridges the **Trust Deficit** between AI and Indian legal professionals by combining **Agentic RAG** (Retrieval-Augmented Generation) with **Strict Evidence Protocols**. Every claim is linked directly to a specific paragraph in a certified court judgment.

## ✨ Key Features

### 🔍 Research Engine (Zero-Hallucination)
- **Agentic RAG**: Team of AI agents (Researcher, Critic, Writer) that iterate until the answer is legally sound
- **Pinpoint Citation**: Every legal claim hyperlinked to the specific paragraph of the source PDF
- **Traffic Light Shepardizing**: Visual validity indicator (🔴 Overruled, 🟡 Distinguished, 🟢 Good Law)

### 🧠 Strategy Engine (Predictive)
- **Judge Analytics**: Behavioral patterns analysis from past rulings
- **Devil's Advocate Simulator**: War Room feature to expose weak arguments before court

### ⚡ Utility Engine (Automation)
- **Multilingual "Hinglish" Bridge**: Query in vernacular, search English repositories
- **Draft-to-Court Auto-Formatter**: Convert raw text to court-compliant PDFs

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Junior Architecture                       │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │  Researcher │→ │   Critic    │→ │   Writer    │         │
│  │    Agent    │  │    Agent    │  │    Agent    │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│         ↑              ↑              ↓                     │
│         └──────────────┴──────────────┘                     │
│                   LangGraph Orchestration                   │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Supabase  │  │    GLiNER   │  │  IndicTrans │         │
│  │  (pgvector) │  │ (PII Guard) │  │ (Translate) │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Groq API Key
- Supabase Account

### Installation

1. Clone the repository:
```bash
git clone https://github.com/your-org/junior.git
cd junior
```

2. Create and activate virtual environment:
```bash
python -m venv .venv
# Windows
.\.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment:
```bash
cp .env.example .env
# Edit .env with your API keys
```

5. Run the application:
```bash
# Windows (PowerShell)
$env:PYTHONPATH = "$PWD\src"; python -m uvicorn junior.main:app --reload

# Linux/Mac
PYTHONPATH=./src python -m uvicorn junior.main:app --reload
```

## 📚 RAG “Training” on Public Manuals (Free)

Junior improves legal quality using **Agentic RAG** + **your ingested evidence**. This is not model fine-tuning.

- Upload any PDF (judgment/manual/book) via `POST /api/v1/documents/upload`.
	- It is chunked + embedded and stored locally under `uploads/`.
- Ingest an allowlisted curated source from the Research catalog (PDF URLs only) via:
	- `POST /api/v1/research/sources/ingest` with JSON `{ "source_id": "..." }`

Relevant environment settings (see `.env.example`):
- `EMBEDDING_MODEL` (free/local; default `BAAI/bge-small-en-v1.5`)
- `MANUALS_DOWNLOAD_DIR`, `MANUALS_MAX_BYTES`
- `MANUALS_ALLOW_URL_INGEST` + `MANUALS_ALLOWLIST_DOMAINS` (disabled by default)

## 📁 Project Structure

```
junior/
├── src/
│   └── junior/
│       ├── agents/          # AI Agents (Researcher, Critic, Writer)
│       ├── api/             # FastAPI endpoints
│       ├── core/            # Core configuration and utilities
│       ├── db/              # Database models and repositories
│       ├── services/        # Business logic services
│       ├── graph/           # LangGraph workflow definitions
│       └── utils/           # Helper utilities
├── tests/                   # Test suite
├── static/                  # Static assets
├── templates/               # Jinja2 templates
└── docs/                    # Documentation
```

## 🔐 Privacy & Compliance

- **DPDP Act Compliant**: Local PII redaction before cloud processing
- **Client Privilege Watermark**: Auto-watermarking of AI drafts
- **Zero-Hallucination Protocol**: Strict citation requirements

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.

## 🤝 Contributing

Contributions are welcome! Please read our contributing guidelines before submitting PRs.

---

**Built with ❤️ for the Indian Legal Community**
