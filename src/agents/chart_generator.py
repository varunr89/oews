"""Chart Generator Agent for creating visualizations."""

from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from langchain_core.tools import tool
from src.config.llm_factory import llm_factory


@tool
def create_bar_chart(title: str, data: str) -> str:
    """
    Create a bar chart specification.

    Args:
        title: Chart title
        data: JSON string with chart data

    Returns:
        Chart specification marker
    """
    import json
    chart_spec = {
        "type": "bar",
        "title": title,
        "data": json.loads(data) if isinstance(data, str) else data
    }
    return f"CHART_SPEC: {json.dumps(chart_spec)}"


CHART_PROMPT = """You are a chart generation agent. Create chart specifications from data.

Available tools:
{tools}

Format:
Question: the input
Thought: think about chart type
Action: create_bar_chart
Action Input: {{"title": "...", "data": "..."}}
Observation: chart created
Final Answer: description of chart

Question: {input}
{agent_scratchpad}
"""


def create_chart_generator_agent() -> AgentExecutor:
    """
    Create agent for generating charts.

    Returns:
        AgentExecutor instance
    """
    llm = llm_factory.get_implementation()
    tools = [create_bar_chart]
    prompt = PromptTemplate.from_template(CHART_PROMPT)
    agent = create_react_agent(llm, tools, prompt)

    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        max_iterations=5,
        handle_parsing_errors=True
    )
