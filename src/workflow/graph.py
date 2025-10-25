"""LangGraph workflow assembly."""

from langgraph.graph import StateGraph, START, END
from src.agents.state import State
from src.agents.planner import planner_node
from src.agents.executor import executor_node
from src.agents.response_formatter import response_formatter_node
from src.agents.text2sql_agent import create_text2sql_agent
from src.agents.chart_generator import create_chart_generator_agent


def cortex_researcher_node(state: State):
    """Wrapper for Text2SQL agent."""
    from langgraph.types import Command
    from langchain_core.messages import AIMessage
    from src.utils.logger import setup_workflow_logger

    logger = setup_workflow_logger("oews.workflow.cortex_researcher")

    agent = create_text2sql_agent()
    agent_query = state.get("agent_query", state.get("user_query", ""))

    # LOG: DIAGNOSTIC - Show what query cortex_researcher receives
    logger.debug("cortex_researcher_input", extra={
        "data": {
            "agent_query_from_state": state.get("agent_query", "NOT SET"),
            "user_query_from_state": state.get("user_query", ""),
            "current_step_from_state": state.get("current_step", 1),
            "actual_query_used": agent_query[:200] + "..." if len(agent_query) > 200 else agent_query
        }
    })

    # Run agent with correct input format
    result = agent.invoke({"messages": [{"role": "user", "content": agent_query}]})

    # LOG: Agent result structure
    logger.debug("agent_result", extra={
        "data": {
            "result_keys": list(result.keys()) if isinstance(result, dict) else "not a dict",
            "result_type": str(type(result)),
            "result_preview": str(result)[:500]
        }
    })

    # Extract final answer from messages
    if isinstance(result, dict) and "messages" in result:
        messages = result["messages"]
        if messages and len(messages) > 0:
            last_msg = messages[-1]
            response_content = last_msg.content if hasattr(last_msg, 'content') else str(last_msg)
        else:
            response_content = "No messages in result"
    else:
        # Fallback to output key
        response_content = result.get("output", "No result")

    return Command(
        update={
            "messages": [AIMessage(content=response_content, name="cortex_researcher")],
            "model_usage": {
                **(state.get("model_usage") or {}),
                "cortex_researcher": state.get("implementation_model_override") or "deepseek-v3"
            }
        },
        goto="executor"
    )


def chart_generator_node(state: State):
    """Wrapper for Chart Generator agent."""
    from langgraph.types import Command
    from langchain_core.messages import AIMessage
    from src.utils.logger import setup_workflow_logger

    logger = setup_workflow_logger("oews.workflow.chart_generator")

    agent = create_chart_generator_agent()
    agent_query = state.get("agent_query", state.get("user_query", ""))

    # Run agent with standard message payload
    result = agent.invoke({
        "messages": [{"role": "user", "content": agent_query}]
    })

    # LOG: Agent result
    logger.debug("agent_result", extra={
        "data": {
            "result_keys": list(result.keys()) if isinstance(result, dict) else "not a dict",
            "result_type": str(type(result))
        }
    })

    response_content = "No charts generated"

    if isinstance(result, dict):
        messages = result.get("messages") or []
        if messages:
            last_msg = messages[-1]
            if isinstance(last_msg, dict):
                response_content = last_msg.get("content", response_content)
            elif hasattr(last_msg, "content"):
                response_content = getattr(last_msg, "content", response_content)
        elif "output" in result:
            response_content = result.get("output", response_content)
    elif hasattr(result, "content"):
        response_content = getattr(result, "content", response_content)

    return Command(
        update={
            "messages": [AIMessage(content=response_content, name="chart_generator")],
            "model_usage": {
                **(state.get("model_usage") or {}),
                "chart_generator": state.get("implementation_model_override") or "deepseek-v3"
            }
        },
        goto="chart_summarizer"
    )


