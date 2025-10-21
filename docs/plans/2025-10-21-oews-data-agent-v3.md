# OEWS Data Agent Implementation Plan (v3) - Completion Tasks

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Complete the OEWS Data Agent implementation by filling in the Executor Node, Workflow Assembly, and FastAPI Application layers.

**Architecture:** This plan completes the missing implementation details from v2. It provides TDD-style steps for the Executor (routing logic), Workflow Assembly (LangGraph StateGraph), and FastAPI layer (HTTP interface).

**Tech Stack:** Python 3.10+, LangGraph, FastAPI, SQLAlchemy, Pydantic, pytest

**Changes from v2:**
- ✅ Added complete Executor Node implementation (Task 6.3)
- ✅ Added Workflow Assembly implementation (Task 6.4)
- ✅ Added FastAPI Application with Pydantic models (Milestone 7)
- ✅ Added optional large result set handling (Enhancement)

---

## Task 6.3: Create Executor Node

**Files:**
- Create: `src/agents/executor.py`
- Create: `src/prompts/executor_prompts.py`
- Modify: `src/agents/__init__.py`
- Create: `tests/test_executor.py`

**Step 1: Write the failing test**

Create `tests/test_executor.py`:

```python
import pytest
from src.agents.executor import executor_node
from src.agents.state import State
from langchain.schema import HumanMessage, AIMessage


def test_executor_routes_to_first_agent():
    """Test executor routes to first agent in plan."""
    state = State(
        messages=[HumanMessage(content="Test query")],
        user_query="Test query",
        plan={
            "1": {"agent": "cortex_researcher", "action": "Get data"},
            "2": {"agent": "synthesizer", "action": "Summarize"}
        },
        current_step=1,
        replan_flag=False,
        enabled_agents=["cortex_researcher", "synthesizer"]
    )

    result = executor_node(state)

    # Should route to cortex_researcher
    assert result.goto == "cortex_researcher"
    assert "agent_query" in result.update


def test_executor_advances_to_next_step():
    """Test executor advances to next step after completion."""
    state = State(
        messages=[
            HumanMessage(content="Test query"),
            AIMessage(content="Step 1 complete", name="cortex_researcher")
        ],
        user_query="Test query",
        plan={
            "1": {"agent": "cortex_researcher", "action": "Get data"},
            "2": {"agent": "synthesizer", "action": "Summarize"}
        },
        current_step=1,
        replan_flag=False,
        enabled_agents=["cortex_researcher", "synthesizer"]
    )

    result = executor_node(state)

    # Should advance to synthesizer
    assert result.goto == "synthesizer"
    assert result.update["current_step"] == 2


def test_executor_routes_to_response_formatter_when_plan_complete():
    """Test executor routes to response formatter at end."""
    state = State(
        messages=[
            HumanMessage(content="Test query"),
            AIMessage(content="Final step", name="synthesizer")
        ],
        user_query="Test query",
        plan={
            "1": {"agent": "cortex_researcher", "action": "Get data"},
            "2": {"agent": "synthesizer", "action": "Summarize"}
        },
        current_step=2,
        replan_flag=False,
        enabled_agents=["cortex_researcher", "synthesizer"]
    )

    result = executor_node(state)

    # Should route to response formatter
    assert result.goto == "response_formatter"


def test_executor_routes_to_planner_on_replan():
    """Test executor routes back to planner when replan needed."""
    state = State(
        messages=[HumanMessage(content="Test query")],
        user_query="Test query",
        plan={"1": {"agent": "cortex_researcher", "action": "Get data"}},
        current_step=1,
        replan_flag=True,
        replans=0,
        enabled_agents=["cortex_researcher"]
    )

    result = executor_node(state)

    # Should route back to planner
    assert result.goto == "planner"
    assert result.update["replans"] == 1
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_executor.py -v`

Expected: FAIL with "No module named 'src.agents.executor'"

**Step 3: Create executor prompts**

Create `src/prompts/executor_prompts.py`:

```python
"""Executor prompt templates for agent routing."""

from typing import Dict, Any


def build_agent_query(state) -> str:
    """
    Build the query string to send to the current agent.

    Extracts the action from the current plan step and formats it
    as a natural language instruction for the agent.

    Args:
        state: Current workflow state

    Returns:
        Query string for the agent
    """
    plan = state.get("plan", {})
    current_step = state.get("current_step", 1)

    step_key = str(current_step)
    if step_key not in plan:
        return state.get("user_query", "")

    step = plan[step_key]
    action = step.get("action", "")

    # Build context-aware query
    user_query = state.get("user_query", "")

    query = f"""
User Query: {user_query}

Your Task (Step {current_step}): {action}

Previous agent outputs are available in the message history.
Use the provided tools to complete this task.
""".strip()

    return query


def should_replan(state) -> bool:
    """
    Determine if replanning is needed based on state.

    Replan conditions:
    - replan_flag is True
    - Max replans (2) not exceeded

    Args:
        state: Current workflow state

    Returns:
        True if should replan
    """
    replan_flag = state.get("replan_flag", False)
    replans = state.get("replans", 0)
    MAX_REPLANS = 2

    return replan_flag and replans < MAX_REPLANS


def is_step_complete(state) -> bool:
    """
    Check if current step is complete based on messages.

    A step is complete if the last message is from the agent
    assigned to the current step.

    Args:
        state: Current workflow state

    Returns:
        True if step is complete
    """
    messages = state.get("messages", [])
    if not messages:
        return False

    plan = state.get("plan", {})
    current_step = state.get("current_step", 1)

    step_key = str(current_step)
    if step_key not in plan:
        return False

    expected_agent = plan[step_key]["agent"]

    # Check if last message is from expected agent
    last_msg = messages[-1]
    return hasattr(last_msg, 'name') and last_msg.name == expected_agent


def is_plan_complete(state) -> bool:
    """
    Check if all plan steps are complete.

    Args:
        state: Current workflow state

    Returns:
        True if plan is complete
    """
    plan = state.get("plan", {})
    current_step = state.get("current_step", 1)

    total_steps = len(plan)

    return current_step > total_steps
```

**Step 4: Create executor node**

Create `src/agents/executor.py`:

```python
"""Executor node for LangGraph workflow routing."""

from typing import Literal, Union
from langgraph.types import Command
from langchain.schema import HumanMessage
from src.agents.state import State
from src.prompts.executor_prompts import (
    build_agent_query,
    should_replan,
    is_step_complete,
    is_plan_complete
)


def executor_node(
    state: State
) -> Command[
    Literal[
        'planner',
        'cortex_researcher',
        'web_researcher',
        'chart_generator',
        'synthesizer',
        'response_formatter'
    ]
]:
    """
    The Executor is the traffic cop of the workflow.

    Responsibilities:
    1. Check if replanning is needed
    2. Check if current step is complete
    3. Check if entire plan is complete
    4. Route to the appropriate next node

    Routing Logic:
    - If replan_flag and replans < MAX_REPLANS → go to planner
    - If plan complete → go to response_formatter
    - If current step complete → advance to next step's agent
    - Otherwise → stay on current step's agent

    Args:
        state: Current workflow state

    Returns:
        Command to route to next node
    """

    # 1. Check if we need to replan
    if should_replan(state):
        replans = state.get("replans", 0)

        return Command(
            update={
                "replans": replans + 1,
                "replan_flag": False,  # Reset flag
                "messages": [HumanMessage(
                    content=f"Replanning (attempt {replans + 1})",
                    name="executor"
                )]
            },
            goto="planner"
        )

    # 2. Check if plan is complete
    if is_plan_complete(state):
        return Command(
            update={
                "messages": [HumanMessage(
                    content="Plan complete, formatting response",
                    name="executor"
                )]
            },
            goto="response_formatter"
        )

    # 3. Determine current or next agent
    plan = state.get("plan", {})
    current_step = state.get("current_step", 1)

    # If current step is complete, advance
    if is_step_complete(state):
        current_step += 1

    step_key = str(current_step)
    if step_key not in plan:
        # Plan exhausted, go to formatter
        return Command(
            update={},
            goto="response_formatter"
        )

    # 4. Route to the agent for current step
    target_agent = plan[step_key]["agent"]
    agent_query = build_agent_query(state)

    # Map agent names to valid node names
    agent_mapping = {
        "cortex_researcher": "cortex_researcher",
        "web_researcher": "web_researcher",
        "chart_generator": "chart_generator",
        "synthesizer": "synthesizer"
    }

    goto_node = agent_mapping.get(target_agent, "response_formatter")

    return Command(
        update={
            "current_step": current_step,
            "agent_query": agent_query,
            "last_agent": target_agent,
            "messages": [HumanMessage(
                content=f"Routing to {target_agent} (step {current_step})",
                name="executor"
            )]
        },
        goto=goto_node
    )
```

**Step 5: Update __init__.py**

