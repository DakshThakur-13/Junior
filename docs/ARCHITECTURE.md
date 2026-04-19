# 🏗️ Detective Wall Architecture

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                          FRONTEND (React)                            │
│  - Wall Canvas (Nodes + Edges)                                       │
│  - Node Details Panel (Enhanced with Provenance)                     │
│  - Search & Filtering                                                │
│  - Suggestion Queue                                                  │
└────────────────────┬──────────────────────────────────────────────────┘
                     │
                     │ HTTP/JSON
                     │
┌────────────────────┴──────────────────────────────────────────────────┐
│                    FASTAPI GATEWAY                                    │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  src/junior/api/endpoints/wall.py                              │  │
│  │  • /analyze (cached)                                           │  │
│  │  • /analyze-async (background job)                             │  │
│  │  • /task-status/{id} (job tracking)                            │  │
│  │  • /snapshot/{id} (persistence)                                │  │
│  │  • /cache/clear (admin)                                        │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  src/junior/api/endpoints/health.py                            │  │
│  │  • /health (full system)                                       │  │
│  │  • /health/redis (cache status)                                │  │
│  │  • /health/wall (wall service)                                 │  │
│  └────────────────────────────────────────────────────────────────┘  │
└────┬───────────────┬────────────────┬─────────────────┬───────────────┘
     │               │                │                 │
     │               │                │                 │
     ▼               ▼                ▼                 ▼
┌─────────────┐ ┌──────────────┐ ┌──────────────┐ ┌─────────────┐
│   CACHE     │ │  BACKEND     │ │  PERSISTENCE │ │  MONITORING │
│   (Redis)   │ │  ANALYSIS    │ │  (Snapshots) │ │  (Health)   │
└─────────────┘ └──────────────┘ └──────────────┘ └─────────────┘
```

## Data Flow: Wall Analysis with Caching

```
                        ┌─ CACHE HIT (100ms)
                        │
User clicks "Analyze"   │
        ↓               │
   Generate cache key   │
   from nodes/edges     │
        ↓               │
 Check Redis cache ─────┤
        ↓               │
        └─ CACHE MISS (15-20s)
           │
           ├→ Run DetectiveWallAgent
           │  (LLM analysis)
           │
           ├→ Cache result (30 min TTL)
           │
           ├→ Get proactive suggestions
           │
           └→ Return result to user
```

## Component Relationships

```
┌──────────────────────────────────────────────────────────────────┐
│                 WallService (Main Orchestrator)                  │
│  src/junior/services/wall_service.py                             │
│  ┌─────────────┐ ┌──────────────┐ ┌──────────────┐              │
│  │   Redis     │ │   Detective  │ │   Proactive  │              │
│  │   Client    │ │   Wall Agent │ │  Assistant   │              │
│  └─────────────┘ └──────────────┘ └──────────────┘              │
│         ↓              ↓                ↓                         │
│   [caching]      [analysis]      [suggestions]                   │
└──────────────────────────────────────────────────────────────────┘
         ↓                ↓                ↓
         
    ┌─────────┐    ┌──────────────┐   ┌──────────────┐
    │  REDIS  │    │   SUPABASE   │   │   GROQ API   │
    │ localhost   (Postgres+Vec)  │   │  (LLM Calls) │
    └─────────┘    └──────────────┘   └──────────────┘
```

## Request Processing Pipeline

### Synchronous Wall Analysis

```
1. User sends POST /api/v1/wall/analyze
   │
2. FastAPI endpoint receives request
   │
3. WallService.analyze() called
   │
4. Generate cache key from nodes/edges
   │
5. Check Redis cache
   ├─ HIT:  Return cached result (1ms)
   └─ MISS: Continue to step 6
   │
6. Call DetectiveWallAgent.analyze()
   │
7. Agent builds prompt + calls Groq LLM
   │
8. LLM returns analysis JSON
   │
9. Get proactive suggestions
   │
10. Merge proactive into next_actions
    │
11. Cache full result in Redis (TTL: 30min)
    │
12. Save snapshot (if case_id provided)
    │
