# Feedback API Proxy - Design Document

**Date:** 2025-11-20
**Status:** Approved
**Target:** Python Backend (FastAPI)

## Overview

Implement a secure API endpoint that proxies feedback submissions from the frontend to GitHub's repository_dispatch API. The backend stores the GitHub token securely, eliminating the need to expose credentials in the frontend.

## Architecture Decisions

### Module Structure

Create a new `src/feedback/` module with clear separation of concerns:

```
src/feedback/
├── __init__.py          # Exports feedback_router
├── endpoints.py         # FastAPI router with routes and HTTP handling
├── github_client.py     # GitHub API integration and retry logic
├── models.py            # Pydantic request/response models
└── validation.py        # Pure validation functions
```

**Rationale:**
- Isolates feedback feature from core API endpoints
- Makes GitHub integration easy to mock for testing
- Keeps validation logic pure and testable
- Aligns with existing modular structure (agents/, tools/, etc.)

### Integration Point

The feedback router will be included in the main FastAPI app:

```python
# In src/api/endpoints.py
from src.feedback import feedback_router

app.include_router(feedback_router, prefix="/api/v1", tags=["feedback"])
```

This creates the endpoint: `POST /api/v1/feedback/submit`

## Component Design

### 1. Data Models (models.py)

```python
from pydantic import BaseModel
from typing import Optional

class FeedbackRequest(BaseModel):
    category: str
    text: str
    email: Optional[str] = ""
    honeypot: str
    timestamp: int
    id: str

class FeedbackResponse(BaseModel):
    success: bool
    message: str

class FeedbackErrorResponse(BaseModel):
    error: str
```

### 2. Validation Layer (validation.py)

**Validation order** (fail-fast):

1. Required fields check
2. Honeypot check (return fake success if triggered)
3. Text length (10-2000 chars after trim)
4. Email format (if provided)
5. Category (must be: bug, feature, improvement, documentation, question)
6. ID format (alphanumeric, dashes, underscores only)
7. Timestamp (not negative, not >60s in future)

**Implementation approach:**

Pure functions that raise custom exceptions:

```python
class ValidationError(Exception):
    """Raised when validation fails"""
    pass

class HoneypotTriggered(Exception):
    """Bot detected via honeypot field"""
    pass

def validate_required_fields(data: dict) -> None:
    required = ['category', 'text', 'honeypot', 'timestamp', 'id']
    for field in required:
        if field not in data:
            raise ValidationError(f"Missing required field: {field}")

def validate_text_length(text: str) -> str:
    trimmed = text.strip()
    if len(trimmed) < 10:
        raise ValidationError("Text must be at least 10 characters")
    if len(trimmed) > 2000:
        raise ValidationError("Text must not exceed 2000 characters")
    return trimmed

def validate_email(email: Optional[str]) -> str:
    if not email or email.strip() == "":
        return ""

    EMAIL_REGEX = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
    if not re.match(EMAIL_REGEX, email.strip()):
        raise ValidationError("Invalid email format")
    return email.strip()

# ... additional validation functions
```

**Honeypot handling:**

When honeypot is filled (bot detected):
- Return `200 OK` with success message (fake success)
- Log warning with ID and timestamp
- Do NOT call GitHub API
- Do NOT process submission

### 3. GitHub Client (github_client.py)

**Configuration:**
- `GITHUB_TOKEN` - From environment variable (required)
- `GITHUB_OWNER` - Hardcoded as "varunr"
- `GITHUB_REPO` - Hardcoded as "oews-data-explorer"

**Implementation:**

