"""Text2SQL Agent for querying the OEWS database with ReAct pattern."""

from typing import Dict, Any, List, Optional
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain.agents import create_agent

from src.config.llm_factory import llm_factory
from src.utils.logger import setup_workflow_logger
from src.tools.database_tools import (
    get_schema_info,
    validate_sql,
    execute_sql_query,
    search_areas,
    search_occupations
)

logger = setup_workflow_logger("oews.workflow.text2sql")


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


def create_text2sql_agent(override_key: Optional[str] = None):
    """
    Create a Text2SQL ReAct agent.

    Args:
        override_key: Optional model key to use instead of default implementation model

    Returns:
        Agent executor that can be invoked with input dict
    """
    # Get implementation model (with optional override)
    llm = llm_factory.get_implementation(override_key=override_key)

    # Track actual model used
    actual_model = llm.model if hasattr(llm, 'model') else \
                   llm.model_name if hasattr(llm, 'model_name') else "unknown"

    logger.info("text2sql_agent_created", extra={
        "data": {
            "model_requested": override_key or "default",
            "model_actual": actual_model
        }
    })

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

        # LOG: Agent input
        logger.debug("agent_input", extra={
            "data": {
                "query": query,
                "messages_count": len(messages)
            }
        })

        try:
            # Get schema
            schema = tools["get_schema_info"].invoke({})

            # LOG: Schema retrieved
            logger.debug("schema_retrieved", extra={
                "data": {
                    "schema_length": len(schema)
                }
            })

            # Create a prompt for the LLM
            prompt = f"""{SYSTEM_PROMPT}

Database Schema:
{schema}

Question: {query}

Generate a SQL query to answer this question. Return ONLY the SQL query."""

            response = llm.invoke([HumanMessage(content=prompt)])
            sql_query = response.content.strip()

            # LOG: SQL generated
            logger.debug("sql_generated", extra={
                "data": {
                    "sql": sql_query,
                    "sql_length": len(sql_query)
                }
            })

            # Execute the query
            result = tools["execute_sql_query"].invoke({"sql": sql_query})

            # Parse result to get row count
            import json
            try:
                result_data = json.loads(result)
                row_count = result_data.get("row_count", 0)
                success = result_data.get("success", False)

                # LOG: Query results
                logger.debug("query_results", extra={
                    "data": {
                        "success": success,
                        "row_count": row_count,
                        "result_preview": result[:200] + "..." if len(result) > 200 else result
                    }
                })

            except json.JSONDecodeError:
                logger.warning("result_parse_error", extra={
                    "data": {"result": result[:200]}
                })

            return {
                "messages": [AIMessage(content=f"Query result: {result}")],
                "intermediate_steps": []
            }

        except Exception as e:
            # LOG: Error
            logger.error("agent_error", extra={
                "data": {
                    "error": str(e),
                    "error_type": type(e).__name__
                }
            })

            return {
                "messages": [AIMessage(content=f"Error: {str(e)}")],
                "intermediate_steps": []
            }

    class SimpleAgent:
        def __init__(self, invoke_fn):
            self.invoke = invoke_fn

    return SimpleAgent(invoke)