13. Return response to user (15-20s total, or 100ms if cached)
```

### Asynchronous Wall Analysis

```
1. User sends POST /api/v1/wall/analyze-async
   │
2. FastAPI endpoint receives request
   │
3. Submit Celery task (returns immediately with task_id)
   │
4. Return {task_id, status_url} to user (instant)
   │
5. Celery worker picks up task from Redis queue
   │
6-13. [Same as synchronous flow above]
   │
14. Celery stores result in Redis (TTL: 1 hour)
    │
15. User polls /api/v1/wall/task-status/{task_id}
    │
16. Return status: PENDING → PROGRESS → SUCCESS/FAILED
```

## Redis Data Structures

### Cache Keys (Namespace: "junior:wall:analysis")

```
Key: analysis:b4f7d2a1c9e3f6b8
Value: {
  "summary": "Analysis summary...",
  "insights": [...],
  "suggested_links": [...],
  "next_actions": [...]
}
TTL: 30 minutes
```

### Snapshot Keys (Namespace: "junior:wall:snapshots")

```
Key: snapshot:abc-123-def
Value: {
  "wall_id": "abc-123-def",
  "case_id": "CASE_123",
  "nodes": [...],
  "edges": [...],
  "analysis": {...},
  "created_at": "2026-04-20T...",
  "version": 1
}
TTL: Indefinite (permanent storage)
```

### Suggestion Cache (Namespace: "junior:wall:suggestions")

```
Key: proactive:CASE_123
Value: [
  "Node #5 claims Section 302 but no FIR",
  "Arnesh Kumar judgment strengthens bail arg",
  "3 evidence nodes lack page citations"
]
TTL: 15 minutes
```

## API Endpoints & Flows

### POST /api/v1/wall/analyze

```
Request Body:
{
  "case_context": "Section 302 case",
  "nodes": [
    {
      "id": "1",
      "title": "Witness Statement",
      "type": "Evidence",
      "source_document_id": "doc-123",
      "page_number": 5,
      "quote_text": "...",
      "confidence_score": 0.95
    }
  ],
  "edges": [{...}]
}

Query Parameters:
- case_id: (optional) For persistence
- force_refresh: (optional) Skip cache

Response:
{
  "summary": "...",
  "insights": [{title, detail, severity, node_ids}],
  "suggested_links": [{source, target, label, confidence, reason}],
  "next_actions": ["...", "..."],
  "analysis_timestamp": "2026-04-20T...",
  "cache_status": "hit|miss",
  "snapshot_id": "abc-123-def"
}
```

### POST /api/v1/wall/analyze-async

```
Request: [same as above]

Response (Immediate):
{
  "task_id": "task-xyz-abc",
  "status": "PENDING",
  "status_url": "/api/v1/wall/task-status/task-xyz-abc"
}

Status Polling:
GET /api/v1/wall/task-status/task-xyz-abc

Response (In Progress):
{
  "task_id": "task-xyz-abc",
  "status": "PROGRESS",
  "progress": {current: 50, total: 100}
}

Response (Complete):
{
  "task_id": "task-xyz-abc",
  "status": "SUCCESS",
  "result": {...full analysis...}
}
```

## Performance Characteristics

### Memory Usage

```
Per Cache Entry:
- Wall Analysis: ~2-5 KB
- Snapshot: ~10-50 KB
- Suggestion: ~0.5-1 KB

Total for 1000 cases:
- Analysis cache: ~3-5 MB
- Snapshots: ~50-100 MB
- Suggestions: ~0.5-1 MB
```

### Network Latency

```
Operation               Local Redis    Cloud Redis
─────────────────────────────────────────────────
Get from cache         ~1ms           ~50-100ms
Set cache              ~1ms           ~50-100ms
Health check           ~1ms           ~50-100ms
Large snapshot load    ~5ms           ~100-150ms
```

### Processing Times

```
Operation                Time (No Cache)    Time (Cached)
──────────────────────────────────────────────────────
50-node wall analysis    15-20s            100-200ms
100-node wall analysis   30-45s (async)    100-200ms
Proactive suggestions    8-10s             10-50ms
Snapshot save            ~100ms            ~100ms
```

## Celery Task Queue Architecture

```
┌─────────────────────────────────────────────────────┐
│          Celery Task Queue (Redis Broker)           │
│  Stores pending/active/completed tasks              │
└────────┬───────────────────┬──────────────┬─────────┘
         │                   │              │
