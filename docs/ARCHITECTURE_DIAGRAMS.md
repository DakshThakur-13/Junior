# Junior Legal Research Platform - Architecture & Diagrams

## 🏗️ System Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        UI[React + TypeScript UI<br/>Vite + Tailwind CSS]
    end
    
    subgraph "API Layer"
        API[FastAPI Backend<br/>Python 3.11+]
    end
    
    subgraph "AI Services"
        GROQ[Groq LLM API<br/>LLaMA 3.3 70B]
        CLAUDE[Anthropic Claude API<br/>Sonnet 3.5]
    end
    
    subgraph "External Services"
        SEARCH[DuckDuckGo Search API<br/>Legal Source Discovery]
        SUPABASE[Supabase<br/>Authentication & Storage]
    end
    
    subgraph "Core Services"
        RESEARCH[Research Service<br/>Document Analysis]
        JUDGE[Judge Analytics<br/>Pattern Recognition]
        DETECTIVE[Detective Wall<br/>Case Visualization]
        EMBED[Embedding Service<br/>Semantic Search]
    end
    
    subgraph "Data Layer"
        LOCAL[Local File Storage<br/>/uploads directory]
        CACHE[In-Memory Cache<br/>Query Results]
    end
    
    UI -->|HTTPS| API
    API -->|AI Analysis| GROQ
    API -->|AI Research| CLAUDE
    API -->|Legal Search| SEARCH
    API -->|Auth & DB| SUPABASE
    API --> RESEARCH
    API --> JUDGE
    API --> DETECTIVE
    API --> EMBED
    RESEARCH --> LOCAL
    RESEARCH --> CACHE
    DETECTIVE --> CACHE
    
    style UI fill:#60a5fa,stroke:#1e40af,stroke-width:3px
    style API fill:#34d399,stroke:#059669,stroke-width:3px
    style GROQ fill:#fbbf24,stroke:#d97706,stroke-width:2px
    style CLAUDE fill:#fbbf24,stroke:#d97706,stroke-width:2px
```

---

## 🔄 Data Flow Diagram

```mermaid
sequenceDiagram
    actor User
    participant UI as Frontend UI
    participant API as FastAPI Backend
    participant AI as Groq LLM
    participant Search as DuckDuckGo
    participant Storage as File Storage
    
    User->>UI: Upload Document
    UI->>API: POST /api/v1/research/upload
    API->>Storage: Save PDF/DOCX
    API->>AI: Extract & Summarize Content
    AI-->>API: Document Summary
    API-->>UI: Upload Success + Summary
    
    User->>UI: Search Legal Sources
    UI->>API: POST /api/v1/research/sources/search
    API->>Search: Query Case Law
    Search-->>API: 20-30 Results
    API->>AI: Analyze Relevance
    AI-->>API: Filtered Results
    API-->>UI: Relevant Sources
    
    User->>UI: Request Judge Analytics
    UI->>API: POST /api/v1/judges/analyze
    API->>AI: Analyze Judgment Patterns
    AI-->>API: Patterns + Recommendations
    API-->>UI: Analytics Report
```

---

## 🎯 Feature Flow: Detective Wall

```mermaid
graph LR
    START([User Opens<br/>Detective Wall]) --> CANVAS[Canvas Interface]
    CANVAS --> ADD[Add Node]
    ADD --> TYPE{Node Type?}
    
    TYPE -->|Document| DOC[Document Node<br/>PDF/DOCX Upload]
    TYPE -->|Case| CASE[Case Node<br/>Case Details]
    TYPE -->|Evidence| EVID[Evidence Node<br/>Tagged Items]
    TYPE -->|Note| NOTE[Note Node<br/>Text Annotations]
    
    DOC --> AI1[AI Analysis<br/>Extract Key Points]
    CASE --> AI2[AI Analysis<br/>Case Summary]
    EVID --> AI3[AI Analysis<br/>Relevance Score]
    
    AI1 --> CONNECT[Connect Nodes]
    AI2 --> CONNECT
    AI3 --> CONNECT
    NOTE --> CONNECT
    
    CONNECT --> VISUAL[Visual Graph<br/>Relationship Mapping]
    VISUAL --> EXPORT[Export Board<br/>JSON/Image]
    
    style START fill:#34d399,stroke:#059669
    style VISUAL fill:#60a5fa,stroke:#1e40af
    style EXPORT fill:#fbbf24,stroke:#d97706
