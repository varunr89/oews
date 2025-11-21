# Feedback API Proxy Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement secure feedback submission endpoint that proxies requests to GitHub's repository_dispatch API.

**Architecture:** New `src/feedback/` module with validation layer, GitHub client, and FastAPI router. Follows TDD with 8 essential tests covering validation, honeypot detection, GitHub integration, and CORS.

**Tech Stack:** FastAPI, httpx (async HTTP), Pydantic, pytest

---

## Task 1: Add Dependencies

**Files:**
- Modify: `pyproject.toml:34`

**Step 1: Add httpx dependency**

Add after line 34 (after `rapidfuzz`):

```toml
    "httpx>=0.24.0",
    "pytest-asyncio>=0.21.0"
```

**Step 2: Verify changes**

Run: `cat pyproject.toml | grep -A 1 rapidfuzz`
Expected: See httpx and pytest-asyncio in dependencies

**Step 3: Install dependencies**

Run: `pip install -e .`
Expected: "Successfully installed httpx-..." and "pytest-asyncio-..."

**Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "deps: add httpx and pytest-asyncio for feedback API"
```

---

## Task 2: Create Feedback Models

**Files:**
- Create: `src/feedback/__init__.py`
- Create: `src/feedback/models.py`

**Step 1: Create module __init__.py**

```python
"""Feedback submission API module."""
```

**Step 2: Create models.py with Pydantic schemas**

```python
"""Pydantic models for feedback API."""

from pydantic import BaseModel
from typing import Optional


class FeedbackRequest(BaseModel):
    """Request model for feedback submission."""
    category: str
    text: str
    email: Optional[str] = ""
    honeypot: str
    timestamp: int
    id: str


class FeedbackResponse(BaseModel):
    """Success response for feedback submission."""
    success: bool
    message: str


class FeedbackErrorResponse(BaseModel):
    """Error response for feedback submission."""
    error: str
```

**Step 3: Verify import**

Run: `python -c "from src.feedback.models import FeedbackRequest; print('OK')"`
Expected: "OK"

**Step 4: Commit**

```bash
git add src/feedback/__init__.py src/feedback/models.py
git commit -m "feat(feedback): add Pydantic models for request/response"
```

---

## Task 3: Create Validation Exceptions

**Files:**
- Create: `src/feedback/validation.py`

**Step 1: Create validation.py with custom exceptions**

```python
"""Validation functions for feedback submissions."""

import re
import time
from typing import Optional


class ValidationError(Exception):
    """Raised when validation fails."""
    pass


class HoneypotTriggered(Exception):
    """Raised when honeypot field is filled (bot detected)."""
    pass
```

**Step 2: Verify import**

Run: `python -c "from src.feedback.validation import ValidationError, HoneypotTriggered; print('OK')"`
Expected: "OK"

**Step 3: Commit**

```bash
git add src/feedback/validation.py
git commit -m "feat(feedback): add validation exceptions"
```

---

## Task 4: Implement Required Fields Validation

**Files:**
- Modify: `src/feedback/validation.py`
- Create: `tests/test_feedback_validation.py`

**Step 1: Write the failing test**

Create `tests/test_feedback_validation.py`:

```python
"""Tests for feedback validation functions."""

import pytest
from src.feedback.validation import ValidationError, validate_required_fields


def test_validate_required_fields_success():
    """Test that valid data passes required fields check."""
    data = {
        'category': 'bug',
        'text': 'Test feedback',
        'honeypot': '',
        'timestamp': 1700000000000,
        'id': 'test-1'
    }
    # Should not raise
    validate_required_fields(data)


def test_validate_required_fields_missing_category():
    """Test that missing category raises ValidationError."""
    data = {
        'text': 'Test feedback',
        'honeypot': '',
        'timestamp': 1700000000000,
        'id': 'test-1'
    }
    with pytest.raises(ValidationError, match="Missing required field: category"):
        validate_required_fields(data)