def chart_summarizer_node(state: State):
    """Describe charts in natural language."""
    from langgraph.types import Command
    from langchain_core.messages import AIMessage

    # Extract chart specs from last message
    messages = state.get("messages", [])
    last_msg = messages[-1] if messages else None

    if not last_msg or "CHART_SPEC" not in last_msg.content:
        summary = "No charts were generated."
    else:
        # Simple extraction of chart type
        import re
        chart_types = re.findall(r'"type":\s*"(\w+)"', last_msg.content)

        if chart_types:
            chart_list = ", ".join(chart_types)
            summary = f"Generated {len(chart_types)} chart(s): {chart_list}"
        else:
            summary = "Generated charts (details in message)."

    return Command(
        update={
            "messages": [AIMessage(content=summary, name="chart_summarizer")]
        },
        goto="executor"
    )


def synthesizer_node(state: State):
    """Create text summary of all findings."""
    from langgraph.types import Command
    from langchain_core.messages import AIMessage, HumanMessage
    from src.config.llm_factory import llm_factory

    # Get implementation model
    impl_llm = llm_factory.get_implementation()

    # Build summary prompt
    messages = state.get("messages", [])
    user_query = state.get("user_query", "")

    context = "\n\n".join([
        f"**{msg.name or 'message'}:** {msg.content}"
        for msg in messages
        if hasattr(msg, 'name') and msg.name in ["cortex_researcher", "web_researcher", "chart_summarizer"]
    ])

    prompt = f"""
You are the Synthesizer agent. Create a concise text summary of the findings.

User Query: {user_query}

Agent Outputs:
{context}

Provide a 2-3 sentence summary that directly answers the user's question.
Focus on key insights and actionable information.
"""

    # Invoke LLM
    response = impl_llm.invoke([HumanMessage(content=prompt)])

    return Command(
        update={
            "messages": [AIMessage(content=response.content, name="synthesizer")],
            "final_answer": response.content,
            "model_usage": {
                **(state.get("model_usage") or {}),
                "synthesizer": state.get("implementation_model_override") or "deepseek-v3"
            }
        },
        goto="executor"
    )


def web_researcher_node(state: State):
    """Web research agent for external data."""
    from langgraph.types import Command
    from langchain_core.messages import AIMessage
    from src.agents.web_research_agent import create_web_research_agent

    agent = create_web_research_agent()
    agent_query = state.get("agent_query", state.get("user_query", ""))

    # Run agent
    result = agent.invoke({"messages": [{"role": "user", "content": agent_query}]})

    final_message = result["messages"][-1] if result.get("messages") else None
    response_content = final_message.content if final_message else "No results from web research."

    return Command(
        update={
            "messages": [AIMessage(content=response_content, name="web_researcher")],
            "model_usage": {
                **(state.get("model_usage") or {}),
                "web_researcher": state.get("implementation_model_override") or "deepseek-v3"
            }
        },
        goto="executor"
    )


def create_workflow_graph():
    """
    Create and compile the complete LangGraph workflow.

    Returns:
        Compiled StateGraph
    """
    # Create graph
    graph = StateGraph(State)

    # Add nodes
    graph.add_node("planner", planner_node)
    graph.add_node("executor", executor_node)
    graph.add_node("cortex_researcher", cortex_researcher_node)
    graph.add_node("chart_generator", chart_generator_node)
    graph.add_node("chart_summarizer", chart_summarizer_node)
    graph.add_node("synthesizer", synthesizer_node)
    graph.add_node("web_researcher", web_researcher_node)
    graph.add_node("response_formatter", response_formatter_node)

    # Define edges
    # START always goes to planner
    graph.add_edge(START, "planner")

    # Planner goes to executor (specified in planner_node Command)
    # Executor routes to agents (specified in executor_node Command)
    # Agents return to executor (specified in agent node Commands)
    # Response formatter goes to END
    graph.add_edge("response_formatter", END)

    # Compile
    return graph.compile()
