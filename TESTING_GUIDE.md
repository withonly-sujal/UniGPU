# 🧪 UniGPU Security Hardening - Testing Guide

## Overview
This document outlines all security features implemented and how to test them. All changes have been simplified and deployed without Alembic migrations.

---

## 📋 Summary of Changes

### Removed
- ❌ Alembic migrations (complex, unnecessary)
- ❌ Tier-based subscriptions (user requested removal)

### Added
- ✅ SlowAPI rate limiting (application level)
- ✅ Redis distributed rate limiting (multi-instance support)
- ✅ Exponential backoff with progressive delays
- ✅ Account lockout after 3 failed attempts
- ✅ WebSocket rate limiting
- ✅ Wallet transaction limits
- ✅ Upload bandwidth limits
- ✅ GPU registration limits
- ✅ Pessimistic database locking for GPU booking
- ✅ Auto-created database tables on startup

---

## 🧪 Test Categories

### 1. Authentication & Account Lockout (CRITICAL)
**Purpose:** Prevent brute-force attacks with progressive delays and lockout

| Test | Expected Result | Command |
|------|-----------------|---------|
| Register new user | ✅ 201 Created | `POST /auth/register` |
| Login correct password | ✅ 200 OK + JWT token | `POST /auth/login` |
| Login wrong password 1x | ✅ 200 OK with 1s delay | `POST /auth/login` (wrong pass) |
| Login wrong password 2x | ✅ 200 OK with 2s delay | `POST /auth/login` (wrong pass) |
| Login wrong password 3x | ✅ 200 OK with 4s delay | `POST /auth/login` (wrong pass) |
| Login wrong password 4x | ✅ 200 OK with 8s delay | `POST /auth/login` (wrong pass) |
| Login while locked | ❌ 429 Account locked | `POST /auth/login` within lockout |
| Login after 15min lockout | ✅ 200 OK | `POST /auth/login` after 900s |
| Successful login resets counter | ✅ Counter cleared | Next failed attempt gets 1s delay |

**Delays Sequence:** 1.0s → 2.0s → 4.0s → 8.0s → 16.0s (exponential)  
**Lockout Duration:** 15 minutes (900 seconds)  
**Max Failed Attempts:** 3

---

### 2. Rate Limiting - Authentication Endpoints (CRITICAL)
**Purpose:** Prevent brute-force via high request volume

| Test | Limit | Expected Result |
|------|-------|-----------------|
| Register requests/minute | 5 per user per min | 6th request: 429 Too Many Requests |
| Login requests/minute | 5 per user per min | 6th request: 429 Too Many Requests |
| Wait 1 minute | Resets | Can make 5 new requests |

---

### 3. Rate Limiting - Job Submission (HIGH)
**Purpose:** Prevent resource exhaustion

| Test | Limit | Expected Result |
|------|-------|-----------------|
| Submit jobs/hour | 10 per user per hour | 11th job: 429 Too Many Requests |
| Different user | Per-user limit | User B can still submit 10 jobs |
| Wait 1 hour | Resets | Can submit 10 new jobs |

---

### 4. Rate Limiting - File Uploads (HIGH)
**Purpose:** Prevent bandwidth exhaustion

| Test | Limit | Expected Result |
|------|-------|-----------------|
| Upload bandwidth/day | 100 MB per user per day | Upload >100MB: 429 Too Many Requests |
| Different user | Per-user limit | User B can upload 100MB |
| Wait 24 hours | Resets | Can upload 100MB again |

---

### 5. Rate Limiting - GPU Registration (HIGH)
**Purpose:** Prevent spam GPU registrations

| Test | Limit | Expected Result |
|------|-------|-----------------|
| Register GPUs/hour | 10 per provider per hour | 11th GPU: 429 Too Many Requests |
| Different provider | Per-user limit | Provider B can register 10 GPUs |
| Wait 1 hour | Resets | Can register 10 new GPUs |

---

### 6. Wallet Security (HIGH)
**Purpose:** Prevent unauthorized large transactions