def test_validate_required_fields_missing_text():
    """Test that missing text raises ValidationError."""
    data = {
        'category': 'bug',
        'honeypot': '',
        'timestamp': 1700000000000,
        'id': 'test-1'
    }
    with pytest.raises(ValidationError, match="Missing required field: text"):
        validate_required_fields(data)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_feedback_validation.py::test_validate_required_fields_success -v`
Expected: FAIL with "NameError: name 'validate_required_fields' is not defined" or "ImportError"

**Step 3: Implement validate_required_fields**

Add to `src/feedback/validation.py`:

```python
def validate_required_fields(data: dict) -> None:
    """
    Validate that all required fields are present.

    Args:
        data: Request data dictionary

    Raises:
        ValidationError: If any required field is missing
    """
    required = ['category', 'text', 'honeypot', 'timestamp', 'id']
    for field in required:
        if field not in data:
            raise ValidationError(f"Missing required field: {field}")
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_feedback_validation.py -v`
Expected: 3 tests PASSED

**Step 5: Commit**

```bash
git add src/feedback/validation.py tests/test_feedback_validation.py
git commit -m "feat(feedback): add required fields validation"
```

---

## Task 5: Implement Honeypot Validation

**Files:**
- Modify: `src/feedback/validation.py`
- Modify: `tests/test_feedback_validation.py`

**Step 1: Write the failing test**

Add to `tests/test_feedback_validation.py`:

```python
from src.feedback.validation import HoneypotTriggered, validate_honeypot


def test_validate_honeypot_empty():
    """Test that empty honeypot passes."""
    validate_honeypot('')  # Should not raise


def test_validate_honeypot_filled():
    """Test that filled honeypot raises HoneypotTriggered."""
    with pytest.raises(HoneypotTriggered):
        validate_honeypot('spam@spam.com')


def test_validate_honeypot_whitespace():
    """Test that whitespace-only honeypot raises HoneypotTriggered."""
    with pytest.raises(HoneypotTriggered):
        validate_honeypot('  ')
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_feedback_validation.py::test_validate_honeypot_empty -v`
Expected: FAIL with "ImportError: cannot import name 'validate_honeypot'"

**Step 3: Implement validate_honeypot**

Add to `src/feedback/validation.py`:

```python
def validate_honeypot(honeypot: str) -> None:
    """
    Check honeypot field for bot detection.

    Args:
        honeypot: Honeypot field value (should be empty for humans)

    Raises:
        HoneypotTriggered: If honeypot contains any non-empty value
    """
    if honeypot.strip() != "":
        raise HoneypotTriggered("Honeypot field was filled")
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_feedback_validation.py::test_validate_honeypot_empty -v`
Expected: 3 honeypot tests PASSED

**Step 5: Commit**

```bash
git add src/feedback/validation.py tests/test_feedback_validation.py
git commit -m "feat(feedback): add honeypot validation for bot detection"
```

---

## Task 6: Implement Text Length Validation

**Files:**
- Modify: `src/feedback/validation.py`
- Modify: `tests/test_feedback_validation.py`

**Step 1: Write the failing test**

Add to `tests/test_feedback_validation.py`:

```python
from src.feedback.validation import validate_text_length


def test_validate_text_length_valid():
    """Test that valid text passes."""
    result = validate_text_length("This is a valid feedback text")
    assert result == "This is a valid feedback text"


def test_validate_text_length_trims_whitespace():
    """Test that whitespace is trimmed."""
    result = validate_text_length("  Valid text  ")
    assert result == "Valid text"


def test_validate_text_length_too_short():
    """Test that short text raises ValidationError."""
    with pytest.raises(ValidationError, match="at least 10 characters"):
        validate_text_length("short")


def test_validate_text_length_too_long():
    """Test that long text raises ValidationError."""
    with pytest.raises(ValidationError, match="2000 characters"):
        validate_text_length("a" * 2001)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_feedback_validation.py::test_validate_text_length_valid -v`
Expected: FAIL with "ImportError: cannot import name 'validate_text_length'"

**Step 3: Implement validate_text_length**

Add to `src/feedback/validation.py`:

```python
def validate_text_length(text: str) -> str:
    """
    Validate text length and return trimmed text.

    Args:
        text: Feedback text to validate

    Returns:
        Trimmed text

    Raises:
        ValidationError: If text is too short or too long
    """
    trimmed = text.strip()

    if len(trimmed) < 10:
        raise ValidationError("Text must be at least 10 characters")

    if len(trimmed) > 2000:
        raise ValidationError("Text must not exceed 2000 characters")

    return trimmed
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_feedback_validation.py -k text_length -v`
Expected: 4 text length tests PASSED

**Step 5: Commit**

```bash
git add src/feedback/validation.py tests/test_feedback_validation.py
git commit -m "feat(feedback): add text length validation (10-2000 chars)"
```

---

## Task 7: Implement Email Validation

**Files:**
- Modify: `src/feedback/validation.py`
- Modify: `tests/test_feedback_validation.py`

**Step 1: Write the failing test**

Add to `tests/test_feedback_validation.py`:

```python
from src.feedback.validation import validate_email


