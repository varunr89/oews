# Workflow Observability Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add comprehensive structured logging to debug Text2SQL agent and understand complete workflow execution flow.

**Architecture:** Use Python standard library logging with JSON formatter writing to rotating file logs. Add logging at all workflow nodes (Planner, Executor, agents) and tools to capture inputs, outputs, SQL queries, and routing decisions.

**Tech Stack:** Python 3.10+, logging module (stdlib), JSON formatting, RotatingFileHandler

---

## Task 1: Create Logger Utility Module

**Files:**
- Create: `src/utils/logger.py`
- Create: `tests/test_logger.py`
- Modify: `src/utils/__init__.py`

**Step 1: Write the failing test**

Create `tests/test_logger.py`:

```python
import json
import logging
from pathlib import Path
from src.utils.logger import setup_workflow_logger, JsonFormatter


def test_logger_creates_log_directory():
    """Test that logger creates logs directory."""
    logger = setup_workflow_logger()

    assert Path("logs").exists()
    assert logger is not None


def test_logger_writes_json_format():
    """Test that logger writes JSON formatted logs."""
    logger = setup_workflow_logger()

    # Clear existing handlers to avoid duplicates
    logger.handlers.clear()

    # Add a handler that writes to a test file
    from logging.handlers import RotatingFileHandler
    test_handler = RotatingFileHandler("logs/test.log", maxBytes=1000, backupCount=1)
    test_handler.setFormatter(JsonFormatter())
    logger.addHandler(test_handler)

    # Write a test log
    logger.debug("test_event", extra={"data": {"key": "value"}})

    # Read back and verify JSON format
    with open("logs/test.log") as f:
        log_line = f.readline()
        log_data = json.loads(log_line)

    assert log_data["level"] == "DEBUG"
    assert log_data["event"] == "test_event"
    assert log_data["data"]["key"] == "value"

    # Cleanup
    Path("logs/test.log").unlink(missing_ok=True)


def test_json_formatter_includes_timestamp():
    """Test that JSON formatter includes timestamp."""
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.DEBUG,
        pathname="",
        lineno=0,
        msg="test_message",
        args=(),
        exc_info=None
    )

    formatted = formatter.format(record)
    log_data = json.loads(formatted)

    assert "timestamp" in log_data
    assert "level" in log_data
    assert "component" in log_data
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_logger.py -v`

Expected: FAIL with "No module named 'src.utils.logger'"

**Step 3: Write minimal implementation**

Create `src/utils/logger.py`:

```python
"""Structured logging for workflow observability."""

import logging
import json
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict


class JsonFormatter(logging.Formatter):
    """Custom formatter that outputs logs as JSON."""

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.

        Args:
            record: Log record to format

        Returns:
            JSON string with timestamp, level, component, event, and optional data
        """
        log_data = {
            "timestamp": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "component": record.name,
            "event": record.getMessage(),
        }

        # Include extra data if provided
        if hasattr(record, 'data'):
            log_data['data'] = record.data

        return json.dumps(log_data)


def setup_workflow_logger(name: str = "oews.workflow") -> logging.Logger:
    """
    Set up structured logger for workflow debugging.

    Creates logs/ directory if it doesn't exist.
    Configures rotating file handler (10MB files, keep 5).

    Args:
        name: Logger name (default: oews.workflow)

    Returns:
        Configured logger instance
    """
    # Create logs directory
    Path("logs").mkdir(exist_ok=True)

    # Get or create logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Avoid adding duplicate handlers
    if logger.handlers:
        return logger

    # Create rotating file handler
    handler = RotatingFileHandler(
        "logs/workflow_debug.log",
        maxBytes=10_000_000,  # 10MB
        backupCount=5
    )

    # Set JSON formatter
    handler.setFormatter(JsonFormatter())

    # Add handler to logger
    logger.addHandler(handler)

    return logger
```

**Step 4: Update utils __init__.py**

Modify `src/utils/__init__.py`:

```python
"""Utility modules for OEWS Data Agent."""

from .fuzzy_matching import (
    fuzzy_match_area,
    fuzzy_match_occupation,
    get_best_matches
)

from .logger import (
    setup_workflow_logger,
    JsonFormatter
)

__all__ = [
    # Fuzzy matching
    "fuzzy_match_area",
    "fuzzy_match_occupation",
    "get_best_matches",
    # Logging
    "setup_workflow_logger",
    "JsonFormatter"
]
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/test_logger.py -v`

Expected: PASS (3 tests)

**Step 6: Commit**

```bash
git add src/utils/logger.py src/utils/__init__.py tests/test_logger.py
git commit -m "feat(utils): add structured JSON logger for workflow observability

- Create JsonFormatter for machine-readable logs
- Add setup_workflow_logger with rotating file handler
- Write to logs/workflow_debug.log (10MB files, keep 5)
- Include tests for logger configuration and JSON format"
```

---

## Task 2: Add Logging to Workflow Nodes

**Files:**
- Modify: `src/agents/planner.py`
- Modify: `src/agents/executor.py`
- Modify: `src/agents/response_formatter.py`

**Step 1: Add logging to Planner node**

Modify `src/agents/planner.py` - add at top:

```python
from src.utils.logger import setup_workflow_logger

logger = setup_workflow_logger()
```

Add logging after receiving user query (around line 30):

```python
def planner_node(state: State) -> Command[Literal['executor']]:
    """
    Runs the planning LLM and stores the resulting plan in state.
    """
    user_query = state.get("user_query", state["messages"][0].content)

    # LOG: Input query
    logger.debug("planner_input", extra={
        "data": {
            "user_query": user_query,
            "enabled_agents": state.get("enabled_agents", [])
        }
    })

    # Get reasoning model from factory
    reasoning_llm = llm_factory.get_reasoning()

    # ... existing code ...

    # Parse and validate JSON
    try:
        # ... existing parsing code ...
        parsed_plan = json.loads(json_str)

        # LOG: Generated plan
        logger.debug("planner_output", extra={
            "data": {
                "plan": parsed_plan,
                "steps": len(parsed_plan)
            }
        })

    except json.JSONDecodeError as e:
        logger.error("planner_parse_error", extra={
            "data": {
                "error": str(e),
                "content": llm_reply.content[:200]
            }
        })
        raise ValueError(f"Planner returned invalid JSON:\n{llm_reply.content}") from e
```

**Step 2: Add logging to Executor node**

Modify `src/agents/executor.py` - add at top:

```python
from src.utils.logger import setup_workflow_logger

logger = setup_workflow_logger()
```

Add logging for routing decisions (around line 50):

```python
def executor_node(state: State) -> Command[...]:
    """
    The Executor is the traffic cop of the workflow.
    """
    # LOG: Current state
    logger.debug("executor_state", extra={
        "data": {
            "current_step": state.get("current_step", 1),
            "replan_flag": state.get("replan_flag", False),
            "plan_steps": len(state.get("plan", {}))
        }
    })

    # 1. Check if we need to replan
    if should_replan(state):
        replans = state.get("replans", 0)

        logger.debug("executor_routing", extra={
            "data": {
                "decision": "replan",
                "replans": replans + 1,
                "reason": "replan_flag set"
            }
        })

        return Command(...)

    # ... existing code ...

    # 4. Route to the agent for current step
    target_agent = plan[step_key]["agent"]
    agent_query = build_agent_query(state)

    # LOG: Routing decision
    logger.debug("executor_routing", extra={
        "data": {
            "decision": "route_to_agent",
            "target_agent": target_agent,
            "step": current_step,
            "total_steps": len(plan),
            "agent_query": agent_query[:100] + "..." if len(agent_query) > 100 else agent_query
        }
    })

    goto_node = agent_mapping.get(target_agent, "response_formatter")

    return Command(...)
```

**Step 3: Add logging to Response Formatter**

Modify `src/agents/response_formatter.py` - add at top:

```python
from src.utils.logger import setup_workflow_logger

logger = setup_workflow_logger()
```

Add logging at end of function (around line 60):

