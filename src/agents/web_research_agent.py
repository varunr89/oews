"""Web Research Agent using Tavily API."""

from typing import Dict, Any
from langchain_core.messages import HumanMessage, AIMessage

from src.config.llm_factory import llm_factory
from src.tools.web_research_tools import (
    tavily_search,
    get_population_data,
    get_cost_of_living_data
)


SYSTEM_PROMPT = """You are a web research specialist. Your job is to find current, factual information from the web.

Available tools:
- tavily_search: General web search
- get_population_data: Find population statistics
- get_cost_of_living_data: Find cost of living information

Always:
1. Use appropriate tools based on the query type
2. Synthesize information from multiple sources when available
3. Cite sources (URLs) when providing information
4. Be clear when information is not found

Be concise but informative."""


def create_web_research_agent():
    """
    Create a web research agent using Tavily.

    Returns:
        Agent executor for web research
    """
    llm = llm_factory.get_implementation()

    tools = {
        "tavily_search": tavily_search,
        "get_population_data": get_population_data,
        "get_cost_of_living_data": get_cost_of_living_data
    }

    def invoke(input_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Execute web research query."""
        messages = input_dict.get("messages", [])
        query = messages[0].get("content", "") if messages else ""

        try:
            # Determine which tool to use based on query
            tool_name = "tavily_search"

            if "population" in query.lower():
                tool_name = "get_population_data"
                # Extract location from query
                query_lower = query.lower()
                # Simple extraction - can be improved
                location = query.split("of")[-1].split("in")[-1].strip(" ?.")
            elif "cost of living" in query.lower():
                tool_name = "get_cost_of_living_data"
                location = query.split("in")[-1].strip(" ?.")

            # Execute search
            if tool_name == "tavily_search":
                search_result = tools[tool_name].invoke({"query": query})
            else:
                search_result = tools[tool_name].invoke({"location": location})

            # Create synthesis prompt
            synthesis_prompt = f"""{SYSTEM_PROMPT}

Web Search Results:
{search_result}

Original Question: {query}

Based on the search results above, provide a clear, concise answer to the question.
Include relevant facts and cite sources when possible."""

            # Get LLM synthesis
            response = llm.invoke([HumanMessage(content=synthesis_prompt)])

            return {
                "messages": [AIMessage(content=response.content)],
                "intermediate_steps": [(tool_name, search_result)]
            }

        except Exception as e:
            return {
                "messages": [AIMessage(content=f"Error during web research: {str(e)}")],
                "intermediate_steps": []
            }

    class SimpleAgent:
        def __init__(self, invoke_fn):
            self.invoke = invoke_fn

    return SimpleAgent(invoke)