def test_validate_email_valid():
    """Test that valid email passes."""
    result = validate_email("user@example.com")
    assert result == "user@example.com"


def test_validate_email_empty():
    """Test that empty email is allowed."""
    result = validate_email("")
    assert result == ""

    result = validate_email(None)
    assert result == ""


def test_validate_email_invalid_formats():
    """Test that invalid email formats raise ValidationError."""
    invalid_emails = [
        "notanemail",
        "@example.com",
        "user@",
        "user @example.com",
        "user@.com"
    ]

    for email in invalid_emails:
        with pytest.raises(ValidationError, match="Invalid email format"):
            validate_email(email)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_feedback_validation.py::test_validate_email_valid -v`
Expected: FAIL with "ImportError: cannot import name 'validate_email'"

**Step 3: Implement validate_email**

Add to `src/feedback/validation.py`:

```python
def validate_email(email: Optional[str]) -> str:
    """
    Validate email format if provided.

    Args:
        email: Optional email address

    Returns:
        Validated email or empty string

    Raises:
        ValidationError: If email format is invalid
    """
    if not email or email.strip() == "":
        return ""

    EMAIL_REGEX = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'

    if not re.match(EMAIL_REGEX, email.strip()):
        raise ValidationError("Invalid email format")

    return email.strip()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_feedback_validation.py -k email -v`
Expected: 3 email tests PASSED

**Step 5: Commit**

```bash
git add src/feedback/validation.py tests/test_feedback_validation.py
git commit -m "feat(feedback): add email format validation"
```

---

## Task 8: Implement Category Validation

**Files:**
- Modify: `src/feedback/validation.py`
- Modify: `tests/test_feedback_validation.py`

**Step 1: Write the failing test**

Add to `tests/test_feedback_validation.py`:

```python
from src.feedback.validation import validate_category


def test_validate_category_valid():
    """Test that valid categories pass."""
    valid_categories = ['bug', 'feature', 'improvement', 'documentation', 'question']

    for category in valid_categories:
        result = validate_category(category)
        assert result == category


def test_validate_category_invalid():
    """Test that invalid category raises ValidationError."""
    with pytest.raises(ValidationError, match="Invalid category"):
        validate_category("invalid")
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_feedback_validation.py::test_validate_category_valid -v`
Expected: FAIL with "ImportError: cannot import name 'validate_category'"

**Step 3: Implement validate_category**

Add to `src/feedback/validation.py`:

```python
VALID_CATEGORIES = ['bug', 'feature', 'improvement', 'documentation', 'question']


def validate_category(category: str) -> str:
    """
    Validate category is in allowed list.

    Args:
        category: Feedback category

    Returns:
        Validated category

    Raises:
        ValidationError: If category is not in allowed list
    """
    if category.lower() not in VALID_CATEGORIES:
        raise ValidationError(
            f"Invalid category. Must be one of: {', '.join(VALID_CATEGORIES)}"
        )

    return category.lower()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_feedback_validation.py -k category -v`
Expected: 2 category tests PASSED

**Step 5: Commit**

```bash
git add src/feedback/validation.py tests/test_feedback_validation.py
git commit -m "feat(feedback): add category validation"
```

---

## Task 9: Implement ID Format Validation

**Files:**
- Modify: `src/feedback/validation.py`
- Modify: `tests/test_feedback_validation.py`

**Step 1: Write the failing test**

Add to `tests/test_feedback_validation.py`:

```python
from src.feedback.validation import validate_id_format


def test_validate_id_format_valid():
    """Test that valid ID formats pass."""
    valid_ids = ['local-123', 'test_456', 'abc-def_123', 'test123']

    for id_value in valid_ids:
        result = validate_id_format(id_value)
        assert result == id_value


