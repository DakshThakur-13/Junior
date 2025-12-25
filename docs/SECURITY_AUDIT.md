# Security Audit Documentation

**System:** Junior AI Legal Assistant  
**Version:** 0.1.0  
**Audit Date:** December 25, 2025  
**Next Audit:** June 25, 2026

## Executive Summary

This document provides a comprehensive security audit of Junior AI Legal Assistant, detailing implemented security measures, identified vulnerabilities, and compliance with security standards.

## Security Architecture

### 1. Authentication & Authorization

#### Current Implementation
- **Authentication Method:** API key-based (development), extensible to OAuth2/JWT
- **Session Management:** Token-based with configurable expiry
- **Admin Authentication:** Separate admin API key for privileged operations
- **Default Security:** Development mode allows unrestricted admin access (must be disabled in production)

#### Security Measures
```python
# Admin endpoint protection
async def verify_admin_key(api_key: str = Header(...)):
    if settings.debug:
        return True  # ⚠️ DEV ONLY
    if api_key != settings.admin_api_key:
        raise HTTPException(status_code=403, detail="Invalid admin key")
```

#### Recommendations
- [ ] Implement JWT-based authentication for production
- [ ] Add rate limiting per user/IP
- [ ] Implement multi-factor authentication (MFA)
- [ ] Add OAuth2 integration (Google, Microsoft)

### 2. Data Protection

#### PII Redaction
**Status:** ✅ Implemented  
**Library:** GLiNER (Generalized Named Entity Recognition)  
**Protected Entities:**
- Person names
- Phone numbers
- Email addresses
- Addresses
- Aadhaar numbers
- PAN cards
- Bank account numbers
- Medical records

```python
# PII Redaction Service
class PIIRedactor:
    ENTITY_LABELS = [
        "person", "phone_number", "email", "address",
        "aadhaar_number", "pan_card", "bank_account",
        "medical_record"
    ]
```

**Coverage:** All user inputs, uploaded documents, chat logs

#### Encryption

**At Rest:**
- Database: Supabase PostgreSQL with encryption at rest
- Uploaded Files: Stored with restricted access permissions
- Environment Variables: `.env` file excluded from version control
- API Keys: Stored as environment variables, never hardcoded

**In Transit:**
- HTTPS/TLS 1.3 for all API communication (production)
- WebSocket connections: WSS (secure WebSocket)
- CORS policy: Restricted to frontend origin

**Status:** ⚠️ Partial (HTTPS must be enforced in production)

#### Sensitive Data Handling
```python
# Configuration class with sensitive fields
class Settings(BaseSettings):
    groq_api_key: str = Field(..., description="Groq API Key")
    supabase_url: str = Field(..., description="Supabase URL")
    supabase_key: str = Field(..., description="Supabase Service Key")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
```

### 3. API Security

#### Request Validation
- **Input Validation:** Pydantic schemas for all endpoints
- **Type Checking:** Strict type validation on all inputs
- **File Upload Limits:** Configurable max file size (default: 10MB)
- **Content Type Validation:** Only allowed MIME types accepted

#### Rate Limiting
**Status:** ❌ Not Implemented  
**Recommendation:** Add rate limiting middleware

```python
# Proposed implementation
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/api/v1/chat/stream")
@limiter.limit("20/minute")  # 20 requests per minute
async def stream_chat(...):
    pass
```

#### CORS Policy
```python
# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Frontend only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Production Recommendation:** Restrict to production domain only

#### Error Handling
```python
# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
        # ✅ Does not leak stack traces to client
    )
```

### 4. Logging & Monitoring

#### Request Logging
**Status:** ✅ Implemented

```python
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    logger.info(f"{request.method} {request.url.path} → {response.status_code} ({duration:.3f}s)")
    return response
```

**Log Contents:**
- HTTP method and path
- Response status code
- Request duration
- Timestamp

**PII Handling:** Logs are sanitized, no sensitive data logged

#### Error Logging
- All exceptions logged with full stack traces (server-side only)
- User-facing errors sanitized
- Log rotation: 90 days retention

#### Security Event Logging
**To Implement:**
- Failed authentication attempts
- Admin endpoint access
- Unusual access patterns
- Data deletion events

### 5. Infrastructure Security

#### File Upload Security
```python
# Secure file handling
ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.txt', '.mp3', '.wav'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def secure_filename(filename: str) -> str:
    """Sanitize uploaded filename"""
    # Remove path traversal attempts
    filename = os.path.basename(filename)
    # Remove non-alphanumeric characters
    filename = re.sub(r'[^\w\s.-]', '', filename)
    return filename
```

**Measures:**
- ✅ File type validation by extension and MIME type
- ✅ File size limits enforced
- ✅ Filename sanitization (prevent path traversal)
- ✅ Isolated upload directory (`uploads/`)
- ⚠️ Missing: Virus scanning integration

#### Database Security (Supabase)
- Row-level security (RLS) policies
- Connection pooling with pg_bouncer
- Encrypted connections (SSL/TLS)
- Automated backups
- Point-in-time recovery (PITR)

**Access Control:**
- Service role key (server-side only)
- Anonymous key (restricted permissions)
- API key rotation capability

#### Environment Isolation
```
Development: localhost:8000, localhost:5173
Staging: [To be configured]
Production: [To be configured with HTTPS]
```

**Security Checklist for Production:**
- [ ] HTTPS/TLS certificate installed
- [ ] Debug mode disabled (`DEBUG=False`)
- [ ] Admin authentication enforced
- [ ] CORS restricted to production domain
- [ ] Environment variables secured (secrets manager)
- [ ] Database firewall rules configured

### 6. Third-Party API Security

#### API Key Management
**Current APIs:**
- Groq (LLM inference)
- Perplexity (web search)
- HuggingFace (embeddings)
- Supabase (database)

**Security Measures:**
- ✅ API keys stored in environment variables
- ✅ Never logged or exposed to client
- ✅ Configurable per environment
- ⚠️ No key rotation policy documented

**Recommendation:** Implement API key rotation every 90 days

#### API Request Security
- Rate limiting on LLM calls (prevent abuse)
- Input sanitization before external API calls
- Response validation and error handling
- Timeout configuration (prevent hanging requests)

### 7. Dependency Security

#### Vulnerability Scanning
**Status:** ⚠️ Not Automated

**Manual Audit (Dec 2025):**
```bash
# Check for known vulnerabilities
pip-audit

