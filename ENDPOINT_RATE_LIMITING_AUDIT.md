# UniGPU Endpoint Rate Limiting Audit
**Date:** May 4, 2026  
**Assessment:** Comprehensive rate limiting analysis for all public and protected endpoints

---

## Executive Summary

**CRITICAL FINDINGS:**
- ❌ **WebSocket endpoints have NO rate limiting** (Agents, Provider Dashboards)
- ❌ **Auth endpoints lack application-level rate limiting** (Nginx only: 30 req/min)
- ⚠️ **Nginx rate limit is lenient** (30 req/min = 0.5 req/sec is low for DDoS protection)
- ⚠️ **Unauthenticated download endpoint NOT rate limited** (path traversal prevention only)
- ✅ **REST API endpoints have Nginx-level protection** (30 req/min burst 20)

**Recommendation Priority:** CRITICAL > HIGH > MEDIUM

---

## 1. Authentication Endpoints (`/auth`)

### 1.1 POST `/auth/register`
- **Public Access:** ✅ Yes (no authentication required)
- **Current Rate Limit:** ⚠️ Nginx only: 30 req/min per IP
- **Risk:** Account enumeration, spam accounts, dictionary attacks
- **Severity:** 🔴 **HIGH** (CWE-770: Allocation of Resources Without Limits)

**Status Code:**
```
✅ 201 Created (success)
❌ 400 Bad Request (invalid input)
```

**Vulnerability:**
```python
# backend/app/routers/auth.py:33-43
@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(data: UserCreate, db: AsyncSession = Depends(get_db)):
    # NO PER-ENDPOINT RATE LIMITING - relies on Nginx only
    # Attackers can:
    # - Brute-force valid usernames/emails
    # - Create spam accounts
    # - Enumerate users in the system
```

**Recommended Rate Limit:** 
- ✅ **3-5 requests per minute** (per IP/account)
- ✅ **Max 10 accounts per 24 hours** (per IP)

---

### 1.2 POST `/auth/login`
- **Public Access:** ✅ Yes (no authentication required)
- **Current Rate Limit:** ⚠️ Nginx only: 30 req/min per IP
- **Risk:** Brute-force password attacks, credential stuffing
- **Severity:** 🔴 **CRITICAL** (CWE-770, CWE-308: Use of Hard-coded Password)

**Vulnerability:**
```python
# backend/app/routers/auth.py:57-64
@router.post("/login", response_model=Token)
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    # NO PER-ENDPOINT RATE LIMITING
    # No exponential backoff or account lockout
    # Attackers can:
    # - Try 30 passwords per minute per IP
    # - Credential stuffing from leaked databases
    # - No account lockout after N failed attempts
```

**Recommended Rate Limit:**
- ✅ **5 requests per minute** (per IP)
- ✅ **3 failed attempts → 15 minute lockout**
- ✅ **Progressive delay** (1s → 2s → 4s after each failure)

---

## 2. GPU Management Endpoints (`/gpus`)

### 2.1 POST `/gpus/register`
- **Authentication:** ✅ Required (provider/admin only)
- **Current Rate Limit:** ✅ Nginx: 30 req/min per IP
- **Risk:** Resource exhaustion, duplicate GPU spam
- **Severity:** 🟡 **MEDIUM**

**Status Code:**
```
201 Created (success)
400 Bad Request (invalid input)
401 Unauthorized (no auth)
403 Forbidden (insufficient role)
```

---

### 2.2 GET `/gpus/`
- **Authentication:** ❌ NOT required (public)
- **Current Rate Limit:** ✅ Nginx: 30 req/min per IP
- **Risk:** Information disclosure, monitoring attacks
- **Severity:** 🟡 **MEDIUM**

**Endpoint Lists All GPUs** - Consider adding pagination/filtering

---

### 2.3 GET `/gpus/available`
- **Authentication:** ❌ NOT required (public)
- **Current Rate Limit:** ✅ Nginx: 30 req/min per IP
- **Risk:** Enumeration of available resources, planning attacks
- **Severity:** 🟡 **MEDIUM**

