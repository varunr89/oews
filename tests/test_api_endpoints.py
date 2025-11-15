"""Integration tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
from src.api.endpoints import app


@pytest.fixture
def client():
    """Create test client for FastAPI app."""
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_endpoint_returns_200(self, client):
        """Test health check endpoint returns 200."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_endpoint_response_structure(self, client):
        """Test health check has required fields."""
        response = client.get("/health")
        data = response.json()

        assert "status" in data
        assert "workflow_loaded" in data
        assert data["status"] == "healthy"
        assert isinstance(data["workflow_loaded"], bool)


class TestModelsEndpoint:
    """Tests for /api/v1/models endpoint."""

    def test_models_endpoint_returns_200(self, client):
        """Test models endpoint returns 200."""
        response = client.get("/api/v1/models")
        assert response.status_code == 200

    def test_models_endpoint_response_structure(self, client):
        """Test models endpoint has correct structure."""
        response = client.get("/api/v1/models")
        data = response.json()

        # Should have defaults and models
        assert "defaults" in data
        assert "models" in data

        # Defaults should have reasoning and implementation
        assert "reasoning" in data["defaults"]
        assert "implementation" in data["defaults"]

    def test_models_endpoint_has_model_info(self, client):
        """Test each model has required fields."""
        response = client.get("/api/v1/models")
        data = response.json()

        # If there are models, they should have required fields
        for model_key, model_info in data.get("models", {}).items():
            assert "provider" in model_info
            assert "model_name" in model_info
            assert "role" in model_info


class TestQueryEndpointValidation:
    """Tests for query endpoint input validation."""

    def test_query_endpoint_requires_query_field(self, client):
        """Test that query field is required."""
        response = client.post("/api/v1/query", json={})
        assert response.status_code == 422

    def test_query_endpoint_enforces_min_length(self, client):
        """Test that query must be at least 3 characters."""
        response = client.post("/api/v1/query", json={"query": "ab"})
        assert response.status_code == 422

    def test_query_endpoint_enforces_max_length(self, client):
        """Test that query cannot exceed 500 characters."""
        response = client.post("/api/v1/query", json={"query": "a" * 501})
        assert response.status_code == 422

    def test_query_endpoint_accepts_valid_query(self, client):
        """Test that valid query passes validation."""
        with patch('src.api.endpoints.workflow_graph') as mock_graph:
            mock_graph.invoke.return_value = {
                "formatted_response": {
                    "answer": "Test answer",
                    "charts": [],
                    "data_sources": []
                },
                "model_usage": {},
                "plan": {},
                "replans": 0
            }

            response = client.post(
                "/api/v1/query",
                json={"query": "What is the median salary for engineers?"}
            )
            assert response.status_code == 200


class TestQueryEndpointModelOverrides:
    """Tests for model override functionality."""

    def test_query_endpoint_accepts_reasoning_model_override(self, client):
        """Test that reasoning_model override is accepted."""
        with patch('src.api.endpoints.workflow_graph') as mock_graph:
            mock_graph.invoke.return_value = {
                "formatted_response": {
                    "answer": "Test answer",
                    "charts": [],
                    "data_sources": []
                },
                "model_usage": {"planner": "deepseek-reasoner"},
                "plan": {},
                "replans": 0
            }

            response = client.post(
                "/api/v1/query",
                json={
                    "query": "Test query",
                    "reasoning_model": "deepseek-reasoner"
                }
            )
            assert response.status_code == 200

    def test_query_endpoint_accepts_implementation_model_override(self, client):
        """Test that implementation_model override is accepted."""
        with patch('src.api.endpoints.workflow_graph') as mock_graph:
            mock_graph.invoke.return_value = {
                "formatted_response": {
                    "answer": "Test answer",
                    "charts": [],
                    "data_sources": []
                },
                "model_usage": {"cortex_researcher": "gpt-4o-mini"},
                "plan": {},
                "replans": 0
            }

            response = client.post(
                "/api/v1/query",
                json={
                    "query": "Test query",
                    "implementation_model": "gpt-4o-mini"
                }
            )
            assert response.status_code == 200

    def test_query_endpoint_passes_model_overrides_to_workflow(self, client):
        """Test that model overrides are passed to workflow state."""
        with patch('src.api.endpoints.workflow_graph') as mock_graph:
            mock_graph.invoke.return_value = {
                "formatted_response": {
                    "answer": "Test answer",
                    "charts": [],
                    "data_sources": []
                },
                "model_usage": {
                    "planner": "gpt-4o",
                    "cortex_researcher": "gpt-4o-mini"
                },
                "plan": {},
                "replans": 0
            }

            response = client.post(
                "/api/v1/query",
                json={
                    "query": "Test query",
                    "reasoning_model": "gpt-4o",
                    "implementation_model": "gpt-4o-mini"
                }
            )

            assert response.status_code == 200

            # Verify workflow was called with correct state
            call_args = mock_graph.invoke.call_args
            state = call_args[0][0]  # First positional arg

            assert state["reasoning_model"] == "gpt-4o"
            assert state["implementation_model"] == "gpt-4o-mini"


