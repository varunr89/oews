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
    from src.utils.trace_utils import build_sql_trace
    import json

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


    # Extract final answer from messages
    if isinstance(result, dict) and "messages" in result:
        messages = result["messages"]
        if messages and len(messages) > 0:
            last_msg = messages[-1]
            response_content = last_msg.content if hasattr(last_msg, 'content') else str(last_msg)
        else:
            response_content = "No messages in result"
    else:
        response_content = result.get("output", "No result")

    # Extract SQL execution traces from messages (LangChain 1.0+ stores tool calls in messages)
    sql_traces = []
    agent_messages = result.get("messages", [])


    # Iterate through messages to find tool calls and responses
    for i, msg in enumerate(agent_messages):
        # Check for AI messages with tool calls
        if hasattr(msg, 'tool_calls') and msg.tool_calls:
            for tool_call in msg.tool_calls:
                if tool_call.get('name') == 'execute_sql_query':
                    # Found an SQL execution - look for the corresponding ToolMessage response
                    tool_call_id = tool_call.get('id')
                    args = tool_call.get('args', {})
                    sql = args.get('sql', '')
                    params_str = args.get('params', '[]')

                    try:
                        params = json.loads(params_str) if params_str else []
                    except json.JSONDecodeError:
                        params = []

                    # Find the corresponding tool response message
                    for j in range(i + 1, len(agent_messages)):
                        next_msg = agent_messages[j]
                        if (hasattr(next_msg, 'tool_call_id') and
                            next_msg.tool_call_id == tool_call_id):
                            # Parse the tool response
                            try:
                                result_data = json.loads(next_msg.content) if isinstance(next_msg.content, str) else next_msg.content
                                if result_data.get("success"):
                                    rows = result_data.get("results", [])
                                    sql_traces.append(build_sql_trace(sql, params, rows))
                            except (json.JSONDecodeError, AttributeError, KeyError) as e:
                                logger.warning("sql_trace_extraction_error", extra={
                                    "data": {"error": str(e)}
                                })
                            break

    # Add EXECUTION_TRACE to message content if we have traces
    if sql_traces:
        response_content = f"{response_content}\n\nEXECUTION_TRACE: {json.dumps(sql_traces)}"

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
    """Describe charts in natural language and preserve CHART_SPEC markers."""
    from langgraph.types import Command
    from langchain_core.messages import AIMessage

    # Extract chart specs from last message
    messages = state.get("messages", [])
    last_msg = messages[-1] if messages else None

    if not last_msg or "CHART_SPEC" not in last_msg.content:
        summary = "No charts were generated."
        content = summary
    else:
        # Simple extraction of chart type
        import re
        chart_types = re.findall(r'"type":\s*"(\w+)"', last_msg.content)

        if chart_types:
            chart_list = ", ".join(chart_types)
            summary = f"Generated {len(chart_types)} chart(s): {chart_list}"
        else:
            summary = "Generated charts (details in message)."

        # CRITICAL: Preserve the original message content with CHART_SPEC markers
        # Append the summary but keep the CHART_SPEC data for response_formatter
        content = f"{summary}\n\n{last_msg.content}"

    return Command(
        update={
            "messages": [AIMessage(content=content, name="chart_summarizer")]
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

    # Check if charts were generated
    has_charts = any(
        hasattr(msg, 'name') and msg.name == "chart_summarizer"
        for msg in messages
    )

    if has_charts:
        prompt = f"""
You are the Synthesizer agent. Create a comprehensive written analysis to accompany the visualizations.

User Query: {user_query}

Agent Outputs:
{context}

Since charts/visualizations were generated, provide a DETAILED written analysis (3-5 paragraphs) that:

1. **Summarizes the key findings** - What does the data show? What are the main takeaways?
2. **Explains trends and patterns** - What trends are visible? How do values compare across categories/time?
3. **Highlights important insights** - What are the notable differences, outliers, or significant patterns?
4. **Provides context** - Why do these patterns matter? What do they tell us about the topic?
5. **Answers the user's question directly** - Address the specific comparison or analysis they requested

Be specific with numbers, percentages, and concrete comparisons. Make the text analysis valuable even without looking at the chart.
"""
    else:
        prompt = f"""
You are the Synthesizer agent. Create a concise text summary of the findings.

User Query: {user_query}

Agent Outputs:
{context}

Provide a clear, informative summary (2-4 sentences) that directly answers the user's question.
Focus on key insights and actionable information with specific numbers and data points.
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
    import json

    agent = create_web_research_agent()
    agent_query = state.get("agent_query", state.get("user_query", ""))

    # Run agent
    result = agent.invoke({"messages": [{"role": "user", "content": agent_query}]})

    final_message = result["messages"][-1] if result.get("messages") else None
    response_content = final_message.content if final_message else "No results from web research."

    # Extract search traces from intermediate_steps
    search_traces = []
    intermediate_steps = result.get("intermediate_steps", [])

    for action, observation in intermediate_steps:
        # Check if this is a search tool call
        if hasattr(action, 'tool') and 'search' in action.tool.lower():
            try:
                search_query = action.tool_input.get("query", "")

                # Parse observation for sources
                # Tavily returns JSON with results array
                obs_data = json.loads(observation) if isinstance(observation, str) else observation

                sources = []
                if isinstance(obs_data, dict) and "results" in obs_data:
                    for item in obs_data["results"][:5]:  # Top 5 sources
                        sources.append({
                            "url": item.get("url", ""),
                            "title": item.get("title", ""),
                            "snippet": item.get("content", "")[:200]  # First 200 chars
                        })

                search_traces.append({
                    "search_query": search_query,
                    "sources": sources
                })
            except (json.JSONDecodeError, AttributeError, KeyError):
                continue

    # Add EXECUTION_TRACE if we have traces
    if search_traces:
        response_content = f"{response_content}\n\nEXECUTION_TRACE: {json.dumps(search_traces)}"

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