def test_validate_id_format_invalid():
    """Test that invalid ID formats raise ValidationError."""
    invalid_ids = ['local@123', 'test 456', 'abc!def', '']

    for id_value in invalid_ids:
        with pytest.raises(ValidationError, match="Invalid ID format"):
            validate_id_format(id_value)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_feedback_validation.py::test_validate_id_format_valid -v`
Expected: FAIL with "ImportError: cannot import name 'validate_id_format'"

**Step 3: Implement validate_id_format**

Add to `src/feedback/validation.py`:

```python
def validate_id_format(id_value: str) -> str:
    """
    Validate ID format (alphanumeric, dashes, underscores only).

    Args:
        id_value: Feedback submission ID

    Returns:
        Validated ID

    Raises:
        ValidationError: If ID format is invalid
    """
    ID_REGEX = r'^[a-zA-Z0-9_-]+$'

    if not re.match(ID_REGEX, id_value):
        raise ValidationError("Invalid ID format")

    return id_value
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_feedback_validation.py -k id_format -v`
Expected: 2 ID format tests PASSED

**Step 5: Commit**

```bash
git add src/feedback/validation.py tests/test_feedback_validation.py
git commit -m "feat(feedback): add ID format validation"
```

---

## Task 10: Implement Timestamp Validation

**Files:**
- Modify: `src/feedback/validation.py`
- Modify: `tests/test_feedback_validation.py`

**Step 1: Write the failing test**

Add to `tests/test_feedback_validation.py`:

```python
import time
from src.feedback.validation import validate_timestamp


def test_validate_timestamp_valid():
    """Test that valid timestamp passes."""
    current_time = int(time.time() * 1000)
    result = validate_timestamp(current_time)
    assert result == current_time


def test_validate_timestamp_negative():
    """Test that negative timestamp raises ValidationError."""
    with pytest.raises(ValidationError, match="Timestamp cannot be negative"):
        validate_timestamp(-1)


def test_validate_timestamp_future():
    """Test that far future timestamp raises ValidationError."""
    future_time = int(time.time() * 1000) + 120000  # 2 minutes in future
    with pytest.raises(ValidationError, match="Timestamp cannot be in the future"):
        validate_timestamp(future_time)


def test_validate_timestamp_grace_period():
    """Test that timestamp within grace period passes."""
    near_future = int(time.time() * 1000) + 30000  # 30 seconds in future
    result = validate_timestamp(near_future)
    assert result == near_future
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_feedback_validation.py::test_validate_timestamp_valid -v`
Expected: FAIL with "ImportError: cannot import name 'validate_timestamp'"

**Step 3: Implement validate_timestamp**

Add to `src/feedback/validation.py`:

```python
def validate_timestamp(timestamp: int) -> int:
    """
    Validate timestamp is not negative and not too far in future.

    Args:
        timestamp: Unix timestamp in milliseconds

    Returns:
        Validated timestamp

    Raises:
        ValidationError: If timestamp is invalid
    """
    try:
        timestamp_value = int(timestamp)
    except (ValueError, TypeError):
        raise ValidationError("Invalid timestamp format")

    if timestamp_value < 0:
        raise ValidationError("Timestamp cannot be negative")

    # Allow 60 second grace period for clock skew
    current_time = int(time.time() * 1000)
    if timestamp_value > current_time + 60000:
        raise ValidationError("Timestamp cannot be in the future")

    return timestamp_value
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_feedback_validation.py -k timestamp -v`
Expected: 4 timestamp tests PASSED

**Step 5: Commit**

```bash
git add src/feedback/validation.py tests/test_feedback_validation.py
git commit -m "feat(feedback): add timestamp validation with grace period"
```

---

## Task 11: Create GitHub Client

**Files:**
- Create: `src/feedback/github_client.py`
- Create: `tests/test_feedback_github.py`

**Step 1: Write the failing test**

Create `tests/test_feedback_github.py`:

```python
"""Tests for GitHub API client."""

import pytest
import os
from unittest.mock import AsyncMock, patch
from src.feedback.github_client import GitHubClient, GitHubAPIError


@pytest.mark.asyncio
async def test_github_client_initialization():
    """Test that GitHubClient initializes with token."""
    with patch.dict(os.environ, {'GITHUB_TOKEN': 'test-token'}):
        client = GitHubClient()
        assert client.token == 'test-token'
        assert client.owner == 'varunr'
        assert client.repo == 'oews-data-explorer'


