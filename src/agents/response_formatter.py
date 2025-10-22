"""Response formatter for final API output."""

import json
import re
from typing import Dict, Any, List
from langgraph.types import Command
from langchain.schema import HumanMessage
from src.agents.state import State


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

    return Command(
        update={
            "formatted_response": formatted_response,
            "messages": [HumanMessage(
                content="Response formatted successfully",
                name="response_formatter"
            )]
        }
    )