# Update all dependencies
pip list --outdated
```

**Findings:**
- Python 3.14: Known Pydantic V1 compatibility warning (non-critical)
- faster-whisper: Installation issues due to Rust dependency

**Recommendations:**
- [ ] Set up automated dependency scanning (GitHub Dependabot)
- [ ] Regular security updates (monthly)
- [ ] Pin dependency versions in requirements.txt

#### Supply Chain Security
```python
# requirements.txt with version pinning
fastapi>=0.115.0
uvicorn>=0.32.0
pydantic>=2.0.0
```

**Recommendations:**
- Use exact version pinning (==) for production
- Verify package signatures
- Use private PyPI mirror for critical deployments

### 8. Incident Response

#### Current Capabilities
- Logging infrastructure in place
- Error tracking and stack traces
- Admin health check endpoints

#### Incident Response Plan
**To Document:**
1. Detection and identification
2. Containment procedures
3. Eradication steps
4. Recovery procedures
5. Post-incident analysis

**Contact Escalation:**
- L1: Development team
- L2: Security team (to be designated)
- L3: Legal/compliance (data breaches)

#### Breach Notification
**Legal Requirements:**
- GDPR: 72 hours for data breaches
- DPDP Act 2023: As soon as practicable
- Indian IT Act: Reasonable time

## Vulnerability Assessment

### High Priority
1. **Missing Rate Limiting** - Risk: API abuse, DoS attacks
2. **No Virus Scanning** - Risk: Malware upload via documents
3. **Production Security Not Enforced** - Risk: Debug mode, weak CORS

### Medium Priority
4. **No JWT Authentication** - Risk: Session management issues
5. **No Automated Dependency Scanning** - Risk: Known vulnerabilities
6. **Missing Security Headers** - Risk: XSS, clickjacking

### Low Priority
7. **No Multi-Factor Authentication** - Risk: Account compromise
8. **Log Retention Not Enforced** - Risk: Disk space, compliance
9. **No Web Application Firewall (WAF)** - Risk: Advanced attacks

## Compliance Status

### GDPR (General Data Protection Regulation)
- ✅ Privacy by design implemented
- ✅ Data minimization practiced
- ✅ PII redaction in place
- ✅ Right to erasure supported
- ⚠️ Data processing agreements needed for third-party APIs
- ⚠️ Cookie consent not implemented (if cookies used)

### Indian IT Act 2000 & DPDP Act 2023
- ✅ Reasonable security practices (Section 43A)
- ✅ Sensitive personal data protection
- ⚠️ Data breach notification procedure needs documentation
- ⚠️ User consent mechanisms need enhancement

### ISO 27001 Alignment
- ✅ Access control (partial)
- ✅ Cryptography (partial)
- ⚠️ Physical security not documented
- ⚠️ Business continuity plan missing

## Security Testing

### Performed Tests
- [x] Manual penetration testing (basic)
- [x] Dependency vulnerability scan
- [x] Configuration review
- [ ] Automated security scanning
- [ ] Load testing
- [ ] Chaos engineering

### Test Results Summary
**SQL Injection:** ✅ Protected (Supabase parameterized queries)  
**XSS:** ⚠️ Needs frontend security headers  
**CSRF:** ✅ Protected (token-based API)  
**Authentication Bypass:** ⚠️ Admin endpoints weak in dev mode  
**File Upload Vulnerabilities:** ⚠️ No virus scanning

## Remediation Roadmap

### Immediate (0-30 days)
1. Implement rate limiting middleware
2. Add security headers (CSP, X-Frame-Options, etc.)
3. Document production security checklist
4. Enforce admin authentication in all modes

### Short-term (1-3 months)
5. Implement JWT authentication
6. Add automated dependency scanning
7. Integrate virus scanning for uploads
8. Set up security monitoring and alerts

### Long-term (3-6 months)
9. Conduct professional penetration test
10. Implement Web Application Firewall (WAF)
11. Add multi-factor authentication
12. Complete ISO 27001 certification preparation

## Security Contacts

**Security Team:**  
Email: security@junior-legal.com

**Vulnerability Disclosure:**  
Email: security@junior-legal.com  
PGP Key: [To be published]

**Responsible Disclosure Policy:**  
We follow a 90-day disclosure timeline for reported vulnerabilities.

## Audit History

| Date | Auditor | Findings | Status |
|------|---------|----------|--------|
| 2025-12-25 | Initial Setup | 9 vulnerabilities identified | In Progress |

## Appendix

### Security Headers Checklist
```python
# To implement in main.py
from fastapi.middleware.security import SecurityHeadersMiddleware

security_headers = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self'",
    "Referrer-Policy": "strict-origin-when-cross-origin"
}
```

### Environment Variables Checklist
- [ ] All secrets in environment variables (not code)
- [ ] `.env` in `.gitignore`
- [ ] Production secrets in secrets manager (AWS Secrets Manager, Azure Key Vault)
- [ ] Regular key rotation schedule documented

---

**Document Control:**  
Owner: Security Team  
Approver: CTO/CISO  
Classification: Internal  
Next Audit: June 25, 2026
