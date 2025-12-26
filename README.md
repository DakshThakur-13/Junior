# Junior - AI Legal Assistant for Indian Lawyers ⚖️

> An Agentic AI Workflow Platform designed as a hyper-efficient Legal Assistant for Indian lawyers.

**Last Updated:** December 26, 2025

## 🎯 Overview

Junior bridges the **Trust Deficit** between AI and Indian legal professionals by combining **Agentic RAG** (Retrieval-Augmented Generation) with **Strict Evidence Protocols**. Every claim is linked directly to a specific paragraph in a certified court judgment.

## ✨ Key Features

### 🔍 Research Engine (Zero-Hallucination)
- **Legal Source Search**: 30+ results from Indian Kanoon, Supreme Court, High Courts
- **Categorized Results**: Case law, statutes, articles, official sources
- **Traffic Light Shepardizing**: Visual validity indicator (🔴 Overruled, 🟡 Distinguished, 🟢 Good Law)
- **Bookmarking & History**: Save important sources and track search history

### 📊 Strategy & Analytics Engine
- **Judge Analytics**: Analyze judicial patterns from past rulings
  - AI-powered pattern detection (High/Medium/Low signals)
  - Evidence-based recommendations
  - Auto-fetch judgments by judge name and case type
- **Devil's Advocate Simulator**: Stress-test your arguments before court
  - Vulnerability scoring (1-10)
  - Counter-argument identification
  - Preparation recommendations

### 📝 Drafting Studio
- **Court-Specific Formatting**: Auto-format for Supreme Court, High Court, District Court, Tribunal
- **9 Templates**: Heading, Petition, Writ, Affidavit, Arguments, Synopsis, and more
- **Live Preview**: Real-time HTML preview with court styling
- **Citation Shepardizing**: Validate citations with visual indicators
- **Export Options**: Download as formatted document

### 🕵️ Detective Wall
- **Visual Case Canvas**: Drag-and-drop evidence nodes
- **AI-Powered Analysis**: Auto-detect connections and contradictions
- **Node Types**: Evidence, Precedent, Statement, Strategy
- **Connection Mapping**: Link related evidence with labeled relationships
- **PDF Upload**: Upload and analyze case documents

### 💬 AI Chat Assistant
- **Multilingual Support**: English, Hindi, Marathi, Hinglish
- **Legal Term Highlighting**: Click for instant definitions
- **Conflict Detection**: Warns when AI response conflicts with evidence
- **Streaming Responses**: Real-time AI interaction

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
Junior/
├── src/                    # Backend Source Code
│   └── junior/
│       ├── agents/         # AI Agents (JudgeAnalytics, DevilsAdvocate)
│       ├── api/            # FastAPI Endpoints
│       │   ├── endpoints/  # Route handlers (research, judges, format, etc.)
│       │   └── schemas.py  # Pydantic models
│       ├── core/           # Config & Settings
│       ├── graph/          # LangGraph Workflows
│       └── services/       # Business Logic
│           ├── official_sources.py   # Legal search engine
│           ├── document_formatter.py # Court document formatting
│           ├── embedding.py          # Vector embeddings
│           └── legal_glossary.py     # Term definitions
│
├── frontend/               # Frontend Source Code (React + TypeScript)
│   └── src/
│       ├── components/     # Reusable UI Components
│       │   ├── DetectiveWall/       # Canvas components
│       │   ├── ChatPanel.tsx        # AI chat interface
│       │   ├── RadialMenu.tsx       # Navigation menu
│       │   ├── ResearchPanel.tsx    # Search interface
│       │   └── ToolsDock.tsx        # Toolbar
│       ├── views/          # Page-level components
│       ├── types/          # TypeScript definitions
│       ├── App.tsx         # Main application (includes Analytics, Drafting)
│       └── styles.css      # Global styles
│
├── docs/                   # Documentation
│   ├── legal/              # Legal policies (Privacy, Terms, GDPR)
│   ├── ARCHITECTURE_DIAGRAMS.md
│   └── FEATURE_VERIFICATION.md
│
├── tests/                  # Test suite
├── uploads/                # Document storage
├── start.py                # One-click startup script
└── requirements.txt        # Python dependencies
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

## 🧪 Testing

```bash
# Run all tests
.\.venv\Scripts\python.exe -m pytest -q

# Run with coverage
.\.venv\Scripts\python.exe -m pytest --cov=src/junior tests/
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

Comprehensive documentation is available in the `docs/` folder:

| Document | Description |
|----------|-------------|
| [Architecture Diagrams](./docs/ARCHITECTURE_DIAGRAMS.md) | System architecture, data flows, component diagrams |
| [Feature Verification](./docs/FEATURE_VERIFICATION.md) | Proof of implementation for all features |
| [Privacy Policy](./docs/legal/PRIVACY_POLICY.md) | GDPR & DPDP Act 2023 compliant |
| [Terms of Service](./docs/legal/TERMS_OF_SERVICE.md) | Usage terms and AI disclaimers |
| [Security Policy](./docs/legal/SECURITY_POLICY.md) | Security measures and disclosure |

---

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