---

### 2.4 PATCH `/gpus/{gpu_id}/status`
- **Authentication:** ✅ Required (provider/admin only)
- **Current Rate Limit:** ✅ Nginx: 30 req/min per IP
- **Risk:** GPU state manipulation
- **Severity:** 🟡 **MEDIUM**

---

## 3. Job Management Endpoints (`/jobs`)

### 3.1 POST `/jobs/submit`
- **Authentication:** ✅ Required (client/admin only)
- **Current Rate Limit:** ✅ Nginx: 30 req/min per IP
- **File Upload:** ⚠️ Max 50MB per request (via Nginx `client_max_body_size`)
- **Risk:** Disk exhaustion, resource abuse
- **Severity:** 🟡 **MEDIUM** (CWE-770: Allocation of Resources Without Limits)

**Vulnerability:**
```python
# backend/app/routers/jobs.py:31-32
# No rate limit on uploads per user, only per IP
# A single authenticated user could:
# - Submit 30 jobs × 50MB = 1.5GB per minute
# - Exhaust disk space
```

**Recommended Rate Limit:**
- ✅ **5-10 job submissions per minute** (per user)
- ✅ **50MB total upload per 24 hours** (per user)
- ✅ **Max 10 concurrent jobs** (per user)

---

### 3.2 GET `/jobs/`
- **Authentication:** ✅ Required
- **Current Rate Limit:** ✅ Nginx: 30 req/min per IP
- **Risk:** Information disclosure (admins see all jobs)
- **Severity:** 🟡 **LOW**

---

### 3.3 GET `/jobs/{job_id}`
- **Authentication:** ✅ Required
- **Current Rate Limit:** ✅ Nginx: 30 req/min per IP
- **Risk:** None (already rate limited)
- **Severity:** 🟢 **LOW**

---

### 3.4 GET `/jobs/{job_id}/logs`
- **Authentication:** ✅ Required
- **Current Rate Limit:** ✅ Nginx: 30 req/min per IP
- **Risk:** Information disclosure
- **Severity:** 🟡 **MEDIUM**

**Recommended Rate Limit:**
- ✅ **60 requests per minute** (logs polling is legitimate use case)

---

### 3.5 GET `/jobs/{job_id}/download/{filename}` ⚠️ **NO AUTH**
- **Authentication:** ❌ NOT required (public - UUID based)
- **Current Rate Limit:** ❌ **NOT rate limited** (no Nginx rule for /download)
- **Risk:** 🔴 **CRITICAL** - Brute-force UUID enumeration
- **Severity:** 🔴 **CRITICAL** (CWE-639: Authorization Bypass)

**Vulnerability:**
```python
# backend/app/routers/jobs.py:159-175
@router.get("/{job_id}/download/{filename}")
async def download_job_file(job_id: str, filename: str):
    """No auth required — job UUID is unguessable."""
    # BUT NO RATE LIMITING!
    # Attackers can:
    # - Brute-force UUIDs: 10^36 possible values
    # - Download unlimited files
    # - Enumerate training scripts, datasets
```

**Current Nginx Config:**
```nginx
location ~ ^/(auth|gpus|jobs|wallet|admin)/ {
    limit_req zone=api burst=20 nodelay;
    # PROBLEM: This regex includes /jobs but NOT the /download subpath specifically
    # The download endpoint IS affected by this rate limit
}
```

**However, the rate limit is per IP, not per job_id.**

**Recommended Rate Limit:**
- ✅ **10 downloads per minute** (per IP)
- ✅ **100 downloads per 24 hours** (per IP)
- ✅ **Implement short-lived signed download tokens** instead
- ✅ **Add authentication** or at minimum token-based access

---

### 3.6 POST `/jobs/{job_id}/cancel`
- **Authentication:** ✅ Required
- **Current Rate Limit:** ✅ Nginx: 30 req/min per IP
- **Risk:** Denial of service to providers
- **Severity:** 🟡 **MEDIUM**

