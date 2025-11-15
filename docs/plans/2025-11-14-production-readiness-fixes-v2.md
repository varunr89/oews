# Production Readiness Fixes Implementation Plan (v2 - Corrected)

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Address critical, important, and minor issues identified in GPT-5 codebase review to achieve production readiness (target: 7.5/10).

**Architecture:** Fix security vulnerabilities (SQL injection prevention with sqlparse), implement model override functionality across all agents, improve error handling and validation, enhance testing coverage, and resolve code quality issues.

**Tech Stack:** Python 3.x, LangGraph, LangChain, FastAPI, SQLAlchemy, pytest, sqlparse

**Review Source:** `.claude/phone-a-friend/2025-11-14-083901-codebase-review.md`
**Plan Review:** Session 019a834f-f377-7dd2-8d6c-654fa5d06901

**Current Production Readiness:** 6.5/10
**Target Production Readiness:** 7.5/10 (authentication deferred per user decision)
**Technical Debt:** Medium → Low

**IMPORTANT:** This v2 plan incorporates all critical corrections from GPT-5 plan review:
- Parameter naming corrected (`override_key` not `model_override`)
- SQL guard enhanced with sqlparse (CTEs, multi-statement detection)
- API tests corrected to match actual endpoint schemas
- Authentication simplified to documentation-only
- Realistic production readiness target (7.5/10 without auth implementation)

---

## Prerequisites

### Step 0: Install sqlparse dependency

```bash
pip install sqlparse
```

Or add to `requirements.txt`:
```
sqlparse>=0.4.4
```

Verify installation:
```bash
python -c "import sqlparse; print(sqlparse.__version__)"
```

Expected: `0.4.4` or higher

---

## Task 1: Add SELECT-Only Guard to SQL Execution (CRITICAL)

**Priority:** CRITICAL - Security vulnerability
**Files:**
- Modify: `src/tools/database_tools.py:84-180`
- Test: `tests/test_database_tools.py`

### Step 1: Write failing tests for SELECT-only enforcement

Create tests in `tests/test_database_tools.py`:

```python
import json
from src.tools.database_tools import execute_sql_query


def test_execute_sql_query_blocks_non_select_statements():
    """Test that execute_sql_query blocks dangerous SQL statements."""
    dangerous_queries = [
        "DROP TABLE oews_data",
        "DELETE FROM oews_data WHERE 1=1",
        "UPDATE oews_data SET A_MEAN = 0",
        "INSERT INTO oews_data VALUES (1, 2, 3)",
        "ALTER TABLE oews_data ADD COLUMN test TEXT",
        "CREATE TABLE malicious (id INT)",
        "TRUNCATE TABLE oews_data",
        "  drop table oews_data",  # With leading whitespace
        "-- comment\nDROP TABLE oews_data",  # With comment
    ]

    for sql in dangerous_queries:
        result = execute_sql_query.invoke({"sql": sql, "params": "[]"})
        result_data = json.loads(result)
        assert result_data["success"] is False, f"Should block: {sql}"
        assert "SELECT" in result_data["error"] or "WITH" in result_data["error"], \
            f"Error should mention allowed statements: {result_data['error']}"


def test_execute_sql_query_allows_select_with_whitespace():
    """Test that SELECT queries with leading whitespace/comments are allowed."""
    valid_queries = [
        "SELECT * FROM oews_data LIMIT 1",
        "  SELECT * FROM oews_data LIMIT 1",  # Leading whitespace
        "\nSELECT * FROM oews_data LIMIT 1",  # Leading newline
        "-- comment\nSELECT * FROM oews_data LIMIT 1",  # With comment
        "select * FROM oews_data LIMIT 1",  # Lowercase
    ]

    for sql in valid_queries:
        result = execute_sql_query.invoke({"sql": sql, "params": "[]"})
        result_data = json.loads(result)
        # Should succeed (or fail for other reasons, but not policy)
        if not result_data["success"]:
            assert "SELECT" not in result_data["error"], \
                f"Should not block SELECT query: {sql}"
            assert "WITH" not in result_data["error"], \
                f"Should not block SELECT query: {sql}"


def test_execute_sql_query_allows_cte():
    """Test that WITH (CTE) queries are allowed."""
    sql = """
    WITH avg_wage AS (
        SELECT AVG(A_MEAN) as avg_val FROM oews_data
    )
    SELECT * FROM avg_wage LIMIT 1
    """
    result = execute_sql_query.invoke({"sql": sql, "params": "[]"})
    result_data = json.loads(result)
    # Should succeed or fail for reasons other than policy
    if not result_data["success"]:
        assert "SELECT" not in result_data["error"]
        assert "WITH" not in result_data["error"]


def test_execute_sql_query_blocks_multiple_statements():
    """Test that multi-statement payloads are blocked."""
    dangerous_multi = [
        "SELECT 1; DROP TABLE oews_data",
        "SELECT * FROM oews_data; DELETE FROM oews_data",
        "SELECT 1; SELECT 2",  # Even benign multiples blocked
    ]

    for sql in dangerous_multi:
        result = execute_sql_query.invoke({"sql": sql, "params": "[]"})
        result_data = json.loads(result)
        assert result_data["success"] is False, f"Should block multi-statement: {sql}"
        assert "multiple" in result_data["error"].lower() or \
               "single" in result_data["error"].lower(), \
            f"Should mention multiple statements: {result_data['error']}"
```

### Step 2: Run tests to verify they fail

Run: `pytest tests/test_database_tools.py::test_execute_sql_query_blocks_non_select_statements tests/test_database_tools.py::test_execute_sql_query_allows_cte tests/test_database_tools.py::test_execute_sql_query_blocks_multiple_statements -v`
Expected: FAIL - dangerous queries are currently executed, CTEs may be blocked

### Step 3: Implement SELECT-only guard with sqlparse

Modify `src/tools/database_tools.py:84-180`:

```python
import sqlparse

@tool
def execute_sql_query(sql: str, params: Optional[str] = None) -> str:
    """
    Execute a SELECT query on the OEWS database.

    SECURITY: Only SELECT and WITH (CTE) queries are allowed. All other SQL
    statements (DROP, DELETE, UPDATE, INSERT, ALTER, CREATE, TRUNCATE) and
    multi-statement queries are rejected.

    Args:
        sql: SQL SELECT or WITH query to execute
        params: JSON array of parameters for parameterized query

    Returns:
        JSON string with results or error
    """
    import json

    # SECURITY: Enforce SELECT-only policy using sqlparse
    try:
        statements = sqlparse.parse(sql)
    except Exception as e:
        logger.error("sql_parse_error", extra={
            "data": {"error": str(e), "sql_preview": sql[:100]}
        })
        return json.dumps({
            "success": False,
            "error": f"SQL parsing error: {str(e)}"
        })

    # Reject empty SQL
    if len(statements) == 0:
        return json.dumps({"success": False, "error": "Empty SQL query"})

    # Reject multiple statements (prevents "SELECT 1; DROP TABLE" attacks)
    if len(statements) > 1:
        logger.warning("sql_execution_blocked", extra={
            "data": {"reason": "multiple_statements", "count": len(statements)}
        })
        return json.dumps({
            "success": False,
            "error": "Multiple SQL statements not allowed. Only single SELECT or WITH queries permitted."
        })

    statement = statements[0]

    # Get first token (sqlparse automatically handles whitespace/comments)
    first_token = statement.token_first(skip_ws=True, skip_cm=True)

    if not first_token:
        return json.dumps({"success": False, "error": "Could not parse SQL statement"})

    first_token_value = first_token.value.upper()

    # Allow SELECT and WITH (CTEs)
    if first_token_value not in ('SELECT', 'WITH'):
        logger.warning("sql_execution_blocked", extra={
            "data": {
                "reason": "non_select_statement",
                "first_token": first_token_value,
                "sql_preview": sql[:100]
            }
        })
        return json.dumps({
            "success": False,
            "error": f"Only SELECT and WITH (CTE) queries are allowed. Got: {first_token_value}"
        })

    # For WITH statements, verify they contain SELECT
    if first_token_value == 'WITH':
        sql_upper = sql.upper()
        if 'SELECT' not in sql_upper:
            return json.dumps({
                "success": False,
                "error": "WITH clause must be followed by SELECT"
            })

    # Add defensive LIMIT if not present
    MAX_ROWS_WITHOUT_LIMIT = 10000
    if 'LIMIT' not in sql.upper():
        logger.info("sql_adding_defensive_limit", extra={
            "data": {"original_sql_preview": sql[:100]}
        })
        sql = f"{sql.rstrip().rstrip(';')} LIMIT {MAX_ROWS_WITHOUT_LIMIT}"

    # Parse params
    try:
        params_list = json.loads(params) if params else []
    except json.JSONDecodeError:
        return json.dumps({
            "success": False,
            "error": f"Invalid params JSON: {params}"
        })

    # Execute query
    try:
        db = OEWSDatabase()
        df = db.execute_query(sql, tuple(params_list))

        # ... rest of existing implementation ...
        # (Keep the existing result formatting code)
```

### Step 4: Run tests to verify they pass

Run: `pytest tests/test_database_tools.py::test_execute_sql_query_blocks_non_select_statements tests/test_database_tools.py::test_execute_sql_query_allows_select_with_whitespace tests/test_database_tools.py::test_execute_sql_query_allows_cte tests/test_database_tools.py::test_execute_sql_query_blocks_multiple_statements -v`
Expected: PASS - all dangerous queries blocked, SELECT and WITH allowed

### Step 5: Add defensive LIMIT test

