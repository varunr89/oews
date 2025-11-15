"""Planner node for LangGraph workflow."""

from typing import Literal
from langgraph.types import Command
from langchain_core.messages import HumanMessage
from src.config.llm_factory import llm_factory
from src.prompts.planner_prompts import plan_prompt
from src.agents.state import State
from src.utils.logger import setup_workflow_logger
import json

logger = setup_workflow_logger()


def planner_node(state: State) -> Command[Literal['executor']]:
    """
    Runs the planning LLM and stores the resulting plan in state.

    Uses the configured reasoning model (high capability for planning),
    or the model specified in state.reasoning_model if provided.

    Returns:
        Command updating state with plan and routing to executor
    """
    user_query = state.get("user_query", state.get("messages", [{}])[0].content if state.get("messages") else "")

    # Get reasoning model (with optional override from state)
    reasoning_model_key = state.get("reasoning_model")
    reasoning_llm = llm_factory.get_reasoning(override_key=reasoning_model_key)

    # Track which model was actually used
    actual_model = reasoning_llm.model if hasattr(reasoning_llm, 'model') else \
                   reasoning_llm.model_name if hasattr(reasoning_llm, 'model_name') else "unknown"

    # LOG: Input query
    logger.debug("planner_input", extra={
        "data": {
            "user_query": user_query,
            "enabled_agents": state.get("enabled_agents", []),
            "model_requested": reasoning_model_key or "default",
            "model_actual": actual_model
        }
    })

    # Invoke LLM
    llm_reply = reasoning_llm.invoke([plan_prompt(state)])

    # Parse and validate JSON
    try:
        content_str = llm_reply.content if isinstance(llm_reply.content, str) else str(llm_reply.content)

        # Handle DeepSeek R1 <think> tags
        import re
        content_str = re.sub(r'<think>.*?</think>', '', content_str, flags=re.DOTALL)

        # Extract JSON
        start_idx = content_str.find('{')
        if start_idx == -1:
            raise json.JSONDecodeError("No JSON object found", content_str, 0)

        brace_count = 0
        json_end_idx = start_idx

        for i in range(start_idx, len(content_str)):
            if content_str[i] == '{':
                brace_count += 1
            elif content_str[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    json_end_idx = i + 1
                    break

        json_str = content_str[start_idx:json_end_idx]
        parsed_plan = json.loads(json_str)

        # LOG: Generated plan
        logger.debug("planner_output", extra={
            "data": {
                "plan": parsed_plan,
                "steps": len(parsed_plan)
            }
        })

    except json.JSONDecodeError as e:
        logger.error("planner_parse_error", extra={
            "data": {
                "error": str(e),
                "content": llm_reply.content[:200] if hasattr(llm_reply, 'content') else ""
            }
        })
        # Fallback to simple plan
        parsed_plan = {
            "1": {"agent": "cortex_researcher", "action": "Query database"},
            "2": {"agent": "synthesizer", "action": "Summarize results"}
        }

    replan = state.get("replan_flag", False)

    return Command(
        update={
            "plan": parsed_plan,
            "messages": [HumanMessage(
                content=f"{json.dumps(parsed_plan)}\n\nEXECUTION_TRACE: {json.dumps({'plan': parsed_plan, 'reasoning_model': actual_model, 'steps': len(parsed_plan)})}",
                name="replan" if replan else "initial_plan"
            )],
            "user_query": state.get("user_query", state.get("messages", [{}])[0].content if state.get("messages") else ""),
            "current_step": 1 if not replan else state.get("current_step", 1),
            "replan_flag": False,
            "last_reason": "",
            "enabled_agents": state.get("enabled_agents", ["cortex_researcher", "synthesizer"]),
            # Track model usage
            "model_usage": {**(state.get("model_usage") or {}), "planner": actual_model}
        },
        goto="executor"
    )