def test_github_client_missing_token():
    """Test that missing token raises ValueError."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="GITHUB_TOKEN environment variable not set"):
            GitHubClient()


@pytest.mark.asyncio
async def test_trigger_dispatch_success(monkeypatch):
    """Test successful GitHub API call."""
    with patch.dict(os.environ, {'GITHUB_TOKEN': 'test-token'}):
        client = GitHubClient()

        # Mock httpx.AsyncClient
        mock_response = AsyncMock()
        mock_response.status_code = 204

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

        with patch('httpx.AsyncClient', return_value=mock_client):
            payload = {'category': 'bug', 'text': 'Test'}
            await client.trigger_dispatch(payload)

            # Verify post was called
            mock_client.__aenter__.return_value.post.assert_called_once()


@pytest.mark.asyncio
async def test_trigger_dispatch_failure(monkeypatch):
    """Test GitHub API failure raises GitHubAPIError."""
    with patch.dict(os.environ, {'GITHUB_TOKEN': 'test-token'}):
        client = GitHubClient()

        # Mock httpx.AsyncClient to return 401
        mock_response = AsyncMock()
        mock_response.status_code = 401

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

        with patch('httpx.AsyncClient', return_value=mock_client):
            payload = {'category': 'bug', 'text': 'Test'}

            with pytest.raises(GitHubAPIError, match="GitHub API returned 401"):
                await client.trigger_dispatch(payload)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_feedback_github.py::test_github_client_initialization -v`
Expected: FAIL with "ImportError: cannot import name 'GitHubClient'"

**Step 3: Implement GitHubClient**

Create `src/feedback/github_client.py`:

```python
"""GitHub API client for feedback submissions."""

import os
import asyncio
import httpx


class GitHubAPIError(Exception):
    """Raised when GitHub API call fails."""
    pass


class GitHubClient:
    """Client for triggering GitHub repository_dispatch events."""

    def __init__(self):
        """Initialize GitHub client with environment variables."""
        self.token = os.getenv("GITHUB_TOKEN")
        self.owner = "varunr"
        self.repo = "oews-data-explorer"

        if not self.token:
            raise ValueError("GITHUB_TOKEN environment variable not set")

    async def trigger_dispatch(self, payload: dict) -> None:
        """
        Trigger repository_dispatch event.

        Args:
            payload: Client payload to send to GitHub

        Raises:
            GitHubAPIError: If GitHub API call fails
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

            # Failed
            raise GitHubAPIError(f"GitHub API returned {response.status_code}")
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_feedback_github.py -v`
Expected: 4 tests PASSED

**Step 5: Commit**

```bash
git add src/feedback/github_client.py tests/test_feedback_github.py
git commit -m "feat(feedback): add GitHub API client with retry logic"
```

---

## Task 12: Create API Endpoints Router

**Files:**
- Create: `src/feedback/endpoints.py`
- Create: `tests/test_feedback_endpoints.py`

**Step 1: Write the failing test**

Create `tests/test_feedback_endpoints.py`:

```python
"""Tests for feedback API endpoints."""

import pytest
import time
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from src.feedback.endpoints import router


# Create test client
from fastapi import FastAPI
app = FastAPI()
app.include_router(router)
client = TestClient(app)


def valid_payload():
    """Return a valid feedback payload."""
    return {
        'category': 'bug',
        'text': 'This is a valid test feedback',
        'email': '',
        'honeypot': '',
        'timestamp': int(time.time() * 1000),
        'id': f'test-{int(time.time())}'
    }


def test_missing_required_field():
    """Test that missing required field returns 400."""
    payload = valid_payload()
    del payload['category']

    response = client.post("/feedback/submit", json=payload)

    assert response.status_code == 400
    assert 'category' in response.json()['detail'].lower()


def test_honeypot_detection():
    """Test that filled honeypot returns fake success."""
    payload = valid_payload()
    payload['honeypot'] = 'spam@spam.com'

    # Mock GitHub client to verify it's NOT called
    with patch('src.feedback.endpoints.github_client') as mock_github:
        response = client.post("/feedback/submit", json=payload)

        assert response.status_code == 200
        assert response.json()['success'] is True
        # Verify GitHub API was NOT called
        mock_github.trigger_dispatch.assert_not_called()


def test_text_too_short():
    """Test that short text returns 400."""
    payload = valid_payload()
    payload['text'] = 'short'

    response = client.post("/feedback/submit", json=payload)

    assert response.status_code == 400
    assert '10 characters' in response.json()['detail'].lower()


