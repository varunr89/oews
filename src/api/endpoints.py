"""FastAPI endpoints for OEWS Data Agent."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import time
import os
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
# For development: Allow GitHub Spark and local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",           # Next.js local
        "https://*.github.io",             # GitHub Pages (Spark)
        "https://microsoftedge-spark.github.io",  # GitHub Spark
        "*"  # Allow all for development (TODO: restrict in production)
    ],
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

        # Invoke workflow
        # Invoke with high recursion limit for debugging
        # Force flush API log
        import logging
        for handler in api_logger.handlers:
            handler.flush()

        result = workflow_graph.invoke(
            initial_state,
            config={"recursion_limit": 100}
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
