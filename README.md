# Junior - Your Trusted AI Legal Assistant 🧑‍⚖️

> An Agentic AI Workflow Platform designed as a hyper-efficient Legal Assistant for Indian lawyers.

## 🎯 Overview

Junior bridges the **Trust Deficit** between AI and Indian legal professionals by combining **Agentic RAG** (Retrieval-Augmented Generation) with **Strict Evidence Protocols**. Every claim is linked directly to a specific paragraph in a certified court judgment.

## ✨ Key Features

### 🔍 Research Engine (Zero-Hallucination)
- **Agentic RAG**: Team of AI agents (Researcher, Critic, Writer) that iterate until the answer is legally sound.
- **Pinpoint Citation**: Every legal claim hyperlinked to the specific paragraph of the source PDF.
- **Traffic Light Shepardizing**: Visual validity indicator (🔴 Overruled, 🟡 Distinguished, 🟢 Good Law).

### 🧠 Strategy Engine (Predictive)
- **Judge Analytics**: Behavioral patterns analysis from past rulings.
- **Devil's Advocate Simulator**: War Room feature to expose weak arguments before court.

### ⚡ Utility Engine (Automation)
- **Multilingual "Hinglish" Bridge**: Query in vernacular, search English repositories.
- **Draft-to-Court Auto-Formatter**: Convert raw text to court-compliant PDFs.

### 💻 Modern Frontend
- **Modular Architecture**: Built with React, TypeScript, and Vite for high performance.
- **Interactive UI**:
  - **Detective Wall**: Visual graph canvas for connecting evidence and arguments.
  - **Radial Menu**: Intuitive navigation system.
  - **Streaming Chat**: Real-time AI interaction with conflict detection.

## 🏗️ Architecture

### Backend (Python + FastAPI)
- **LangGraph**: Orchestrates the cyclic workflow of agents (Search → Research → Critique → Write).
- **Supabase**: Vector database (pgvector) for semantic search and storage.
- **GLiNER**: PII redaction for privacy compliance.
- **IndicTrans2**: Local translation models for Hinglish support.

### Frontend (React + TypeScript)
- **Vite**: Fast build tool and dev server.
- **Tailwind CSS**: Utility-first styling.
- **Lucide React**: Beautiful, consistent icons.
- **Component Structure**:
  - `components/`: Reusable UI elements (ChatPanel, RadialMenu, etc.).
  - `views/`: Page-level components (LandingPage, CaseSelection).
  - `types/`: Centralized TypeScript definitions.

## 📂 Project Structure

```
ZeroDay/
├── src/                    # Backend Source Code
│   ├── junior/
│   │   ├── agents/         # AI Agents (Researcher, Critic, etc.)
│   │   ├── api/            # FastAPI Endpoints
│   │   ├── core/           # Config & Types
│   │   ├── graph/          # LangGraph Workflows
│   │   └── services/       # Business Logic (PDF, Search, etc.)
│
├── frontend/               # Frontend Source Code
│   ├── src/
│   │   ├── components/     # Modular UI Components
│   │   │   ├── DetectiveWall/
│   │   │   ├── ChatPanel.tsx
│   │   │   ├── RadialMenu.tsx
│   │   │   └── ...
│   │   ├── views/          # Application Views
│   │   ├── types/          # TypeScript Definitions
│   │   └── App.tsx         # Main Application Component
│
├── docs/                   # Documentation
├── scripts/                # Utility Scripts
└── uploads/                # Local Document Storage
```

## 🚀 Quick Start

### Prerequisites
- **Python 3.11+**
- **Node.js 18+** & **npm**
- **Perplexity API Key** (recommended) or **Groq API Key**
- **Supabase Account**

### 1. Backend Setup

1. Create and activate virtual environment:
   ```bash
   python -m venv .venv
   # Windows
   .\.venv\Scripts\activate
   # Linux/Mac
   source .venv/bin/activate
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys (PERPLEXITY_API_KEY and/or GROQ_API_KEY, SUPABASE_URL, etc.)
   ```

   Minimum required (for Chat + Research):
   - `PERPLEXITY_API_KEY` (recommended) OR `GROQ_API_KEY`
   - `SUPABASE_URL`, `SUPABASE_KEY` (if you use the vector DB features)

4. Run the backend server:
   ```bash
   # Windows (PowerShell)
   $env:PYTHONPATH = "$PWD\src"; python -m uvicorn junior.main:app --reload

   # Linux/Mac
   PYTHONPATH=./src python -m uvicorn junior.main:app --reload
   ```
   Backend will run at `http://localhost:8000`.

### 2. Frontend Setup

1. Navigate to frontend directory:
   ```bash
   cd frontend
   ```

2. Install Node dependencies:
   ```bash
   npm install
   ```

3. Run the development server:
   ```bash
   npm run dev
   ```
   Frontend will run at `http://localhost:5173`.

### 3. One-Click Start (Windows)

