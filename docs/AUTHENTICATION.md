# Authentication and Authorization

## Current Status

**⚠️ WARNING: The API currently has NO authentication or authorization.**

This is acceptable for:
- Local development
- Private networks with trusted clients
- MVP/prototype deployments

This is **NOT acceptable** for:
- Public internet deployment
- Production systems with untrusted access
- Multi-tenant environments

## Recommended Solutions

### Option 1: API Key Authentication (Simple)

**When to use:** Single-tenant, trusted clients, internal tools

**Implementation:**
1. Generate API keys for each client
2. Store keys securely (hashed in database)
3. Require `X-API-Key` header on all requests
4. Validate key in middleware before processing

**Example:**
```python
# src/api/auth.py
from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key")

def validate_api_key(api_key: str = Security(api_key_header)):
    if api_key not in get_valid_api_keys():
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key
```

**Pros:**
- Simple to implement
- No external dependencies
- Good for internal APIs

**Cons:**
- No user-specific tracking
- Keys can be shared
- No expiration by default

---

### Option 2: OAuth 2.0 / JWT (Production)

**When to use:** Multi-tenant, user-specific access, production systems

**Implementation:**
1. Integrate with OAuth provider (Auth0, Okta, Azure AD)
2. Require Bearer token in Authorization header
3. Validate JWT signature and claims
4. Extract user identity for audit logging

**Example:**
```python
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id
```

**Pros:**
- Industry standard
- Supports multiple providers
- User-specific tracking
- Token expiration

**Cons:**
- More complex implementation
- Requires external provider or JWT infrastructure
- Token validation overhead

---

### Option 3: Reverse Proxy Authentication

**When to use:** Enterprise deployment with existing auth infrastructure

**Implementation:**
1. Deploy behind nginx, Caddy, or API Gateway
2. Proxy handles authentication
3. Proxy forwards validated requests with user headers
4. API trusts headers from proxy (validate proxy identity)

**Example Caddy configuration:**
```caddy
api.example.com {
    reverse_proxy localhost:8000 {
        header_up X-Forwarded-User {http.auth.user.id}
    }

    basicauth /* {
        user $2a$14$hashed_password
    }
}
```

**Pros:**
- Offload auth to dedicated layer
- Works with any auth backend
- Minimal code changes
- Good for enterprises with existing infrastructure

**Cons:**
- Requires proxy infrastructure
- More complex deployment
- Trust proxy identity

---

## Rate Limiting

**Current Status:** No rate limiting implemented

**Recommended:**
- Use `slowapi` package for per-IP rate limiting
- Configure limits based on authentication tier
- Example: 100 requests/hour for free tier, 1000/hour for paid

**Implementation:**
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/api/v1/query")
@limiter.limit("10/minute")
async def query(request: QueryRequest):
    # ... existing code ...
```

**Per-user rate limiting (with API key):**
```python
def get_key_func(request):
    api_key = request.headers.get("X-API-Key", "anonymous")
    return f"{request.client.host}:{api_key}"

limiter = Limiter(key_func=get_key_func)
```

---

## Cost Control

With LLM API costs, authentication is critical for:
- Tracking usage per user/client
- Billing and quota enforcement
- Preventing abuse and DoS
- Audit trails

**Recommendation:** Implement authentication before public deployment.

---

## HTTPS/TLS

**Current Status:** No TLS configuration in application code

**Recommendation:**
- Deploy behind reverse proxy with HTTPS
- Use modern TLS 1.2+ only
- Redirect HTTP to HTTPS

**Example Caddy configuration:**
```caddy
api.example.com {
    # Automatic HTTPS with Let's Encrypt
    reverse_proxy localhost:8000
}
```

---

## Usage Tracking

**Minimal implementation (with API keys):**
```python
import json
from datetime import datetime

# In your query endpoint
api_key = request.headers.get("X-API-Key")
log_usage({
    "timestamp": datetime.utcnow().isoformat(),
    "api_key": api_key,
    "query": request.query[:100],  # Don't log full queries
    "models": request.reasoning_model or "default",
    "success": response.status_code == 200,
    "execution_time_ms": execution_time
})
```

---

## Next Steps for Implementation

### Immediate (for production):
1. **Implement Option 1 (API key)** as minimum viable auth
2. **Add rate limiting** with `slowapi`
3. **Deploy behind HTTPS** reverse proxy
4. **Set up usage tracking**

### Short term (for scaling):
1. **Migrate to Option 2 (OAuth/JWT)** for user-specific access
2. **Add usage tracking and quota enforcement**
3. **Implement audit logging**
4. **Set up alerts for unusual usage patterns**

### Long term (for enterprise):
1. **Option 3 (reverse proxy auth)** integration
2. **SSO support**
3. **Role-based access control (RBAC)**
4. **Advanced analytics and billing**

---

## References

- [FastAPI Security Documentation](https://fastapi.tiangolo.com/tutorial/security/)
- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [slowapi - Rate Limiting for FastAPI](https://github.com/laurents/slowapi)
- [Python-JOSE JWT Documentation](https://python-jose.readthedocs.io/)

---

**Status:** DOCUMENTED (not implemented) - User decision to defer implementation

**Production Impact:** This limitation prevents 8.5/10 production readiness rating

**Current Target:** 7.5/10 (acceptable for private/trusted deployments)