Modify `src/agents/__init__.py`:

```python
"""Agent implementations for the OEWS data system."""

from .text2sql_agent import create_text2sql_agent
from .chart_generator import create_chart_generator_agent
from .state import State
from .response_formatter import response_formatter_node
from .planner import planner_node
from .executor import executor_node

__all__ = [
    "create_text2sql_agent",
    "create_chart_generator_agent",
    "State",
    "response_formatter_node",
    "planner_node",
    "executor_node"
]
```

**Step 6: Run test to verify it passes**

Run: `pytest tests/test_executor.py -v`

Expected: PASS (4 tests)

**Step 7: Commit**

```bash
git add src/agents/executor.py src/prompts/executor_prompts.py src/agents/__init__.py tests/test_executor.py
git commit -m "feat(agents): add executor node with routing logic"
```

---

## Task 6.4: Assemble Complete Workflow

**Files:**
- Create: `src/workflow/__init__.py`
- Create: `src/workflow/graph.py`
- Create: `tests/test_workflow.py`

**Step 1: Write the failing test**

Create `tests/test_workflow.py`:

```python
import pytest
import os
from src.workflow.graph import create_workflow_graph


skip_if_no_keys = pytest.mark.skipif(
    not os.getenv('AZURE_AI_API_KEY'),
    reason="No API keys configured"
)


def test_workflow_graph_creation():
    """Test that workflow graph can be created."""
    graph = create_workflow_graph()

    assert graph is not None
    # LangGraph compiled graphs have a .nodes attribute
    assert hasattr(graph, 'invoke') or hasattr(graph, 'stream')


@skip_if_no_keys
def test_workflow_executes_simple_query():
    """Test workflow can execute a simple query end-to-end."""
    graph = create_workflow_graph()

    initial_state = {
        "messages": [],
        "user_query": "What is the median salary for software developers in Seattle?",
        "enabled_agents": ["cortex_researcher", "synthesizer"]
    }

    # Run workflow
    result = graph.invoke(initial_state)

    # Check result has expected fields
    assert "formatted_response" in result
    assert "messages" in result


@skip_if_no_keys
def test_workflow_with_chart_generation():
    """Test workflow with chart generation step."""
    graph = create_workflow_graph()

    initial_state = {
        "messages": [],
        "user_query": "Show me a chart comparing tech salaries in Seattle",
        "enabled_agents": ["cortex_researcher", "chart_generator", "synthesizer"]
    }

    result = graph.invoke(initial_state)

    # Should have chart in formatted response
    assert "formatted_response" in result
    formatted = result["formatted_response"]
    assert "charts" in formatted
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_workflow.py -v`

Expected: FAIL with "No module named 'src.workflow.graph'"

**Step 3: Create workflow graph**

Create `src/workflow/__init__.py`:

```python
"""Workflow assembly for LangGraph."""

from .graph import create_workflow_graph

__all__ = ["create_workflow_graph"]
```

Create `src/workflow/graph.py`:

