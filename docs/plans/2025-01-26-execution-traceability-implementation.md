# Execution Traceability Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add comprehensive execution tracing that captures SQL queries, web searches, and planning decisions to prove AI outputs are grounded in actual data.

**Architecture:** Enhance existing `data_sources` array by adding EXECUTION_TRACE markers to agent messages. Response formatter extracts these traces and builds detailed execution steps. Frontend displays traces in expandable accordion with syntax highlighting and data tables.

**Tech Stack:** Python (FastAPI, LangChain), TypeScript/React, react-syntax-highlighter

---

## Task 1: Add Planner Execution Trace

**Files:**
- Modify: `src/agents/planner.py:95-113`
- Test: Manual verification (planner integration test exists)

**Step 1: Add EXECUTION_TRACE to planner message**

In `src/agents/planner.py`, modify the Command return to include execution trace in the message content:

```python
# Around line 95, replace the return Command block
return Command(
    update={
        "plan": parsed_plan,
        "messages": [HumanMessage(
            content=f"{json.dumps(parsed_plan)}\n\nEXECUTION_TRACE: {json.dumps({'plan': parsed_plan, 'reasoning_model': model_key, 'steps': len(parsed_plan)})}",
            name="replan" if replan else "initial_plan"
        )],
        "user_query": state.get("user_query", state.get("messages", [{}])[0].content if state.get("messages") else ""),
        "current_step": 1 if not replan else state.get("current_step", 1),
        "replan_flag": False,
        "last_reason": "",
        "enabled_agents": state.get("enabled_agents", ["cortex_researcher", "synthesizer"]),
        "model_usage": {**(state.get("model_usage") or {}), "planner": model_key}
    },
    goto="executor"
)
```

**Step 2: Test planner trace**

Run API server and make a test query:

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the median salary for nurses in Seattle?", "enable_charts": false}'
```

Check logs for planner message containing EXECUTION_TRACE marker.

**Step 3: Commit**

```bash
git add src/agents/planner.py
git commit -m "feat(planner): add EXECUTION_TRACE marker to plan messages"
```

---

## Task 2: Add Cortex Researcher SQL Execution Trace

**Files:**
- Modify: `src/workflow/graph.py:12-56`
- Create: `src/utils/trace_utils.py`

**Step 2.1: Create trace utilities module**

Create `src/utils/trace_utils.py`:

```python
"""Utilities for building execution traces."""

import json
from typing import Any, Dict, List, Optional


def calculate_column_stats(rows: List[Dict[str, Any]], column: str) -> Optional[Dict[str, Any]]:
    """
    Calculate min/max/avg statistics for a numeric column.

    Args:
        rows: List of result rows
        column: Column name to analyze

    Returns:
        Dict with min, max, avg or None if column is not numeric
    """
    if not rows or column not in rows[0]:
        return None

    values = []
    for row in rows:
        val = row[column]
        # Try to convert to float
        try:
            if val is not None:
                values.append(float(val))
        except (ValueError, TypeError):
            return None  # Not numeric

    if not values:
        return None

    return {
        "min": min(values),
        "max": max(values),
        "avg": sum(values) / len(values)
    }


