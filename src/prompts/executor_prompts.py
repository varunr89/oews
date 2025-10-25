"""Executor prompt templates for agent routing."""

from typing import Dict, Any


def build_agent_query(state) -> str:
    """
    Build the query string to send to the current agent.

    Extracts the action from the current plan step and formats it
    as a natural language instruction for the agent.

    Args:
        state: Current workflow state

    Returns:
        Query string for the agent
    """
    plan = state.get("plan", {})
    current_step = state.get("current_step", 1)

    step_key = str(current_step)
    if step_key not in plan:
        return state.get("user_query", "")

    step = plan[step_key]
    action = step.get("action", "")

    # Build context-aware query
    user_query = state.get("user_query", "")

    query = f"""
User Query: {user_query}

Your Task (Step {current_step}): {action}

Previous agent outputs are available in the message history.
Use the provided tools to complete this task.
""".strip()

    return query


def should_replan(state) -> bool:
    """
    Determine if replanning is needed based on state.

    Replan conditions:
    - replan_flag is True
    - Max replans (2) not exceeded

    Args:
        state: Current workflow state

    Returns:
        True if should replan
    """
    replan_flag = state.get("replan_flag", False)
    replans = state.get("replans", 0)
    MAX_REPLANS = 2

    return replan_flag and replans < MAX_REPLANS


def is_step_complete(state) -> bool:
    """
    Check if current step is complete based on messages.

    A step is complete if the last message is from the agent
    assigned to the current step.

    Args:
        state: Current workflow state

    Returns:
        True if step is complete
    """
    messages = state.get("messages", [])
    if not messages:
        return False

    plan = state.get("plan", {})
    current_step = state.get("current_step", 1)

    step_key = str(current_step)
    if step_key not in plan:
        return False

    expected_agent = plan[step_key]["agent"]

    # Check if last message is from expected agent
    last_msg = messages[-1]
    if hasattr(last_msg, "name"):
        if last_msg.name == expected_agent:
            return True
        if expected_agent == "chart_generator" and last_msg.name == "chart_summarizer":
            return True

    return False


def is_plan_complete(state) -> bool:
    """
    Check if all plan steps are complete.

    Args:
        state: Current workflow state

    Returns:
        True if plan is complete
    """
    plan = state.get("plan", {})
    current_step = state.get("current_step", 1)

    total_steps = len(plan)

    return current_step > total_steps