┌────────▼─────┐    ┌───────▼──────┐  ┌──▼───────────┐
│   PENDING    │    │   ACTIVE     │  │   RESULTS    │
│   Tasks      │    │   Tasks      │  │   (1 hour)   │
│   (queued)   │    │   (running)  │  │              │
└──────────────┘    └──────────────┘  └──────────────┘
         ↑                  ↑                  ↑
         │                  │                  │
      submit             execute             store
      (instant)          (30-45s)          (retrieved
                                           by client)
```

## Monitoring Stack

```
┌──────────────────────────────────────────┐
│     Health Check Endpoints                │
│                                           │
│  GET /api/v1/health                      │
│  ├─ System Status                        │
│  ├─ All Service Statuses                 │
│  └─ Timestamp                            │
│                                           │
│  GET /api/v1/health/redis                │
│  ├─ Redis Connection                     │
│  ├─ Database Number                      │
│  └─ URL (masked password)                │
│                                           │
│  GET /api/v1/health/wall                 │
│  ├─ Wall Service Status                  │
│  └─ Available Features                   │
└──────────────────────────────────────────┘
         │
         ├─ Groq API Status
         ├─ Supabase Connection
         ├─ Redis Connection
         ├─ Celery Job Queue
         ├─ PII Redaction
         └─ Embeddings Model
```

## Database Schema Additions

### Wall Snapshots (Future Supabase Table)

```sql
CREATE TABLE wall_snapshots (
  id UUID PRIMARY KEY,
  case_id STRING NOT NULL,
  wall_id STRING NOT NULL,
  nodes JSONB NOT NULL,
  edges JSONB NOT NULL,
  analysis JSONB,
  metadata JSONB,
  version INT DEFAULT 1,
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now(),
  
  INDEX (case_id),
  INDEX (created_at)
);
```

### Wall Nodes (Enhanced)

```sql
ALTER TABLE wall_nodes ADD COLUMN (
  source_document_id STRING,
  page_number INT,
  paragraph_number INT,
  quote_text TEXT,
  source_type STRING,
  court STRING,
  case_number STRING,
  confidence_score FLOAT
);
```

## Deployment Architecture

### Development (Single Machine)

```
┌─────────────────────────────────────┐
│    Your Laptop                       │
│                                     │
│  ┌───────────────────────────────┐  │
│  │ Python 3.9+                   │  │
│  │ ├─ FastAPI (port 8000)       │  │
│  │ ├─ Celery Worker             │  │
│  │ └─ Redis (port 6379)         │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
```

### Production (Cloud)

```
┌────────────────────────────────────┐
│       AWS/Vercel/Railway           │
│                                    │
│  ┌──────────────┐  ┌────────────┐  │
│  │  App Server  │  │   Celery   │  │
│  │  (Gunicorn)  │  │  Worker    │  │
│  │  Port 8000   │  │  (Scaled)  │  │
│  └──────┬───────┘  └─────┬──────┘  │
│         │                │         │
│         └────────┬───────┘         │
│                  ▼                 │
│         ┌──────────────────┐       │
│         │  Redis Cloud     │       │
│         │  or ElastiCache  │       │
│         │                  │       │
│         │  (External)      │       │
│         └──────────────────┘       │
└────────────────────────────────────┘
         │
         ▼
    ┌─────────────┐
    │  Supabase   │
    │  (Database) │
    └─────────────┘
```

---

This architecture provides:
- ✅ **Scalability** - Async processing for large walls
- ✅ **Performance** - 10-150x speedup via caching
- ✅ **Reliability** - Health checks and monitoring
- ✅ **Persistence** - Snapshots and versioning
- ✅ **Accuracy** - Enhanced provenance tracking
- ✅ **Intelligence** - Proactive suggestions

