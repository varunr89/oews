"""Planner prompt templates."""

from typing import Dict, Any
from langchain_core.messages import HumanMessage


def get_agent_descriptions() -> Dict[str, str]:
    """Get descriptions of available agents."""
    return {
        "web_researcher": "Fetch public data via web search (for external facts, news, current events)",
        "cortex_researcher": "Query OEWS database with Text2SQL (for employment and wage statistics)",
        "chart_generator": "Create interactive chart specifications (when user requests visualizations)",
        "synthesizer": "Create text summary of findings (final step for text-only responses)"
    }


def plan_prompt(state) -> HumanMessage:
    """
    Build the prompt that instructs the LLM to return a plan.

    Args:
        state: Current workflow state

    Returns:
        HumanMessage with planning instructions
    """
    user_query = state.get("user_query", state["messages"][0].content if state.get("messages") else "")
    enabled_agents = state.get("enabled_agents", ["cortex_researcher", "synthesizer"])

    # Filter agent descriptions
    descriptions = get_agent_descriptions()
    enabled_descriptions = {k: v for k, v in descriptions.items() if k in enabled_agents}

    agent_list = "\n".join([f"  • `{k}` – {v}" for k, v in enabled_descriptions.items()])

    prompt = f"""
You are the **Planner** in a multi-agent system. Break the user's request
into a sequence of numbered steps (1, 2, 3, …).

Available agents:
{agent_list}

Return **ONLY** valid JSON (no markdown, no explanations) in this form:

{{
  "1": {{
    "agent": "cortex_researcher",
    "action": "Get salary data for software developers in Seattle"
  }},
  "2": {{
    "agent": "synthesizer",
    "action": "Summarize findings"
  }}
}}

Guidelines:
- Use `cortex_researcher` for OEWS database queries (employment, wages, occupations)
- Use `web_researcher` for external data (population, news, trends)
- Use `chart_generator` when user requests charts/visualizations/graphs
- **ALWAYS use `synthesizer` as the final step** to provide detailed text analysis
- When charts are generated, synthesizer should explain insights, trends, and key takeaways from the visualization

CRITICAL: Every plan MUST end with a `synthesizer` step to provide comprehensive written analysis.

User query: "{user_query}"
"""

    return HumanMessage(content=prompt)