```

---

## 🔍 Judge Analytics Workflow

```mermaid
graph TD
    INPUT[User Input:<br/>Judge Name + Excerpts] --> PARSE[Parse Judgment Text]
    PARSE --> GROQ[Send to Groq LLM<br/>LLaMA 3.3 70B]
    
    GROQ --> ANALYZE{AI Analysis}
    
    ANALYZE --> PATTERNS[Identify Patterns:<br/>- Argumentative tendencies<br/>- Evidence preferences<br/>- Precedent usage]
    
    ANALYZE --> SIGNALS[Signal Strength:<br/>- High ⚠️<br/>- Medium ⚡<br/>- Low ✓]
    
    ANALYZE --> RECOMMEND[Generate Recommendations:<br/>- Strategy tips<br/>- Argument framing<br/>- Evidence focus]
    
    PATTERNS --> SUMMARY[Summary Card:<br/>📊 Case Count<br/>🎯 Pattern Count<br/>💡 Recommendations]
    SIGNALS --> SUMMARY
    RECOMMEND --> SUMMARY
    
    SUMMARY --> UI[Display in UI<br/>+ Export Option]
    
    style INPUT fill:#60a5fa,stroke:#1e40af
    style GROQ fill:#fbbf24,stroke:#d97706
    style SUMMARY fill:#34d399,stroke:#059669
    style UI fill:#a78bfa,stroke:#7c3aed
```

---

## 🎭 Devil's Advocate Simulation Flow

```mermaid
graph TD
    INPUT[User Input:<br/>Case Summary + Arguments] --> VALIDATE[Validate Input]
    VALIDATE --> GROQ[Send to Groq LLM]
    
    GROQ --> SIMULATE{AI Simulation}
    
    SIMULATE --> ATTACK[Attack Vectors:<br/>- Weak points<br/>- Counter-arguments<br/>- Logical fallacies]
    
    SIMULATE --> DEFENSE[Defense Strategy:<br/>- Response preparation<br/>- Evidence needs<br/>- Rebuttal points]
    
    SIMULATE --> SCORE[Vulnerability Score:<br/>0-100 Rating]
    
    ATTACK --> VISUAL[Visual Display:<br/>Color-coded by severity]
    DEFENSE --> VISUAL
    SCORE --> VISUAL
    
    VISUAL --> EXPORT[Export Results]
    
    style INPUT fill:#60a5fa,stroke:#1e40af
    style GROQ fill:#fbbf24,stroke:#d97706
    style SCORE fill:#f87171,stroke:#dc2626
    style VISUAL fill:#34d399,stroke:#059669
```

---

## 🔐 Authentication & Security Flow

```mermaid
sequenceDiagram
    actor User
    participant UI
    participant API
    participant Supabase
    participant Session
    
    User->>UI: Click Sign In
    UI->>Supabase: OAuth Request
    Supabase-->>User: Authorization Page
    User->>Supabase: Grant Access
    Supabase-->>UI: Access Token
    UI->>API: Request with Bearer Token
    API->>Supabase: Validate Token
    Supabase-->>API: User Verified
    API->>Session: Create Session
    API-->>UI: Protected Resource
    
    Note over UI,Session: JWT Token stored in HttpOnly cookie
    Note over API,Supabase: Token refresh handled automatically
```

---

## 📊 Search Service Architecture

```mermaid
graph TB
    QUERY[User Search Query] --> VALIDATE[Input Validation<br/>& Sanitization]
    VALIDATE --> CACHE{Check Cache?}
    
    CACHE -->|Hit| RETURN[Return Cached Results]
    CACHE -->|Miss| DDGS[DuckDuckGo Search API]
    
    DDGS --> PARSE[Parse Results:<br/>- Indian Case Law<br/>- Statutes<br/>- Legal Articles]
    
    PARSE --> FILTER[Filter & Rank:<br/>- Relevance Score<br/>- Date Priority<br/>- Source Authority]
    
    FILTER --> ENRICH[Enrich Results:<br/>- Add metadata<br/>- Extract snippets<br/>- Format citations]
    
    ENRICH --> CACHE_STORE[Store in Cache<br/>TTL: 1 hour]
    CACHE_STORE --> RETURN
    
    RETURN --> UI[Display 20-30 Results]
    
    style QUERY fill:#60a5fa,stroke:#1e40af
    style CACHE fill:#fbbf24,stroke:#d97706
    style DDGS fill:#34d399,stroke:#059669
    style UI fill:#a78bfa,stroke:#7c3aed
