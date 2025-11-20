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