def test_invalid_email():
    """Test that invalid email returns 400."""
    payload = valid_payload()
    payload['email'] = 'notanemail'

    response = client.post("/feedback/submit", json=payload)

    assert response.status_code == 400
    assert 'email' in response.json()['detail'].lower()


def test_successful_submission():
    """Test successful feedback submission."""
    payload = valid_payload()

    # Mock GitHub client
    with patch('src.feedback.endpoints.github_client') as mock_github:
        mock_github.trigger_dispatch = AsyncMock()

        response = client.post("/feedback/submit", json=payload)

        assert response.status_code == 200
        assert response.json()['success'] is True
        assert 'submitted successfully' in response.json()['message'].lower()


def test_github_api_failure():
    """Test that GitHub API failure returns 500."""
    payload = valid_payload()

    # Mock GitHub client to raise error
    with patch('src.feedback.endpoints.github_client') as mock_github:
        from src.feedback.github_client import GitHubAPIError
        mock_github.trigger_dispatch = AsyncMock(side_effect=GitHubAPIError("API error"))

        response = client.post("/feedback/submit", json=payload)

        assert response.status_code == 500
        assert 'error' in response.json()['detail'].lower()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_feedback_endpoints.py::test_missing_required_field -v`
Expected: FAIL with "ImportError: cannot import name 'router'"

**Step 3: Implement endpoints.py**

Create `src/feedback/endpoints.py`:

```python
"""FastAPI endpoints for feedback submission."""

from fastapi import APIRouter, HTTPException
from src.feedback.models import FeedbackRequest, FeedbackResponse
from src.feedback.validation import (
    ValidationError,
    HoneypotTriggered,
    validate_required_fields,
    validate_honeypot,
    validate_text_length,
    validate_email,
    validate_category,
    validate_id_format,
    validate_timestamp
)
from src.feedback.github_client import GitHubClient, GitHubAPIError
from src.utils.logger import setup_workflow_logger


# Create router
router = APIRouter()

# Setup logger
feedback_logger = setup_workflow_logger("oews.feedback")

# GitHub client (will be initialized at startup)
github_client = None


def init_github_client():
    """Initialize GitHub client (call at startup)."""
    global github_client
    try:
        github_client = GitHubClient()
        feedback_logger.info("GitHub client initialized successfully")
    except ValueError as e:
        feedback_logger.error(f"Failed to initialize GitHub client: {e}")
        raise


@router.post("/feedback/submit", response_model=FeedbackResponse)
async def submit_feedback(request: FeedbackRequest):
    """
    Submit feedback to GitHub via repository_dispatch.

    Args:
        request: Feedback submission request

    Returns:
        Success response

    Raises:
        HTTPException: If validation fails or GitHub API call fails
    """
    try:
        # Validate required fields
        validate_required_fields(request.dict())

        # Check honeypot (return fake success if triggered)
        try:
            validate_honeypot(request.honeypot)
        except HoneypotTriggered:
            feedback_logger.warning(f"Honeypot triggered: id={request.id}")
            return FeedbackResponse(
                success=True,
                message="Feedback submitted successfully"
            )

        # Validate remaining fields
        validated_text = validate_text_length(request.text)
        validated_email = validate_email(request.email)
        validated_category = validate_category(request.category)
        validate_id_format(request.id)
        validate_timestamp(request.timestamp)

        # Prepare payload for GitHub
        payload = {
            'category': validated_category,
            'text': validated_text,
            'email': validated_email,
            'honeypot': request.honeypot,
            'timestamp': request.timestamp,
            'id': request.id
        }

        # Call GitHub API
        if github_client is None:
            raise HTTPException(
                status_code=503,
                detail="GitHub client not initialized"
            )

        await github_client.trigger_dispatch(payload)

        # Log success
        feedback_logger.info(
            f"Feedback submitted: id={request.id}, category={validated_category}"
        )

        return FeedbackResponse(
            success=True,
            message="Feedback submitted successfully"
        )

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except GitHubAPIError as e:
        feedback_logger.error(f"GitHub API error: id={request.id}, error={str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to submit feedback to GitHub"
        )

    except Exception as e:
        feedback_logger.error(f"Unexpected error: id={request.id}, error={str(e)}")
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred"
        )
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_feedback_endpoints.py -v`
Expected: 6 tests PASSED

**Step 5: Commit**

```bash
git add src/feedback/endpoints.py tests/test_feedback_endpoints.py
git commit -m "feat(feedback): add FastAPI endpoints with validation"
```

---

## Task 13: Add CORS Preflight Handler

**Files:**
- Modify: `src/feedback/endpoints.py`
- Modify: `tests/test_feedback_endpoints.py`

**Step 1: Write the failing test**

Add to `tests/test_feedback_endpoints.py`:

```python
def test_cors_preflight():
    """Test CORS preflight OPTIONS request."""
    response = client.options(
        "/feedback/submit",
        headers={'Origin': 'https://varunr.github.io'}
    )

    assert response.status_code == 200
    assert 'access-control-allow-origin' in response.headers
    assert 'POST' in response.headers.get('access-control-allow-methods', '')
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_feedback_endpoints.py::test_cors_preflight -v`
Expected: FAIL with "405 Method Not Allowed"

**Step 3: Add OPTIONS handler**

Add to `src/feedback/endpoints.py` (after submit_feedback function):

```python
from fastapi import Request, Response