```python
import httpx
import asyncio
import os

class GitHubAPIError(Exception):
    """Raised when GitHub API call fails"""
    pass

class GitHubClient:
    def __init__(self):
        self.token = os.getenv("GITHUB_TOKEN")
        self.owner = "varunr"
        self.repo = "oews-data-explorer"

        if not self.token:
            raise ValueError("GITHUB_TOKEN environment variable not set")

    async def trigger_dispatch(self, payload: dict) -> None:
        """
        Trigger repository_dispatch event.
        Retries once on 5xx errors.
        Raises GitHubAPIError on failure.
        """
        url = f"https://api.github.com/repos/{self.owner}/{self.repo}/dispatches"

        headers = {
            'Accept': 'application/vnd.github.v3+json',
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json',
            'User-Agent': 'OEWS-Feedback-Backend'
        }

        body = {
            'event_type': 'submit_feedback',
            'client_payload': payload
        }

        async with httpx.AsyncClient() as client:
            # First attempt
            response = await client.post(url, json=body, headers=headers, timeout=10)

            if response.status_code == 204:
                return  # Success

            # Retry once on 5xx
            if 500 <= response.status_code < 600:
                await asyncio.sleep(2)
                response = await client.post(url, json=body, headers=headers, timeout=10)
                if response.status_code == 204:
                    return

            # Failed - log and raise
            raise GitHubAPIError(f"GitHub API returned {response.status_code}")
```

**Why async?**
- FastAPI app is already async
- Using `httpx` keeps everything non-blocking
- Better performance under concurrent requests

**Why singleton?**
Create one `GitHubClient` instance at app startup (in lifespan context) to validate token exists early rather than on first request.

### 4. API Endpoints (endpoints.py)

**Routes:**
- `POST /api/v1/feedback/submit` - Submit feedback
- `OPTIONS /api/v1/feedback/submit` - CORS preflight

**Flow:**

```python
from fastapi import APIRouter, HTTPException, Request, Response
from src.utils.logger import setup_workflow_logger

router = APIRouter()
feedback_logger = setup_workflow_logger("oews.feedback")

@router.post("/feedback/submit", response_model=FeedbackResponse)
async def submit_feedback(request: FeedbackRequest):
    try:
        # Run all validations
        validate_required_fields(request.dict())

        # Check honeypot (return fake success if triggered)
        if request.honeypot.strip() != "":
            feedback_logger.warning(f"Honeypot triggered: id={request.id}")
            return FeedbackResponse(
                success=True,
                message="Feedback submitted successfully"
            )

        # Validate remaining fields
        validated_text = validate_text_length(request.text)
        validated_email = validate_email(request.email)
        validate_category(request.category)
        validate_id_format(request.id)
        validate_timestamp(request.timestamp)

        # Prepare payload for GitHub
        payload = {
            'category': request.category,
            'text': validated_text,
            'email': validated_email,
            'honeypot': request.honeypot,
            'timestamp': request.timestamp,
            'id': request.id
        }

        # Call GitHub API
        await github_client.trigger_dispatch(payload)

        # Log success
        feedback_logger.info(
            f"Feedback submitted: id={request.id}, category={request.category}"
        )

        return FeedbackResponse(
            success=True,
            message="Feedback submitted successfully"
        )

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except GitHubAPIError as e:
        feedback_logger.error(
            f"GitHub API error: id={request.id}, error={str(e)}"
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to submit feedback to GitHub"
        )

    except Exception as e:
        feedback_logger.error(
            f"Unexpected error: id={request.id}, error={str(e)}"
        )
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred"
        )

@router.options("/feedback/submit")
async def feedback_preflight(request: Request):
    """Handle CORS preflight"""
    origin = request.headers.get("origin")

    # Reuse existing CORS allowed origins check
    if not is_allowed_origin(origin):
        raise HTTPException(status_code=403, detail="Origin not allowed")

    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Max-Age": "86400"
        }
    )
```

## Error Handling

**Exception mapping:**

| Exception | HTTP Status | Response | Action |
|-----------|-------------|----------|--------|
| `ValidationError` | 400 | Specific error message | Return to client |
| `HoneypotTriggered` | 200 | Fake success message | Log warning, don't process |
| `GitHubAPIError` | 500 | Generic error message | Log full error server-side |
| Other exceptions | 500 | Generic error message | Log full error server-side |

**Logging policy:**
- ✅ Log: ID, category, timestamp, error types
- ❌ Don't log: Full feedback text, email addresses, GitHub token

## CORS Configuration