---

### 3.7 DELETE `/jobs/{job_id}`
- **Authentication:** ✅ Required
- **Current Rate Limit:** ✅ Nginx: 30 req/min per IP
- **Risk:** Data loss
- **Severity:** 🟡 **MEDIUM**

---

## 4. Wallet Endpoints (`/wallet`)

### 4.1 GET `/wallet/`
- **Authentication:** ✅ Required
- **Current Rate Limit:** ✅ Nginx: 30 req/min per IP
- **Risk:** None (user-specific data)
- **Severity:** 🟢 **LOW**

---

### 4.2 POST `/wallet/topup`
- **Authentication:** ✅ Required
- **Current Rate Limit:** ✅ Nginx: 30 req/min per IP
- **Risk:** ⚠️ **Unlimited top-up amount** (no upper limit validation)
- **Severity:** 🔴 **HIGH** (CWE-400: Uncontrolled Resource Consumption)

**Vulnerability:**
```python
# backend/app/routers/wallet.py:20-24
if data.amount <= 0:
    raise HTTPException(status_code=400, detail="Amount must be positive")
wallet.balance += data.amount  # NO UPPER LIMIT!
```

**Recommended Rate Limit:**
- ✅ **5 top-ups per hour** (per user)
- ✅ **Max amount: ₹10,000 per transaction**
- ✅ **Max ₹50,000 per 24 hours** (per user)
- ✅ **Add financial audit logging**

---

### 4.3 GET `/wallet/transactions`
- **Authentication:** ✅ Required
- **Current Rate Limit:** ✅ Nginx: 30 req/min per IP
- **Risk:** None
- **Severity:** 🟢 **LOW**

---

## 5. Admin Endpoints (`/admin`)

### 5.1 GET `/admin/gpus`
- **Authentication:** ✅ Required (admin only)
- **Current Rate Limit:** ✅ Nginx: 30 req/min per IP
- **Risk:** Information disclosure
- **Severity:** 🟡 **LOW**

---

### 5.2 GET `/admin/jobs`
- **Authentication:** ✅ Required (admin only)
- **Current Rate Limit:** ✅ Nginx: 30 req/min per IP
- **Risk:** None (privileged endpoint)
- **Severity:** 🟢 **LOW**

---

### 5.3 GET `/admin/users`
- **Authentication:** ✅ Required (admin only)
- **Current Rate Limit:** ✅ Nginx: 30 req/min per IP
- **Risk:** Sensitive data exposure if admin account compromised
- **Severity:** 🟡 **MEDIUM**

---

### 5.4 GET `/admin/stats`
- **Authentication:** ✅ Required (admin only)
- **Current Rate Limit:** ✅ Nginx: 30 req/min per IP
- **Risk:** None (privileged endpoint)
- **Severity:** 🟢 **LOW**

---

## 6. WebSocket Endpoints - ⚠️ **CRITICAL FINDINGS**

### 6.1 WebSocket `/ws/agent/{gpu_id}`
- **Authentication:** ✅ JWT token required (via query param)
- **Current Rate Limit:** ❌ **NO rate limiting** (long-lived connection)
- **Risk:** 🔴 **CRITICAL** Resource exhaustion, connection flooding
- **Severity:** 🔴 **CRITICAL** (CWE-770: Allocation of Resources Without Limits)

**Vulnerability:**
```python
# backend/app/routers/ws.py:50
@router.websocket("/ws/agent/{gpu_id}")
async def agent_websocket(websocket: WebSocket, gpu_id: str, token: str | None = Query(default=None)):
    # NO RATE LIMITING!
    # NO connection count limit!
    # NO message frequency limit!
    # Attacker can:
    # - Open 1000s of WebSocket connections
    # - Send massive volumes of messages
    # - Exhaust server memory
    # - Cause DoS to legitimate providers
```