| Test | Limit | Expected Result |
|------|-------|-----------------|
| Single transaction | ₹10,000 max | ₹10,001: Error "Exceeds limit" |
| Daily total | ₹50,000 max/24h | Exceed daily: Error "Daily limit exceeded" |
| Topup requests/hour | 5 per user per hour | 6th request: 429 Too Many Requests |
| Next day after 24h | Daily resets | Can add more transactions |

---

### 7. WebSocket Rate Limiting (CRITICAL)
**Purpose:** Prevent message flooding and connection abuse

| Test | Limit | Expected Result |
|------|-------|-----------------|
| Messages/minute | 100 per connection | 101st message: Connection throttled |
| Active connections per GPU | 1 max | 2nd connection attempt: Rejected |
| Active connections per provider | 5 max | 6th connection attempt: Rejected |

---

### 8. GPU Locking - Race Condition Prevention (CRITICAL)
**Purpose:** Prevent double-booking of same GPU

| Test | Expected Result |
|------|-----------------|
| Submit 2 concurrent jobs for GPU A | First locks GPU, second gets alternative or queued |
| First job completes within 30s | Lock released, GPU available |
| Lock expires after 30s | Background cleanup removes stale locks |
| Cleanup runs every 60s | Expired locks cleaned up automatically |
| Single GPU = single job | No two jobs can run on same GPU simultaneously |

---

### 9. File Download Security (CRITICAL)
**Purpose:** Prevent unauthorized file access

| Test | Expected Result | Status Code |
|------|-----------------|------------|
| Download without JWT token | Unauthorized | 401 |
| Download with valid JWT (owner) | Success, file served | 200 |
| Download with valid JWT (non-owner) | Forbidden | 403 |
| Download with invalid UUID | Not found | 404 |

---

### 10. Database Auto-Initialization (MEDIUM)
**Purpose:** Ensure tables created automatically without migrations

| Test | Expected Result |
|------|-----------------|
| Start backend | All tables auto-created from models |
| Restart backend | Tables already exist, no errors |
| Check tables exist | users, gpus, jobs, wallets, transactions all present |
| Check columns | locked_by_job_id, locked_until columns in gpus table |

---

### 11. Redis Integration (MEDIUM)
**Purpose:** Ensure distributed rate limiting across multiple instances

| Test | Expected Result |
|------|-----------------|
| Make request (hits rate limit) | Rate limit stored in Redis |
| Restart backend container | Rate limit still enforced (from Redis) |
| Multiple backend instances | Share same Redis rate limits |
| Check Redis keys | Keys like `rate_limit:user-123`, `login_attempts:user@test.com` |

---

### 12. System Health (MEDIUM)
**Purpose:** Ensure all components working correctly

| Test | Expected Result |
|------|-----------------|
| GET /docs | Swagger UI loads (DEBUG=true) |
| GET /openapi.json | API schema returns |
| GET any endpoint | No 500 Internal Server errors |
| Celery worker log | GPU heartbeat checks succeed |
| Backend logs | No import errors or warnings |
| PostgreSQL | Connected, tables accessible |
| Redis | Connected, keys stored/retrieved |

---

## 🚀 Quick Test Commands

### Test 1: Account Lockout (Progressive Delays)
```bash
# Request 1: 1 second delay
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"wrongpass"}' -w "\n%{time_total}s\n"

# Request 2: 2 second delay
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"wrongpass"}' -w "\n%{time_total}s\n"

# Request 3: 4 second delay
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"wrongpass"}' -w "\n%{time_total}s\n"

# Request 4: Locked for 15 minutes
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"wrongpass"}'
# Expected: {"detail": "Account temporarily locked"}
```

### Test 2: Auth Rate Limiting (5 req/min)
```bash
for i in {1..6}; do
  echo "Request $i:"
  curl -X POST http://localhost:8000/auth/register \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"user$i@test.com\",\"username\":\"user$i\",\"password\":\"Test123!\"}" \
    -w "Status: %{http_code}\n"
  sleep 1
done
# Expected: 6th request returns 429 Too Many Requests
```