```python
def response_formatter_node(state: State) -> Command[Literal["__end__"]]:
    """
    Formats the workflow results into structured JSON response.
    """
    # ... existing code ...

    # LOG: Final response
    logger.debug("response_formatter_output", extra={
        "data": {
            "answer_length": len(formatted_response.get("answer", "")),
            "charts_count": len(formatted_response.get("charts", [])),
            "data_sources_count": len(formatted_response.get("data_sources", [])),
            "models_used": formatted_response.get("metadata", {}).get("models_used", {})
        }
    })

    return Command(...)
```

**Step 4: Test workflow logging**

Run a query and check logs are created:

```bash
# Start server (if not running)
python -m src.main &

# Run a query
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "test query", "enable_charts": false}'

# Check logs were created
ls -lh logs/workflow_debug.log

# View logs
tail -20 logs/workflow_debug.log | jq .
```

Expected: See JSON logs with planner_input, planner_output, executor_routing events

**Step 5: Commit**

```bash
git add src/agents/planner.py src/agents/executor.py src/agents/response_formatter.py
git commit -m "feat(agents): add structured logging to workflow nodes

- Log planner input (query) and output (plan)
- Log executor routing decisions and state
- Log response formatter final output
- Include relevant data in each log entry"
```

---

## Task 3: Add Logging to Text2SQL Agent

**Files:**
- Modify: `src/agents/text2sql_agent.py`

**Step 1: Add logging to Text2SQL agent**

Modify `src/agents/text2sql_agent.py` - add at top:

```python
from src.utils.logger import setup_workflow_logger

logger = setup_workflow_logger("oews.workflow.text2sql")
```

Add logging throughout the invoke function:

```python
def invoke(input_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Simple agent that executes SQL queries."""
    messages = input_dict.get("messages", [])
    query = messages[0].get("content", "") if messages else ""

    # LOG: Agent input
    logger.debug("agent_input", extra={
        "data": {
            "query": query,
            "messages_count": len(messages)
        }
    })

    try:
        # Get schema
        schema = tools["get_schema_info"].invoke({})

        # LOG: Schema retrieved
        logger.debug("schema_retrieved", extra={
            "data": {
                "schema_length": len(schema)
            }
        })

        # Create a prompt for the LLM
        prompt = f"""..."""

        from langchain_core.messages import HumanMessage
        response = llm.invoke([HumanMessage(content=prompt)])

        sql_query = response.content.strip()

        # LOG: SQL generated
        logger.debug("sql_generated", extra={
            "data": {
                "sql": sql_query,
                "sql_length": len(sql_query)
            }
        })

        # Execute the query
        result = tools["execute_sql_query"].invoke({"sql": sql_query})

        # Parse result to get row count
        import json
        try:
            result_data = json.loads(result)
            row_count = result_data.get("row_count", 0)
            success = result_data.get("success", False)

            # LOG: Query results
            logger.debug("query_results", extra={
                "data": {
                    "success": success,
                    "row_count": row_count,
                    "result_preview": result[:200] + "..." if len(result) > 200 else result
                }
            })

        except json.JSONDecodeError:
            logger.warning("result_parse_error", extra={
                "data": {"result": result[:200]}
            })

        return {
            "messages": [AIMessage(content=f"Query result: {result}")],
            "intermediate_steps": []
        }

    except Exception as e:
        # LOG: Error
        logger.error("agent_error", extra={
            "data": {
                "error": str(e),
                "error_type": type(e).__name__
            }
        })

        return {
            "messages": [AIMessage(content=f"Error: {str(e)}")],
            "intermediate_steps": []
        }
```

**Step 2: Test Text2SQL logging**

Run a query and check for text2sql logs:

```bash
# Run query
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What are software developer salaries?", "enable_charts": false}'

# Filter for text2sql logs
grep '"component":"oews.workflow.text2sql"' logs/workflow_debug.log | jq .
```

Expected: See logs for agent_input, schema_retrieved, sql_generated, query_results

**Step 3: Commit**

```bash
git add src/agents/text2sql_agent.py
git commit -m "feat(agents): add detailed logging to Text2SQL agent

- Log agent input query
- Log schema retrieval
- Log generated SQL query
- Log query execution results with row count
- Log errors with context"
```

---

## Task 4: Add Logging to Database Tools

**Files:**
- Modify: `src/tools/database_tools.py`

**Step 1: Add logging to execute_sql_query tool**