You can use the provided `start.bat` script to launch both backend and frontend simultaneously:
```bash
.\start.bat
```

Note: `start.bat` is venv-aware and will prefer `.venv\Scripts\python.exe` when present.

If you run `start.py` manually, use the venv interpreter to avoid “installed but not found” issues:
```bash
# Windows (PowerShell)
& .\.venv\Scripts\python.exe .\start.py
```

## 🧪 Verification (Smoke Tests)

With the backend running (`http://localhost:8000`), you can run the included test scripts:

```bash
# Search endpoint
& .\.venv\Scripts\python.exe .\tests\test_api_search.py

# Streaming chat endpoint
& .\.venv\Scripts\python.exe .\tests\test_streaming.py

# Direct chat service (uses your configured provider)
& .\.venv\Scripts\python.exe .\tests\test_chat_quick.py
```

## 🛠️ Troubleshooting

### “Unable to load sources. Please check backend connection.”
- Ensure the backend is running on `http://localhost:8000`.
- Confirm Vite proxy is active (frontend calls `/api/...`).
- Make sure you installed backend deps in the same venv you’re running:
   - `diskcache`
   - `ddgs` (optional for live web search)

### “langchain-perplexity is not installed”
- Install deps into the project venv:
   - `pip install -r requirements.txt`
- Ensure you start the server with the venv interpreter (see One-Click Start / manual start above).

### Chat returns “No API key configured”
- Set `PERPLEXITY_API_KEY` and/or `GROQ_API_KEY` in `.env`.

## 📚 RAG “Training” on Public Manuals (Free)

Junior improves legal quality using **Agentic RAG** + **your ingested evidence**. This is not model fine-tuning.

- Upload any PDF (judgment/manual/book) via `POST /api/v1/documents/upload`.
	- It is chunked + embedded and stored locally under `uploads/`.
- Ingest an allowlisted curated source from the Research catalog (PDF URLs only) via:
	- `POST /api/v1/research/sources/ingest` with JSON `{ "source_id": "..." }`

Relevant environment settings (see `.env.example`):
- `EMBEDDING_MODEL` (free/local; default `BAAI/bge-small-en-v1.5`)
- `MANUALS_DOWNLOAD_DIR`, `MANUALS_MAX_BYTES`

## 📚 Documentation

### **Comprehensive Documentation Suite**

We've created extensive documentation addressing architecture, features, legal compliance, and market research:

#### **🏗️ Architecture & Technical Design**
- **[Architecture Diagrams & Flowcharts](./docs/ARCHITECTURE_DIAGRAMS.md)**
  - System architecture, data flows, component diagrams
  - 13+ professional diagrams using Mermaid syntax
  - Covers: Detective Wall, Judge Analytics, Search Engine, AI Integration

#### **✅ Feature Verification**
- **[Feature Verification Documentation](./docs/FEATURE_VERIFICATION.md)**
  - Proof that all claimed features are implemented and working
  - Code locations, API endpoints, test results
  - Complete feature matrix with performance metrics

#### **🔐 Legal & Compliance**
- **[Privacy Policy](./docs/legal/PRIVACY_POLICY.md)** - GDPR & DPDP Act 2023 compliant
- **[Terms of Service](./docs/legal/TERMS_OF_SERVICE.md)** - Strong AI liability disclaimers
- **[GDPR & DPDP Compliance](./docs/legal/GDPR_DPDP_COMPLIANCE.md)** - Detailed compliance mapping
- **[Data Retention Policy](./docs/legal/DATA_RETENTION_POLICY.md)** - Complete data lifecycle
- **[Security Policy](./docs/legal/SECURITY_POLICY.md)** - Security measures & vulnerability disclosure

#### **📊 Market Research & Citations**
- **[Market Research & Academic Citations](./docs/MARKET_RESEARCH.md)**
  - 50+ quantitative market statistics
  - 10+ peer-reviewed academic citations with DOIs
  - Competitive landscape analysis
  - $28B+ global legal tech market analysis

#### **📑 Complete Index**
- **[Documentation Index](./docs/DOCUMENTATION_INDEX.md)** - Quick access to all documentation

### **🎯 Key Highlights**

**Legal Compliance:**
- ⚠️ **Strong AI Disclaimers**: "AI is NOT legal advice" - no liability for AI errors
- ✅ GDPR & DPDP Act 2023 compliant
- ✅ Vulnerability disclosure program
- ✅ Comprehensive data protection policies

**Market Validation:**
- 📊 $28.1B global legal tech market (2023)
- 📈 $1.8B India market growing to $5B by 2030
- 🎓 10+ academic papers cited (ACM, Springer, Oxford)
- 🏆 51.2M pending cases in Indian courts = massive opportunity

**Technical Credibility:**
- 🏗️ Complete system architecture diagrams
- ✅ All 7 major features verified with code proof
- 📈 Performance metrics: 2.3s search, 30+ results
- 🧪 Automated test suite included

---

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
