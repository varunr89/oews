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
    """Test that missing required field returns 422 (Pydantic validation)."""
    payload = valid_payload()
    del payload['category']

    response = client.post("/feedback/submit", json=payload)

    # Pydantic returns 422 for validation errors at model level
    assert response.status_code == 422
    # Check that the error mentions the missing field
    response_text = str(response.json()).lower()
    assert 'category' in response_text


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
        assert 'failed' in response.json()['detail'].lower() or 'error' in response.json()['detail'].lower()
