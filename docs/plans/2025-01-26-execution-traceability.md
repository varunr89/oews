# Execution Traceability Design

**Date:** 2025-01-26
**Status:** Approved for implementation

## Problem

Users cannot verify that AI-generated answers come from actual data rather than model hallucinations. The system needs to show the exact steps it took: what it planned, what queries it ran, what data it retrieved, and where external information came from.

## Solution

Add comprehensive execution tracing that captures every information source. Display this trace in an expandable "Execution Details" section in the frontend UI, showing SQL queries, parameters, sample data, web searches, and the execution plan.

## Requirements

### Display Location
- Expandable details section in frontend UI
- Hidden by default to keep results clean
- Available on demand for verification

### Trace Content (Information Sources Only)
Capture execution details from agents that generate new information:

1. **Planner** - The generated plan and reasoning model
2. **Web Researcher** - Search queries, sources, URLs, snippets
3. **Cortex Researcher** - SQL queries, parameters, row counts, sample data, statistics

Omit chart_generator and synthesizer traces. Their outputs are already visible (charts and answer text).

### Detail Level Per Step
- Agent name and action description
- SQL queries with parameterized values shown separately
- Sample data: first 5-10 rows from query results
- Statistics: row counts, min/max ranges, value summaries

### UI Formatting
- SQL in syntax-highlighted code blocks
- Data samples in formatted tables
- Clean, developer-friendly appearance
- Copy buttons for SQL queries

## Architecture

### Approach: Enhance Existing data_sources Array

Expand the current `data_sources` field in API responses. This reuses existing frontend accordion infrastructure while adding rich execution details.

### Data Structure

Each execution step becomes a data_source entry:

```json
{
  "step": 2,
  "agent": "cortex_researcher",
  "action": "Retrieved median wages for software developers in Seattle",
  "type": "oews_database",
  "sql": "SELECT occupation_title, a_median FROM oews_data WHERE area_title LIKE ? AND occupation_title LIKE ?",
  "params": ["%Seattle%", "%Software Developer%"],
  "row_count": 3,
  "sample_data": [
    {"occupation_title": "Software Developers", "a_median": 151930},
    {"occupation_title": "Software Developers, Applications", "a_median": 148520},
    {"occupation_title": "Software Developers, Systems Software", "a_median": 155340}
  ],
  "stats": {
    "a_median": {"min": 148520, "max": 155340, "avg": 151596}
  }
}
```

## Implementation

### Backend Changes

#### 1. Planner (`src/agents/planner.py`)

Add execution trace to the planner message:

```python
# After generating plan
trace = {
    "plan": parsed_plan,
    "reasoning_model": model_key,
    "steps": len(parsed_plan)
}

message_content = f"{json.dumps(parsed_plan)}\n\nEXECUTION_TRACE: {json.dumps(trace)}"
```

#### 2. Cortex Researcher (`src/workflow/graph.py` - cortex_researcher_node)

Extract SQL execution details from agent intermediate_steps:

```python
# After agent.invoke()
intermediate_steps = result.get("intermediate_steps", [])

# Find execute_sql_query tool calls
sql_traces = []
for action, observation in intermediate_steps:
    if action.tool == "execute_sql_query":
        sql = action.tool_input.get("sql")
        params = json.loads(action.tool_input.get("params", "[]"))

        # Parse observation for results
        result_data = json.loads(observation)
        rows = result_data.get("results", [])

        sql_traces.append({
            "sql": sql,
            "params": params,
            "row_count": len(rows),
            "sample_data": rows[:10],  # First 10 rows
            "stats": calculate_stats(rows)  # Min/max/avg for numeric columns
        })

# Add to message
trace_content = f"{response_content}\n\nEXECUTION_TRACE: {json.dumps(sql_traces)}"
```

#### 3. Web Researcher (`src/workflow/graph.py` - web_researcher_node)

Extract search queries and sources:

```python
# After agent.invoke()
intermediate_steps = result.get("intermediate_steps", [])

# Find search tool calls
search_traces = []
for action, observation in intermediate_steps:
    if "search" in action.tool.lower():
        search_traces.append({
            "search_query": action.tool_input.get("query"),
            "sources": parse_sources(observation)  # Extract URLs, titles, snippets
        })

trace_content = f"{response_content}\n\nEXECUTION_TRACE: {json.dumps(search_traces)}"
```

#### 4. Response Formatter (`src/agents/response_formatter.py`)

Enhance data_sources extraction to parse EXECUTION_TRACE markers:

