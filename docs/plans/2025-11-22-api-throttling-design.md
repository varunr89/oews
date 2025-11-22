# API Throttling Design

**Date**: 2025-11-22
**Status**: Approved for Implementation
**Goal**: Protect hobby API from abuse and overload using lightweight, simple-to-implement throttling

## Overview

Two-layer protection addresses cost control, system stability, and fair usage without authentication infrastructure.

### Problem Statement

The current API lacks throttling:
- Any IP can make unlimited requests to expensive LLM workflows
- System overload (convoy effect) can occur unchecked
- Excessive LLM API costs risk from malicious or accidental abuse
- System lacks graceful degradation under heavy load

Each `/api/v1/query` request:
- Takes up to 5 minutes to complete
- Consumes multiple LLM API calls (planning, text2sql, synthesis, optional chart generation)
- Uses 1 of 8 available ThreadPoolExecutor workers

### Solution Architecture

**Two-Layer Protection:**

1. **Rate Limiting (Per-IP)** - Prevents individual IPs from making too many requests over time
2. **Backpressure (System-wide)** - Prevents system overload regardless of who's calling

**Design Principles:**
- Simple implementation (~20 lines of code)
- No external dependencies (Redis, database)
- In-memory state (acceptable for single-container hobby deployment)
- Works with existing Docker infrastructure
- Extensible to future authentication systems without refactoring

## Layer 1: Rate Limiting (Per-IP)

### Implementation

**Library**: `slowapi` - FastAPI-specific rate limiting middleware

**Limits**:
- `/api/v1/query`: 10 requests/hour per IP (conservative, protects against abuse)
- `/health`, `/api/v1/models`: 100 requests/hour per IP (cheap read-only endpoints)

**Storage**: In-memory (no Redis required)

**Code Changes** (`src/api/endpoints.py`):

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Create limiter instance
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[os.getenv("RATE_LIMIT_DEFAULT", "100/hour")],
    storage_uri="memory://"
)

# Register with FastAPI app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Apply to expensive endpoint
@app.post("/api/v1/query")
@limiter.limit(os.getenv("RATE_LIMIT_QUERY_ENDPOINT", "10/hour"))
async def query(request: QueryRequest) -> QueryResponse:
    ...
```

**Dependency** (add to `pyproject.toml`):
```toml
slowapi = "^0.1.9"
```

### Response Format

When a client exceeds the rate limit, it receives **429 Too Many Requests**:

```json
{
  "error": "Rate limit exceeded: 10 per 1 hour"
}
```

**Response Headers**:
- `X-RateLimit-Limit: 10` - Total allowed per window
- `X-RateLimit-Remaining: 0` - Requests left in current window
- `X-RateLimit-Reset: 1732334400` - Unix timestamp when limit resets
- `Retry-After: 3456` - Seconds until reset

### Limitations

**Multi-container deployments**: Each container instance tracks limits independently. If running N containers behind a load balancer, effective limit is 10N requests/hour per IP. This is acceptable for hobby use and actually provides additional capacity.

**Shared IPs**: Users behind NAT/corporate proxies share the same limit. This is a known limitation of IP-based rate limiting without authentication.

## Layer 2: Backpressure (System-wide)

### Implementation

**Mechanism**: asyncio.Semaphore limiting concurrent workflows

**Limit**: 8 concurrent requests (matches existing ThreadPoolExecutor `max_workers`)

**Code Changes** (`src/api/endpoints.py`):

```python
from asyncio import Semaphore

# Limit concurrent workflow executions
max_concurrent_requests = Semaphore(
    int(os.getenv("MAX_CONCURRENT_REQUESTS", "8"))
)

@app.post("/api/v1/query")
@limiter.limit(os.getenv("RATE_LIMIT_QUERY_ENDPOINT", "10/hour"))
async def query(request: QueryRequest) -> QueryResponse:
    # Check if system is overloaded
    if max_concurrent_requests.locked():
        raise HTTPException(
            status_code=503,
            detail="System at capacity. Please retry in 1-2 minutes.",
            headers={"Retry-After": "60"}
        )

    async with max_concurrent_requests:
        # ... existing workflow code (no changes)
        if workflow_graph is None:
            raise HTTPException(...)

        start_time = time.time()
        # ... rest of existing implementation
```

### Response Format

When the system is overloaded, clients receive **503 Service Unavailable**:

```json
{
  "detail": "System at capacity. Please retry in 1-2 minutes."
}
```

**Response Headers**:
- `Retry-After: 60` - Suggested retry delay in seconds

### Benefits

- Prevents convoy effect (cascading failures from queue buildup)
- Gives system time to recover under heavy load
- Fast-fail instead of queueing requests indefinitely
- No memory pressure from unbounded request queue

## Configuration

Configure all limits via environment variables:

**`.env` file**:
```bash
# Rate limiting
RATE_LIMIT_QUERY_ENDPOINT="10/hour"  # Conservative for hobby use
RATE_LIMIT_DEFAULT="100/hour"        # For health/models endpoints

