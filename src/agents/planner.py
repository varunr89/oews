"""Planner node for LangGraph workflow."""

from typing import Literal
from langgraph.types import Command
from langchain.schema import HumanMessage
from src.config.llm_factory import llm_factory
from src.prompts.planner_prompts import plan_prompt
from src.agents.state import State
import json


def planner_node(state: State) -> Command[Literal['executor']]:
    """
    Runs the planning LLM and stores the resulting plan in state.

    Uses the configured reasoning model (high capability for planning).

    Args:
        state: Current workflow state

    Returns:
        Command to route to executor
    """
    # Get reasoning model from factory
    reasoning_llm = llm_factory.get_reasoning()

    # Track which model was used
    model_key = state.get("reasoning_model_override") or "deepseek-r1"

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

    except json.JSONDecodeError as e:
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
                content=json.dumps(parsed_plan),
                name="replan" if replan else "initial_plan"
            )],
            "user_query": state.get("user_query", state.get("messages", [{}])[0].content if state.get("messages") else ""),
            "current_step": 1 if not replan else state.get("current_step", 1),
            "replan_flag": False,
            "last_reason": "",
            "enabled_agents": state.get("enabled_agents", ["cortex_researcher", "synthesizer"]),
            # Track model usage
            "model_usage": {**(state.get("model_usage") or {}), "planner": model_key}
        },
        goto="executor"
    )
