"""Pydantic models for API requests and responses."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator


class QueryRequest(BaseModel):
    """Request model for /api/v1/query endpoint."""

    query: str = Field(
        ...,
        description="Natural language question about OEWS employment data",
        min_length=3,
        max_length=500,
        examples=["What are software developer salaries in Seattle?"]
    )

    enable_charts: bool = Field(
        default=True,
        description="Whether to generate chart visualizations"
    )

    reasoning_model: Optional[str] = Field(
        default=None,
        description="Override default reasoning model (e.g., 'gpt-4o', 'deepseek-r1')"
    )

    implementation_model: Optional[str] = Field(
        default=None,
        description="Override default implementation model (e.g., 'deepseek-v3')"
    )

    @field_validator('reasoning_model', 'implementation_model')
    @classmethod
    def validate_model_key(cls, v: Optional[str]) -> Optional[str]:
        """Validate that model key exists in registry."""
        if v is None:
            return v

        # Import here to avoid circular dependency
        from src.config.llm_config import get_default_registry

        try:
            registry = get_default_registry()
            if v not in registry.models:
                available = ", ".join(sorted(registry.models.keys()))
                raise ValueError(
                    f"Model '{v}' not found in registry. "
                    f"Available models: {available}"
                )
            return v
        except Exception as e:
            # If config loading fails, log but don't block (degraded mode)
            import logging
            logging.warning(f"Could not validate model key '{v}': {e}")
            return v


class ChartSpec(BaseModel):
    """Chart specification in ECharts/Plotly format."""

    type: str = Field(
        ...,
        description="Chart type (bar, line, scatter, etc.)"
    )

    title: str = Field(
        ...,
        description="Chart title"
    )

    data: Dict[str, Any] = Field(
        ...,
        description="Chart data in format compatible with frontend library"
    )

    options: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional chart options"
    )


class DataSource(BaseModel):
    """Execution trace for an agent action."""

    step: int = Field(..., description="Step number in execution sequence")
    agent: str = Field(..., description="Agent that performed this action")
    type: str = Field(..., description="Type of action (planning, oews_database, web_search)")
    action: Optional[str] = Field(None, description="Human-readable description of action")

    # Planning-specific fields
    plan: Optional[Dict[str, Any]] = Field(None, description="Generated execution plan")
    reasoning_model: Optional[str] = Field(None, description="Model used for reasoning")

    # SQL-specific fields
    sql: Optional[str] = Field(None, description="SQL query executed")
    params: Optional[List[Any]] = Field(None, description="Query parameters")
    row_count: Optional[int] = Field(None, description="Number of rows returned")
    sample_data: Optional[List[Dict[str, Any]]] = Field(None, description="Sample result rows")
    stats: Optional[Dict[str, Any]] = Field(None, description="Column statistics (min/max/avg)")

    # Web search-specific fields
    search_query: Optional[str] = Field(None, description="Search query executed")
    sources: Optional[List[Dict[str, Any]]] = Field(None, description="Web sources found")


class Metadata(BaseModel):
    """Response metadata including model usage and timing."""

    models_used: Dict[str, str] = Field(
        ...,
        description="Mapping of agent name to model used"
    )

    execution_time_ms: Optional[int] = Field(
        None,
        description="Total execution time in milliseconds"
    )

    plan: Optional[Dict[str, Any]] = Field(
        None,
        description="Execution plan created by planner"
    )

    replans: int = Field(
        default=0,
        description="Number of times the plan was revised"
    )


class QueryResponse(BaseModel):
    """Response model for /api/v1/query endpoint."""

    answer: str = Field(
        ...,
        description="Natural language answer to the query"
    )

    charts: List[ChartSpec] = Field(
        default_factory=list,
        description="List of chart specifications for frontend rendering"
    )

    data_sources: List[DataSource] = Field(
        default_factory=list,
        description="Data sources used to generate the response"
    )

    metadata: Metadata = Field(
        ...,
        description="Execution metadata and model tracking"
    )


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