Modify `src/tools/database_tools.py` - add at top:

```python
from src.utils.logger import setup_workflow_logger

logger = setup_workflow_logger("oews.workflow.tools")
```

Add logging to execute_sql_query (around line 120):

```python
@tool
def execute_sql_query(sql: str, params: Optional[str] = None) -> str:
    """
    Executes SQL query against OEWS database and returns results.
    """
    import json

    # LOG: SQL execution start
    logger.debug("sql_execution_start", extra={
        "data": {
            "sql": sql,
            "params": params,
            "has_params": params is not None
        }
    })

    try:
        # Parse params if provided
        params_tuple = None
        if params:
            params_list = json.loads(params)
            params_tuple = tuple(params_list)

            logger.debug("sql_params_parsed", extra={
                "data": {
                    "params_count": len(params_list),
                    "params": params_list
                }
            })

        db = OEWSDatabase()
        df = db.execute_query(sql, params=params_tuple)
        db.close()

        row_count = len(df)

        # LOG: Query success
        logger.debug("sql_execution_success", extra={
            "data": {
                "row_count": row_count,
                "columns": df.columns.tolist() if row_count > 0 else [],
                "sample_data": df.head(3).to_dict('records') if row_count > 0 else []
            }
        })

        # Handle large result sets
        if row_count > 1000:
            # ... existing code ...
            result = { ... }
        else:
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
        # LOG: Query error
        logger.error("sql_execution_error", extra={
            "data": {
                "error": str(e),
                "error_type": type(e).__name__,
                "sql": sql,
                "params": params
            }
        })

        result = {
            "success": False,
            "error": str(e),
            "sql": sql,
            "params": params
        }
        return json.dumps(result, indent=2)
```

**Step 2: Add logging to search tools**

Add logging to search_areas and search_occupations:

```python
@tool
def search_areas(search_term: str) -> List[str]:
    """
    Searches for geographic areas matching the search term.
    """
    import json
    from src.utils.fuzzy_matching import fuzzy_match_area

    # LOG: Search start
    logger.debug("search_areas_start", extra={
        "data": {"search_term": search_term}
    })

    # First try fuzzy matching for better results
    fuzzy_matches = fuzzy_match_area(search_term, limit=20)

    if fuzzy_matches:
        # LOG: Fuzzy matches found
        logger.debug("search_areas_fuzzy_match", extra={
            "data": {
                "matches_count": len(fuzzy_matches),
                "top_match": fuzzy_matches[0] if fuzzy_matches else None
            }
        })
        return [match["name"] for match in fuzzy_matches]

    # Fallback to SQL LIKE search
    logger.debug("search_areas_sql_fallback", extra={
        "data": {"reason": "no_fuzzy_matches"}
    })

    # ... existing SQL code ...
```

**Step 3: Test tool logging**

Run a query and check tool logs:

```bash
# Filter for tool logs
grep '"component":"oews.workflow.tools"' logs/workflow_debug.log | jq .
```

Expected: See sql_execution_start, sql_execution_success with sample data

**Step 4: Commit**

```bash
git add src/tools/database_tools.py
git commit -m "feat(tools): add detailed logging to database tools

- Log SQL execution with query and parameters
- Log query results with row count and sample data
- Log search tool invocations
- Log errors with full context"
```

---

## Task 5: Create Log Analysis Script

**Files:**
- Create: `scripts/analyze_workflow.py`

**Step 1: Create analysis script**

Create `scripts/analyze_workflow.py`:

```python
#!/usr/bin/env python3
"""Analyze workflow execution logs for debugging."""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime


def load_logs(log_file: str = "logs/workflow_debug.log", num_lines: int = None) -> List[Dict[str, Any]]:
    """
    Load logs from file.

    Args:
        log_file: Path to log file
        num_lines: Number of lines to load from end (None = all)

    Returns:
        List of parsed log entries
    """
    log_path = Path(log_file)

    if not log_path.exists():
        print(f"❌ Log file not found: {log_file}")
        return []

    with open(log_path) as f:
        lines = f.readlines()

    if num_lines:
        lines = lines[-num_lines:]

    logs = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            logs.append(json.loads(line))
        except json.JSONDecodeError:
            print(f"⚠️  Could not parse line: {line[:50]}...")

    return logs


def display_workflow_execution(logs: List[Dict[str, Any]]):
    """
    Display workflow execution in readable format.

    Args:
        logs: List of log entries
    """
    print("\n" + "=" * 100)
    print("WORKFLOW EXECUTION TRACE")
    print("=" * 100 + "\n")

    print(f"{'Component':<30} | {'Event':<35} | {'Data'}")
    print("-" * 100)

    for log in logs:
        component = log.get('component', 'unknown')
        event = log.get('event', 'unknown')
        data = log.get('data', {})

        # Format data for display
        if isinstance(data, dict):
            if 'sql' in data:
                data_str = f"SQL: {data['sql'][:50]}..."
            elif 'row_count' in data:
                data_str = f"Rows: {data['row_count']}"
            elif 'query' in data:
                data_str = f"Query: {data['query'][:50]}..."
            elif 'plan' in data:
                data_str = f"Plan: {len(data['plan'])} steps"
            else:
                data_str = str(data)[:50]
        else:
            data_str = str(data)[:50]

        # Truncate if too long
        if len(data_str) > 50:
            data_str = data_str[:47] + "..."

        print(f"{component:<30} | {event:<35} | {data_str}")


def analyze_text2sql_execution(logs: List[Dict[str, Any]]):
    """
    Analyze Text2SQL agent execution specifically.

    Args:
        logs: List of log entries
    """
    print("\n" + "=" * 100)
    print("TEXT2SQL AGENT ANALYSIS")
    print("=" * 100 + "\n")

    # Filter for text2sql logs
    text2sql_logs = [log for log in logs if 'text2sql' in log.get('component', '')]

    if not text2sql_logs:
        print("❌ No Text2SQL agent logs found")
        return

    for log in text2sql_logs:
        event = log.get('event', '')
        data = log.get('data', {})

        if event == 'agent_input':
            print(f"📥 INPUT QUERY:")
            print(f"   {data.get('query', 'N/A')}\n")

        elif event == 'sql_generated':
            print(f"🔍 GENERATED SQL:")
            print(f"   {data.get('sql', 'N/A')}\n")

        elif event == 'query_results':
            print(f"📊 QUERY RESULTS:")
            print(f"   Success: {data.get('success', False)}")
            print(f"   Row count: {data.get('row_count', 0)}")
            if data.get('row_count', 0) > 0:
                print(f"   Preview: {str(data.get('result_preview', ''))[:100]}...")
            print()


def compare_with_expected_sql(logs: List[Dict[str, Any]], expected_sql: str):
    """
    Compare generated SQL with expected SQL.

    Args:
        logs: List of log entries
        expected_sql: Expected SQL query
    """
    print("\n" + "=" * 100)
    print("SQL COMPARISON")
    print("=" * 100 + "\n")

    # Find generated SQL
    for log in logs:
        if log.get('event') == 'sql_generated':
            actual_sql = log.get('data', {}).get('sql', '')

            print("EXPECTED SQL:")
            print(expected_sql)
            print("\nACTUAL SQL:")
            print(actual_sql)
            print("\nMATCH:", "✅ YES" if actual_sql.strip() == expected_sql.strip() else "❌ NO")

            return

    print("❌ No SQL generation found in logs")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Analyze workflow execution logs")
    parser.add_argument("--lines", "-n", type=int, default=50, help="Number of log lines to analyze")
    parser.add_argument("--text2sql-only", action="store_true", help="Show only Text2SQL analysis")
    parser.add_argument("--compare-sql", type=str, help="Expected SQL to compare against")

    args = parser.parse_args()

    # Load logs
    logs = load_logs(num_lines=args.lines)

    if not logs:
        print("❌ No logs found")
        sys.exit(1)

    print(f"✅ Loaded {len(logs)} log entries")

    # Display based on options
    if args.text2sql_only:
        analyze_text2sql_execution(logs)
    else:
        display_workflow_execution(logs)
        analyze_text2sql_execution(logs)

    # Compare SQL if provided
    if args.compare_sql:
        compare_with_expected_sql(logs, args.compare_sql)


if __name__ == "__main__":
    main()
```

