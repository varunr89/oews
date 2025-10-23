"""Chart Generator Agent for creating visualizations."""

from typing import Dict, Any
import json
from src.config.llm_factory import llm_factory


def create_chart_generator_agent():
    """
    Create a simple chart generator agent.

    Returns:
        Callable agent function
    """
    llm = llm_factory.get_implementation()

    def invoke(input_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Generate chart specifications from data."""
        messages = input_dict.get("messages", [])
        query = messages[0].get("content", "") if messages else ""

        try:
            # Create a prompt for chart generation
            prompt = f"""You are a chart generation agent. Create a bar chart specification from the data.

Question: {query}

Generate a JSON chart specification with this format:
{{
  "type": "bar",
  "title": "Chart Title",
  "data": {{
    "labels": ["Label1", "Label2"],
    "values": [value1, value2]
  }}
}}

Return ONLY the JSON specification wrapped in CHART_SPEC markers like this:
CHART_SPEC: {{"type": "bar", ...}}
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
