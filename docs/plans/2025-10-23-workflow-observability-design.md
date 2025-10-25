
# Workflow Observability Design

**Date:** 2025-10-23
**Purpose:** Add comprehensive logging to debug Text2SQL agent and understand workflow execution flow

## Problem Statement

The OEWS Data Agent workflow is executing but not returning expected results. We need visibility into:
- What input each agent receives
- What SQL queries are generated
- What data is returned from the database
- How the Executor routes between agents

## Solution: Enhanced Structured Logging

### Architecture

**Approach:** Python standard library logging with JSON formatter writing to rotating file logs

**Components:**
1. **Logger Setup** (`src/utils/logger.py`) - Centralized logger configuration
2. **JSON Formatter** - Structured logs for easy parsing
3. **Rotating File Handler** - Write to `logs/workflow_debug.log` (10MB files, keep 5)
4. **Integration Points** - Add logging to all workflow nodes and agents

### Logging Points

**Captured Information:**

1. **Planner Node**:
   - Input: User query
   - Output: Generated execution plan

2. **Executor Node**:
   - Current step number
   - Target agent for routing
   - Routing decision rationale

3. **Text2SQL Agent**:
   - Input query/prompt
   - Generated SQL query
   - SQL parameters
   - Query results (row count + first 3 rows)
   - Tool invocations (get_schema_info, search_areas, execute_sql_query)

4. **Other Agents**:
   - Input prompts
   - LLM responses
   - Tool calls and results

5. **Response Formatter**:
   - Final structured response

### Log Format

```json
{
  "timestamp": "2025-10-23T15:30:45.123Z",
  "level": "DEBUG",
  "component": "text2sql_agent",
  "event": "sql_generated",
  "data": {
    "sql": "SELECT AREA_TITLE, OCC_TITLE, A_MEDIAN FROM oews_data WHERE AREA_TITLE LIKE ? AND OCC_TITLE LIKE ?",
    "params": ["%Seattle%", "%Software%"],
    "row_count": 10
  }
}
```

### Implementation Details

**Logger Configuration:**
- Logger name: `oews.workflow`
- Level: DEBUG
- Handler: RotatingFileHandler
- Format: JSON with timestamp, level, component, event, data

**Integration:**
- Import logger in each module
- Add `logger.debug(event, extra={"data": {...}})` at key points
- No changes to existing logic - purely additive

### Usage Workflow

**1. Run Query:**
```bash
curl -X POST http://localhost:8000/api/v1/query \
  -d '{"query": "What is the median salary for software developers in Seattle, WA?"}'
```

**2. Watch Logs:**
```bash
tail -f logs/workflow_debug.log | jq .
```

**3. Analyze Execution:**
```bash
# Filter by component
grep '"component":"text2sql_agent"' logs/workflow_debug.log | jq .

# Find SQL queries
grep '"event":"sql_generated"' logs/workflow_debug.log | jq .data

# Check results
grep '"event":"query_results"' logs/workflow_debug.log | jq .data.row_count
```

**4. Compare vs Expected:**
- Extract actual SQL from logs
- Compare with manually written SQL
- Identify discrepancies in query generation

### Analysis Tools

**Quick Analysis Script** (`scripts/analyze_workflow.py`):
```python
import json
from pathlib import Path

def analyze_last_execution(num_logs=20):
    """Display last workflow execution in readable format."""
    log_file = Path('logs/workflow_debug.log')

    if not log_file.exists():
        print("No logs found")
        return

    with open(log_file) as f:
        logs = [json.loads(line) for line in f if line.strip()]

    recent = logs[-num_logs:]

    print(f"{'Component':<25} | {'Event':<35} | Data")
    print("-" * 100)

    for log in recent:
        component = log.get('component', 'unknown')
        event = log.get('event', 'unknown')
        data = log.get('data', {})

        # Format data for display
        data_str = str(data)[:50] + "..." if len(str(data)) > 50 else str(data)

        print(f"{component:<25} | {event:<35} | {data_str}")

if __name__ == "__main__":
    analyze_last_execution()
```

### Benefits

1. **Root Cause Analysis** - See exactly where queries fail
2. **Query Debugging** - Compare generated SQL vs expected SQL
3. **Performance Insights** - Track execution time per component
4. **Regression Testing** - Logs serve as execution traces
5. **Persistent History** - Review past executions

### Non-Goals

- Real-time streaming logs to API response (adds complexity)
- Metrics/monitoring system (out of scope)
- Log aggregation across multiple instances (single instance for now)

## Implementation Plan

See: `docs/plans/2025-10-23-workflow-observability.md` (to be created)

Tasks:
1. Create logger utility module
2. Add logging to workflow nodes
3. Add logging to Text2SQL agent
4. Add logging to tools
5. Create analysis script
6. Test and verify logs