```

---

## 🧠 AI Service Integration

```mermaid
graph LR
    subgraph "AI Models"
        GROQ_MODEL[Groq LLaMA 3.3 70B<br/>- Judge Analytics<br/>- Devil's Advocate<br/>- Pattern Recognition]
        CLAUDE_MODEL[Anthropic Claude<br/>- Deep Research<br/>- Document Analysis<br/>- Complex Reasoning]
    end
    
    subgraph "Backend Services"
        ROUTER[Model Router<br/>Intelligent Selection]
    end
    
    subgraph "Use Cases"
        QUICK[Quick Queries<br/>< 2 sec response]
        DEEP[Deep Analysis<br/>Complex reasoning]
        PATTERN[Pattern Detection<br/>Large context]
    end
    
    QUICK --> ROUTER
    DEEP --> ROUTER
    PATTERN --> ROUTER
    
    ROUTER -->|Fast & Cheap| GROQ_MODEL
    ROUTER -->|Quality & Depth| CLAUDE_MODEL
    
    style GROQ_MODEL fill:#fbbf24,stroke:#d97706
    style CLAUDE_MODEL fill:#a78bfa,stroke:#7c3aed
    style ROUTER fill:#34d399,stroke:#059669
```

---

## 🗄️ Data Model Relationships

```mermaid
erDiagram
    USER ||--o{ DOCUMENT : uploads
    USER ||--o{ SEARCH_QUERY : performs
    USER ||--o{ DETECTIVE_BOARD : creates
    
    DOCUMENT ||--o{ ANALYSIS : generates
    DOCUMENT ||--o{ NODE : represents
    
    DETECTIVE_BOARD ||--o{ NODE : contains
    NODE ||--o{ CONNECTION : has
    
    SEARCH_QUERY ||--o{ SEARCH_RESULT : returns
    
    JUDGE_ANALYTICS ||--o{ PATTERN : identifies
    JUDGE_ANALYTICS ||--o{ RECOMMENDATION : generates
    
    USER {
        string user_id PK
        string email
        string name
        timestamp created_at
    }
    
    DOCUMENT {
        string doc_id PK
        string user_id FK
        string filename
        string file_path
        string summary
        timestamp uploaded_at
    }
    
    DETECTIVE_BOARD {
        string board_id PK
        string user_id FK
        string title
        json board_data
        timestamp created_at
    }
    
    NODE {
        string node_id PK
        string board_id FK
        string node_type
        json content
        array connections
    }
    
    JUDGE_ANALYTICS {
        string analysis_id PK
        string judge_name
        array patterns
        array recommendations
        timestamp created_at
    }
```

---

## 🚀 Deployment Architecture (Current)

```mermaid
graph TB
    subgraph "Local Development"
        DEV[Developer Machine<br/>Windows/Linux/Mac]
        
        subgraph "Frontend"
            VITE[Vite Dev Server<br/>Port 5173]
        end
        
        subgraph "Backend"
            UVICORN[Uvicorn ASGI Server<br/>Port 8000]
            PYTHON[Python 3.11+<br/>Virtual Environment]
        end
        
        subgraph "External"
            EXT_AI[AI APIs<br/>Groq + Claude]
            EXT_SEARCH[DuckDuckGo API]
            EXT_AUTH[Supabase Auth]
        end
    end
    
    DEV --> VITE
    DEV --> UVICORN
    UVICORN --> PYTHON
    PYTHON --> EXT_AI
    PYTHON --> EXT_SEARCH
    PYTHON --> EXT_AUTH
    
    style VITE fill:#60a5fa,stroke:#1e40af
    style UVICORN fill:#34d399,stroke:#059669
    style EXT_AI fill:#fbbf24,stroke:#d97706
```

---

## 🔮 Proposed Production Architecture

```mermaid
graph TB
    subgraph "CDN Layer"
        CF[CloudFront CDN<br/>Static Assets]
    end
    
    subgraph "Frontend"
        VERCEL[Vercel Deployment<br/>Auto-scaling]
        S3_STATIC[S3 Bucket<br/>Static Files]
    end
    
    subgraph "Load Balancer"
        ALB[AWS ALB<br/>HTTPS Termination]
    end
    
    subgraph "Backend Cluster"
        API1[FastAPI Instance 1]
        API2[FastAPI Instance 2]
        API3[FastAPI Instance 3]
    end
    
    subgraph "Data Layer"
        RDS[(PostgreSQL RDS<br/>Connection Pooling)]
        REDIS[(Redis Cache<br/>Query Results)]
        S3_FILES[S3 Bucket<br/>Document Storage]
    end
    
    subgraph "External Services"
        AI_SERVICES[Groq + Claude APIs]
        SEARCH_API[DuckDuckGo API]
    end
    
    CF --> VERCEL
    VERCEL --> S3_STATIC
    USER[Users] --> CF
    USER --> ALB
    ALB --> API1
    ALB --> API2
    ALB --> API3
    
    API1 --> RDS
    API2 --> RDS
    API3 --> RDS
    
    API1 --> REDIS
    API2 --> REDIS
    API3 --> REDIS
    
    API1 --> S3_FILES
    API2 --> S3_FILES
    API3 --> S3_FILES
    
    API1 --> AI_SERVICES
    API2 --> AI_SERVICES
    API3 --> AI_SERVICES
    
    API1 --> SEARCH_API
    API2 --> SEARCH_API
    API3 --> SEARCH_API
    
    style CF fill:#fbbf24,stroke:#d97706
    style ALB fill:#34d399,stroke:#059669
    style RDS fill:#60a5fa,stroke:#1e40af
    style REDIS fill:#f87171,stroke:#dc2626
```

---

## 📈 Performance Optimization Strategy

```mermaid
graph TD
    REQUEST[User Request] --> CDN{CDN Cache?}
    CDN -->|Hit| FAST[Return Cached<br/>< 50ms]
    CDN -->|Miss| LB[Load Balancer]
    
    LB --> API[API Server]
    API --> REDIS{Redis Cache?}
    
    REDIS -->|Hit| MED[Return from Cache<br/>< 100ms]
    REDIS -->|Miss| DB[Database Query]
    
    DB --> COMPUTE[Compute Result]
    COMPUTE --> CACHE_WRITE[Write to Redis]
    CACHE_WRITE --> RETURN[Return to User<br/>< 500ms]
    
    style FAST fill:#34d399,stroke:#059669
    style MED fill:#fbbf24,stroke:#d97706
    style RETURN fill:#60a5fa,stroke:#1e40af
```

---

## 🎨 Component Architecture (Frontend)

```mermaid
graph TD
    APP[App.tsx<br/>Root Component] --> ROUTER[React Router]
    
    ROUTER --> HOME[Home Page]
    ROUTER --> RESEARCH[Research Page]
    ROUTER --> DETECTIVE[Detective Wall]
    ROUTER --> ANALYTICS[Analytics Page]
    ROUTER --> CHAT[Legal Chat]
    
    ANALYTICS --> JUDGE[Judge Analytics Component]
    ANALYTICS --> DEVIL[Devil's Advocate Component]
    
    JUDGE --> FORM_J[Input Form]
    JUDGE --> RESULTS_J[Results Display]
    JUDGE --> EXPORT_J[Export Button]
    
    DEVIL --> FORM_D[Input Form]
    DEVIL --> RESULTS_D[Results Display]
    DEVIL --> EXPORT_D[Export Button]
    
    DETECTIVE --> CANVAS[Canvas Component]
    CANVAS --> NODE_MGR[Node Manager]
    CANVAS --> CONN_MGR[Connection Manager]
    CANVAS --> AI_ASSIST[AI Assistant]
    
    RESEARCH --> SEARCH[Search Interface]
    RESEARCH --> UPLOAD[Document Upload]
    RESEARCH --> RESULTS[Search Results]
    
    style APP fill:#60a5fa,stroke:#1e40af
    style ANALYTICS fill:#fbbf24,stroke:#d97706
    style DETECTIVE fill:#34d399,stroke:#059669
    style RESEARCH fill:#a78bfa,stroke:#7c3aed
```

---

## 🔄 State Management Flow

```mermaid
stateDiagram-v2
    [*] --> Idle
    
    Idle --> Loading : User Action
    Loading --> Success : API Response OK
    Loading --> Error : API Error
    
    Success --> Idle : Reset
    Error --> Idle : Retry
    
    Success --> Processing : Further Action
    Processing --> Success : Complete
    Processing --> Error : Failed
    
    note right of Loading
        Show spinner
        Disable inputs
    end note
    
    note right of Success
        Display results
        Enable export
    end note
    
    note right of Error
        Show error message
        Enable retry button
    end note
```

---

*All diagrams are rendered automatically in GitHub, GitLab, and modern markdown viewers.*
