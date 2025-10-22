"""Text2SQL Agent for querying the OEWS database."""

from langchain.agents import create_react_agent, AgentExecutor
from langchain.prompts import PromptTemplate
from src.config.llm_factory import llm_factory
from src.tools.database_tools import (
    get_schema_info,
    validate_sql,
    execute_sql_query,
    search_areas,
    search_occupations
)


REACT_PROMPT = """You are a Text2SQL agent. Answer the question using the OEWS employment database.

Use these tools to explore the database and execute queries:
{tools}

IMPORTANT SECURITY: Always use parameterized queries with ? placeholders.
Never use string formatting or f-strings for user inputs.

Use this format:

Question: the input question
Thought: think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (repeat Thought/Action/Action Input/Observation as needed)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Question: {input}
Thought: {agent_scratchpad}
"""


def create_text2sql_agent() -> AgentExecutor:
    """
    Create a ReAct agent for Text2SQL queries.

    Returns:
        AgentExecutor instance
    """
    llm = llm_factory.get_implementation()

    tools = [
        get_schema_info,
        validate_sql,
        execute_sql_query,
        search_areas,
        search_occupations
    ]

    prompt = PromptTemplate.from_template(REACT_PROMPT)

    agent = create_react_agent(llm, tools, prompt)

    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        max_iterations=10,
        handle_parsing_errors=True
    )