**Attacks:**
```bash
# Connection flooding attack
for i in {1..1000}; do
    wscat -c "wss://domain/ws/agent/fake-gpu-$i?token=VALID_JWT" &
done

# Message flooding attack (after connection)
while true; do
    echo '{"type":"metrics","data":{"large":"payload"*1000}}'
done
```

**Recommended Rate Limit:**
- ✅ **Max 1 WebSocket connection per GPU** (per provider)
- ✅ **Max 100 messages per minute** (per connection)
- ✅ **Max message size: 1MB**
- ✅ **Connection timeout: 30 minutes idle**

---

### 6.2 WebSocket `/ws/provider/{provider_id}`
- **Authentication:** ✅ JWT token required (via query param)
- **Current Rate Limit:** ❌ **NO rate limiting**
- **Risk:** 🔴 **CRITICAL** Connection flooding
- **Severity:** 🔴 **CRITICAL**

**Vulnerability:**
```python
# backend/app/routers/ws.py:212
@router.websocket("/ws/provider/{provider_id}")
async def provider_websocket(websocket: WebSocket, provider_id: str, token: str | None = Query(default=None)):
    # NO RATE LIMITING!
    # Multiple connections allowed per provider
    # Attacker can:
    # - Open 100+ dashboard connections
    # - Starve server resources
```

**Recommended Rate Limit:**
- ✅ **Max 5 WebSocket connections per provider** (active dashboards)
- ✅ **Connection timeout: 1 hour idle**

---

## 7. Public/Health Endpoint

### 7.1 GET `/` (health check)
- **Authentication:** ❌ NOT required
- **Current Rate Limit:** ✅ Nginx: 30 req/min per IP
- **Risk:** Minimal (status only)
- **Severity:** 🟢 **LOW**

---

## 8. Documentation Endpoints (Swagger UI)

### 8.1 GET `/docs` (Swagger UI)
- **Authentication:** ❌ NOT required
- **Current Rate Limit:** ✅ Nginx: 30 req/min per IP
- **Risk:** 🔴 **HIGH** - API documentation exposed, enables attacks
- **Severity:** 🔴 **HIGH** (CWE-200: Information Exposure)

**Recommendation:**
- ✅ **Disable in production** or restrict to admin IPs only
- ✅ **Use environment variable to hide Swagger**

---

### 8.2 GET `/openapi.json`
- **Authentication:** ❌ NOT required
- **Current Rate Limit:** ✅ Nginx: 30 req/min per IP
- **Risk:** 🔴 **HIGH** - OpenAPI schema exposes all endpoints
- **Severity:** 🔴 **HIGH**

---

### 8.3 GET `/redoc` (ReDoc)
- **Authentication:** ❌ NOT required
- **Current Rate Limit:** ✅ Nginx: 30 req/min per IP
- **Risk:** 🔴 **HIGH** - Interactive API docs
- **Severity:** 🔴 **HIGH**

---

## Summary Table: Rate Limiting Status

