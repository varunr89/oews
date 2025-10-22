"""State management for LangGraph workflow."""

from typing import Dict, Any, List, Optional
from langgraph.graph import MessagesState


class State(MessagesState):
    """
    State object for the OEWS Data Agent workflow.

    Tracks the complete state of the multi-agent system including:
    - User query and plan
    - Execution control
    - Results and formatted responses
    - Model usage tracking
    """

    # Query and planning
    user_query: str = ""
    plan: Dict[str, Dict[str, Any]] = {}
    current_step: int = 1

    # Execution control
    replan_flag: bool = False
    replans: int = 0
    last_reason: str = ""
    agent_query: str = ""
    last_agent: str = ""
    enabled_agents: List[str] = []

    # Model overrides
    reasoning_model_override: Optional[str] = None
    implementation_model_override: Optional[str] = None

    # Results
    final_answer: str = ""
    formatted_response: Dict[str, Any] = {}

    # Tracking
    model_usage: Dict[str, str] = {}
