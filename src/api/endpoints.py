"""FastAPI endpoints for OEWS Data Agent."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import time
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import AsyncGenerator

from src.api.models import (
    QueryRequest,
    QueryResponse,
    ChartSpec,
    DataSource,
    Metadata,
    ErrorResponse
)
from src.workflow.graph import create_workflow_graph
from src.utils.logger import setup_workflow_logger


# Global workflow graph instance
workflow_graph = None

# Initialize logger for API diagnostics
api_logger = setup_workflow_logger("oews.api")

# Thread pool for running blocking workflow operations
executor = ThreadPoolExecutor(max_workers=8)  # Allow up to 8 concurrent workflow executions

# Request timeout in seconds (5 minutes)
REQUEST_TIMEOUT = 300


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Lifespan context manager for startup/shutdown."""
    global workflow_graph

    # Startup: Create workflow graph once
    print("Initializing workflow graph...")
    try:
        workflow_graph = create_workflow_graph()
        print("Workflow graph ready.")
    except Exception as e:
        print(f"Warning: Failed to initialize workflow graph: {e}")
        print("API will return 503 errors until API keys are configured.")

    yield

    # Shutdown
    print("Shutting down...")


# Create FastAPI app
app = FastAPI(
    title="OEWS Data Agent API",
    description="Multi-agent system for OEWS employment data queries",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
# Get frontend origins from environment (comma-separated)
cors_origins_str = os.getenv("CORS_ORIGINS", "http://localhost:3000")
frontend_origins = [origin.strip() for origin in cors_origins_str.split(",")]

# Convert GitHub wildcards to regex patterns if present
import re
allow_origin_regex = None
regex_patterns = []

if any("*.github.io" in origin for origin in frontend_origins):
    # Remove wildcard entry and add ANCHORED regex pattern
    # SECURITY: Anchored pattern prevents https://github.io.attacker.com bypass
    frontend_origins = [o for o in frontend_origins if "*.github.io" not in o]
    regex_patterns.append(r"https://[a-z0-9-]+\.github\.io")

if any("*.app.github.dev" in origin for origin in frontend_origins):
    # Remove wildcard entry and add ANCHORED regex pattern for GitHub Codespaces
    # SECURITY: Anchored pattern prevents subdomain bypass attacks
    frontend_origins = [o for o in frontend_origins if "*.app.github.dev" not in o]
    regex_patterns.append(r"https://[a-z0-9-]+\.app\.github\.dev")

# Combine all regex patterns with anchors
if regex_patterns:
    allow_origin_regex = r"^(" + "|".join(regex_patterns) + r")$"

app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,  # Specific origins only
    allow_origin_regex=allow_origin_regex,  # Regex for GitHub Pages wildcard
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "workflow_loaded": workflow_graph is not None
    }


@app.post(
    "/api/v1/query",
    response_model=QueryResponse,
    responses={
        422: {"model": ErrorResponse},
        503: {"model": ErrorResponse}
    }
)
async def query(request: QueryRequest) -> QueryResponse:
    """
    Process a natural language query about OEWS employment data.

    This endpoint invokes the multi-agent workflow to:
    1. Plan the execution steps
    2. Query the database (Text2SQL)
    3. Generate charts (if requested)
    4. Synthesize a text answer
    5. Format the response

    Args:
        request: Query request with natural language question

    Returns:
        Formatted response with answer, charts, and metadata

    Raises:
        HTTPException: If workflow execution fails
    """
    if workflow_graph is None:
        raise HTTPException(
            status_code=503,
            detail="Workflow not initialized. Check API keys and configuration."
        )

    # Record start time
    start_time = time.time()

    # DIAGNOSTIC: Test if logging works in API process
    api_logger.debug("query_received", extra={
        "data": {
            "query": request.query[:100],
            "enable_charts": request.enable_charts,
            "cwd": os.getcwd()
        }
    })

    try:
        # Prepare initial state
        enabled_agents = ["cortex_researcher", "synthesizer"]
        if request.enable_charts:
            enabled_agents.insert(-1, "chart_generator")

        initial_state = {
            "messages": [],
            "user_query": request.query,
            "enabled_agents": enabled_agents,
            "reasoning_model_override": request.reasoning_model,
            "implementation_model_override": request.implementation_model
        }

        # Invoke workflow with timeout
        # Run blocking workflow_graph.invoke() in thread pool to avoid blocking event loop
        # Force flush API log
        import logging
        for handler in api_logger.handlers:
            handler.flush()

        # Define blocking workflow execution
        def run_workflow():
            return workflow_graph.invoke(
                initial_state,
                config={"recursion_limit": 100}
            )

        # Run with timeout (5 minutes)
        loop = asyncio.get_event_loop()
        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(executor, run_workflow),
                timeout=REQUEST_TIMEOUT
            )
        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=504,
                detail=f"Request processing exceeded {REQUEST_TIMEOUT} second timeout. The query may be too complex or the system is under heavy load."
            )

        # Extract formatted response
        formatted = result.get("formatted_response", {})

        # Calculate execution time
        execution_time = int((time.time() - start_time) * 1000)

        # Build response
        response = QueryResponse(
            answer=formatted.get("answer", result.get("final_answer", "No answer generated.")),
            charts=[
                ChartSpec(**chart)
                for chart in formatted.get("charts", [])
            ],
            data_sources=[
                DataSource(**source)
                for source in formatted.get("data_sources", [])
            ],
            metadata=Metadata(
                models_used=result.get("model_usage", {}),
                execution_time_ms=execution_time,
                plan=result.get("plan"),
                replans=result.get("replans", 0)
            )
        )

        return response

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Workflow execution failed: {str(e)}"
        )


@app.get("/api/v1/models")
async def list_models():
    """List available LLM models from configuration."""
    from src.config.llm_config import get_default_registry

    try:
        registry = get_default_registry()

        return {
            "defaults": {
                "reasoning": registry.default_reasoning,
                "implementation": registry.default_implementation
            },
            "models": {
                key: {
                    "provider": config.provider,
                    "model_name": config.model_name,
                    "role": config.role,
                    "cost_per_1m_tokens": config.cost_per_1m_tokens
                }
                for key, config in registry.models.items()
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load model registry: {str(e)}"
        )
