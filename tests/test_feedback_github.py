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
