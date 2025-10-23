"""Text2SQL Agent for querying the OEWS database."""

from typing import Dict, Any
from src.config.llm_factory import llm_factory
from src.tools.database_tools import (
    get_schema_info,
    validate_sql,
    execute_sql_query,
    search_areas,
    search_occupations
)


def create_text2sql_agent():
    """
    Create a simple function-based agent for Text2SQL queries.

    Returns:
        Callable agent function
    """
    llm = llm_factory.get_implementation()

    tools = {
        "get_schema_info": get_schema_info,
        "validate_sql": validate_sql,
        "execute_sql_query": execute_sql_query,
        "search_areas": search_areas,
        "search_occupations": search_occupations
    }

    def invoke(input_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Simple agent that executes SQL queries."""
        messages = input_dict.get("messages", [])
        query = messages[0].get("content", "") if messages else ""

        # Simple implementation: directly use tools
        try:
            # Get schema
            schema = tools["get_schema_info"].invoke({})

            # Create a prompt for the LLM
            prompt = f"""You are a Text2SQL agent. Answer this question using the OEWS database.

Database Schema:
{schema}

IMPORTANT: Always use parameterized queries with ? placeholders for user inputs.

Question: {query}

Generate a SQL query to answer this question. Return ONLY the SQL query."""

            from langchain_core.messages import HumanMessage
            response = llm.invoke([HumanMessage(content=prompt)])

            sql_query = response.content.strip()

            # Execute the query
            result = tools["execute_sql_query"].invoke({"sql": sql_query})

            return {
                "messages": [{"role": "assistant", "content": f"Query result: {result}"}]
            }

        except Exception as e:
            return {
                "messages": [{"role": "assistant", "content": f"Error: {str(e)}"}]
            }

    class SimpleAgent:
        def __init__(self, invoke_fn):
            self.invoke = invoke_fn

    return SimpleAgent(invoke)