```python
data_sources = []
step_num = 0

for msg in messages:
    if not hasattr(msg, 'content') or "EXECUTION_TRACE" not in msg.content:
        continue

    # Extract trace
    trace_start = msg.content.find("EXECUTION_TRACE:")
    trace_json = msg.content[trace_start + 16:].strip()

    try:
        trace_data = json.loads(trace_json)
        agent_name = getattr(msg, "name", "unknown")

        # Handle different agent types
        if agent_name == "planner":
            step_num += 1
            data_sources.append({
                "step": step_num,
                "agent": "planner",
                "type": "planning",
                **trace_data
            })
        elif agent_name == "cortex_researcher":
            # trace_data is a list of SQL executions
            for sql_trace in trace_data:
                step_num += 1
                data_sources.append({
                    "step": step_num,
                    "agent": "cortex_researcher",
                    "type": "oews_database",
                    **sql_trace
                })
        elif agent_name == "web_researcher":
            for search_trace in trace_data:
                step_num += 1
                data_sources.append({
                    "step": step_num,
                    "agent": "web_researcher",
                    "type": "web_search",
                    **search_trace
                })
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning("trace_parse_error", extra={"error": str(e)})
        continue
```

### Frontend Changes

#### 5. Results Display (`/home/varun/oews-data-explorer/src/components/ResultsDisplay.tsx`)

Enhance the existing Data Sources accordion:

```tsx
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

#### 6. New Component: ExecutionStep

Create `/home/varun/oews-data-explorer/src/components/ExecutionStep.tsx`:

```tsx
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
        </div>
      )}

      {/* SQL Query */}
      {step.sql && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="font-semibold text-gray-800">SQL Query:</h4>
            <Badge variant="secondary">{step.row_count} rows</Badge>
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
                  <Badge key={i} variant="outline">{param}</Badge>
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

          {step.stats && (
            <div>
              <h5 className="text-sm font-semibold text-gray-700 mb-2">Statistics:</h5>
              <div className="flex gap-2 flex-wrap">
                {Object.entries(step.stats).map(([col, stats]: [string, any]) => (
                  <Badge key={col} variant="secondary">
                    {col}: {stats.min} - {stats.max} (avg: {stats.avg})
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
          <div>
            <h4 className="font-semibold text-gray-800 mb-2">Search Query:</h4>
            <code className="bg-white px-3 py-2 rounded border text-sm block">
              {step.search_query}
            </code>
          </div>

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
                      {source.title}
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

#### 7. Add Dependencies

Install syntax highlighting library:

```bash
npm install react-syntax-highlighter
npm install --save-dev @types/react-syntax-highlighter
```

## Error Handling

### Missing Traces
If EXECUTION_TRACE marker is not found, skip that message. The data_sources array will only contain steps with available traces.

### Parse Failures
Wrap all JSON parsing in try-catch blocks. Log warnings for debugging but don't fail the request:

```python
try:
    trace_data = json.loads(trace_json)
except json.JSONDecodeError as e:
    logger.warning("trace_parse_error", extra={
        "agent": agent_name,
        "error": str(e),
        "content_preview": trace_json[:200]
    })
    continue
```

### Large Result Sets
Limit sample_data to 10 rows maximum. Show indicator: "showing X of Y rows".

### Empty Data Sources
If no traces are captured, hide the "Execution Details" accordion entirely:

```tsx
{results.data_sources && results.data_sources.length > 0 && (
  // Accordion component
)}
```

## Success Criteria

1. **Planner trace visible** - Users see the generated plan with step-by-step breakdown
2. **SQL queries visible** - Every database query shown with parameters and results
3. **Web searches visible** - Search queries and source URLs displayed
4. **Data samples shown** - First 5-10 rows of query results in formatted tables
5. **Statistics calculated** - Min/max/avg for numeric columns
6. **UI stays clean** - Execution details hidden by default, expandable on demand
7. **Syntax highlighting works** - SQL appears in syntax-highlighted code blocks
8. **No errors on missing traces** - System gracefully handles agents without EXECUTION_TRACE markers

## Files Modified

### Backend
- `src/agents/planner.py` - Add EXECUTION_TRACE to plan message
- `src/workflow/graph.py` - cortex_researcher_node, web_researcher_node (extract and add traces)
- `src/agents/response_formatter.py` - Parse EXECUTION_TRACE markers, build data_sources array

### Frontend
- `/home/varun/oews-data-explorer/src/components/ResultsDisplay.tsx` - Enhance accordion
- `/home/varun/oews-data-explorer/src/components/ExecutionStep.tsx` - New component (create)
- `/home/varun/oews-data-explorer/package.json` - Add react-syntax-highlighter dependency

## Testing Plan

1. **Test query with cortex_researcher only** - Verify SQL traces appear
2. **Test query with web_researcher** - Verify search queries and sources appear
3. **Test query with multiple steps** - Verify all steps numbered correctly
4. **Test query without enable_charts** - Verify no chart_generator/synthesizer traces
5. **Test with missing traces** - Verify no errors, graceful degradation
6. **Test UI interaction** - Verify accordion expands/collapses, tables render correctly
7. **Test syntax highlighting** - Verify SQL appears with proper colors
8. **Test large result sets** - Verify 10-row limit, "showing X of Y" indicator