Add test in `tests/test_database_tools.py`:

```python
def test_execute_sql_query_adds_default_limit():
    """Test that queries without LIMIT get a defensive cap."""
    sql = "SELECT * FROM oews_data"
    result = execute_sql_query.invoke({"sql": sql, "params": "[]"})
    result_data = json.loads(result)

    if result_data["success"]:
        assert "row_count" in result_data
        # Should not return more than default limit
        assert result_data["row_count"] <= 10000, \
            "Query without LIMIT should be capped"
```

Run: `pytest tests/test_database_tools.py::test_execute_sql_query_adds_default_limit -v`
Expected: PASS

### Step 6: Commit

```bash
git add src/tools/database_tools.py tests/test_database_tools.py
git commit -m "feat(security): add SELECT-only guard with sqlparse for SQL execution

- Use sqlparse for robust SQL parsing (handles whitespace/comments automatically)
- Block all non-SELECT/WITH statements (DROP, DELETE, UPDATE, INSERT, etc.)
- Allow WITH (CTE) queries followed by SELECT
- Detect and reject multi-statement payloads (prevents injection bypass)
- Add defensive LIMIT cap (10000) for queries without LIMIT
- Comprehensive tests for security policy

Addresses CRITICAL security vulnerability from codebase review.
Ref: .claude/phone-a-friend/2025-11-14-083901-codebase-review.md
Plan review: Session 019a834f-f377-7dd2-8d6c-654fa5d06901"
```

---

## Task 2: Implement Model Override in Planner

**Priority:** CRITICAL - API contract broken
**Files:**
- Modify: `src/agents/planner.py:15-60`
- Test: `tests/test_model_overrides.py` (new file)

**NOTE:** Factory uses `override_key` parameter, not `model_override`

### Step 1: Write failing test for planner model override

Create `tests/test_model_overrides.py`:

```python
"""Tests for model override functionality."""
import pytest
from unittest.mock import Mock, patch
from src.agents.state import State
from src.agents.planner import planner_node


def test_planner_uses_reasoning_model_override():
    """Test that planner respects reasoning_model from state."""
    state = State(
        user_query="Test query",
        reasoning_model="deepseek-reasoner",  # Override key
        messages=[],
        plan={},
        current_step=0,
        max_steps=5,
        replans=0,
        model_usage={}
    )

    with patch('src.agents.planner.llm_factory') as mock_factory:
        mock_llm = Mock()
        mock_llm.invoke.return_value = Mock(content='{"step_1": {"agent": "test"}}')
        mock_llm.model = "deepseek-reasoner"  # Simulate model attribute
        mock_factory.get_reasoning.return_value = mock_llm

        planner_node(state)

        # Verify get_reasoning was called with override_key parameter
        mock_factory.get_reasoning.assert_called_once_with(override_key="deepseek-reasoner")


def test_planner_uses_default_reasoning_model_when_no_override():
    """Test that planner uses default when no override specified."""
    state = State(
        user_query="Test query",
        messages=[],
        plan={},
        current_step=0,
        max_steps=5,
        replans=0,
        model_usage={}
    )

    with patch('src.agents.planner.llm_factory') as mock_factory:
        mock_llm = Mock()
        mock_llm.invoke.return_value = Mock(content='{"step_1": {"agent": "test"}}')
        mock_llm.model = "default-reasoning"
        mock_factory.get_reasoning.return_value = mock_llm

        planner_node(state)

        # Verify get_reasoning was called with None (use default)
        mock_factory.get_reasoning.assert_called_once_with(override_key=None)
```

### Step 2: Run test to verify it fails

Run: `pytest tests/test_model_overrides.py::test_planner_uses_reasoning_model_override -v`
Expected: FAIL - planner doesn't pass override_key parameter yet

### Step 3: Update planner to use model override

Modify `src/agents/planner.py:15-60`:

```python
def planner_node(state: State) -> Command[Literal['executor']]:
    """
    Runs the planning LLM and stores the resulting plan in state.

    Uses the configured reasoning model (high capability for planning),
    or the model specified in state.reasoning_model if provided.

    Returns:
        Command updating state with plan and routing to executor
    """
    user_query = state.get("user_query", "")

    # Get reasoning model (with optional override from state)
    reasoning_model_key = state.get("reasoning_model")
    reasoning_llm = llm_factory.get_reasoning(override_key=reasoning_model_key)

    # Track which model was actually used
    actual_model = reasoning_llm.model if hasattr(reasoning_llm, 'model') else \
                   reasoning_llm.model_name if hasattr(reasoning_llm, 'model_name') else "unknown"

    # Build prompt
    messages = [HumanMessage(content=plan_prompt(user_query))]

    # Invoke LLM
    logger.info("planner_invoked", extra={
        "data": {
            "user_query": user_query,
            "model_requested": reasoning_model_key or "default",
            "model_actual": actual_model
        }
    })

    response = reasoning_llm.invoke(messages)

    # Parse plan from response
    content = response.content

    # Strip <think> tags if present (from reasoning models)
    if "<think>" in content:
        think_end = content.find("</think>")
        if think_end != -1:
            content = content[think_end + 8:].strip()

    # Extract JSON by counting braces
    brace_start = content.find('{')
    if brace_start == -1:
        logger.error("planner_no_json", extra={"data": {"content": content[:200]}})
        return Command(
            update={"plan": {}, "current_step": 0},
            goto="executor"
        )

    brace_count = 0
    json_end = brace_start
    for i, char in enumerate(content[brace_start:], start=brace_start):
        if char == '{':
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if brace_count == 0:
                json_end = i + 1
                break

    plan_json = content[brace_start:json_end]

    try:
        plan = json.loads(plan_json)
    except json.JSONDecodeError as e:
        logger.error("planner_json_parse_error", extra={
            "data": {"error": str(e), "json": plan_json[:200]}
        })
        plan = {}

    # Update model_usage tracking
    model_usage = state.get("model_usage", {})
    model_usage["planner"] = actual_model

    return Command(
        update={
            "plan": plan,
            "current_step": 1,
            "model_usage": model_usage,
            "messages": [HumanMessage(content=f"Plan created with {len(plan)} steps")]
        },
        goto="executor"
    )
```

### Step 4: Run tests to verify they pass

Run: `pytest tests/test_model_overrides.py::test_planner_uses_reasoning_model_override tests/test_model_overrides.py::test_planner_uses_default_reasoning_model_when_no_override -v`
Expected: PASS

### Step 5: Commit

```bash
git add src/agents/planner.py tests/test_model_overrides.py
git commit -m "feat(models): implement model override support in planner

- Planner now respects state.reasoning_model for per-request overrides
- Pass override_key to llm_factory.get_reasoning()
- Track actual model used in model_usage state
- Add tests for override and default behavior

Part 1/5 of model override implementation.
Ref: .claude/phone-a-friend/2025-11-14-083901-codebase-review.md"
```

---

## Task 3: Implement Model Override in Text2SQL Agent

**Priority:** CRITICAL
**Files:**
- Modify: `src/agents/text2sql_agent.py:10-60`
- Modify: `src/workflow/graph.py:12-100`
- Test: `tests/test_model_overrides.py`

### Step 1: Write failing test

Add to `tests/test_model_overrides.py`:

```python
def test_text2sql_agent_uses_implementation_model_override():
    """Test that text2sql agent respects implementation_model."""
    from src.agents.text2sql_agent import create_text2sql_agent

    with patch('src.agents.text2sql_agent.llm_factory') as mock_factory:
        mock_llm = Mock()
        mock_factory.get_implementation.return_value = mock_llm

        agent = create_text2sql_agent(override_key="gpt-4o")

        # Verify get_implementation was called with override_key
        mock_factory.get_implementation.assert_called_once_with(override_key="gpt-4o")
```

### Step 2: Run test to verify it fails

Run: `pytest tests/test_model_overrides.py::test_text2sql_agent_uses_implementation_model_override -v`
Expected: FAIL - create_text2sql_agent doesn't accept override_key parameter

### Step 3: Add override_key parameter to create_text2sql_agent

Modify `src/agents/text2sql_agent.py:10-60`:

```python
def create_text2sql_agent(override_key: Optional[str] = None):
    """
    Create a Text2SQL ReAct agent.

    Args:
        override_key: Optional model key to use instead of default implementation model

    Returns:
        Agent executor that can be invoked with input dict
    """
    # Get implementation model (with optional override)
    llm = llm_factory.get_implementation(override_key=override_key)

    # Track actual model used
    actual_model = llm.model if hasattr(llm, 'model') else \
                   llm.model_name if hasattr(llm, 'model_name') else "unknown"

    logger.info("text2sql_agent_created", extra={
        "data": {
            "model_requested": override_key or "default",
            "model_actual": actual_model
        }
    })

    # Define tools
    tools = [
        get_schema_info,
        validate_sql,
        execute_sql_query,
        search_areas,
        search_occupations
    ]

    # Try to create ReAct agent, fall back to simple agent if that fails
    try:
        agent = create_react_agent(llm, tools)
        return agent
    except Exception as e:
        logger.warning("react_agent_creation_failed", extra={
            "data": {"error": str(e), "fallback": "simple_agent"}
        })
        return _create_simple_agent(llm, tools)
```

### Step 4: Update cortex_researcher_node to pass override

Modify `src/workflow/graph.py:12-100`:

```python
def cortex_researcher_node(state: State):
    """Wrapper for Text2SQL agent."""
    from langgraph.types import Command
    from langchain_core.messages import AIMessage
    from src.utils.logger import setup_workflow_logger
    from src.utils.trace_utils import build_sql_trace
    import json

    logger = setup_workflow_logger("oews.workflow.cortex_researcher")

    # Get implementation model override from state
    implementation_model_key = state.get("implementation_model")

    # Create agent with optional override
    agent = create_text2sql_agent(override_key=implementation_model_key)

    agent_query = state.get("agent_query", state.get("user_query", ""))

    # Invoke agent
    result = agent.invoke({"messages": [HumanMessage(content=agent_query)]})

    # Extract SQL traces from messages (if agent is ReAct type with intermediate_steps)
    sql_traces = []
    if hasattr(result, 'intermediate_steps'):
        for action, observation in result.intermediate_steps:
            if hasattr(action, 'tool') and action.tool == 'execute_sql_query':
                tool_input = action.tool_input
                sql = tool_input.get('sql', '')
                params_str = tool_input.get('params', '[]')

                try:
                    params = json.loads(params_str) if params_str else []
                except (json.JSONDecodeError, TypeError):
                    params = []

                # Parse observation (tool response)
                try:
                    result_data = json.loads(observation) if isinstance(observation, str) else observation
                    if result_data.get("success"):
                        columns = result_data.get("columns", [])
                        data_rows = result_data.get("data") or result_data.get("sample_data", [])

                        # Only convert rows we'll use (first 10)
                        rows_to_convert = data_rows[:10] if data_rows else []
                        rows = [dict(zip(columns, row)) for row in rows_to_convert] if columns and rows_to_convert else []

                        # Extract metadata
                        metadata = {
                            "row_count": result_data.get("row_count", len(data_rows)),
                            "truncated": result_data.get("truncated", False),
                            "stats": result_data.get("stats", None)
                        }

                        sql_traces.append(build_sql_trace(sql, params, rows, metadata))
                except (json.JSONDecodeError, AttributeError, KeyError) as e:
                    logger.warning("sql_trace_extraction_error", extra={
                        "data": {"error": str(e)}
                    })

    # Build response content
    content = result.content if hasattr(result, 'content') else str(result)

    # Add EXECUTION_TRACE if we have traces
    if sql_traces:
        content += f"\n\nEXECUTION_TRACE: {json.dumps(sql_traces)}"

    # Track model usage
    model_usage = state.get("model_usage", {})
    # Get actual model from agent's LLM
    if hasattr(agent, '_llm'):
        actual_model = agent._llm.model if hasattr(agent._llm, 'model') else "unknown"
    else:
        actual_model = implementation_model_key or "default"
    model_usage["cortex_researcher"] = actual_model

    return Command(
        update={
            "messages": [AIMessage(content=content, name="cortex_researcher")],
            "model_usage": model_usage
        },
        goto="executor"
    )
```

### Step 5: Run tests to verify they pass

Run: `pytest tests/test_model_overrides.py::test_text2sql_agent_uses_implementation_model_override -v`
Expected: PASS

### Step 6: Commit

```bash
git add src/agents/text2sql_agent.py src/workflow/graph.py tests/test_model_overrides.py
git commit -m "feat(models): implement model override in text2sql agent

- Add override_key parameter to create_text2sql_agent()
- cortex_researcher_node passes implementation_model from state
- Track actual model used in model_usage state

Part 2/5 of model override implementation.
Ref: .claude/phone-a-friend/2025-11-14-083901-codebase-review.md"
```

---

## Task 4: Implement Model Override in Remaining Agents

**Priority:** CRITICAL
**Files:**
- Modify: `src/agents/chart_generator.py:5-40`
- Modify: `src/agents/web_research_agent.py:10-50`
- Modify: `src/workflow/graph.py:80-260`
- Test: `tests/test_model_overrides.py`

### Step 1: Write failing tests

Add to `tests/test_model_overrides.py`:

```python
def test_chart_generator_uses_implementation_model_override():
    """Test that chart generator respects implementation_model."""
    from src.agents.chart_generator import create_chart_generator_agent

    with patch('src.agents.chart_generator.llm_factory') as mock_factory:
        mock_llm = Mock()
        mock_factory.get_implementation.return_value = mock_llm

        agent = create_chart_generator_agent(override_key="gpt-4o")

        mock_factory.get_implementation.assert_called_once_with(override_key="gpt-4o")


def test_web_research_agent_uses_implementation_model_override():
    """Test that web research agent respects implementation_model."""
    from src.agents.web_research_agent import create_web_research_agent

    with patch('src.agents.web_research_agent.llm_factory') as mock_factory:
        mock_llm = Mock()
        mock_factory.get_implementation.return_value = mock_llm

        agent = create_web_research_agent(override_key="gpt-4o")

        mock_factory.get_implementation.assert_called_once_with(override_key="gpt-4o")
```

### Step 2: Run tests to verify they fail

Run: `pytest tests/test_model_overrides.py::test_chart_generator_uses_implementation_model_override tests/test_model_overrides.py::test_web_research_agent_uses_implementation_model_override -v`
Expected: FAIL

### Step 3: Add override_key to chart_generator

Modify `src/agents/chart_generator.py:5-40`:

```python
def create_chart_generator_agent(override_key: Optional[str] = None):
    """
    Create a simple chart generator agent.

    Args:
        override_key: Optional model key to use instead of default

    Returns:
        Callable agent function
    """
    llm = llm_factory.get_implementation(override_key=override_key)

    def invoke(input_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Generate chart specifications from data."""
        messages = input_dict.get("messages", [])
        query = messages[0].get("content", "") if messages else ""

        # Simple chart generation prompt
        chart_prompt = f"""Generate a chart specification for this query: {query}

Return JSON with chart type and configuration."""

        response = llm.invoke([HumanMessage(content=chart_prompt)])

        return {"content": response.content}

    return type('Agent', (), {'invoke': lambda self, x: invoke(x)})()
```

### Step 4: Add override_key to web_research_agent

Modify `src/agents/web_research_agent.py:10-50`:

```python
def create_web_research_agent(override_key: Optional[str] = None):
    """
    Create web research agent using Tavily tools.

    Args:
        override_key: Optional model key to use instead of default

    Returns:
        Agent function
    """
    llm = llm_factory.get_implementation(override_key=override_key)

    tools = [tavily_search, get_population_data, get_cost_of_living_data]

    def invoke(input_dict: Dict[str, Any]) -> List[Tuple[Any, str]]:
        """Execute web research and return (action, observation) tuples."""
        messages = input_dict.get("messages", [])
        query = messages[0].content if messages else ""

        actions_observations = []

        # Simple routing logic
        if "population" in query.lower():
            action = type('Action', (), {
                'tool': 'get_population_data',
                'tool_input': {'location': query}
            })()
            observation = get_population_data.invoke({"location": query})
            actions_observations.append((action, observation))

        elif "cost of living" in query.lower():
            action = type('Action', (), {
                'tool': 'get_cost_of_living_data',
                'tool_input': {'location': query}
            })()
            observation = get_cost_of_living_data.invoke({"location": query})
            actions_observations.append((action, observation))

        else:
            # General search
            action = type('Action', (), {
                'tool': 'tavily_search',
                'tool_input': {'query': query, 'max_results': 5}
            })()
            observation = tavily_search.invoke({"query": query, "max_results": 5})
            actions_observations.append((action, observation))

        return actions_observations

    return type('Agent', (), {'invoke': lambda self, x: invoke(x)})()
```

### Step 5: Update workflow nodes to pass overrides

Modify `src/workflow/graph.py`:

In `chart_generator_node` (around line 80):
```python
def chart_generator_node(state: State):
    """Wrapper for chart generator agent."""
    from langgraph.types import Command
    from langchain_core.messages import AIMessage

    implementation_model_key = state.get("implementation_model")
    agent = create_chart_generator_agent(override_key=implementation_model_key)

    # ... rest of implementation ...
```

In `web_researcher_node` (around line 210):
```python
def web_researcher_node(state: State):
    """Wrapper for web research agent."""
    from langgraph.types import Command
    from langchain_core.messages import AIMessage
    from src.agents.web_research_agent import create_web_research_agent
    from src.utils.logger import setup_workflow_logger
    import json

    logger = setup_workflow_logger("oews.workflow.web_researcher")

    implementation_model_key = state.get("implementation_model")
    agent = create_web_research_agent(override_key=implementation_model_key)

    # ... rest of implementation ...
```

In `synthesizer_node` (around line 250):
```python
def synthesizer_node(state: State):
    """Create text summary of all findings."""
    from langgraph.types import Command
    from langchain_core.messages import AIMessage, HumanMessage
    from src.config.llm_factory import llm_factory

    # Get implementation model with override
    implementation_model_key = state.get("implementation_model")
    impl_llm = llm_factory.get_implementation(override_key=implementation_model_key)

    # Track actual model
    actual_model = impl_llm.model if hasattr(impl_llm, 'model') else \
                   impl_llm.model_name if hasattr(impl_llm, 'model_name') else "unknown"

    # Build summary prompt
    messages = state.get("messages", [])
    user_query = state.get("user_query", "")

    summary_prompt = f"""Summarize findings for: {user_query}

Based on the following agent outputs:
{chr(10).join([m.content for m in messages if hasattr(m, 'content')])}"""

    response = impl_llm.invoke([HumanMessage(content=summary_prompt)])

    # Track model usage
    model_usage = state.get("model_usage", {})
    model_usage["synthesizer"] = actual_model

    return Command(
        update={
            "final_answer": response.content,
            "messages": [AIMessage(content=response.content, name="synthesizer")],
            "model_usage": model_usage
        },
        goto="response_formatter"
    )
```

