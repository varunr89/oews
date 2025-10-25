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
        if hasattr(msg, 'content') and "CHART_SPEC" in msg.content:
            # Extract JSON from CHART_SPEC markers
            chart_matches = re.findall(r'CHART_SPEC:\s*({.*?})', msg.content, re.DOTALL)
            for chart_json in chart_matches:
                try:
                    chart_spec = json.loads(chart_json)
                    charts.append(chart_spec)
                except json.JSONDecodeError:
                    pass

    # Extract data sources
    data_sources = []
    for msg in messages:
        if hasattr(msg, 'name') and msg.name == "cortex_researcher":
            # Try to extract SQL queries from message
            if "success" in msg.content and "sql" in msg.content.lower():
                try:
                    result_data = json.loads(msg.content)
                    if result_data.get("success"):
                        data_sources.append({
                            "name": "OEWS Database",
                            "sql_query": result_data.get("sql", ""),
                            "row_count": result_data.get("row_count", 0)
                        })
                except:
                    pass

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
