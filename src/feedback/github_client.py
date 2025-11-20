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