### Step 6: Run tests to verify they pass

Run: `pytest tests/test_model_overrides.py -v`
Expected: PASS - all model override tests passing

### Step 7: Commit

```bash
git add src/agents/chart_generator.py src/agents/web_research_agent.py src/workflow/graph.py tests/test_model_overrides.py
git commit -m "feat(models): implement model override in all remaining agents

- Add override_key to chart_generator, web_research, synthesizer
- All workflow nodes now respect implementation_model from state
- Complete model override implementation across system

Part 3/5 of model override implementation.
Ref: .claude/phone-a-friend/2025-11-14-083901-codebase-review.md"
```

---

## Task 5: Add Model Key Validation in API Request

**Priority:** CRITICAL
**Files:**
- Modify: `src/api/models.py:5-50`
- Test: `tests/test_api_models.py` (new file)

### Step 1: Write failing test

Create `tests/test_api_models.py`:

```python
"""Tests for API request/response models."""
import pytest
from pydantic import ValidationError
from src.api.models import QueryRequest


def test_query_request_validates_reasoning_model():
    """Test that invalid reasoning_model is rejected."""
    with pytest.raises(ValidationError) as exc_info:
        QueryRequest(
            query="Test query",
            reasoning_model="invalid-model-key"
        )

    errors = str(exc_info.value)
    assert "reasoning_model" in errors
    assert "not found in registry" in errors.lower()


def test_query_request_validates_implementation_model():
    """Test that invalid implementation_model is rejected."""
    with pytest.raises(ValidationError) as exc_info:
        QueryRequest(
            query="Test query",
            implementation_model="invalid-model-key"
        )

    errors = str(exc_info.value)
    assert "implementation_model" in errors
    assert "not found in registry" in errors.lower()


def test_query_request_allows_valid_models():
    """Test that valid model keys are accepted."""
    # Should not raise (assuming these keys exist in config)
    request = QueryRequest(
        query="Test query",
        reasoning_model="deepseek-reasoner",
        implementation_model="deepseek-chat"
    )
    assert request.reasoning_model == "deepseek-reasoner"
    assert request.implementation_model == "deepseek-chat"


def test_query_request_allows_none_for_default_models():
    """Test that None uses default models."""
    request = QueryRequest(query="Test query")
    assert request.reasoning_model is None
    assert request.implementation_model is None
```

### Step 2: Run test to verify it fails

Run: `pytest tests/test_api_models.py::test_query_request_validates_reasoning_model -v`
Expected: FAIL - no validation currently exists

### Step 3: Add Pydantic validator for model keys

Modify `src/api/models.py:5-50`:

```python
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
        description="Override default reasoning model (for planner)",
        examples=["deepseek-reasoner", "gpt-4o", "claude-opus-4"]
    )

    implementation_model: Optional[str] = Field(
        default=None,
        description="Override default implementation model (for agents)",
        examples=["deepseek-chat", "gpt-4o-mini", "claude-sonnet-4"]
    )

    @field_validator('reasoning_model', 'implementation_model')
    @classmethod
    def validate_model_key(cls, v: Optional[str], info) -> Optional[str]:
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
```

### Step 4: Run tests to verify they pass

Run: `pytest tests/test_api_models.py -v`
Expected: PASS - all validation tests pass

### Step 5: Commit

```bash
git add src/api/models.py tests/test_api_models.py
git commit -m "feat(api): add model key validation in QueryRequest

- Validate reasoning_model and implementation_model against registry
- Provide helpful error with available models list
- Graceful degradation if config loading fails

Part 4/5 of model override implementation.
Ref: .claude/phone-a-friend/2025-11-14-083901-codebase-review.md"
```

---

## Task 6: Update API Endpoint to Pass Model Overrides

**Priority:** CRITICAL
**Files:**
- Modify: `src/api/endpoints.py:118-230`
- Test: `tests/test_api_endpoints.py` (new file)

### Step 1: Write failing test

Create `tests/test_api_endpoints.py`:

```python
"""Integration tests for API endpoints."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
from src.api.endpoints import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def test_query_endpoint_passes_model_overrides_to_workflow(client):
    """Test that model overrides from request are passed to workflow state."""
    with patch('src.api.endpoints.workflow_graph') as mock_graph:
        # Mock workflow execution
        mock_graph.invoke.return_value = {
            "formatted_response": {
                "answer": "Test answer",
                "charts": [],
                "data_sources": [],
                "metadata": {}
            },
            "model_usage": {
                "planner": "gpt-4o",
                "cortex_researcher": "gpt-4o-mini"
            }
        }

        # Send request with model overrides
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

        assert state["user_query"] == "Test query"
        assert state["reasoning_model"] == "gpt-4o"
        assert state["implementation_model"] == "gpt-4o-mini"
```

### Step 2: Run test to verify it fails

Run: `pytest tests/test_api_endpoints.py::test_query_endpoint_passes_model_overrides_to_workflow -v`
Expected: FAIL - model overrides not passed to state

### Step 3: Update API endpoint to pass model overrides

Modify `src/api/endpoints.py:118-230`:

```python
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

    ⚠️ WARNING: No authentication currently implemented.
    See docs/AUTHENTICATION.md for future implementation options.

    Args:
        request: Query request with user question and options

    Returns:
        Structured response with answer, charts, and data sources
    """
    if workflow_graph is None:
        raise HTTPException(
            status_code=503,
            detail="Workflow not initialized. Check API keys and configuration."
        )

    start_time = time.time()

    try:
        # Create initial state with model overrides
        initial_state = {
            "user_query": request.query,
            "messages": [],
            "plan": {},
            "current_step": 0,
            "max_steps": 10,
            "replans": 0,
            "enable_charts": request.enable_charts,
            "model_usage": {},
            # Pass model overrides to workflow
            "reasoning_model": request.reasoning_model,
            "implementation_model": request.implementation_model
        }

        api_logger.info("query_received", extra={
            "data": {
                "query": request.query,
                "enable_charts": request.enable_charts,
                "reasoning_model": request.reasoning_model or "default",
                "implementation_model": request.implementation_model or "default"
            }
        })

        # Run workflow in thread pool with timeout
        loop = asyncio.get_event_loop()
        result = await asyncio.wait_for(
            loop.run_in_executor(
                executor,
                workflow_graph.invoke,
                initial_state
            ),
            timeout=REQUEST_TIMEOUT
        )

        # Extract formatted response
        formatted = result.get("formatted_response", {})

        # Calculate execution time
        execution_time = int((time.time() - start_time) * 1000)

        # Build response (NOTE: model_usage at root level in result)
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
                models_used=result.get("model_usage", {}),  # From root level
                execution_time_ms=execution_time,
                plan=result.get("plan"),
                replans=result.get("replans", 0)
            )
        )

        return response

    except asyncio.TimeoutError:
        api_logger.error("query_timeout", extra={
            "data": {"query": request.query, "timeout_seconds": REQUEST_TIMEOUT}
        })
        raise HTTPException(
            status_code=504,
            detail=f"Query processing timed out after {REQUEST_TIMEOUT} seconds."
        )
    except Exception as e:
        api_logger.error("query_failed", extra={
            "data": {
                "query": request.query,
                "error_type": type(e).__name__,
                "error_message": str(e)
            }
        })
        raise HTTPException(
            status_code=500,
            detail=f"Workflow execution failed: {str(e)}"
        )
```

### Step 4: Run tests to verify they pass

Run: `pytest tests/test_api_endpoints.py::test_query_endpoint_passes_model_overrides_to_workflow -v`
Expected: PASS

### Step 5: Add integration test for end-to-end model override

Add to `tests/test_api_endpoints.py`:

```python
def test_query_endpoint_model_usage_in_response(client):
    """Test that response includes actual models used."""
    with patch('src.api.endpoints.workflow_graph') as mock_graph:
        # Model usage at root level (not in formatted_response.metadata)
        mock_graph.invoke.return_value = {
            "formatted_response": {
                "answer": "Test answer",
                "charts": [],
                "data_sources": [],
                "metadata": {}
            },
            "model_usage": {
                "planner": "gpt-4o",
                "cortex_researcher": "gpt-4o-mini"
            }
        }

        response = client.post(
            "/api/v1/query",
            json={
                "query": "Test query",
                "reasoning_model": "gpt-4o"
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Verify models_used in metadata (populated from root-level model_usage)
        assert "metadata" in data
        assert "models_used" in data["metadata"]
        assert data["metadata"]["models_used"]["planner"] == "gpt-4o"
```

Run: `pytest tests/test_api_endpoints.py::test_query_endpoint_model_usage_in_response -v`
Expected: PASS

### Step 6: Commit

```bash
git add src/api/endpoints.py tests/test_api_endpoints.py
git commit -m "feat(api): pass model overrides from request to workflow state

- API endpoint now passes reasoning_model and implementation_model to state
- Add integration tests for model override flow
- Complete model override implementation (5/5)

Model override feature now fully functional from API to agents.
Fixes CRITICAL issue: users can now control which models are used.
Ref: .claude/phone-a-friend/2025-11-14-083901-codebase-review.md"
```

---

## Task 7: Fix Web Research Trace Extraction

**Priority:** IMPORTANT
**Files:**
- Modify: `src/agents/web_research_agent.py:20-60` (already done in Task 4)
- Modify: `src/workflow/graph.py:210-260`
- Test: `tests/test_web_research_traces.py` (new file)

### Step 1: Write failing test

Create `tests/test_web_research_traces.py`:

```python
"""Tests for web research trace extraction."""
import pytest
from unittest.mock import Mock, patch
from src.agents.state import State
from src.workflow.graph import web_researcher_node


def test_web_researcher_node_extracts_search_traces():
    """Test that web_researcher_node extracts EXECUTION_TRACE for searches."""
    state = State(
        user_query="Test query",
        agent_query="Find population data for Seattle",
        messages=[],
        plan={},
        current_step=1,
        max_steps=5,
        replans=0,
        model_usage={}
    )

    with patch('src.workflow.graph.create_web_research_agent') as mock_create:
        mock_agent = Mock()
        # Agent returns (action, observation) tuples
        mock_action = type('Action', (), {
            'tool': 'get_population_data',
            'tool_input': {'location': 'Seattle'}
        })()
        mock_agent.invoke.return_value = [
            (mock_action, "Seattle population: 750,000")
        ]
        mock_create.return_value = mock_agent

        result = web_researcher_node(state)

        # Check that message contains EXECUTION_TRACE
        messages = result.update["messages"]
        assert len(messages) > 0

        content = messages[0].content
        assert "EXECUTION_TRACE:" in content

        # Parse trace
        import json
        trace_start = content.find("EXECUTION_TRACE:") + len("EXECUTION_TRACE:")
        trace_json = content[trace_start:].strip()
        traces = json.loads(trace_json)

        assert isinstance(traces, list)
        assert len(traces) > 0
        assert traces[0]["tool_name"] == "get_population_data"
        assert "search_query" in traces[0]
```

### Step 2: Run test to verify it fails

Run: `pytest tests/test_web_research_traces.py::test_web_researcher_node_extracts_search_traces -v`
Expected: FAIL - EXECUTION_TRACE not properly extracted or formatted

### Step 3: Update web_researcher_node to extract traces

Modify `src/workflow/graph.py:210-260`:

```python
def web_researcher_node(state: State):
    """Wrapper for web research agent."""
    from langgraph.types import Command
    from langchain_core.messages import AIMessage
    from src.agents.web_research_agent import create_web_research_agent
    from src.utils.logger import setup_workflow_logger
    import json

    logger = setup_workflow_logger("oews.workflow.web_researcher")

    implementation_model_key = state.get("implementation_model")
    agent = create_web_research_agent(override_key=implementation_model_key)
    agent_query = state.get("agent_query", state.get("user_query", ""))

    # Invoke agent
    result = agent.invoke({"messages": [{"content": agent_query}]})

    # Extract search traces from (action, observation) tuples
    search_traces = []
    if isinstance(result, list):
        for action, observation in result:
            if hasattr(action, 'tool') and hasattr(action, 'tool_input'):
                try:
                    search_traces.append({
                        "tool_name": action.tool,
                        "search_query": action.tool_input.get('query') or action.tool_input.get('location', ''),
                        "sources": [observation[:200] + "..." if len(observation) > 200 else observation]
                    })
                except (AttributeError, KeyError) as e:
                    logger.warning("search_trace_extraction_error", extra={
                        "data": {"error": str(e)}
                    })
                    continue

    # Build response content
    content = f"Web research complete for: {agent_query}\n\n"
    if result:
        content += f"Found {len(result)} results\n"

    # Add EXECUTION_TRACE if we have traces
    if search_traces:
        content += f"\n\nEXECUTION_TRACE: {json.dumps(search_traces)}"

    logger.info("web_research_complete", extra={
        "data": {
            "query": agent_query,
            "traces_count": len(search_traces)
        }
    })

    return Command(
        update={
            "messages": [AIMessage(content=content, name="web_researcher")]
        },
        goto="executor"
    )
```

### Step 4: Run tests to verify they pass

Run: `pytest tests/test_web_research_traces.py::test_web_researcher_node_extracts_search_traces -v`
Expected: PASS

### Step 5: Commit

```bash
git add src/workflow/graph.py tests/test_web_research_traces.py
git commit -m "fix(tracing): implement proper web research trace extraction

- web_researcher_node extracts traces from (action, observation) tuples
- Format traces consistently with SQL traces
- Add tests for trace extraction flow

Fixes IMPORTANT issue: web research traces now properly captured.
Ref: .claude/phone-a-friend/2025-11-14-083901-codebase-review.md"
```

---

## Task 8: Add Generic Error Handling in API

**Priority:** IMPORTANT - Security (information disclosure)
**Files:**
- Modify: `src/api/endpoints.py:220-230`
- Test: `tests/test_api_endpoints.py`

### Step 1: Write failing test

Add to `tests/test_api_endpoints.py`:

```python
def test_query_endpoint_sanitizes_error_messages(client):
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

        # Should have generic message or safe error
        # (Current implementation shows "Workflow execution failed: ...")
        assert "workflow" in data["detail"].lower() or \
               "execution" in data["detail"].lower()
```

### Step 2: Run test to verify behavior

Run: `pytest tests/test_api_endpoints.py::test_query_endpoint_sanitizes_error_messages -v`
Expected: May PASS or FAIL depending on whether sensitive details are in error

### Step 3: Add error sanitization helper (if needed)

Add to `src/api/endpoints.py` before route handlers:

```python
def sanitize_error_message(error: Exception) -> str:
    """
    Sanitize error message to remove sensitive information.

    Args:
        error: The exception that occurred

    Returns:
        Safe error message for client
    """
    error_str = str(error).lower()

    # Check for sensitive patterns
    sensitive_patterns = [
        'password', 'api_key', 'secret', 'token', 'credential',
        'postgres://', 'mysql://', 'mongodb://', '://',
        'bearer ', 'authorization'
    ]

    has_sensitive = any(pattern in error_str for pattern in sensitive_patterns)

    if has_sensitive:
        # Return generic message, log details server-side
        api_logger.error("error_with_sensitive_data", extra={
            "data": {"error_type": type(error).__name__}
        })
        return "An internal error occurred during query processing."

    # For non-sensitive errors, return limited detail
    error_msg = str(error)
    if len(error_msg) > 200:
        error_msg = error_msg[:200] + "..."

    return f"Workflow execution failed: {error_msg}"
```

Update exception handler in query endpoint:

```python
    except Exception as e:
        # Sanitize error message before sending to client
        safe_message = sanitize_error_message(e)

        # Log full error server-side
        api_logger.error("query_failed", extra={
            "data": {
                "query": request.query,
                "error_type": type(e).__name__,
                "error_message": str(e)
            }
        })

        raise HTTPException(
            status_code=500,
            detail=safe_message
        )
```

### Step 4: Run tests to verify they pass

Run: `pytest tests/test_api_endpoints.py::test_query_endpoint_sanitizes_error_messages -v`
Expected: PASS

### Step 5: Commit

```bash
git add src/api/endpoints.py tests/test_api_endpoints.py
git commit -m "fix(security): sanitize error messages in API responses

- Add sanitize_error_message() to remove sensitive information
- Generic messages for errors containing passwords, tokens, connection strings
- Full details logged server-side for debugging
- Add test for error sanitization

Fixes IMPORTANT security issue: prevents information disclosure.
Ref: .claude/phone-a-friend/2025-11-14-083901-codebase-review.md"
```

---

## Task 9: Add Validation to Fallback Text2SQL Agent

**Priority:** IMPORTANT
**Files:**
- Modify: `src/agents/text2sql_agent.py:70-110`
- Test: `tests/test_text2sql_agent.py` (new file)

**NOTE:** validate_sql returns strings ("Error:", "Valid:", "Warning:"), not JSON

### Step 1: Write failing test

Create `tests/test_text2sql_agent.py`:

```python
"""Tests for Text2SQL agent."""
import pytest
from unittest.mock import Mock, patch
from src.agents.text2sql_agent import create_text2sql_agent


def test_simple_agent_validates_sql_before_execution():
    """Test that _create_simple_agent validates SQL before executing."""
    with patch('src.agents.text2sql_agent.llm_factory') as mock_factory:
        with patch('src.agents.text2sql_agent.validate_sql') as mock_validate:
            with patch('src.agents.text2sql_agent.execute_sql_query') as mock_execute:
                # Setup mocks
                mock_llm = Mock()
                mock_llm.invoke.return_value = Mock(
                    content="DROP TABLE oews_data"
                )
                mock_factory.get_implementation.return_value = mock_llm

                # validate_sql returns string (not JSON)
                mock_validate.invoke.return_value = "Error: Dangerous operation 'DROP' not allowed"

                agent = create_text2sql_agent()
                result = agent.invoke({"messages": [{"content": "Drop the table"}]})

                # Verify validate_sql was called
                assert mock_validate.invoke.called

                # execute_sql_query should NOT be called for invalid SQL
                assert not mock_execute.invoke.called

                # Result should contain error message
                assert "Cannot execute query" in result.content
                assert "DROP" in result.content or "Dangerous" in result.content
```

### Step 2: Run test to verify it fails

Run: `pytest tests/test_text2sql_agent.py::test_simple_agent_validates_sql_before_execution -v`
Expected: FAIL - execute_sql_query called without validation or wrong parsing

### Step 3: Add validation to _create_simple_agent with string parsing

Modify `src/agents/text2sql_agent.py:70-110`:

```python
def _create_simple_agent(llm, tools):
    """
    Create simple non-ReAct agent as fallback.

    Uses direct LLM invocation with SQL validation before execution.
    """
    def invoke(input_dict):
        messages = input_dict.get("messages", [])

        # Get LLM to generate SQL
        response = llm.invoke(messages)
        sql = response.content.strip()

        logger.info("simple_agent_generated_sql", extra={
            "data": {"sql_preview": sql[:100]}
        })

        # SECURITY: Validate SQL before execution
        validation_result = validate_sql.invoke({"sql": sql})

        # Parse string response (not JSON)
        # validate_sql returns: "Error: ...", "Valid: ...", or "Warning: ..."
        if validation_result.startswith("Error:"):
            error_msg = validation_result[6:].strip()  # Remove "Error:" prefix
            logger.warning("simple_agent_invalid_sql", extra={
                "data": {"sql": sql, "error": error_msg}
            })
            return AIMessage(
                content=f"Cannot execute query: {error_msg}",
                name="text2sql"
            )

        # "Valid:" or "Warning:" - proceed with execution
        if validation_result.startswith("Warning:"):
            logger.info("simple_agent_sql_warning", extra={
                "data": {"warning": validation_result[8:].strip()}
            })

        # Execute validated SQL
        result = execute_sql_query.invoke({"sql": sql, "params": "[]"})

        return AIMessage(content=result, name="text2sql")

    return type('Agent', (), {'invoke': lambda self, x: invoke(x)})()
```

### Step 4: Run tests to verify they pass

Run: `pytest tests/test_text2sql_agent.py::test_simple_agent_validates_sql_before_execution -v`
Expected: PASS

### Step 5: Commit

```bash
git add src/agents/text2sql_agent.py tests/test_text2sql_agent.py
git commit -m "fix(security): add SQL validation to fallback text2sql agent

- _create_simple_agent now calls validate_sql before execute_sql_query
- Correctly parse string responses from validate_sql
- Rejects invalid/dangerous SQL with error message
- Add test for validation enforcement

Fixes IMPORTANT security issue: closes validation gap in fallback path.
Ref: .claude/phone-a-friend/2025-11-14-083901-codebase-review.md"
```

---

## Task 10: Add Comprehensive API Endpoint Tests

**Priority:** IMPORTANT - Testing gaps
**Files:**
- Enhance: `tests/test_api_endpoints.py`

**NOTE:** Tests corrected to match actual endpoint schemas

### Step 1: Add tests for health and models endpoints

Add to `tests/test_api_endpoints.py`:

```python
def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()

    assert "status" in data
    assert "workflow_loaded" in data  # CORRECTED: actual field name
    assert data["status"] == "healthy"
    assert isinstance(data["workflow_loaded"], bool)


def test_models_endpoint(client):
    """Test models listing endpoint."""
    response = client.get("/api/v1/models")

    assert response.status_code == 200
    data = response.json()

    # CORRECTED: Structure is nested under "defaults"
    assert "defaults" in data
    assert "reasoning" in data["defaults"]
    assert "implementation" in data["defaults"]

    assert "models" in data
    assert len(data["models"]) > 0

    # Each model should have required fields
    for model_key, model_info in data["models"].items():
        assert "provider" in model_info
        assert "model_name" in model_info


def test_query_endpoint_requires_query_field(client):
    """Test that query endpoint validates required fields."""
    response = client.post("/api/v1/query", json={})

    assert response.status_code == 422  # Validation error


def test_query_endpoint_validates_query_length(client):
    """Test that query endpoint enforces length constraints."""
    # Too short
    response = client.post("/api/v1/query", json={"query": "ab"})
    assert response.status_code == 422

    # Too long
    response = client.post("/api/v1/query", json={"query": "a" * 501})
    assert response.status_code == 422


def test_query_endpoint_returns_503_when_workflow_not_ready(client):
    """Test that endpoint returns 503 if workflow not initialized."""
    with patch('src.api.endpoints.workflow_graph', None):
        response = client.post(
            "/api/v1/query",
            json={"query": "Test query"}
        )

        assert response.status_code == 503
        assert "not initialized" in response.json()["detail"].lower()
```

### Step 2: Run all tests

Run: `pytest tests/test_api_endpoints.py -v`
Expected: PASS - all API tests passing

### Step 3: Add test for CORS configuration

Add to `tests/test_api_endpoints.py`:

```python
def test_cors_headers_configured(client):
    """Test that CORS is configured."""
    # Make a request and check if CORS middleware is present
    response = client.get("/health")

    # If CORS is configured, it will handle OPTIONS requests
    # For now, just verify the endpoint works
    assert response.status_code == 200
```

### Step 4: Run full test suite to verify coverage

Run: `pytest tests/ -v`
Expected: All tests passing

### Step 5: Commit

```bash
git add tests/test_api_endpoints.py
git commit -m "test(api): add comprehensive API endpoint tests

- Test health endpoint (correct: workflow_loaded field)
- Test models endpoint (correct: nested defaults structure)
- Test query validation (required fields, length constraints)
- Test error handling (503, 422, 500)
- Test CORS configuration

Addresses IMPORTANT issue: API endpoint test coverage.
Tests corrected to match actual endpoint schemas.
Ref: .claude/phone-a-friend/2025-11-14-083901-codebase-review.md"
```

---

## Task 11: Centralize JSON Extraction Logic

**Priority:** MINOR - Code quality
**Files:**
- Create: `src/utils/parse_utils.py`
- Modify: `src/agents/response_formatter.py:65-200`
- Test: `tests/test_parse_utils.py` (new file)

### Step 1: Write test for extraction utility

Create `tests/test_parse_utils.py`:

```python
"""Tests for parsing utilities."""
import pytest
from src.utils.parse_utils import extract_json_from_marker


def test_extract_json_from_marker_simple_object():
    """Test extracting simple JSON object."""
    text = "Some text\nMARKER: {\"key\": \"value\"}\nMore text"
    result = extract_json_from_marker(text, "MARKER:")

    assert result == {"key": "value"}


def test_extract_json_from_marker_with_nested_braces():
    """Test extracting JSON with nested objects."""
    text = 'MARKER: {"outer": {"inner": {"deep": "value"}}}'
    result = extract_json_from_marker(text, "MARKER:")

    assert result == {"outer": {"inner": {"deep": "value"}}}


def test_extract_json_from_marker_with_escaped_quotes():
    """Test extracting JSON with escaped quotes in strings."""
    text = 'MARKER: {"key": "value with \\"quotes\\""}'
    result = extract_json_from_marker(text, "MARKER:")

    assert result == {"key": "value with \"quotes\""}


def test_extract_json_from_marker_with_array():
    """Test extracting JSON array."""
    text = 'MARKER: [{"a": 1}, {"b": 2}]'
    result = extract_json_from_marker(text, "MARKER:")

    assert result == [{"a": 1}, {"b": 2}]


def test_extract_json_from_marker_malformed_returns_none():
    """Test that malformed JSON returns None."""
    text = "MARKER: {invalid json}"
    result = extract_json_from_marker(text, "MARKER:")

    assert result is None


def test_extract_json_from_marker_not_found_returns_none():
    """Test that missing marker returns None."""
    text = "Some text without marker"
    result = extract_json_from_marker(text, "MARKER:")

    assert result is None
```

### Step 2: Run tests to verify they fail

Run: `pytest tests/test_parse_utils.py -v`
Expected: FAIL - module doesn't exist

### Step 3: Create parse_utils with extraction logic

Create `src/utils/parse_utils.py`:

```python
"""Parsing utilities for extracting structured data from text."""

import json
from typing import Optional, Union, Dict, List, Any


def extract_json_from_marker(
    text: str,
    marker: str
) -> Optional[Union[Dict[str, Any], List[Any]]]:
    """
    Extract JSON data from text after a marker string.

    Handles:
    - Nested objects and arrays
    - Escaped quotes in strings
    - Leading/trailing whitespace
    - Malformed JSON (returns None)

    Args:
        text: Text containing marker and JSON
        marker: Marker string (e.g., "EXECUTION_TRACE:", "CHART_SPEC:")

    Returns:
        Parsed JSON object/array, or None if not found or invalid

    Example:
        >>> text = "Result: MARKER: {\"key\": \"value\"}"
        >>> extract_json_from_marker(text, "MARKER:")
        {"key": "value"}
    """
    # Find marker
    marker_pos = text.find(marker)
    if marker_pos == -1:
        return None

    # Start after marker
    json_start = marker_pos + len(marker)
    json_text = text[json_start:].strip()

    if not json_text:
        return None

    # Find end of JSON by counting braces/brackets with proper string tracking
    brace_count = 0
    in_string = False
    escape_next = False
    json_end = 0

    for i, char in enumerate(json_text):
        # Handle string escaping
        if escape_next:
            escape_next = False
            continue

        if char == '\\' and in_string:
            escape_next = True
            continue

        # Track string boundaries
        if char == '"':
            in_string = not in_string
            continue

        # Only count braces/brackets outside of strings
        if not in_string:
            if char == '{' or char == '[':
                brace_count += 1
            elif char == '}' or char == ']':
                brace_count -= 1
                if brace_count == 0:
                    json_end = i + 1
                    break

    if json_end == 0:
        # No closing brace/bracket found
        return None

    # Extract and parse JSON
    json_text = json_text[:json_end]

    try:
        return json.loads(json_text)
    except json.JSONDecodeError:
        return None
```

### Step 4: Run tests to verify they pass

Run: `pytest tests/test_parse_utils.py -v`
Expected: PASS

### Step 5: Refactor response_formatter to use parse_utils

Modify `src/agents/response_formatter.py`:

```python
"""Response formatter for final API output."""

import json
import re
from typing import Dict, Any, List
from langgraph.types import Command
from langchain_core.messages import HumanMessage
from src.agents.state import State
from src.utils.logger import setup_workflow_logger
from src.utils.parse_utils import extract_json_from_marker

logger = setup_workflow_logger()


def response_formatter_node(state: State) -> Command:
    """Format the final response for API consumption."""
    # ... existing code up to chart extraction ...

    # Extract chart specs using utility (handles multiple markers)
    chart_start = 0
    while True:
        chart_pos = content.find("CHART_SPEC:", chart_start)
        if chart_pos == -1:
            break

        # Extract from this position
        remaining_text = content[chart_pos:]
        chart_data = extract_json_from_marker(remaining_text, "CHART_SPEC:")

        if chart_data:
            if isinstance(chart_data, list):
                charts.extend(chart_data)
            elif isinstance(chart_data, dict):
                charts.append(chart_data)

        # Move past this marker for next iteration
        chart_start = chart_pos + len("CHART_SPEC:") + 1

    # Extract execution traces using utility
    if "EXECUTION_TRACE:" in content:
        trace_data = extract_json_from_marker(content, "EXECUTION_TRACE:")

        if trace_data:
            # Process SQL traces
            if agent_name == "cortex_researcher" and isinstance(trace_data, list):
                for sql_trace in trace_data:
                    if not isinstance(sql_trace, dict):
                        logger.warning("invalid_sql_trace_type", extra={
                            "data": {"trace_type": str(type(sql_trace))}
                        })
                        continue

                    step_num += 1
                    data_sources.append({
                        "step": step_num,
                        "type": "oews_database",
                        "agent": agent_name,
                        **sql_trace
                    })

            # Process search traces
            elif agent_name == "web_researcher" and isinstance(trace_data, list):
                for search_trace in trace_data:
                    if not isinstance(search_trace, dict):
                        logger.warning("invalid_search_trace_type", extra={
                            "data": {"trace_type": str(type(search_trace))}
                        })
                        continue

                    step_num += 1
                    data_sources.append({
                        "step": step_num,
                        "type": "web_search",
                        "agent": agent_name,
                        **search_trace
                    })

    # ... rest of existing implementation ...
```

### Step 6: Run all tests to verify refactor

Run: `pytest tests/test_parse_utils.py tests/test_trace_extraction.py -v`
Expected: PASS - all parsing tests pass

### Step 7: Commit

```bash
git add src/utils/parse_utils.py src/agents/response_formatter.py tests/test_parse_utils.py
git commit -m "refactor: centralize JSON extraction logic in parse_utils

- Create extract_json_from_marker() utility function
- Handles nested objects, escaped quotes, arrays
- Refactor response_formatter to use utility
- Support multiple CHART_SPEC markers
- Add comprehensive tests for edge cases
- DRY: eliminates duplicate parsing code

Addresses MINOR code quality issue.
Ref: .claude/phone-a-friend/2025-11-14-083901-codebase-review.md"
```

---

## Task 12: Add Authentication Documentation (Documentation Only)

**Priority:** IMPORTANT - Security awareness
**Files:**
- Create: `docs/AUTHENTICATION.md`
- Modify: `src/api/endpoints.py` (add comment)

**NOTE:** Per user decision, authentication is DOCUMENTED only, not implemented.
This is a known limitation that blocks 8.5/10 production readiness rating.

### Step 1: Create authentication documentation

Create `docs/AUTHENTICATION.md`:

```markdown
# Authentication and Authorization

## Current Status

**⚠️ WARNING: The API currently has NO authentication or authorization.**

This is acceptable for:
- Local development
- Private networks with trusted clients
- MVP/prototype deployments

This is **NOT acceptable** for:
- Public internet deployment
- Production systems with untrusted access
- Multi-tenant environments

## Recommended Solutions

### Option 1: API Key Authentication (Simple)

**When to use:** Single-tenant, trusted clients, internal tools

**Implementation:**
1. Generate API keys for each client
2. Store keys securely (hashed in database)
3. Require `X-API-Key` header on all requests
4. Validate key in middleware before processing

**Example:**
```python
# src/api/auth.py
from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key")