**Strategy:** Leverage existing CORS middleware in `src/api/endpoints.py`

Your app already supports:
- `https://varunr.github.io` (production frontend)
- `http://localhost:5173` (Vite dev server)
- `http://localhost:4173` (Vite preview)

The feedback endpoint will work with existing CORS config. We only need to add an explicit OPTIONS handler for the preflight request.

## Dependencies

**New dependency required:**

Add to `pyproject.toml`:
```toml
dependencies = [
    # ... existing dependencies ...
    "httpx>=0.24.0",  # Async HTTP client for GitHub API
]
```

## Testing Strategy

**Essential test coverage (8 tests):**

```python
# tests/test_feedback.py

1. test_missing_required_field()
   - Verify 400 when category/text/id/timestamp/honeypot missing

2. test_honeypot_detection()
   - Verify 200 fake success when honeypot filled
   - Verify GitHub API NOT called (mock and assert)

3. test_text_too_short()
   - Verify 400 when text < 10 characters

4. test_text_too_long()
   - Verify 400 when text > 2000 characters

5. test_invalid_email()
   - Test malformed emails: "notanemail", "@example.com", "user@"
   - Verify 400 returned

6. test_invalid_category()
   - Verify 400 for category not in allowed list

7. test_successful_submission()
   - Mock GitHub API to return 204
   - Verify 200 response
   - Verify GitHub API called with correct payload

8. test_github_api_failure()
   - Mock GitHub API to return 500
   - Verify retry logic (2 attempts)
   - Verify 500 returned to client

9. test_cors_preflight()
   - Send OPTIONS request with valid origin
   - Verify correct CORS headers returned
```

**Testing tools:**
- `pytest` (already in project)
- `pytest-asyncio` for async tests
- `httpx` MockTransport for mocking GitHub API
- FastAPI TestClient for endpoint tests

## Deployment Plan

### 1. Branch Setup

Create feature branch:
```bash
git checkout -b feedback-api-proxy
```

### 2. Implementation

Implement files in order:
1. `src/feedback/models.py` - Data models
2. `src/feedback/validation.py` - Validation functions + tests
3. `src/feedback/github_client.py` - GitHub integration + tests
4. `src/feedback/endpoints.py` - API routes + tests
5. `src/feedback/__init__.py` - Export router
6. Update `src/api/endpoints.py` - Include feedback router

### 3. Local Testing

```bash
# Install dependencies
pip install -e .

# Set environment variable
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx

# Run tests
pytest tests/test_feedback.py -v

# Start server
uvicorn src.api.endpoints:app --reload --port 8000

# Test with curl
curl -X POST http://localhost:8000/api/v1/feedback/submit \
  -H "Content-Type: application/json" \
  -d '{
    "category": "bug",
    "text": "Test feedback submission",
    "email": "",
    "honeypot": "",
    "timestamp": 1700000000000,
    "id": "local-test-1"
  }'
```

### 4. Container Build

GitHub Actions will automatically build and push container when branch is pushed:

```bash
git push origin feedback-api-proxy
```

Container will be tagged as: `ghcr.io/varunr89/oews:feedback-api-proxy`

### 5. Server Deployment

SSH to server and deploy preview container:

```bash
ssh varun@100.107.15.52

# Pull latest image
docker pull ghcr.io/varunr89/oews:feedback-api-proxy

# Stop old container if exists
docker stop oews-feedback 2>/dev/null || true
docker rm oews-feedback 2>/dev/null || true

# Start new container
docker run -d \
  --name oews-feedback \
  -p 8003:8000 \
  -v /home/varun/projects/oews/data:/app/data:ro \
  --env-file /home/varun/projects/oews/.env \
  ghcr.io/varunr89/oews:feedback-api-proxy

# Connect to Caddy network
docker network connect oews_default oews-feedback

# Verify
docker ps | grep oews-feedback
docker logs oews-feedback --tail 20
```

### 6. Environment Configuration

Add to `/home/varun/projects/oews/.env` on server:

```bash
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
```