### Test 3: Wallet Transaction Limit (₹10,000 max)
```bash
# Get JWT token first
TOKEN=$(curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"Test123!"}' \
  | jq -r '.access_token')

# Try transaction over limit
curl -X POST http://localhost:8000/wallet/topup \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"amount": 10001}'
# Expected: {"detail": "Transaction exceeds ₹10,000 limit"}
```

### Test 4: GPU Locking (Concurrent Submissions)
```bash
# Submit 2 jobs simultaneously for same GPU
curl -X POST http://localhost:8000/jobs/submit \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"gpu_id":"gpu-123","script_path":"train.py"}' &

curl -X POST http://localhost:8000/jobs/submit \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"gpu_id":"gpu-123","script_path":"train.py"}' &

wait
# Expected: One succeeds, one gets alternative or queued
```

### Test 5: Check Redis Rate Limit Keys
```bash
docker exec unigpu-redis redis-cli KEYS "rate_limit:*"
docker exec unigpu-redis redis-cli KEYS "login_attempts:*"

# Example output:
# 1) "rate_limit:user-abc123:jobs"
# 2) "login_attempts:user@test.com:127.0.0.1"
```

### Test 6: Check Database Tables
```bash
docker exec unigpu-postgres psql -U unigpu -d unigpu -c "\dt"

# Expected tables:
# users, wallets, gpus, jobs, transactions

# Check GPU locking columns:
docker exec unigpu-postgres psql -U unigpu -d unigpu \
  -c "SELECT column_name FROM information_schema.columns WHERE table_name='gpus' AND column_name IN ('locked_by_job_id', 'locked_until');"
```

---

## ✅ Test Checklist

### Critical Features (Must Pass)
- [ ] Account lockout with exponential backoff works
- [ ] GPU locking prevents double-booking
- [ ] WebSocket rate limiting enforced
- [ ] File download requires authentication
- [ ] Auth endpoints rate limited (5 req/min)

### High Priority Features (Should Pass)
- [ ] Job submission limited to 10/hour per user
- [ ] Wallet transaction limited to ₹10,000
- [ ] Wallet daily limit ₹50,000/24h
- [ ] Upload bandwidth limited to 100MB/day
- [ ] GPU registration limited to 10/hour

### Medium Priority Features (Nice to Have)
- [ ] Database tables auto-created on startup
- [ ] Redis persists rate limits across restarts
- [ ] Celery worker processes heartbeats successfully
- [ ] Swagger UI loads with DEBUG=true

---

## 📊 Success Criteria

**All tests pass when:**
1. ✅ Account lockout delays increase exponentially
2. ✅ Rate limits are enforced per-user (not global)
3. ✅ GPU locking prevents concurrent access
4. ✅ WebSocket connections properly throttled
5. ✅ Wallet prevents unauthorized transactions
6. ✅ Database initializes automatically
7. ✅ No migration files needed
8. ✅ Redis backing distributed rate limiting
9. ✅ No security warnings in logs

---

## 🔧 Troubleshooting

### Issue: Rate limit not enforcing
**Solution:** Check Redis connection
```bash
docker exec unigpu-backend ping redis:6379
docker exec unigpu-redis redis-cli PING
```

### Issue: GPU locking not working
**Solution:** Check background cleanup task
```bash
docker logs unigpu-backend | grep "GPU lock cleanup"
```

### Issue: Account lockout not working
**Solution:** Verify security_utils.py has proper imports
```bash
docker logs unigpu-backend | grep "NameError\|defaultdict"
```

### Issue: Database tables missing
**Solution:** Check startup logs
```bash
docker logs unigpu-backend | grep "Database tables initialized"
```

---

## 📝 Notes

- All rate limits are **per-user**, not global
- All timeouts use **UTC timezone** (timezone-aware)
- Redis keys expire automatically
- GPU locks auto-cleanup every 60 seconds
- Account lockout is per `username + IP address` combination
- No external migration tool needed

---

**Last Updated:** May 7, 2026  
**Status:** Ready for Testing 🚀