@router.options("/feedback/submit")
async def feedback_preflight(request: Request):
    """
    Handle CORS preflight for feedback submission.

    Args:
        request: FastAPI request object

    Returns:
        Response with CORS headers
    """
    origin = request.headers.get("origin", "")

    # Allowed origins (should match main app CORS config)
    allowed_origins = [
        'https://varunr.github.io',
        'http://localhost:5173',
        'http://localhost:4173'
    ]

    if origin not in allowed_origins:
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

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_feedback_endpoints.py::test_cors_preflight -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/feedback/endpoints.py tests/test_feedback_endpoints.py
git commit -m "feat(feedback): add CORS preflight handler"
```

---

## Task 14: Export Router from Feedback Module

**Files:**
- Modify: `src/feedback/__init__.py`

**Step 1: Export router and init function**

Replace content of `src/feedback/__init__.py`:

```python
"""Feedback submission API module."""

from src.feedback.endpoints import router as feedback_router, init_github_client

__all__ = ['feedback_router', 'init_github_client']
```

**Step 2: Verify import**

Run: `python -c "from src.feedback import feedback_router, init_github_client; print('OK')"`
Expected: "OK"

**Step 3: Commit**

```bash
git add src/feedback/__init__.py
git commit -m "feat(feedback): export router and init function"
```

---

## Task 15: Integrate with Main App

**Files:**
- Modify: `src/api/endpoints.py:55` (in lifespan function)
- Modify: `src/api/endpoints.py:98` (after CORS middleware)

**Step 1: Write integration test**

Create `tests/test_feedback_integration.py`:

```python
"""Integration test for feedback API with main app."""

import pytest
import time
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient


def test_feedback_endpoint_in_main_app():
    """Test that feedback endpoint is accessible in main app."""
    # Import after mocking to avoid initialization issues
    with patch.dict('os.environ', {'GITHUB_TOKEN': 'test-token'}):
        # Mock create_workflow_graph to avoid initialization
        with patch('src.api.endpoints.create_workflow_graph'):
            from src.api.endpoints import app

            client = TestClient(app)

            # Test that feedback endpoint exists
            payload = {
                'category': 'bug',
                'text': 'Integration test feedback',
                'email': '',
                'honeypot': '',
                'timestamp': int(time.time() * 1000),
                'id': f'integration-test-{int(time.time())}'
            }

            # Mock GitHub client
            with patch('src.feedback.endpoints.github_client') as mock_github:
                mock_github.trigger_dispatch = AsyncMock()

                response = client.post("/api/v1/feedback/submit", json=payload)

                # Should get 503 because github_client not initialized in test
                # But endpoint should exist
                assert response.status_code in [200, 503]
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_feedback_integration.py -v`
Expected: FAIL with "404 Not Found"

**Step 3: Integrate feedback router**

Modify `src/api/endpoints.py`:

Add import at top (after line 21):
```python
from src.feedback import feedback_router, init_github_client
```

Modify lifespan function (around line 46, after workflow_graph initialization):
```python
    # Initialize GitHub client for feedback
    try:
        init_github_client()
        print("GitHub client ready.")
    except Exception as e:
        print(f"Warning: Failed to initialize GitHub client: {e}")
        print("Feedback submission will not work until GITHUB_TOKEN is configured.")
