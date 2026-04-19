# 🚀 Quick Start - Redis & Backend Upgrades

## 5-Minute Setup

### 1️⃣ Install Dependencies
```bash
pip install -r requirements.txt
```

### 2️⃣ Get Redis Running

**Option A: Docker (Easiest)**
```bash
docker run -d -p 6379:6379 --name redis redis:latest
```

**Option B: Local Installation**
```bash
# Windows: Use WSL or Windows Redis
# macOS: brew install redis && redis-server
# Linux: sudo apt-get install redis-server && redis-server
```

**Option C: Redis Cloud (Free)**
- Go to https://redis.com/try-free/
- Create account and database
- Copy connection string

### 3️⃣ Update `.env`

```env
REDIS_ENABLED=true
REDIS_URL=redis://localhost:6379/0
```

If using Redis Cloud:
```env
REDIS_URL=redis://default:YOUR_PASSWORD@YOUR_HOST:YOUR_PORT
```

### 4️⃣ Start the App

**Terminal 1:**
```bash
cd src
python -m uvicorn junior.main:app --reload
```

**Terminal 2:**
```bash
# For async jobs (optional but recommended)
celery -A junior.workers.celery_app worker --loglevel=info
```

### 5️⃣ Verify Everything Works

```bash
# Check health
curl http://localhost:8000/api/v1/health

# Test wall analysis (with caching)
curl -X POST http://localhost:8000/api/v1/wall/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "nodes": [{"id": "1", "title": "Test", "type": "Evidence"}],
    "edges": []
  }'
```

## 🎯 What's New?

### ⚡ Performance
- Wall analysis: **10-150x faster** (cached)
- Proactive suggestions: **instant** (cached)
- Large walls: **no timeouts** (async)

### 💾 Persistence
- Save wall snapshots: `POST /api/v1/wall/analyze?case_id=CASE_123`
- Load anytime: `POST /api/v1/wall/snapshot/{snapshot_id}`
- Full version history

### 📊 Enhanced Metadata
Nodes now track:
- Document source
- Page numbers
- Quote text
- Court information
- Confidence scores

### 🔄 Async Processing
For large walls (50+ nodes):
```bash
# Submit job
POST /api/v1/wall/analyze-async

# Check progress
GET /api/v1/wall/task-status/{task_id}
```

### 🚀 Proactive Suggestions
Automatically integrated into wall analysis:
- Missing documents
- Uncited evidence
- Relevant recent judgments
- Procedural next steps

### 📈 Monitoring
Check all services:
```bash
GET /api/v1/health
GET /api/v1/health/redis
GET /api/v1/health/wall
```

## 📚 API Examples

### Basic Wall Analysis (Cached)

```bash
curl -X POST http://localhost:8000/api/v1/wall/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "case_context": "Section 302 IPC case",
    "nodes": [
      {
        "id": "1",
        "title": "Witness Statement",
        "type": "Evidence",
        "content": "Witness saw incident",
        "source_document_id": "doc-123",
        "page_number": 5
      }
    ],
    "edges": []
  }'
```

### Save & Load Snapshot

```bash
# Analyze and save
curl -X POST 'http://localhost:8000/api/v1/wall/analyze?case_id=CASE_123' \
  -H "Content-Type: application/json" \
  -d '{"nodes": [...], "edges": []}'

# Returns: {"snapshot_id": "abc-123"}

# Load later
curl -X POST http://localhost:8000/api/v1/wall/snapshot/abc-123
```

### Async Analysis (Large Walls)

```bash
# Submit
curl -X POST http://localhost:8000/api/v1/wall/analyze-async \
  -H "Content-Type: application/json" \
  -d '{"nodes": [...lots of nodes...], "edges": [...]}'

# Returns: {"task_id": "task-xyz"}

# Check progress
curl http://localhost:8000/api/v1/wall/task-status/task-xyz

# When done: {"status": "SUCCESS", "result": {...}}
```

## ✅ Verification Checklist

- [ ] Redis running (`redis-cli ping` returns PONG)
- [ ] App starts without errors
- [ ] `/api/v1/health` shows `"status": "healthy"`
- [ ] Redis connection: `"redis": "connected"`
- [ ] Wall analysis returns cached results on 2nd call
- [ ] Celery worker running (if using async)

## 🆘 Troubleshooting

| Issue | Solution |
|-------|----------|
| `Connection refused` | Ensure Redis is running |
| `redis://localhost:6379/0` not working | Use `redis://127.0.0.1:6379/0` |
| Slow cache hits | Check network latency to Redis |
| Tasks not processing | Start Celery worker in terminal 2 |
| Module import errors | Run `pip install -r requirements.txt` again |

## 📚 Full Documentation

See [REDIS_SETUP_GUIDE.md](REDIS_SETUP_GUIDE.md) for:
- Detailed configuration
- Architecture overview
- Performance benchmarks
- Security best practices
- API reference

## 🎓 Key Features Explained

### 🔄 Caching
Once a wall is analyzed, results cached for 30 minutes. Same wall analyzed again returns instant result.

### 💾 Snapshots
Save the current state of the wall with all analysis. Load it later to continue working or create comparison.

### ⏳ Async
For large cases with 50+ evidence nodes, submit as background job. Get status updates as it processes.

### 🤖 Proactive
After analysis, get AI suggestions for missing evidence, related judgments, next procedural steps.

### 📍 Provenance
Every evidence node tracks where it came from - document, page, quote, confidence level.

## 🔗 Useful Commands

```bash
# Start Redis (local)
redis-server

# Check Redis
redis-cli ping

# View cache keys
redis-cli KEYS "junior:*"

# Clear all cache
redis-cli FLUSHALL

# Start Celery worker
celery -A junior.workers.celery_app worker --loglevel=info

# Monitor Celery tasks
celery -A junior.workers.celery_app inspect active
```

## 📊 Expected Performance

| Metric | Value |
|--------|-------|
| First analysis (50 nodes) | 15-20s |
| Cached analysis | ~100ms |
| Proactive suggestions | instant |
| Async large wall (100 nodes) | 30-45s |
| Health check | <100ms |

---

**Ready?** Start with step 1️⃣ above!

Need help? Check `REDIS_SETUP_GUIDE.md` for detailed information.