class TestQueryEndpointErrorHandling:
    """Tests for error handling."""

    def test_query_endpoint_returns_503_when_workflow_not_ready(self, client):
        """Test that endpoint returns 503 if workflow not initialized."""
        with patch('src.api.endpoints.workflow_graph', None):
            response = client.post(
                "/api/v1/query",
                json={"query": "Test query"}
            )

            assert response.status_code == 503
            assert "not initialized" in response.json()["detail"].lower()

    def test_query_endpoint_sanitizes_error_messages(self, client):
        """Test that internal errors don't leak sensitive details."""
        with patch('src.api.endpoints.workflow_graph') as mock_graph:
            # Simulate internal error with sensitive info
            mock_graph.invoke.side_effect = Exception(
                "Database connection failed: postgres://user:password@host:5432/db"
            )

            response = client.post(
                "/api/v1/query",
                json={"query": "Test query"}
            )

            assert response.status_code == 500
            data = response.json()

            # Should not contain sensitive details
            assert "password" not in data["detail"].lower()
            assert "postgres://" not in data["detail"]
            assert "user:" not in data["detail"]

    def test_query_endpoint_sanitizes_api_key_errors(self, client):
        """Test that API key errors are sanitized."""
        with patch('src.api.endpoints.workflow_graph') as mock_graph:
            mock_graph.invoke.side_effect = Exception(
                "Failed to authenticate: api_key=sk-1234567890abcdef"
            )

            response = client.post(
                "/api/v1/query",
                json={"query": "Test query"}
            )

            assert response.status_code == 500
            data = response.json()

            # Should not contain the API key
            assert "sk-1234567890abcdef" not in data["detail"]
            assert "api_key" not in data["detail"].lower()


class TestQueryEndpointResponse:
    """Tests for query endpoint response format."""

    def test_query_endpoint_response_structure(self, client):
        """Test that response has required fields."""
        with patch('src.api.endpoints.workflow_graph') as mock_graph:
            mock_graph.invoke.return_value = {
                "formatted_response": {
                    "answer": "Test answer",
                    "charts": [],
                    "data_sources": []
                },
                "model_usage": {
                    "planner": "deepseek-r1",
                    "cortex_researcher": "deepseek-v3"
                },
                "plan": {"step_1": "example"},
                "replans": 0
            }

            response = client.post(
                "/api/v1/query",
                json={"query": "Test query"}
            )

            assert response.status_code == 200
            data = response.json()

            # Check response structure
            assert "answer" in data
            assert "charts" in data
            assert "data_sources" in data
            assert "metadata" in data

    def test_query_endpoint_includes_model_usage_in_response(self, client):
        """Test that response includes actual models used."""
        with patch('src.api.endpoints.workflow_graph') as mock_graph:
            mock_graph.invoke.return_value = {
                "formatted_response": {
                    "answer": "Test answer",
                    "charts": [],
                    "data_sources": []
                },
                "model_usage": {
                    "planner": "gpt-4o",
                    "cortex_researcher": "gpt-4o-mini"
                },
                "plan": {},
                "replans": 0
            }

            response = client.post(
                "/api/v1/query",
                json={"query": "Test query"}
            )

            assert response.status_code == 200
            data = response.json()

            # Verify models_used in metadata
            assert "metadata" in data
            assert "models_used" in data["metadata"]
            assert data["metadata"]["models_used"]["planner"] == "gpt-4o"
            assert data["metadata"]["models_used"]["cortex_researcher"] == "gpt-4o-mini"

    def test_query_endpoint_includes_execution_time(self, client):
        """Test that response includes execution time."""
        with patch('src.api.endpoints.workflow_graph') as mock_graph:
            mock_graph.invoke.return_value = {
                "formatted_response": {
                    "answer": "Test answer",
                    "charts": [],
                    "data_sources": []
                },
                "model_usage": {},
                "plan": {},
                "replans": 0
            }

            response = client.post(
                "/api/v1/query",
                json={"query": "Test query"}
            )

            assert response.status_code == 200
            data = response.json()

            # Should have execution_time_ms in metadata
            assert "metadata" in data
            assert "execution_time_ms" in data["metadata"]
            assert isinstance(data["metadata"]["execution_time_ms"], int)


class TestQueryEndpointCharts:
    """Tests for chart handling in responses."""

    def test_query_endpoint_includes_charts_when_enabled(self, client):
        """Test that charts are included in response when enabled."""
        with patch('src.api.endpoints.workflow_graph') as mock_graph:
            chart = {
                "type": "bar",
                "title": "Test Chart",
                "data": {"labels": ["A", "B"], "datasets": [{"name": "Data", "values": [1, 2]}]},
                "options": {}
            }

            mock_graph.invoke.return_value = {
                "formatted_response": {
                    "answer": "Test answer",
                    "charts": [chart],
                    "data_sources": []
                },
                "model_usage": {},
                "plan": {},
                "replans": 0
            }

            response = client.post(
                "/api/v1/query",
                json={"query": "Test query", "enable_charts": True}
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data["charts"]) > 0
            assert data["charts"][0]["type"] == "bar"

    def test_query_endpoint_respects_enable_charts_flag(self, client):
        """Test that enable_charts flag controls chart generation."""
        with patch('src.api.endpoints.workflow_graph') as mock_graph:
            mock_graph.invoke.return_value = {
                "formatted_response": {
                    "answer": "Test answer",
                    "charts": [],
                    "data_sources": []
                },
                "model_usage": {},
                "plan": {},
                "replans": 0
            }

            response = client.post(
                "/api/v1/query",
                json={"query": "Test query", "enable_charts": False}
            )

            assert response.status_code == 200
            # Verify that chart_generator was not in enabled_agents
            call_args = mock_graph.invoke.call_args
            state = call_args[0][0]
            assert "chart_generator" not in state.get("enabled_agents", [])
