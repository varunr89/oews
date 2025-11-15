"""Chart Generator Agent for creating visualizations."""

from typing import Dict, Any, Optional
import json
from src.config.llm_factory import llm_factory


def create_chart_generator_agent(override_key: Optional[str] = None):
    """
    Create a simple chart generator agent.

    Args:
        override_key: Optional model key to use instead of default implementation model

    Returns:
        Callable agent function
    """
    llm = llm_factory.get_implementation(override_key=override_key)

    def invoke(input_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Generate chart specifications from data."""
        messages = input_dict.get("messages", [])
        query = messages[0].get("content", "") if messages else ""

        try:
            # Create a prompt for chart generation
            prompt = f"""You are a chart generation agent. Analyze the previous agent outputs and create appropriate chart specifications.

Question: {query}

Generate a JSON chart specification with this EXACT format:
{{
  "type": "bar|line|scatter",
  "title": "Descriptive Chart Title",
  "data": {{
    "labels": ["X-axis Label1", "X-axis Label2", "..."],
    "datasets": [
      {{
        "name": "Dataset Name",
        "values": [number1, number2, ...]
      }}
    ]
  }},
  "options": {{
    "xAxis": {{"title": "X Axis Label"}},
    "yAxis": {{"title": "Y Axis Label"}}
  }}
}}

IMPORTANT:
- Use "name" (not "label") for dataset names
- Use "values" (not "data") for dataset values
- Choose appropriate chart type: bar, line, or scatter
- Include multiple datasets for comparisons
- Return ONLY the JSON specification wrapped in CHART_SPEC markers like this:

CHART_SPEC: {{"type": "bar", "title": "...", ...}}

DO NOT include explanatory text, ONLY output the CHART_SPEC line with valid JSON.
"""

            from langchain_core.messages import HumanMessage
            response = llm.invoke([HumanMessage(content=prompt)])

            return {
                "messages": [{"role": "assistant", "content": response.content}]
            }

        except Exception as e:
            return {
                "messages": [{"role": "assistant", "content": f"Error generating chart: {str(e)}"}]
            }

    class SimpleAgent:
        def __init__(self, invoke_fn):
            self.invoke = invoke_fn

    return SimpleAgent(invoke)