| Endpoint | Auth Required | Public | Current Rate Limit | Status | Severity |
|---|---|---|---|---|---|
| **POST /auth/register** | ❌ | ✅ | 30 req/min (Nginx) | ⚠️ Insufficient | 🔴 CRITICAL |
| **POST /auth/login** | ❌ | ✅ | 30 req/min (Nginx) | ⚠️ Insufficient | 🔴 CRITICAL |
| **POST /gpus/register** | ✅ | ❌ | 30 req/min (Nginx) | ✅ Adequate | 🟡 MEDIUM |
| **GET /gpus/** | ❌ | ✅ | 30 req/min (Nginx) | ✅ Adequate | 🟡 MEDIUM |
| **GET /gpus/available** | ❌ | ✅ | 30 req/min (Nginx) | ✅ Adequate | 🟡 MEDIUM |
| **PATCH /gpus/{id}/status** | ✅ | ❌ | 30 req/min (Nginx) | ✅ Adequate | 🟡 MEDIUM |
| **POST /jobs/submit** | ✅ | ❌ | 30 req/min (Nginx) | ⚠️ Insufficient | 🟡 MEDIUM |
| **GET /jobs/** | ✅ | ❌ | 30 req/min (Nginx) | ✅ Adequate | 🟢 LOW |
| **GET /jobs/{id}** | ✅ | ❌ | 30 req/min (Nginx) | ✅ Adequate | 🟢 LOW |
| **GET /jobs/{id}/logs** | ✅ | ❌ | 30 req/min (Nginx) | ✅ Adequate | 🟡 MEDIUM |
| **GET /jobs/{id}/download/{file}** | ❌ | ✅ | 30 req/min (Nginx) | ⚠️ Per IP only | 🔴 CRITICAL |
| **POST /jobs/{id}/cancel** | ✅ | ❌ | 30 req/min (Nginx) | ✅ Adequate | 🟡 MEDIUM |
| **DELETE /jobs/{id}** | ✅ | ❌ | 30 req/min (Nginx) | ✅ Adequate | 🟡 MEDIUM |
| **GET /wallet/** | ✅ | ❌ | 30 req/min (Nginx) | ✅ Adequate | 🟢 LOW |
| **POST /wallet/topup** | ✅ | ❌ | 30 req/min (Nginx) | ⚠️ No amount limit | 🔴 CRITICAL |
| **GET /wallet/transactions** | ✅ | ❌ | 30 req/min (Nginx) | ✅ Adequate | 🟢 LOW |
| **GET /admin/gpus** | ✅ | ❌ | 30 req/min (Nginx) | ✅ Adequate | 🟡 MEDIUM |
| **GET /admin/jobs** | ✅ | ❌ | 30 req/min (Nginx) | ✅ Adequate | 🟢 LOW |
| **GET /admin/users** | ✅ | ❌ | 30 req/min (Nginx) | ✅ Adequate | 🟡 MEDIUM |
| **GET /admin/stats** | ✅ | ❌ | 30 req/min (Nginx) | ✅ Adequate | 🟢 LOW |
| **WS /ws/agent/{gpu_id}** | ✅ | ❌ | ❌ NONE | 🔴 CRITICAL | 🔴 CRITICAL |
| **WS /ws/provider/{id}** | ✅ | ❌ | ❌ NONE | 🔴 CRITICAL | 🔴 CRITICAL |
| **GET /** | ❌ | ✅ | 30 req/min (Nginx) | ✅ Adequate | 🟢 LOW |
| **GET /docs** | ❌ | ✅ | 30 req/min (Nginx) | ⚠️ Should be disabled | 🔴 CRITICAL |
| **GET /openapi.json** | ❌ | ✅ | 30 req/min (Nginx) | ⚠️ Should be disabled | 🔴 CRITICAL |
| **GET /redoc** | ❌ | ✅ | 30 req/min (Nginx) | ⚠️ Should be disabled | 🔴 CRITICAL |

---

## Current Nginx Rate Limit Configuration

```nginx
# backend/nginx/nginx.conf:13
limit_req_zone $binary_remote_addr zone=api:10m rate=30r/m;

# Applied to REST endpoints
location ~ ^/(auth|gpus|jobs|wallet|admin)/ {
    limit_req zone=api burst=20 nodelay;
}
```

**Analysis:**
- ✅ **30 requests per minute** = 1 request every 2 seconds
- ✅ **Burst of 20** allows temporary spikes
- ✅ **Per IP address** (not per user/account)
- ❌ **WebSocket excluded** (no rate limiting)
- ❌ **Not per-user** (all users on same IP share quota)
- ❌ **Not endpoint-specific** (all endpoints treated equally)

---

## Recommended Rate Limiting Strategy

### Phase 1: CRITICAL (Implement Immediately)

1. **Install SlowAPI or fastapi-limiter2**
   ```bash
   pip install slowapi  # or fastapi-limiter2
   ```

2. **Add application-level rate limiting to auth endpoints**
   ```python
   from slowapi import Limiter
   from slowapi.util import get_remote_address

   limiter = Limiter(key_func=get_remote_address)
   
   @router.post("/register")
   @limiter.limit("5/minute")
   async def register(request: Request, ...):
       pass
   
   @router.post("/login")
   @limiter.limit("5/minute")
   async def login(request: Request, ...):
       pass
   ```

3. **Add WebSocket rate limiting**
   ```python
   # Track connections per GPU/provider
   # Limit messages per second
   # Implement connection timeout
   ```

4. **Require authentication for `/jobs/{id}/download`**
   - Replace UUID-based access with signed tokens
   - Or require user authentication

5. **Disable Swagger UI in production**
   ```python
   if not settings.DEBUG:
       app = FastAPI(openapi_url=None, docs_url=None, redoc_url=None)
   ```

### Phase 2: HIGH (Implement Within 1 Week)

1. **Per-user rate limiting**
   - Track by user ID (authenticated)
   - Track by IP + user-agent (unauthenticated)

2. **Progressive delays & account lockout**
   - After 3 failed login attempts: 15 minute lockout
   - Exponential backoff: 1s → 2s → 4s

3. **Wallet top-up limits**
   - Max ₹10,000 per transaction
   - Max ₹50,000 per 24 hours

4. **Job submission limits**
   - Max 10 jobs per hour per user
   - Max 100MB total upload per 24 hours

### Phase 3: MEDIUM (Implement Within 2 Weeks)

1. **Redis-backed distributed rate limiting**
   - For multi-instance deployments
   - Use Redis to track rate limit state

2. **Endpoint-specific rate limits**
   - Different limits for different endpoints
   - Tier-based limits (free vs paid users)

3. **DDoS mitigation**
   - Cloudflare or similar WAF
   - Geographic rate limiting
   - Challenge-response for suspicious IPs

---

## Impact Assessment

### Without Rate Limiting:
- 🔴 **Brute-force attacks:** 30 passwords/minute per IP
- 🔴 **Account enumeration:** Unlimited registration attempts
- 🔴 **Connection flooding:** 1000s of WebSocket connections
- 🔴 **File enumeration:** Brute-force job file UUIDs
- 🔴 **Financial abuse:** Unlimited wallet top-ups
- 🔴 **Resource exhaustion:** Disk filled with large uploads

### With Recommended Rate Limiting:
- ✅ **Brute-force reduced:** 5 attempts/minute per IP
- ✅ **Account enumeration prevented:** Max 5 registrations/min
- ✅ **Connection flooding prevented:** Max 1 GPU connection
- ✅ **File enumeration slowed:** 10 downloads/min per IP
- ✅ **Financial abuse prevented:** Max ₹10K/transaction
- ✅ **Resource exhaustion prevented:** Per-user upload quotas

---

## Compliance Standards

**OWASP Top 10 (2021):**
- A04:2021 – Insecure Deserialization → Rate limiting protects against abuse
- A05:2021 – Broken Access Control → Auth + rate limiting required

**CWE Top 25:**
- CWE-770: Allocation of Resources Without Limits or Throttling
- CWE-307: Improper Restriction of Rendered UI Layers or Frames
- CWE-400: Uncontrolled Resource Consumption

**NIST Cybersecurity Framework:**
- PR.AC-6: Access is managed through identities and permissions
- PR.PT-4: Communications and control networks are protected

---

## Conclusion

**Current Status:** ⚠️ **PARTIALLY PROTECTED**

- ✅ Nginx provides basic IP-level rate limiting (30 req/min)
- ❌ WebSocket endpoints completely unprotected
- ❌ No per-user rate limiting
- ❌ No account lockout mechanisms
- ❌ Auth endpoints lack strong rate limits
- ❌ Unauthenticated file downloads unprotected

**Recommendation:** Implement Phase 1 (CRITICAL) within **1 week** to close security gaps.