# Backpressure
MAX_CONCURRENT_REQUESTS=8             # Matches ThreadPoolExecutor workers
```

**Benefit**: Adjust limits without code changes, different limits per environment (dev/prod).

## Frontend Integration

The GitHub Pages frontend should enhance user experience by:

1. **Display remaining quota**: Check `X-RateLimit-Remaining` header after each request
   - Show warning when remaining < 3: "You have N queries remaining this hour"

2. **Handle 429 gracefully**: Parse `Retry-After` header
   - Display: "Rate limit reached. Resets in X minutes"
   - Disable submit button until reset

3. **Handle 503 with retry logic**: Implement exponential backoff
   - Display: "System busy, retrying automatically..."
   - Auto-retry after 60s, then 120s, then give up

## Logging & Monitoring

Add structured logging for operational visibility:

```python
# On rate limit hit
api_logger.warning("rate_limit_exceeded", extra={
    "data": {"ip": client_ip}
})

# On backpressure rejection
api_logger.warning("system_overloaded", extra={
    "data": {"active_requests": 8}
})
```

**Operational queries**:
```bash
# Check rate limit patterns
docker logs oews-main | grep "rate_limit_exceeded" | tail -20

# Check system overload frequency
docker logs oews-main | grep "system_overloaded" | tail -20
```

## Testing Strategy

### Local Testing

**Test rate limiting**:
```bash
# Should succeed 10 times, then return 429
for i in {1..12}; do
  curl -X POST http://localhost:8000/api/v1/query \
    -H "Content-Type: application/json" \
    -d '{"query": "test query '$i'"}' \
    -w "\nStatus: %{http_code}\n"
done
```

**Test backpressure**:
```bash
# Fire 10 concurrent requests (should get 2 x 503 responses)
seq 1 10 | xargs -P10 -I{} curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "concurrent test {}"}' \
  -w "\nStatus: %{http_code}\n"
```

### Production Validation

After deployment:
1. Verify rate limit headers present in responses
2. Trigger 429 by exceeding limit from single IP
3. Verify 503 under concurrent load (10+ simultaneous requests)
4. Check logs for throttling events

## Deployment

**No infrastructure changes required**:
- Same Docker build process
- Same GitHub Actions workflow
- Same deployment steps to server

**Steps**:
1. Add `slowapi` dependency to `pyproject.toml`
2. Update `src/api/endpoints.py` with throttling code
3. Add environment variables to server's `.env` file
4. Build and deploy Docker container as usual
5. Test endpoints to verify throttling works

## Future Evolution Path

This design accommodates future authentication without refactoring:

### Phase 1: Current (IP-based)
- Unauthenticated requests: 10/hour per IP
- Simple, works immediately

### Phase 2: Optional API Keys (Future)
- Keep IP-based as fallback for unauthenticated
- Authenticated requests: Higher limits (e.g., 100/hour per key)
- Change only `key_func`:

```python
def get_rate_limit_key(request: Request):
    # Check for API key first
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return f"key:{api_key}"  # Rate limit per key
    # Fallback to IP
    return f"ip:{get_remote_address(request)}"

limiter = Limiter(key_func=get_rate_limit_key, ...)
```

### Phase 3: Per-Tier Limits (Future)
- Free tier: 100/hour
- Paid tier: 1000/hour
- Use dynamic limits:

```python
@limiter.limit(lambda: get_user_tier_limit(request))
@app.post("/api/v1/query")
async def query(...):
    ...
```

**No refactoring required** - the design extends naturally.

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| `slowapi` library bug/crash | Rate limiting disabled | Backpressure still protects system. Remove decorator and restart. |
| Multi-container deployments give higher effective limits | Users get 10N requests/hour | Acceptable for hobby use. Document behavior. |
| Shared IPs (NAT/corporate) hit limit quickly | Legitimate users blocked | Expected limitation without auth. Can add API keys later. |
| In-memory state lost on container restart | Rate limits reset | Acceptable. Users get fresh 10/hour window. |
| Strict limits frustrate power users | Reduced engagement | Monitor logs. Increase limits if abuse is rare. |

## Success Criteria

1. **Cost protection**: No single IP can trigger >10 expensive queries/hour
2. **System stability**: 503 errors prevent queue buildup under load
3. **Observability**: Rate limit and overload events logged
4. **User experience**: Clear error messages with retry guidance
5. **Simplicity**: Implementation < 25 lines of code, no external services

## Open Questions

None - design is approved for implementation.

## References

- `slowapi` documentation: https://github.com/laurentS/slowapi
- FastAPI rate limiting: https://fastapi.tiangolo.com/advanced/middleware/
- Current endpoint implementation: `src/api/endpoints.py:154-286`
