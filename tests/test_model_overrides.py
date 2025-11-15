"""Tests for model override functionality."""
import pytest
from unittest.mock import Mock, patch
from src.agents.state import State
from src.agents.planner import planner_node


def test_planner_uses_reasoning_model_override():
    """Test that planner respects reasoning_model from state."""
    state = State(
        user_query="Test query",
        reasoning_model="deepseek-reasoner",  # Override key
        messages=[],
        plan={},
        current_step=0,
        max_steps=5,
        replans=0,
        model_usage={}
    )

    with patch('src.agents.planner.llm_factory') as mock_factory:
        mock_llm = Mock()
        mock_llm.invoke.return_value = Mock(content='{"step_1": {"agent": "test"}}')
        mock_llm.model = "deepseek-reasoner"  # Simulate model attribute
        mock_factory.get_reasoning.return_value = mock_llm

        planner_node(state)

        # Verify get_reasoning was called with override_key parameter
        mock_factory.get_reasoning.assert_called_once_with(override_key="deepseek-reasoner")


def test_planner_uses_default_reasoning_model_when_no_override():
    """Test that planner uses default when no override specified."""
    state = State(
        user_query="Test query",
        messages=[],
        plan={},
        current_step=0,
        max_steps=5,
        replans=0,
        model_usage={}
    )

    with patch('src.agents.planner.llm_factory') as mock_factory:
        mock_llm = Mock()
        mock_llm.invoke.return_value = Mock(content='{"step_1": {"agent": "test"}}')
        mock_llm.model = "default-reasoning"
        mock_factory.get_reasoning.return_value = mock_llm

        planner_node(state)

        # Verify get_reasoning was called with None (use default)
        mock_factory.get_reasoning.assert_called_once_with(override_key=None)
