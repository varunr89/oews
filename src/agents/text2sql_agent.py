"""Text2SQL Agent for querying the OEWS database with ReAct pattern."""

from typing import Dict, Any, List
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain.agents import create_agent

from src.config.llm_factory import llm_factory
from src.tools.database_tools import (
    get_schema_info,
    validate_sql,
    execute_sql_query,
    search_areas,
    search_occupations
)


SYSTEM_PROMPT = """You are a Text2SQL expert agent. Your job is to answer questions about OEWS employment data by:

1. Understanding the database schema using get_schema_info
2. Finding exact area/occupation names using search_areas and search_occupations
3. Validating your SQL queries using validate_sql
4. Executing queries using execute_sql_query with parameterized queries

CRITICAL SECURITY RULES:
- ALWAYS use parameterized queries with ? placeholders
- NEVER use f-strings or string formatting with user input
- Pass wildcard patterns (%) as part of the parameter value, NOT in the SQL string

Example CORRECT usage:
sql = "SELECT * FROM oews_data WHERE AREA_TITLE LIKE ? LIMIT ?"
params = ['%Seattle%', 10]
execute_sql_query(sql=sql, params=json.dumps(params))

Example WRONG usage:
sql = f"SELECT * FROM oews_data WHERE AREA_TITLE LIKE '%{area}%'"  # SQL INJECTION!

Work step-by-step:
1. Use get_schema_info to understand available columns
2. Use search tools to find exact names
3. Construct parameterized SQL query
4. Validate with validate_sql
5. Execute with execute_sql_query
6. Analyze results and answer the question

Be thorough but concise. If you can't find data, say so clearly."""


def create_text2sql_agent():
    """
    Create a ReAct Text2SQL agent with tool calling.

    Returns:
        Agent graph with proper tool calling setup
    """
    llm = llm_factory.get_implementation()

    # Ensure LLM supports tool calling
    if not hasattr(llm, 'bind_tools'):
        # Fallback to simple implementation for models without tool calling
        return _create_simple_agent(llm)

    tools = [
        get_schema_info,
        validate_sql,
        execute_sql_query,
        search_areas,
        search_occupations
    ]

    # Create agent using LangChain 1.0 API
    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=SYSTEM_PROMPT
    )

    return agent


def _create_simple_agent(llm):
    """Fallback simple agent for models without tool calling."""
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

        try:
            # Get schema
            schema = tools["get_schema_info"].invoke({})

            # Create a prompt for the LLM
            prompt = f"""{SYSTEM_PROMPT}

Database Schema:
{schema}

Question: {query}

Generate a SQL query to answer this question. Return ONLY the SQL query."""

            response = llm.invoke([HumanMessage(content=prompt)])
            sql_query = response.content.strip()

            # Execute the query
            result = tools["execute_sql_query"].invoke({"sql": sql_query})

            return {
                "messages": [AIMessage(content=f"Query result: {result}")],
                "intermediate_steps": []
            }

        except Exception as e:
            return {
                "messages": [AIMessage(content=f"Error: {str(e)}")],
                "intermediate_steps": []
            }

    class SimpleAgent:
        def __init__(self, invoke_fn):
            self.invoke = invoke_fn

    return SimpleAgent(invoke)