**Step 2: Make script executable**

```bash
chmod +x scripts/analyze_workflow.py
```

**Step 3: Test analysis script**

```bash
# Analyze last 30 log entries
python scripts/analyze_workflow.py -n 30

# Show only Text2SQL analysis
python scripts/analyze_workflow.py --text2sql-only

# Compare with expected SQL
python scripts/analyze_workflow.py --compare-sql "SELECT AREA_TITLE, A_MEDIAN FROM oews_data WHERE AREA_TITLE LIKE '%Seattle%'"
```

Expected: See formatted workflow trace and Text2SQL analysis

**Step 4: Commit**

```bash
git add scripts/analyze_workflow.py
git commit -m "feat(scripts): add workflow log analysis tool

- Parse and display workflow execution trace
- Analyze Text2SQL agent specifically
- Compare generated SQL with expected SQL
- Support filtering by component and event"
```

---

## Task 6: End-to-End Testing and Verification

**Files:**
- None (testing only)

**Step 1: Restart server with logging enabled**

```bash
# Stop old server
ps aux | grep -E "[p]ython.*src.main" | awk '{print $2}' | xargs kill

# Start server
python -m src.main &

# Wait for startup
sleep 5
```

**Step 2: Run test query**

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the median annual salary for software developers in Seattle, WA?", "enable_charts": false}'
```

**Step 3: Analyze logs**

```bash
# View raw logs
tail -50 logs/workflow_debug.log | jq .

# Use analysis script
python scripts/analyze_workflow.py -n 50
```

**Step 4: Extract key information**

```bash
# Find SQL query generated
grep '"event":"sql_generated"' logs/workflow_debug.log | tail -1 | jq .data.sql

# Find row count returned
grep '"event":"query_results"' logs/workflow_debug.log | tail -1 | jq .data.row_count

# Check planner output
grep '"event":"planner_output"' logs/workflow_debug.log | tail -1 | jq .data.plan
```

**Step 5: Compare with expected SQL**

Expected SQL for the query:
```sql
SELECT AREA_TITLE, OCC_TITLE, A_MEDIAN
FROM oews_data
WHERE AREA_TITLE LIKE '%Seattle%'
AND OCC_TITLE LIKE '%Software%'
AND A_MEDIAN IS NOT NULL
ORDER BY A_MEDIAN DESC
LIMIT 10
```

Compare:
```bash
python scripts/analyze_workflow.py --compare-sql "SELECT AREA_TITLE, OCC_TITLE, A_MEDIAN FROM oews_data WHERE AREA_TITLE LIKE '%Seattle%' AND OCC_TITLE LIKE '%Software%'"
```

**Step 6: Document findings**

Create `docs/debugging/2025-10-23-text2sql-analysis.md` with findings:
- What query was sent to Text2SQL agent
- What SQL was generated
- What data was returned (row count, sample)
- Comparison with expected SQL
- Root cause of issue

**Step 7: Commit**

```bash
git add docs/debugging/
git commit -m "docs: add Text2SQL debugging analysis from logs"
```

---

## Summary

This plan implements comprehensive workflow observability:

**What's Logged:**
1. ✅ Planner: Input query, generated plan
2. ✅ Executor: Routing decisions, current step
3. ✅ Text2SQL: Input, SQL generation, query results
4. ✅ Tools: SQL execution with params and results
5. ✅ Response Formatter: Final output

**How to Use:**
- Logs written to `logs/workflow_debug.log` (JSON format)
- Use `jq` to filter: `grep '"component":"text2sql"' logs/workflow_debug.log | jq .`
- Use analysis script: `python scripts/analyze_workflow.py`
- Compare SQL: `python scripts/analyze_workflow.py --compare-sql "..."`

**Next Steps After Implementation:**
1. Run test query
2. Analyze logs to find where Text2SQL fails
3. Compare generated SQL with expected SQL
4. Fix root cause based on findings

---

**Plan complete and saved to `docs/plans/2025-10-23-workflow-observability.md`**

**Two execution options:**

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task with code review between tasks for fast iteration

**2. Manual Execution** - You implement step-by-step following the plan

**Which approach would you like?**