**Token requirements:**
- Personal Access Token (classic) or Fine-grained token
- Scope: `repo` (full repository access)
- Permission: Trigger `repository_dispatch` events

**How to create:**
1. GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Generate new token → Select `repo` scope → Generate
3. Copy token and add to `.env` file

### 7. Caddy Configuration

Update Caddy config to route feedback API:

```caddyfile
api.oews.bhavanaai.com {
    # Existing routes...

    # Feedback API preview
    handle /feedback-api-proxy/* {
        reverse_proxy oews-feedback:8000
    }
}
```

Reload Caddy:
```bash
docker exec caddy caddy reload --config /etc/caddy/Caddyfile
```

### 8. Testing

```bash
# Test health endpoint
curl https://api.oews.bhavanaai.com/feedback-api-proxy/health

# Test feedback submission
curl -X POST https://api.oews.bhavanaai.com/feedback-api-proxy/api/v1/feedback/submit \
  -H "Content-Type: application/json" \
  -H "Origin: https://varunr.github.io" \
  -d '{
    "category": "bug",
    "text": "Test feedback from preview deployment",
    "email": "test@example.com",
    "honeypot": "",
    "timestamp": '$(date +%s000)',
    "id": "preview-test-'$(date +%s)'"
  }'

# Verify GitHub issue created
# Check: https://github.com/varunr89/oews-data-explorer/issues
```

### 9. Frontend Integration

Update frontend to use preview API:
```javascript
const BACKEND_URL = 'https://api.oews.bhavanaai.com/feedback-api-proxy'
```

### 10. End-to-End Test

1. Open frontend in browser
2. Click feedback button
3. Fill form with valid data
4. Submit
5. Verify success toast appears
6. Check GitHub repo for new issue
7. Check server logs: `docker logs oews-feedback --tail 50`

## Security Considerations

1. **Token Security**
   - Store in environment variables only
   - Never log the token
   - Never expose in error messages
   - Rotate if compromised

2. **Input Validation**
   - All validation happens before GitHub API call
   - Trim whitespace from all string fields
   - Never trust client input

3. **Bot Protection**
   - Honeypot field catches automated submissions
   - Return fake success (don't reveal detection)

4. **CORS**
   - Only allow specific origins
   - No wildcard (`*`) usage
   - Verify origin on every request

5. **Rate Limiting**
   - Not implemented (frontend has client-side limiting)
   - Can add later if abuse detected in logs
   - Monitor honeypot detections for bot activity

6. **Error Messages**
   - Specific messages only for validation errors
   - Generic messages for server/GitHub errors
   - Never expose internal details to client

7. **PII Protection**
   - Don't log full feedback text
   - Don't log email addresses
   - Only log IDs and metadata

## Future Enhancements

**Not included in initial implementation:**

1. **Rate limiting** - Add if abuse detected
2. **Comprehensive test coverage** - Expand beyond 8 essential tests
3. **Request ID tracing** - Correlate frontend to backend logs
4. **Metrics** - Track submission rates, failure rates
5. **Admin dashboard** - View feedback stats
6. **Duplicate detection** - Check for repeated submissions

These can be added in follow-up iterations based on actual usage patterns.

## Success Criteria

The implementation is complete when:

- ✅ All 8 essential tests pass
- ✅ Local curl test succeeds
- ✅ Preview container deployed and accessible
- ✅ Frontend can submit feedback successfully
- ✅ GitHub issues are created automatically
- ✅ Honeypot detection works (logs show bot attempts)
- ✅ CORS works for production frontend URL
- ✅ Error handling returns appropriate status codes

## Questions & Assumptions

**Assumptions:**
- Frontend already has rate limiting (10 submissions per hour)
- GitHub repo has workflow to handle `repository_dispatch` events
- Caddy reverse proxy is already configured and running
- Docker network `oews_default` exists and Caddy is connected

**Open questions:**
- Should we implement request deduplication (check if same ID already submitted)?
- Should we add a health check that verifies GitHub token validity?
- Should we implement webhook verification if GitHub calls back?

These can be addressed during implementation if needed.