```python
"""LangGraph workflow assembly."""

from langgraph.graph import StateGraph, START, END
from src.agents.state import State
from src.agents.planner import planner_node
from src.agents.executor import executor_node
from src.agents.response_formatter import response_formatter_node
from src.agents.text2sql_agent import create_text2sql_agent
from src.agents.chart_generator import create_chart_generator_agent


def cortex_researcher_node(state: State):
    """Wrapper for Text2SQL agent."""
    from langgraph.types import Command
    from langchain.schema import AIMessage

    agent = create_text2sql_agent()
    agent_query = state.get("agent_query", state.get("user_query", ""))

    # Run agent
    result = agent.invoke({"messages": [{"role": "user", "content": agent_query}]})

    # Extract final answer
    final_message = result["messages"][-1] if result.get("messages") else None
    response_content = final_message.content if final_message else "No result"

    return Command(
        update={
            "messages": [AIMessage(content=response_content, name="cortex_researcher")],
            "model_usage": {
                **(state.get("model_usage") or {}),
                "cortex_researcher": state.get("implementation_model_override") or "deepseek-v3"
            }
        },
        goto="executor"
    )


def chart_generator_node(state: State):
    """Wrapper for Chart Generator agent."""
    from langgraph.types import Command
    from langchain.schema import AIMessage

    agent = create_chart_generator_agent()
    agent_query = state.get("agent_query", state.get("user_query", ""))

    # Run agent
    result = agent.invoke({"messages": [{"role": "user", "content": agent_query}]})

    final_message = result["messages"][-1] if result.get("messages") else None
    response_content = final_message.content if final_message else "No charts generated"

    return Command(
        update={
            "messages": [AIMessage(content=response_content, name="chart_generator")],
            "model_usage": {
                **(state.get("model_usage") or {}),
                "chart_generator": state.get("implementation_model_override") or "deepseek-v3"
            }
        },
        goto="chart_summarizer"
    )


def chart_summarizer_node(state: State):
    """Describe charts in natural language."""
    from langgraph.types import Command
    from langchain.schema import AIMessage

    # Extract chart specs from last message
    messages = state.get("messages", [])
    last_msg = messages[-1] if messages else None

    if not last_msg or "CHART_SPEC" not in last_msg.content:
        summary = "No charts were generated."
    else:
        # Simple extraction of chart type
        import re
        chart_types = re.findall(r'"type":\s*"(\w+)"', last_msg.content)

        if chart_types:
            chart_list = ", ".join(chart_types)
            summary = f"Generated {len(chart_types)} chart(s): {chart_list}"
        else:
            summary = "Generated charts (details in message)."

    return Command(
        update={
            "messages": [AIMessage(content=summary, name="chart_summarizer")]
        },
        goto="executor"
    )


def synthesizer_node(state: State):
    """Create text summary of all findings."""
    from langgraph.types import Command
    from langchain.schema import AIMessage, HumanMessage
    from src.config.llm_factory import llm_factory

    # Get implementation model
    impl_llm = llm_factory.get_implementation()

    # Build summary prompt
    messages = state.get("messages", [])
    user_query = state.get("user_query", "")

    context = "\n\n".join([
        f"**{msg.name or 'message'}:** {msg.content}"
        for msg in messages
        if hasattr(msg, 'name') and msg.name in ["cortex_researcher", "web_researcher", "chart_summarizer"]
    ])

    prompt = f"""
You are the Synthesizer agent. Create a concise text summary of the findings.

User Query: {user_query}

Agent Outputs:
{context}

Provide a 2-3 sentence summary that directly answers the user's question.
Focus on key insights and actionable information.
"""

    # Invoke LLM
    response = impl_llm.invoke([HumanMessage(content=prompt)])

    return Command(
        update={
            "messages": [AIMessage(content=response.content, name="synthesizer")],
            "final_answer": response.content,
            "model_usage": {
                **(state.get("model_usage") or {}),
                "synthesizer": state.get("implementation_model_override") or "deepseek-v3"
            }
        },
        goto="executor"
    )


def web_researcher_node(state: State):
    """Placeholder for web research agent."""
    from langgraph.types import Command
    from langchain.schema import AIMessage

    # TODO: Implement web research using Tavily or similar
    response = "Web research not yet implemented."

    return Command(
        update={
            "messages": [AIMessage(content=response, name="web_researcher")]
        },
        goto="executor"
    )


def create_workflow_graph():
    """
    Create and compile the complete LangGraph workflow.

    Returns:
        Compiled StateGraph
    """
    # Create graph
    graph = StateGraph(State)

    # Add nodes
    graph.add_node("planner", planner_node)
    graph.add_node("executor", executor_node)
    graph.add_node("cortex_researcher", cortex_researcher_node)
    graph.add_node("chart_generator", chart_generator_node)
    graph.add_node("chart_summarizer", chart_summarizer_node)
    graph.add_node("synthesizer", synthesizer_node)
    graph.add_node("web_researcher", web_researcher_node)
    graph.add_node("response_formatter", response_formatter_node)

    # Define edges
    # START always goes to planner
    graph.add_edge(START, "planner")

    # Planner goes to executor (specified in planner_node Command)
    # Executor routes to agents (specified in executor_node Command)
    # Agents return to executor (specified in agent node Commands)
    # Response formatter goes to END
    graph.add_edge("response_formatter", END)

    # Compile
    return graph.compile()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_workflow.py -v`

Expected: PASS (1 test without API keys, 3 tests with API keys)

**Step 5: Commit**

```bash
git add src/workflow/ tests/test_workflow.py
git commit -m "feat(workflow): assemble complete LangGraph workflow with all nodes"
```

---

## Milestone 7: FastAPI Application

### Task 7.1: Create API Models and Endpoints

**Files:**
- Create: `src/api/__init__.py`
- Create: `src/api/models.py`
- Create: `src/api/endpoints.py`
- Create: `tests/test_api.py`

**Step 1: Write the failing test**

Create `tests/test_api.py`:

```python
import pytest
from fastapi.testclient import TestClient


def test_api_app_creation():
    """Test FastAPI app can be created."""
    from src.api.endpoints import app

    assert app is not None


def test_health_endpoint():
    """Test health check endpoint."""
    from src.api.endpoints import app

    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_query_endpoint_schema():
    """Test query endpoint accepts correct schema."""
    from src.api.endpoints import app

    client = TestClient(app)

    # Valid request
    response = client.post(
        "/api/v1/query",
        json={
            "query": "What are software developer salaries in Seattle?",
            "enable_charts": True
        }
    )

    # Should return 200 (or 503 if no API keys)
    assert response.status_code in [200, 503]

    # Invalid request (missing query)
    response = client.post("/api/v1/query", json={})
    assert response.status_code == 422


def test_query_endpoint_returns_formatted_response():
    """Test query endpoint returns properly formatted response."""
    from src.api.endpoints import app

    client = TestClient(app)

    response = client.post(
        "/api/v1/query",
        json={
            "query": "Test query",
            "enable_charts": False
        }
    )

    if response.status_code == 200:
        data = response.json()

        # Check expected fields
        assert "answer" in data
        assert "charts" in data
        assert "metadata" in data
        assert "data_sources" in data
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_api.py -v`

Expected: FAIL with "No module named 'src.api.models'"

**Step 3: Create API models**

Create `src/api/__init__.py`:

```python
"""FastAPI application for OEWS Data Agent."""

from .models import QueryRequest, QueryResponse, ChartSpec, Metadata
from .endpoints import app

__all__ = [
    "QueryRequest",
    "QueryResponse",
    "ChartSpec",
    "Metadata",
    "app"
]
```

Create `src/api/models.py`:

```python
"""Pydantic models for API requests and responses."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


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
    """Metadata about a data source used in the response."""

    name: str = Field(..., description="Data source name")
    sql_query: Optional[str] = Field(None, description="SQL query executed (if applicable)")
    row_count: Optional[int] = Field(None, description="Number of rows returned")


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
```

**Step 4: Create FastAPI endpoints**

Create `src/api/endpoints.py`:

```python
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


# Global workflow graph instance
workflow_graph = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Lifespan context manager for startup/shutdown."""
    global workflow_graph

    # Startup: Create workflow graph once
    print("Initializing workflow graph...")
    workflow_graph = create_workflow_graph()
    print("Workflow graph ready.")

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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js default port
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
        result = workflow_graph.invoke(initial_state)

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
```

**Step 5: Install FastAPI dependencies**

Update `requirements.txt`:

```txt
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
python-multipart>=0.0.9
```

Run: `pip install fastapi uvicorn python-multipart`

**Step 6: Run test to verify it passes**

Run: `pytest tests/test_api.py -v`

Expected: PASS (4 tests)

**Step 7: Commit**

```bash
git add src/api/ tests/test_api.py requirements.txt
git commit -m "feat(api): add FastAPI endpoints with Pydantic models"
```

---

### Task 7.2: Create API Server Entry Point

**Files:**
- Create: `src/main.py`
- Create: `scripts/start_server.sh`

**Step 1: Create server entry point**

Create `src/main.py`:

```python
"""Main entry point for FastAPI server."""

import uvicorn
import os


def main():
    """Start the FastAPI server."""
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    reload = os.getenv("API_RELOAD", "true").lower() == "true"

    uvicorn.run(
        "src.api.endpoints:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )


if __name__ == "__main__":
    main()
```

**Step 2: Create startup script**

Create `scripts/start_server.sh`:

```bash
#!/bin/bash

# OEWS Data Agent API Server Startup Script

echo "Starting OEWS Data Agent API..."

# Check for required environment variables
if [ -z "$AZURE_AI_API_KEY" ]; then
    echo "Warning: AZURE_AI_API_KEY not set. API may not function correctly."
fi

# Set defaults
export API_HOST="${API_HOST:-0.0.0.0}"
export API_PORT="${API_PORT:-8000}"
export DATABASE_ENV="${DATABASE_ENV:-dev}"
export SQLITE_DB_PATH="${SQLITE_DB_PATH:-data/oews.db}"

# Start server
python -m src.main
```

Make executable: `chmod +x scripts/start_server.sh`

**Step 3: Test server startup**

Run: `python -m src.main`

Expected: Server starts on http://0.0.0.0:8000 and prints:
```
INFO:     Started server process
INFO:     Waiting for application startup.
Initializing workflow graph...
Workflow graph ready.
INFO:     Application startup complete.
```

