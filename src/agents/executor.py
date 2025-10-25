"""Executor node for LangGraph workflow routing."""

from typing import Literal, Union
from langgraph.types import Command
from langchain_core.messages import HumanMessage
from src.agents.state import State
from src.utils.logger import setup_workflow_logger
from src.prompts.executor_prompts import (
    build_agent_query,
    should_replan,
    is_step_complete,
    is_plan_complete
)

logger = setup_workflow_logger()


def executor_node(
    state: State
) -> Command[
    Literal[
        'planner',
        'cortex_researcher',
        'web_researcher',
        'chart_generator',
        'synthesizer',
        'response_formatter'
    ]
]:
    """
    The Executor is the traffic cop of the workflow.

    Responsibilities:
    1. Check if replanning is needed
    2. Check if current step is complete
    3. Check if entire plan is complete
    4. Route to the appropriate next node

    Routing Logic:
    - If replan_flag and replans < MAX_REPLANS → go to planner
    - If plan complete → go to response_formatter
    - If current step complete → advance to next step's agent
    - Otherwise → stay on current step's agent

    Args:
        state: Current workflow state

    Returns:
        Command to route to next node
    """
    # LOG: Current state
    logger.debug("executor_state", extra={
        "data": {
            "current_step": state.get("current_step", 1),
            "replan_flag": state.get("replan_flag", False),
            "plan_steps": len(state.get("plan", {}))
        }
    })

    # 1. Check if we need to replan
    if should_replan(state):
        replans = state.get("replans", 0)

        logger.debug("executor_routing", extra={
            "data": {
                "decision": "replan",
                "replans": replans + 1,
                "reason": "replan_flag set"
            }
        })

        return Command(
            update={
                "replans": replans + 1,
                "replan_flag": False,  # Reset flag
                "messages": [HumanMessage(
                    content=f"Replanning (attempt {replans + 1})",
                    name="executor"
                )]
            },
            goto="planner"
        )

    # 2. Check if plan is complete
    if is_plan_complete(state):
        return Command(
            update={
                "messages": [HumanMessage(
                    content="Plan complete, formatting response",
                    name="executor"
                )]
            },
            goto="response_formatter"
        )

    # 3. Determine current or next agent
    plan = state.get("plan", {})
    current_step = state.get("current_step", 1)

    # If current step is complete, advance
    if is_step_complete(state):
        current_step += 1

    step_key = str(current_step)
    if step_key not in plan:
        # Plan exhausted, go to formatter
        return Command(
            update={},
            goto="response_formatter"
        )

    # 4. Route to the agent for current step
    target_agent = plan[step_key]["agent"]

    # LOG: DIAGNOSTIC - Check state vs local variable mismatch
    logger.debug("executor_step_comparison", extra={
        "data": {
            "local_current_step": current_step,
            "state_current_step": state.get("current_step", 1),
            "target_agent": target_agent,
            "expected_action": plan[step_key].get("action", "")
        }
    })

    # Pass the incremented current_step explicitly to avoid state mismatch
    agent_query = build_agent_query(state, current_step=current_step)

    # LOG: Routing decision
    logger.debug("executor_routing", extra={
        "data": {
            "decision": "route_to_agent",
            "target_agent": target_agent,
            "step": current_step,
            "total_steps": len(plan),
            "agent_query": agent_query[:100] + "..." if len(agent_query) > 100 else agent_query
        }
    })

    # Map agent names to valid node names
    agent_mapping = {
        "cortex_researcher": "cortex_researcher",
        "web_researcher": "web_researcher",
        "chart_generator": "chart_generator",
        "synthesizer": "synthesizer"
    }

    goto_node = agent_mapping.get(target_agent, "response_formatter")

    return Command(
        update={
            "current_step": current_step,
            "agent_query": agent_query,
            "last_agent": target_agent,
            "messages": [HumanMessage(
                content=f"Routing to {target_agent} (step {current_step})",
                name="executor"
            )]
        },
        goto=goto_node
    )