def build_sql_trace(sql: str, params: List[Any], rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Build execution trace for SQL query.

    Args:
        sql: SQL query string
        params: Query parameters
        rows: Query result rows

    Returns:
        Trace dict with sql, params, row_count, sample_data, stats
    """
    # Calculate statistics for numeric columns
    stats = {}
    if rows:
        for column in rows[0].keys():
            col_stats = calculate_column_stats(rows, column)
            if col_stats:
                stats[column] = col_stats

    return {
        "sql": sql,
        "params": params,
        "row_count": len(rows),
        "sample_data": rows[:10],  # First 10 rows
        "stats": stats if stats else None
    }
```

**Step 2.2: Add trace extraction to cortex_researcher_node**

In `src/workflow/graph.py`, modify `cortex_researcher_node` function (around line 12-56):

```python
def cortex_researcher_node(state: State):
    """Wrapper for Text2SQL agent."""
    from langgraph.types import Command
    from langchain_core.messages import AIMessage
    from src.utils.logger import setup_workflow_logger
    from src.utils.trace_utils import build_sql_trace
    import json

    logger = setup_workflow_logger("oews.workflow.cortex_researcher")

    agent = create_text2sql_agent()
    agent_query = state.get("agent_query", state.get("user_query", ""))

    # LOG: DIAGNOSTIC - Show what query cortex_researcher receives
    logger.debug("cortex_researcher_input", extra={
        "data": {
            "agent_query_from_state": state.get("agent_query", "NOT SET"),
            "user_query_from_state": state.get("user_query", ""),
            "current_step_from_state": state.get("current_step", 1),
            "actual_query_used": agent_query[:200] + "..." if len(agent_query) > 200 else agent_query
        }
    })

    # Run agent with correct input format
    result = agent.invoke({"messages": [{"role": "user", "content": agent_query}]})

    # LOG: Agent result structure
    logger.debug("agent_result", extra={
        "data": {
            "result_keys": list(result.keys()) if isinstance(result, dict) else "not a dict",
            "result_type": str(type(result)),
            "result_preview": str(result)[:500]
        }
    })

    # Extract final answer from messages
    if isinstance(result, dict) and "messages" in result:
        messages = result["messages"]
        if messages and len(messages) > 0:
            last_msg = messages[-1]
            response_content = last_msg.content if hasattr(last_msg, 'content') else str(last_msg)
        else:
            response_content = "No messages in result"
    else:
        response_content = result.get("output", "No result")

    # Extract SQL execution traces from intermediate_steps
    sql_traces = []
    intermediate_steps = result.get("intermediate_steps", [])

    for action, observation in intermediate_steps:
        # Check if this is an execute_sql_query tool call
        if hasattr(action, 'tool') and action.tool == "execute_sql_query":
            try:
                # Extract SQL and params from action
                sql = action.tool_input.get("sql", "")
                params_str = action.tool_input.get("params", "[]")
                params = json.loads(params_str) if params_str else []

                # Parse observation for results
                result_data = json.loads(observation) if isinstance(observation, str) else observation

                if result_data.get("success"):
                    rows = result_data.get("results", [])
                    sql_traces.append(build_sql_trace(sql, params, rows))
            except (json.JSONDecodeError, AttributeError, KeyError) as e:
                logger.warning("sql_trace_extraction_error", extra={
                    "data": {"error": str(e)}
                })
                continue

    # Add EXECUTION_TRACE to message content if we have traces
    if sql_traces:
        response_content = f"{response_content}\n\nEXECUTION_TRACE: {json.dumps(sql_traces)}"

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
```

**Step 2.3: Test cortex researcher trace**

Start server and test:

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the median salary for nurses in Seattle?", "enable_charts": false}' | jq '.data_sources'
```

Expected: Should see data_sources array (currently empty, will be populated in Task 4).

**Step 2.4: Commit**

```bash
git add src/workflow/graph.py src/utils/trace_utils.py
git commit -m "feat(cortex): add SQL execution trace extraction with statistics"
```

---

## Task 3: Add Web Researcher Search Trace

**Files:**
- Modify: `src/workflow/graph.py:187-211`

**Step 1: Add trace extraction to web_researcher_node**

In `src/workflow/graph.py`, modify `web_researcher_node` function (around line 187-211):

```python
def web_researcher_node(state: State):
    """Web research agent for external data."""
    from langgraph.types import Command
    from langchain_core.messages import AIMessage
    from src.agents.web_research_agent import create_web_research_agent
    import json

    agent = create_web_research_agent()
    agent_query = state.get("agent_query", state.get("user_query", ""))

    # Run agent
    result = agent.invoke({"messages": [{"role": "user", "content": agent_query}]})

    final_message = result["messages"][-1] if result.get("messages") else None
    response_content = final_message.content if final_message else "No results from web research."

    # Extract search traces from intermediate_steps
    search_traces = []
    intermediate_steps = result.get("intermediate_steps", [])

    for action, observation in intermediate_steps:
        # Check if this is a search tool call
        if hasattr(action, 'tool') and 'search' in action.tool.lower():
            try:
                search_query = action.tool_input.get("query", "")

                # Parse observation for sources
                # Tavily returns JSON with results array
                obs_data = json.loads(observation) if isinstance(observation, str) else observation

                sources = []
                if isinstance(obs_data, dict) and "results" in obs_data:
                    for item in obs_data["results"][:5]:  # Top 5 sources
                        sources.append({
                            "url": item.get("url", ""),
                            "title": item.get("title", ""),
                            "snippet": item.get("content", "")[:200]  # First 200 chars
                        })

                search_traces.append({
                    "search_query": search_query,
                    "sources": sources
                })
            except (json.JSONDecodeError, AttributeError, KeyError):
                continue

    # Add EXECUTION_TRACE if we have traces
    if search_traces:
        response_content = f"{response_content}\n\nEXECUTION_TRACE: {json.dumps(search_traces)}"

    return Command(
        update={
            "messages": [AIMessage(content=response_content, name="web_researcher")],
            "model_usage": {
                **(state.get("model_usage") or {}),
                "web_researcher": state.get("implementation_model_override") or "deepseek-v3"
            }
        },
        goto="executor"
    )
```

**Step 2: Test web researcher trace**

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the population of Bellingham Washington?", "enable_charts": false}'
```

Check response for web_researcher message with EXECUTION_TRACE.

**Step 3: Commit**

```bash
git add src/workflow/graph.py
git commit -m "feat(web-research): add search execution trace with sources"
```

---

## Task 4: Enhance Response Formatter to Extract Traces

**Files:**
- Modify: `src/agents/response_formatter.py:41-97`

**Step 1: Replace data sources extraction logic**

In `src/agents/response_formatter.py`, replace the data sources extraction section (lines 41-82) with comprehensive trace parsing:

```python
    # Extract execution traces from all agents
    data_sources = []
    step_num = 0

    for msg in messages:
        if not hasattr(msg, 'content') or "EXECUTION_TRACE" not in msg.content:
            continue

        # Find EXECUTION_TRACE marker
        content = msg.content
        trace_start = content.find("EXECUTION_TRACE:")
        if trace_start == -1:
            continue

        # Extract JSON after marker
        trace_json_start = trace_start + len("EXECUTION_TRACE:")
        trace_json = content[trace_json_start:].strip()

        # Find end of JSON by counting braces
        brace_count = 0
        json_end = 0
        for i, char in enumerate(trace_json):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    json_end = i + 1
                    break
            elif char == '[':
                # Handle array start
                brace_count += 1
            elif char == ']':
                brace_count -= 1
                if brace_count == 0:
                    json_end = i + 1
                    break

        if json_end > 0:
            trace_json = trace_json[:json_end]

        try:
            trace_data = json.loads(trace_json)
            agent_name = getattr(msg, "name", "unknown")

            # Handle different agent types
            if agent_name in ["initial_plan", "replan"]:
                # Planner trace
                step_num += 1
                data_sources.append({
                    "step": step_num,
                    "agent": "planner",
                    "type": "planning",
                    "action": f"Generated execution plan with {trace_data.get('steps', 0)} steps",
                    "plan": trace_data.get("plan", {}),
                    "reasoning_model": trace_data.get("reasoning_model", "unknown")
                })

            elif agent_name == "cortex_researcher":
                # SQL traces (list of executions)
                if isinstance(trace_data, list):
                    for sql_trace in trace_data:
                        step_num += 1
                        data_sources.append({
                            "step": step_num,
                            "agent": "cortex_researcher",
                            "type": "oews_database",
                            "action": f"Executed SQL query returning {sql_trace.get('row_count', 0)} rows",
                            **sql_trace
                        })

            elif agent_name == "web_researcher":
                # Search traces (list of searches)
                if isinstance(trace_data, list):
                    for search_trace in trace_data:
                        step_num += 1
                        data_sources.append({
                            "step": step_num,
                            "agent": "web_researcher",
                            "type": "web_search",
                            "action": f"Searched: {search_trace.get('search_query', '')}",
                            **search_trace
                        })

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("trace_parse_error", extra={
                "data": {
                    "agent": getattr(msg, "name", "unknown"),
                    "error": str(e),
                    "trace_preview": trace_json[:200] if 'trace_json' in locals() else ""
                }
            })
            continue

    # LOG: Extracted traces
    logger.debug("traces_extracted", extra={
        "data": {
            "total_traces": len(data_sources),
            "trace_types": [ds.get("type") for ds in data_sources]
        }
    })
```

**Step 2: Test trace extraction**

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the median salary for nurses in Seattle?", "enable_charts": false}' | jq '.data_sources'
```

Expected output should show data_sources array with planner and cortex_researcher entries.

**Step 3: Commit**

```bash
git add src/agents/response_formatter.py
git commit -m "feat(formatter): extract and structure execution traces from all agents"
```

---

## Task 5: Add Frontend Execution Step Component

**Files:**
- Create: `/home/varun/oews-data-explorer/src/components/ExecutionStep.tsx`

**Step 1: Install syntax highlighting dependency**

```bash
cd /home/varun/oews-data-explorer
npm install react-syntax-highlighter
npm install --save-dev @types/react-syntax-highlighter
```

**Step 2: Create ExecutionStep component**

Create `/home/varun/oews-data-explorer/src/components/ExecutionStep.tsx`:

```typescript
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface ExecutionStepProps {
  step: {
    step: number;
    agent: string;
    action?: string;
    type: string;
    sql?: string;
    params?: any[];
    row_count?: number;
    sample_data?: any[];
    stats?: any;
    search_query?: string;
    sources?: any[];
    plan?: any;
    reasoning_model?: string;
  };
}

export function ExecutionStep({ step }: ExecutionStepProps) {
  return (
    <Card className="p-6 bg-gray-50">
      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <Badge variant="outline" className="text-sm">
          Step {step.step}
        </Badge>
        <Badge className="bg-blue-600">
          {step.agent}
        </Badge>
        {step.action && (
          <span className="text-sm text-gray-700">{step.action}</span>
        )}
      </div>

      {/* Planner */}
      {step.type === 'planning' && step.plan && (
        <div className="space-y-2">
          <h4 className="font-semibold text-gray-800">Generated Plan:</h4>
          <pre className="bg-white p-4 rounded border text-sm overflow-x-auto">
            {JSON.stringify(step.plan, null, 2)}
          </pre>
          {step.reasoning_model && (
            <Badge variant="secondary" className="mt-2">
              Model: {step.reasoning_model}
            </Badge>
          )}
        </div>
      )}

      {/* SQL Query */}
      {step.sql && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="font-semibold text-gray-800">SQL Query:</h4>
            {step.row_count !== undefined && (
              <Badge variant="secondary">{step.row_count} rows</Badge>
            )}
          </div>

          <SyntaxHighlighter
            language="sql"
            style={vscDarkPlus}
            className="rounded-md text-sm"
          >
            {step.sql}
          </SyntaxHighlighter>

          {step.params && step.params.length > 0 && (
            <div>
              <h5 className="text-sm font-semibold text-gray-700 mb-2">Parameters:</h5>
              <div className="flex gap-2 flex-wrap">
                {step.params.map((param, i) => (
                  <Badge key={i} variant="outline">{String(param)}</Badge>
                ))}
              </div>
            </div>
          )}

          {step.sample_data && step.sample_data.length > 0 && (
            <div>
              <h5 className="text-sm font-semibold text-gray-700 mb-2">
                Sample Data (showing {step.sample_data.length} of {step.row_count} rows):
              </h5>
              <div className="overflow-x-auto">
                <table className="min-w-full bg-white border rounded text-sm">
                  <thead className="bg-gray-100">
                    <tr>
                      {Object.keys(step.sample_data[0]).map((col) => (
                        <th key={col} className="px-4 py-2 text-left border-b">
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {step.sample_data.map((row, i) => (
                      <tr key={i} className="border-b">
                        {Object.values(row).map((val: any, j) => (
                          <td key={j} className="px-4 py-2">
                            {val}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {step.stats && Object.keys(step.stats).length > 0 && (
            <div>
              <h5 className="text-sm font-semibold text-gray-700 mb-2">Statistics:</h5>
              <div className="flex gap-2 flex-wrap">
                {Object.entries(step.stats).map(([col, stats]: [string, any]) => (
                  <Badge key={col} variant="secondary" className="text-xs">
                    {col}: {stats.min?.toLocaleString()} - {stats.max?.toLocaleString()}
                    (avg: {stats.avg?.toLocaleString()})
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Web Search */}
      {step.type === 'web_search' && (
        <div className="space-y-3">
          {step.search_query && (
            <div>
              <h4 className="font-semibold text-gray-800 mb-2">Search Query:</h4>
              <code className="bg-white px-3 py-2 rounded border text-sm block">
                {step.search_query}
              </code>
            </div>
          )}

          {step.sources && step.sources.length > 0 && (
            <div>
              <h5 className="text-sm font-semibold text-gray-700 mb-2">Sources:</h5>
              <div className="space-y-2">
                {step.sources.map((source: any, i: number) => (
                  <div key={i} className="bg-white p-3 rounded border">
                    <a
                      href={source.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:underline font-medium"
                    >
                      {source.title || source.url}
                    </a>
                    {source.snippet && (
                      <p className="text-sm text-gray-600 mt-1">{source.snippet}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </Card>
  );
}
```

**Step 3: Commit**

```bash
cd /home/varun/oews-data-explorer
git add src/components/ExecutionStep.tsx package.json package-lock.json
git commit -m "feat(frontend): add ExecutionStep component with syntax highlighting"
```

---

## Task 6: Update ResultsDisplay to Show Execution Traces

**Files:**
- Modify: `/home/varun/oews-data-explorer/src/components/ResultsDisplay.tsx:82-113`

**Step 1: Import ExecutionStep component**

At the top of ResultsDisplay.tsx, add import:

```typescript
import { ExecutionStep } from './ExecutionStep';
```

**Step 2: Replace data sources accordion**

Find the existing data sources accordion section (around lines 82-113) and replace with:

```typescript
      {results.data_sources && results.data_sources.length > 0 && (
        <Accordion type="single" collapsible className="w-full">
          <AccordionItem value="execution-trace">
            <AccordionTrigger className="text-lg font-semibold text-gray-700">
              Execution Details ({results.data_sources.length} steps)
            </AccordionTrigger>
            <AccordionContent>
              <div className="space-y-6 pt-2">
                {results.data_sources.map((source, index) => (
                  <ExecutionStep key={index} step={source} />
                ))}
              </div>
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      )}
```

**Step 3: Test frontend rendering**

Start frontend dev server:

```bash
cd /home/varun/oews-data-explorer
npm run dev
```

Open browser to frontend, make a query, verify "Execution Details" section appears.

**Step 4: Commit**

```bash
git add src/components/ResultsDisplay.tsx
git commit -m "feat(frontend): integrate ExecutionStep into ResultsDisplay accordion"
```

---

## Task 7: Add Unit Tests for Trace Utils

**Files:**
- Create: `tests/test_trace_utils.py`

**Step 1: Write test for calculate_column_stats**

Create `tests/test_trace_utils.py`:

```python
"""Tests for trace utilities."""

import pytest
from src.utils.trace_utils import calculate_column_stats, build_sql_trace


def test_calculate_column_stats_numeric():
    """Test statistics calculation for numeric column."""
    rows = [
        {"salary": 50000, "name": "Alice"},
        {"salary": 60000, "name": "Bob"},
        {"salary": 70000, "name": "Carol"}
    ]

    stats = calculate_column_stats(rows, "salary")

    assert stats is not None
    assert stats["min"] == 50000
    assert stats["max"] == 70000
    assert stats["avg"] == 60000


def test_calculate_column_stats_non_numeric():
    """Test that non-numeric columns return None."""
    rows = [
        {"name": "Alice"},
        {"name": "Bob"}
    ]

    stats = calculate_column_stats(rows, "name")

    assert stats is None


def test_calculate_column_stats_empty_rows():
    """Test empty rows return None."""
    stats = calculate_column_stats([], "salary")
    assert stats is None


def test_calculate_column_stats_missing_column():
    """Test missing column returns None."""
    rows = [{"salary": 50000}]
    stats = calculate_column_stats(rows, "bonus")
    assert stats is None


def test_build_sql_trace():
    """Test building complete SQL trace."""
    sql = "SELECT * FROM oews_data WHERE area = ?"
    params = ["Seattle"]
    rows = [
        {"occupation": "Nurse", "salary": 80000},
        {"occupation": "Developer", "salary": 120000}
    ]

    trace = build_sql_trace(sql, params, rows)

    assert trace["sql"] == sql
    assert trace["params"] == params
    assert trace["row_count"] == 2
    assert len(trace["sample_data"]) == 2
    assert trace["stats"] is not None
    assert "salary" in trace["stats"]
    assert trace["stats"]["salary"]["min"] == 80000
    assert trace["stats"]["salary"]["max"] == 120000


def test_build_sql_trace_limits_sample_data():
    """Test that sample data is limited to 10 rows."""
    sql = "SELECT * FROM test"
    params = []
    rows = [{"id": i} for i in range(20)]

    trace = build_sql_trace(sql, params, rows)

    assert trace["row_count"] == 20
    assert len(trace["sample_data"]) == 10


def test_build_sql_trace_no_stats_for_non_numeric():
    """Test that non-numeric columns don't produce stats."""
    sql = "SELECT name FROM users"
    params = []
    rows = [{"name": "Alice"}, {"name": "Bob"}]

    trace = build_sql_trace(sql, params, rows)

    assert trace["stats"] is None
```

**Step 2: Run tests**

```bash
pytest tests/test_trace_utils.py -v
```

Expected: All tests pass.

**Step 3: Commit**

```bash
git add tests/test_trace_utils.py
git commit -m "test(trace): add comprehensive tests for trace utilities"
```

---

## Task 8: End-to-End Integration Test

**Files:**
- Manual testing only

**Step 1: Test query with SQL trace**

Start backend server:

```bash
python -m src.main
```

Make API request:

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the median salary for registered nurses in Seattle?", "enable_charts": false}' | jq '.data_sources'
```

Verify:
- Step 0: planner with plan object
- Step 1+: cortex_researcher with SQL, params, sample_data, stats

**Step 2: Test query with web search**

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the population of Bellingham Washington and compare salaries to similar sized cities?", "enable_charts": false}' | jq '.data_sources'
```

Verify:
- Step 0: planner
- Step 1: web_researcher with search_query and sources
- Step 2+: cortex_researcher with SQL traces

**Step 3: Test frontend UI**

Open browser to frontend URL, make same queries, verify:
- "Execution Details" accordion appears
- Click to expand
- See steps numbered correctly
- SQL appears syntax highlighted
- Data tables render
- Statistics badges show
- Web sources show as links

**Step 4: Test edge cases**

Test query that only uses cortex_researcher (no web search):

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Show me software developer salaries in Portland", "enable_charts": false}' | jq '.data_sources'
```

Verify no errors, graceful handling.

**Step 5: Document test results**

Create test summary in commit message for final commit.

---

## Task 9: Final Integration and Cleanup

**Step 1: Review all changes**

```bash
git log --oneline execution-traceability
git diff main...execution-traceability --stat
```

**Step 2: Run full test suite**

```bash
pytest tests/ -v
```

Expected: All tests pass.

**Step 3: Test with charts enabled**

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Compare software developer salaries in Seattle vs Portland in a graph", "enable_charts": true}' | jq '.data_sources'
```

Verify execution traces still work with chart generation.

**Step 4: Create final summary commit**

```bash
git commit --allow-empty -m "chore: execution traceability implementation complete

Summary of changes:
- Added EXECUTION_TRACE markers to planner, cortex_researcher, web_researcher
- Created trace_utils module for SQL statistics calculation
- Enhanced response_formatter to extract and structure traces
- Added ExecutionStep frontend component with syntax highlighting
- Updated ResultsDisplay to show expandable execution details
- Added comprehensive unit tests for trace utilities

Testing:
- ✓ Planner trace with plan object
- ✓ SQL traces with queries, params, sample data, statistics
- ✓ Web search traces with queries and sources
- ✓ Frontend displays all trace types correctly
- ✓ Syntax highlighting works for SQL
- ✓ Data tables render sample results
- ✓ Statistics badges show min/max/avg
- ✓ Graceful handling of missing traces

All 8 trace_utils tests passing.
End-to-end integration verified."
```

---

## Success Criteria Checklist

Before marking complete, verify:

- [ ] Planner shows generated plan in execution details
- [ ] SQL queries visible with syntax highlighting
- [ ] SQL parameters shown separately
- [ ] Sample data (5-10 rows) displayed in tables
- [ ] Statistics calculated for numeric columns (min/max/avg)
- [ ] Web searches show query and source URLs
- [ ] Frontend "Execution Details" accordion expandable
- [ ] No errors when traces missing (graceful degradation)
- [ ] All unit tests passing
- [ ] End-to-end queries work with traceability

---

## Notes for Implementation

**Backend Testing:**
- Use curl or httpie for API testing
- Check logs for trace extraction warnings
- Verify JSON structure in responses

**Frontend Testing:**
- Use browser DevTools to inspect data_sources
- Verify react-syntax-highlighter loads correctly
- Test accordion expand/collapse

**Debugging Tips:**
- If traces don't appear: Check for EXECUTION_TRACE marker in agent messages
- If JSON parse fails: Check brace counting logic in response_formatter
- If frontend crashes: Verify data_sources structure matches ExecutionStep interface

**DRY Principles Applied:**
- Trace extraction logic centralized in trace_utils
- Single ExecutionStep component handles all agent types
- Response formatter uses common parsing approach

**YAGNI:**
- No copy buttons (can add later if needed)
- No interactive SQL execution (read-only display)
- No export functionality (future enhancement)