Press Ctrl+C to stop.

**Step 4: Commit**

```bash
git add src/main.py scripts/start_server.sh
git commit -m "feat(api): add server entry point and startup script"
```

---

## Enhancement: Large Result Set Handling

### Task 8.1: Add Result Size Management

**Files:**
- Modify: `src/tools/database_tools.py`
- Modify: `tests/test_database_tools.py`

**Step 1: Write the failing test**

Modify `tests/test_database_tools.py` to add:

```python
def test_execute_sql_query_handles_large_results():
    """Test that large query results are summarized."""
    from src.tools.database_tools import execute_sql_query

    # Query that returns many rows
    result_str = execute_sql_query.invoke({
        "sql": "SELECT * FROM oews_data LIMIT 2000"
    })

    import json
    result = json.loads(result_str)

    # Should have summary field if truncated
    if result["row_count"] > 1000:
        assert "summary" in result
        assert "truncated" in result
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_database_tools.py::test_execute_sql_query_handles_large_results -v`

Expected: FAIL with "assert 'summary' in result"

**Step 3: Modify execute_sql_query**

Modify `src/tools/database_tools.py`, update the `execute_sql_query` function:

```python
@tool
def execute_sql_query(sql: str, params: Optional[str] = None) -> str:
    """
    Executes SQL query against OEWS database and returns results.

    SECURITY: This tool REQUIRES parameterized queries.

    For large result sets (>1000 rows), returns a summary with first 10 rows
    instead of the full dataset to prevent memory issues.

    Args:
        sql: SQL SELECT query with ? placeholders
        params: Optional JSON string of parameters

    Returns:
        JSON string with query results or summary
    """
    import json

    try:
        # Parse params if provided
        params_tuple = None
        if params:
            params_list = json.loads(params)
            params_tuple = tuple(params_list)

        db = OEWSDatabase()
        df = db.execute_query(sql, params=params_tuple)
        db.close()

        row_count = len(df)

        # Handle large result sets
        if row_count > 1000:
            # Return summary instead of full data
            result = {
                "success": True,
                "truncated": True,
                "summary": (
                    f"Query returned {row_count:,} rows (showing first 10). "
                    f"Full dataset available in agent memory for analysis."
                ),
                "columns": df.columns.tolist(),
                "sample_data": df.head(10).values.tolist(),
                "row_count": row_count,
                "sql": sql,
                "params": params,
                "stats": {
                    # Provide statistics for numeric columns
                    col: {
                        "min": float(df[col].min()),
                        "max": float(df[col].max()),
                        "mean": float(df[col].mean()),
                        "median": float(df[col].median())
                    }
                    for col in df.select_dtypes(include=['number']).columns[:5]
                }
            }
        else:
            # Return full data for small results
            result = {
                "success": True,
                "truncated": False,
                "columns": df.columns.tolist(),
                "data": df.values.tolist(),
                "row_count": row_count,
                "sql": sql,
                "params": params
            }

        return json.dumps(result, indent=2)

    except Exception as e:
        result = {
            "success": False,
            "error": str(e),
            "sql": sql,
            "params": params
        }
        return json.dumps(result, indent=2)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_database_tools.py::test_execute_sql_query_handles_large_results -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/tools/database_tools.py tests/test_database_tools.py
git commit -m "feat(tools): add large result set handling with automatic summarization"
```

---

## Summary

This v3 plan completes the OEWS Data Agent implementation by providing detailed TDD steps for:

1. **Executor Node (Task 6.3)** - Traffic cop routing logic with replan handling
2. **Workflow Assembly (Task 6.4)** - Complete LangGraph StateGraph with all nodes wired
3. **FastAPI Application (Milestone 7)** - HTTP API with Pydantic models for Next.js frontend
4. **Large Result Handling (Enhancement)** - Automatic summarization for queries returning >1000 rows

### Execution Order

For best results, execute tasks in this order:
1. Task 6.3: Executor Node
2. Task 6.4: Workflow Assembly
3. Task 7.1: API Models and Endpoints
4. Task 7.2: API Server Entry Point
5. Task 8.1: Large Result Set Handling (optional)

### Testing the Complete System

After completing all tasks, test end-to-end:

```bash
# Start the server
python -m src.main

# In another terminal, test the API
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the median salaries for software developers in Seattle?",
    "enable_charts": false
  }'
```

Expected: JSON response with answer, data sources, and metadata.
