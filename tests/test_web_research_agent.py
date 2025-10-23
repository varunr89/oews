import pytest
import os
from src.agents.web_research_agent import create_web_research_agent


skip_if_no_keys = pytest.mark.skipif(
    not (os.getenv('AZURE_INFERENCE_CREDENTIAL') and os.getenv('TAVILY_API_KEY')),
    reason="No API keys configured"
)


@skip_if_no_keys
def test_web_research_agent_searches_web():
    """Test that web research agent searches and returns results."""
    agent = create_web_research_agent()

    result = agent.invoke({
        "messages": [{"role": "user", "content": "What is the population of Seattle in 2024?"}]
    })

    messages = result.get("messages", [])
    assert len(messages) > 0

    final_message = str(messages[-1])
    # Should contain population data
    assert "Seattle" in final_message
    assert any(char.isdigit() for char in final_message)


@skip_if_no_keys
def test_web_research_agent_handles_no_results():
    """Test that agent handles queries with no results."""
    agent = create_web_research_agent()

    result = agent.invoke({
        "messages": [{"role": "user", "content": "xyznonexistent123city456"}]
    })

    messages = result.get("messages", [])
    final_message = str(messages[-1])

    # Should indicate no results
    assert "no" in final_message.lower() or "not found" in final_message.lower()
