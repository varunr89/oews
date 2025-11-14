"""Response formatter for final API output."""

import json
import re
from typing import Dict, Any, List
from langgraph.types import Command
from langchain_core.messages import HumanMessage
from src.agents.state import State
from src.utils.logger import setup_workflow_logger

logger = setup_workflow_logger()


def response_formatter_node(state: State) -> Command:
    """
    Format the final response for API consumption.

    Extracts:
    - Final answer from synthesizer
    - Chart specifications from chart_generator
    - Data sources from messages
    - Metadata (model usage, plan, etc.)

    Args:
        state: Current workflow state

    Returns:
        Command with formatted response
    """
    messages = state.get("messages", [])

    # Extract final answer
    final_answer = state.get("final_answer", "")
    if not final_answer:
        # Try to get from last synthesizer message
        for msg in reversed(messages):
            if hasattr(msg, 'name') and msg.name == "synthesizer":
                final_answer = msg.content
                break

    # Extract charts
    charts = []

    # LOG: Debug chart extraction
    logger.debug("extracting_charts", extra={
        "data": {
            "message_count": len(messages),
            "chart_messages": [
                {"name": getattr(msg, "name", "unknown"), "has_chart_spec": "CHART_SPEC" in msg.content if hasattr(msg, "content") else False}
                for msg in messages if hasattr(msg, "name") and getattr(msg, "name", "") in ["chart_generator", "chart_summarizer"]
            ]
        }
    })

    for msg in messages:
        # Only extract charts from chart_summarizer (it has the preserved CHART_SPEC)
        if hasattr(msg, 'name') and msg.name == "chart_summarizer" and hasattr(msg, 'content') and "CHART_SPEC" in msg.content:
            # Extract JSON from CHART_SPEC markers
            # Use a more robust approach: find "CHART_SPEC:" then parse JSON from that position
            content = msg.content
            chart_start = 0
            while True:
                chart_start = content.find("CHART_SPEC:", chart_start)
                if chart_start == -1:
                    break

                # Find the JSON object starting position
                json_start = content.find("{", chart_start)
                if json_start == -1:
                    break

                # Extract JSON by counting braces
                brace_count = 0
                json_end = json_start
                for i in range(json_start, len(content)):
                    if content[i] == '{':
                        brace_count += 1
                    elif content[i] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_end = i + 1
                            break

                if brace_count == 0:  # Found complete JSON
                    chart_json = content[json_start:json_end]
                    try:
                        chart_spec = json.loads(chart_json)
                        # Add unique ID if not present
                        if 'id' not in chart_spec:
                            chart_spec['id'] = f"chart_{len(charts) + 1}"
                        charts.append(chart_spec)
                    except json.JSONDecodeError as e:
                        logger.warning("chart_json_parse_error", extra={
                            "data": {"error": str(e), "json_preview": chart_json[:200]}
                        })

                chart_start = json_end if json_end > json_start else chart_start + 1

    # Extract execution traces from all agents
    data_sources = []
    step_num = 0

    # LOG: Debug message inspection
    logger.debug("inspecting_messages_for_traces", extra={
        "data": {
            "total_messages": len(messages),
            "message_agents": [getattr(msg, "name", "no_name") for msg in messages],
            "messages_with_trace_marker": sum(1 for msg in messages if hasattr(msg, 'content') and "EXECUTION_TRACE" in msg.content),
            "message_previews": [
                {
                    "agent": getattr(msg, "name", "no_name"),
                    "content_length": len(msg.content) if hasattr(msg, 'content') else 0,
                    "has_trace": "EXECUTION_TRACE" in msg.content if hasattr(msg, 'content') else False,
                    "content_preview": msg.content[:200] if hasattr(msg, 'content') else "no content"
                }
                for msg in messages
            ]
        }
    })

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

    # Build formatted response
    formatted_response = {
        "answer": final_answer or "No answer generated.",
        "charts": charts,
        "data_sources": data_sources,
        "metadata": {
            "models_used": state.get("model_usage", {}),
            "plan": state.get("plan", {}),
            "replans": state.get("replans", 0)
        }
    }

    # LOG: Final response
    logger.debug("response_formatter_output", extra={
        "data": {
            "answer_length": len(formatted_response.get("answer", "")),
            "charts_count": len(formatted_response.get("charts", [])),
            "data_sources_count": len(formatted_response.get("data_sources", [])),
            "models_used": formatted_response.get("metadata", {}).get("models_used", {})
        }
    })

    return Command(
        update={
            "formatted_response": formatted_response,
            "messages": [HumanMessage(
                content="Response formatted successfully",
                name="response_formatter"
            )]
        }
    )