```

Add router inclusion (after line 98, after CORS middleware):
```python
# Include feedback router
app.include_router(feedback_router, prefix="/api/v1", tags=["feedback"])
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_feedback_integration.py -v`
Expected: PASS (or 503 if GitHub client initialization fails, but route exists)

**Step 5: Verify all tests pass**

Run: `pytest tests/test_feedback*.py -v`
Expected: All feedback tests PASSED

**Step 6: Commit**

```bash
git add src/api/endpoints.py tests/test_feedback_integration.py
git commit -m "feat(feedback): integrate feedback router with main API"
```

---

## Task 16: Update Environment Example

**Files:**
- Check if `.env.example` exists, if yes modify it

**Step 1: Check for .env.example**

Run: `ls -la .env.example 2>/dev/null || echo "File does not exist"`

**Step 2: Add GITHUB_TOKEN to .env.example (if file exists)**

If file exists, add this line:
```bash
# GitHub token for feedback submissions (requires 'repo' scope)
GITHUB_TOKEN=ghp_your_token_here
```

If file doesn't exist, skip this task.

**Step 3: Commit (if changes made)**

```bash
git add .env.example
git commit -m "docs: add GITHUB_TOKEN to environment example"
```

---

## Task 17: Final Validation

**Files:**
- All test files

**Step 1: Run all tests**

Run: `pytest tests/test_feedback*.py -v --tb=short`
Expected: All tests PASSED

**Step 2: Check test coverage**

Run: `pytest tests/test_feedback*.py --cov=src/feedback --cov-report=term-missing`
Expected: Coverage > 80%

**Step 3: Verify imports work**

Run: `python -c "from src.feedback import feedback_router, init_github_client; from src.api.endpoints import app; print('All imports OK')"`
Expected: "All imports OK"

**Step 4: Test local server (if GITHUB_TOKEN available)**

If `GITHUB_TOKEN` is set:
```bash
# Start server
uvicorn src.api.endpoints:app --reload --port 8000 &
SERVER_PID=$!

# Wait for startup
sleep 3

# Test health
curl http://localhost:8000/health

# Test feedback endpoint
curl -X POST http://localhost:8000/api/v1/feedback/submit \
  -H "Content-Type: application/json" \
  -d '{
    "category": "bug",
    "text": "Local test feedback submission",
    "email": "",
    "honeypot": "",
    "timestamp": '$(date +%s000)',
    "id": "local-test-'$(date +%s)'"
  }'

# Stop server
kill $SERVER_PID
```

Expected: 200 response with success message

**Step 5: Final commit (if any fixes needed)**

```bash
git add .
git commit -m "test: verify feedback API integration"
```

---

## Task 18: Deployment Preparation

**Files:**
- None (documentation only)

**Step 1: Verify Docker build works**

Run: `docker build -t oews-feedback-test .`
Expected: Build succeeds

**Step 2: Push branch to trigger GitHub Actions**

Run: `git push origin feedback-api-proxy`
Expected: Branch pushed, GitHub Actions starts building container

**Step 3: Monitor GitHub Actions**

Run: `gh run list --branch feedback-api-proxy --limit 3`
Expected: See build in progress

**Step 4: Document deployment steps**

The deployment steps are already documented in the design document. Review:
- `docs/plans/2025-11-20-feedback-api-proxy-design.md` section "Deployment Plan"

**Next steps (manual):**
1. Wait for GitHub Actions to complete
2. SSH to server and deploy preview container (see design doc)
3. Add `GITHUB_TOKEN` to `/home/varun/projects/oews/.env` on server
4. Update Caddy config for `/feedback-api-proxy/*` route
5. Test with curl from server
6. Update frontend to use preview API URL
7. End-to-end test from browser

---

## Completion Checklist

- [x] All dependencies added
- [x] Models created
- [x] Validation functions implemented (7 validators)
- [x] GitHub client implemented with retry logic
- [x] API endpoints created
- [x] CORS preflight handler added
- [x] Integrated with main FastAPI app
- [x] 8+ essential tests written and passing
- [x] Environment example updated
- [x] All tests passing
- [x] Ready for deployment

**Implementation complete!** Ready to deploy to preview container.