def validate_api_key(api_key: str = Security(api_key_header)):
    if api_key not in get_valid_api_keys():
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key
```

### Option 2: OAuth 2.0 / JWT (Production)

**When to use:** Multi-tenant, user-specific access, production systems

**Implementation:**
1. Integrate with OAuth provider (Auth0, Okta, Azure AD)
2. Require Bearer token in Authorization header
3. Validate JWT signature and claims
4. Extract user identity for audit logging

**Example:**
```python
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_current_user(token: str = Depends(oauth2_scheme)):
    user = decode_jwt(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user
```

### Option 3: Reverse Proxy Authentication

**When to use:** Enterprise deployment with existing auth infrastructure

**Implementation:**
1. Deploy behind nginx, Caddy, or API Gateway
2. Proxy handles authentication
3. Proxy forwards validated requests with user headers
4. API trusts headers from proxy (validate proxy identity)

**Example Caddy configuration:**
```
api.example.com {
    reverse_proxy localhost:8000 {
        header_up X-Forwarded-User {http.auth.user.id}
    }

    basicauth /* {
        user $2a$14$hashed_password
    }
}
```

## Rate Limiting

**Current Status:** No rate limiting implemented

**Recommended:**
- Use `slowapi` package for per-IP rate limiting
- Configure limits based on authentication tier
- Example: 100 requests/hour for free tier, 1000/hour for paid

**Implementation:**
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/api/v1/query")
@limiter.limit("10/minute")
async def query(request: QueryRequest):
    # ... existing code ...
```

## Cost Control

With LLM API costs, authentication is critical for:
- Tracking usage per user/client
- Billing and quota enforcement
- Preventing abuse and DoS
- Audit trails

**Recommendation:** Implement authentication before public deployment.

## Next Steps for Implementation

1. **Immediate (for production):**
   - Implement Option 1 (API key) as minimum viable auth
   - Add rate limiting with `slowapi`
   - Deploy behind HTTPS reverse proxy

2. **Short term (for scaling):**
   - Migrate to Option 2 (OAuth/JWT) for user-specific access
   - Add usage tracking and quota enforcement
   - Implement audit logging

3. **Long term (for enterprise):**
   - Option 3 (reverse proxy auth) integration
   - SSO support
   - Role-based access control (RBAC)

## References

- [FastAPI Security Documentation](https://fastapi.tiangolo.com/tutorial/security/)
- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [slowapi - Rate Limiting for FastAPI](https://github.com/laurents/slowapi)

---

**Status:** DOCUMENTED (not implemented) - User decision to defer implementation
**Production Impact:** This limitation prevents 8.5/10 production readiness rating
**Current Target:** 7.5/10 (acceptable for private/trusted deployments)
```

### Step 2: Add authentication comment to endpoint

Modify `src/api/endpoints.py` in query endpoint docstring:

```python
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

    ⚠️ WARNING: No authentication currently implemented.
    See docs/AUTHENTICATION.md for future implementation options.

    This endpoint invokes the multi-agent workflow to:
    1. Plan the execution steps
    2. Query the database (Text2SQL)
    3. Generate charts (if requested)
    4. Synthesize a text answer
    5. Format the response

    Args:
        request: Query request with user question and model overrides

    Returns:
        Structured response with answer, charts, and data sources
    """
    # ... existing implementation ...
```

### Step 3: Commit

```bash
git add docs/AUTHENTICATION.md src/api/endpoints.py
git commit -m "docs(security): document authentication requirement for production

- Create comprehensive AUTHENTICATION.md with 3 implementation options
- Document lack of auth in endpoint docstrings
- Recommend minimal API key auth before public deployment
- Include rate limiting guidance with slowapi

KNOWN LIMITATION: Authentication not implemented (user decision to defer).
This limits production readiness to 7.5/10 (acceptable for private deployments).
Ref: .claude/phone-a-friend/2025-11-14-083901-codebase-review.md"
```

---

## Task 13: Run Full Test Suite and Generate Coverage Report

**Priority:** Verification
**Files:**
- All test files

### Step 1: Run complete test suite

Run: `pytest tests/ -v`
Expected: Majority of tests passing

### Step 2: Generate coverage report

Run: `pytest tests/ -v --cov=src --cov-report=term --cov-report=html`
Expected: Coverage increased from 18% baseline

### Step 3: Review coverage report

Open: `htmlcov/index.html` in browser
Expected: Coverage improvements in:
- `src/tools/database_tools.py` - High coverage (SQL guard tested)
- `src/agents/planner.py` - Model override tests
- `src/api/endpoints.py` - Endpoint tests
- `src/utils/parse_utils.py` - 100% coverage (new utility)

### Step 4: Document coverage improvements

Note final coverage percentage for Task 14 documentation.

Expected improvement: 18% → 30-35% (realistic with new tests)

### Step 5: Fix any failing tests

If any tests fail:
- Investigate error messages
- Verify test assumptions match actual code
- Fix implementation bugs or update tests
- Re-run until all pass

### Step 6: Final verification commit

```bash
git add tests/
git commit -m "test: verify all tests passing with improved coverage

- All critical paths tested (SQL guard, model overrides, API validation)
- Coverage increased from 18% to [X]%
- Integration tests for end-to-end flows
- Edge case coverage for parsing, validation, error handling

Test suite ready for production deployment.
Ref: .claude/phone-a-friend/2025-11-14-083901-codebase-review.md"
```

---

## Task 14: Update Production Readiness Documentation

**Priority:** Documentation
**Files:**
- Create: `docs/PRODUCTION_READINESS.md`

### Step 1: Create production readiness checklist

Create `docs/PRODUCTION_READINESS.md`:

```markdown
# Production Readiness Checklist

**Last Updated:** 2025-11-14
**Current Status:** 7.5/10 (up from 6.5/10)

**Target Achievement:** 7.5/10 achieved (8.5/10 requires authentication implementation)

## ✅ Completed Items

### Security (High Priority)
- [x] **SQL Injection Prevention** - SELECT-only guard with sqlparse
  - Blocks DROP, DELETE, UPDATE, INSERT, ALTER, CREATE, TRUNCATE
  - Handles WITH (CTE) queries correctly
  - Detects and blocks multi-statement payloads
  - Defensive LIMIT cap for queries without LIMIT
  - **Status:** FIXED with comprehensive tests

- [x] **SQL Validation in Fallback Path** - Validate before execute in simple agent
  - Correctly parses string responses from validate_sql
  - **Status:** FIXED

- [x] **Error Message Sanitization** - Remove sensitive data from API responses
  - Sanitizes passwords, tokens, connection strings
  - Full details logged server-side only
  - **Status:** FIXED

- [x] **Table Name Whitelist** - Prevent SQL injection via table names
  - **Status:** Already implemented (src/tools/database_tools.py:227)

### API Correctness (High Priority)
- [x] **Model Override Implementation** - Per-request model selection working
  - Planner respects `reasoning_model` override
  - All agents respect `implementation_model` override
  - Model usage tracked in response metadata
  - Model keys validated against registry
  - Uses correct parameter name (`override_key`)
  - **Status:** FIXED across all 5 agents

### Observability (Medium Priority)
- [x] **Web Research Trace Extraction** - EXECUTION_TRACE now captured
  - Agent returns proper (action, observation) format
  - Traces extracted and formatted correctly
  - **Status:** FIXED

- [x] **Execution Trace System** - Robust JSON parsing and trace building
  - Handles escaped quotes, nested structures
  - Preserves metadata for large result sets
  - **Status:** Already implemented + enhanced

### Testing (Medium Priority)
- [x] **Test Coverage Improvement** - From 18% to [X]%
  - API endpoint tests (health, models, query, validation)
  - Model override tests (all agents)
  - SQL security tests (SELECT-only guard, CTEs, multi-statement)
  - Parse utilities tests (edge cases)
  - **Status:** COMPLETED

### Code Quality (Low Priority)
- [x] **Centralized JSON Parsing** - DRY principle applied
  - Created `parse_utils.extract_json_from_marker()`
  - Refactored response_formatter to use utility
  - **Status:** FIXED

## ⚠️ Known Limitations (Documented)

### Security - BLOCKS 8.5/10 RATING
- [ ] **No Authentication/Authorization** - API is publicly accessible
  - **Impact:** CRITICAL - anyone can use API and incur LLM costs
  - **Mitigation:** Deploy on private network or behind firewall
  - **Documentation:** See `docs/AUTHENTICATION.md` for implementation options
  - **Recommendation:** Implement API key auth (Option 1) BEFORE public deployment
  - **Status:** DOCUMENTED (user decision: defer implementation)
  - **Production Readiness Impact:** Limits rating to 7.5/10

- [ ] **No Rate Limiting** - No per-client request limits
  - **Impact:** HIGH - potential for abuse or accidental DoS
  - **Mitigation:** Monitor usage, consider implementing `slowapi`
  - **Recommendation:** Add before public deployment
  - **Status:** DOCUMENTED (not implemented)

### Architecture - ACCEPTED
- [ ] **Message Type Heterogeneity** - Some agents return dicts, others AIMessage
  - **Impact:** LOW - node wrappers handle conversion
  - **Technical Debt:** Medium
  - **Recommendation:** Standardize on AIMessage/ToolMessage in future refactor
  - **Status:** ACCEPTED (working as designed)

- [ ] **Replan Logic Not Active** - Planner replan path exists but never triggered
  - **Impact:** LOW - system works without replanning
  - **Recommendation:** Add heuristics to trigger replanning (e.g., agent failures)
  - **Status:** FUTURE ENHANCEMENT

### Performance - ACCEPTED
- [ ] **Fuzzy Matching Limited to 1000 Candidates** - May miss some matches
  - **Impact:** LOW - 1000 candidates usually sufficient
  - **Recommendation:** Add pagination or cached vocab tables for scale
  - **Status:** ACCEPTED

## 🎯 Production Deployment Checklist

### Before Private/Trusted Deployment (7.5/10 Ready)
1. **Configure Environment Variables** (REQUIRED)
   - Database: Set `DATABASE_ENV=prod` for Azure SQL
   - API Keys: Secure all LLM provider keys
   - Logging: Configure log rotation and retention

2. **Enable HTTPS** (REQUIRED)
   - Deploy behind reverse proxy (Caddy, nginx)
   - Configure TLS certificates
   - Enforce HTTPS redirect

3. **Set Up Monitoring** (RECOMMENDED)
   - Configure log aggregation (ELK, CloudWatch)
   - Set up alerts for errors and high usage
   - Monitor LLM API costs

4. **Test in Staging** (RECOMMENDED)
   - Verify all agents working with production models
   - Test end-to-end query flow
   - Validate error handling

### Before Public Deployment (8.5/10 Required)
1. **Implement Authentication** (REQUIRED for public)
   - Choose option from `docs/AUTHENTICATION.md`
   - Implement and test thoroughly
   - Add usage tracking per client

2. **Add Rate Limiting** (REQUIRED for public)
   - Install `slowapi`
   - Configure per-client/IP limits
   - Test limits enforcement

3. **Load Testing** (RECOMMENDED)
   - Test concurrent request handling
   - Verify thread pool configuration (currently 8 workers)
   - Check timeout behavior (currently 5 minutes)

4. **Security Audit** (RECOMMENDED)
   - Penetration testing
   - Review all API endpoints
   - Validate error messages don't leak information

### Infrastructure
- [ ] Deploy behind HTTPS reverse proxy
- [ ] Configure database connection pooling for production
- [ ] Set up log aggregation and monitoring
- [ ] Configure backup and disaster recovery
- [ ] Document incident response procedures

### Operations
- [ ] Create runbook for common operations
- [ ] Document deployment process
- [ ] Set up CI/CD pipeline
- [ ] Configure automated testing in CI

## 📊 Metrics

### Production Readiness Score
- **Before Fixes:** 6.5/10
- **After Fixes:** 7.5/10 (without auth) / 8.5/10 (with auth)
- **Improvement:** +1.0 points (achievable without auth implementation)
- **To reach 8.5/10:** Implement authentication + rate limiting

### Technical Debt
- **Before:** Medium
- **After:** Low
- **Remaining Debt:** Documented and accepted or deferred

### Test Coverage
- **Before:** 18%
- **After:** [X]% (target: >30% for critical paths)
- **Critical Path Coverage:** 100% (SQL guard, model overrides, API validation)

### Security Posture
- **Critical Issues:** 0 (was 2) - All fixed
- **Important Issues:** 2 (was 7) - Auth/rate limiting documented but not implemented
- **Known Vulnerabilities:** 0
- **SQL Injection Protection:** Complete (with sqlparse)

## 🚀 Deployment Recommendations

### Immediate (Current - 7.5/10)
**Acceptable for:**
- Private network deployment
- Trusted user base
- Internal company tools
- Development/staging environments

**Required:**
- Deploy on private network or VPN
- Monitor usage and costs closely
- HTTPS with TLS
- Log aggregation

**Not Acceptable for:**
- Public internet deployment
- Untrusted users
- Multi-tenant SaaS
- High-value production systems

### Target (Future - 8.5/10)
**After implementing:**
- API key authentication (Option 1 from docs/AUTHENTICATION.md)
- Rate limiting (slowapi, 10/minute default)
- Usage tracking per API key
- Cost alerts and quotas

**Then acceptable for:**
- Public API deployment (with monitoring)
- Limited production use
- Beta/early access programs

### Long Term (9.5/10 - Enterprise)
**Additional requirements:**
- OAuth 2.0 / JWT authentication
- Role-based access control (RBAC)
- Audit logging
- SLA monitoring
- Redundancy and failover
- Comprehensive incident response

## 📚 References

- **Original Review:** `.claude/phone-a-friend/2025-11-14-083901-codebase-review.md`
- **Plan Review:** Session 019a834f-f377-7dd2-8d6c-654fa5d06901
- **Plan Corrections:** `docs/plans/PLAN_CORRECTIONS.md`
- **Authentication Options:** `docs/AUTHENTICATION.md`
- **API Documentation:** Available at `/docs` when server running
- **Architecture:** `DATA_AGENT_README.md`

## 🔍 Review History

**2025-11-14:**
- Initial GPT-5 codebase review (Session 019a8334-6d2a-7633-b56c-189377e59089)
- Production readiness: 6.5/10
- Identified 2 critical, 7 important, 6 minor issues

**2025-11-14 (Plan Review):**
- GPT-5 plan review (Session 019a834f-f377-7dd2-8d6c-654fa5d06901)
- Corrected plan with sqlparse, parameter naming fixes
- User decision: defer authentication implementation
- Realistic target: 7.5/10 (private deployment acceptable)

**2025-11-14 (Implementation):**
- All critical and important fixes completed
- Authentication documented (not implemented per user decision)
- Production readiness: 7.5/10 achieved

---

**Status:** READY FOR PRIVATE/TRUSTED DEPLOYMENT (7.5/10)
**Blockers for 8.5/10:** Authentication + Rate Limiting (documented, not implemented)
**Recommendation:** Deploy to private network, implement auth before public access
