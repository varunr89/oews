import pytest
import os
from src.agents.text2sql_agent import create_text2sql_agent


skip_if_no_keys = pytest.mark.skipif(
    not os.getenv('AZURE_INFERENCE_CREDENTIAL'),
    reason="No API keys configured"
)


@skip_if_no_keys
def test_text2sql_agent_uses_schema_tool():
    """Test that agent uses get_schema_info tool."""
    agent = create_text2sql_agent()

    # Query that requires schema understanding
    result = agent.invoke({
        "messages": [{"role": "user", "content": "What columns are in the oews_data table?"}]
    })

    messages = result.get("messages", [])
    assert len(messages) > 0

    # Should mention AREA_TITLE or other columns
    final_message = str(messages[-1])
    assert "AREA_TITLE" in final_message or "OCC_TITLE" in final_message


@skip_if_no_keys
def test_text2sql_agent_uses_search_tool():
    """Test that agent uses search_areas tool."""
    agent = create_text2sql_agent()

    result = agent.invoke({
        "messages": [{"role": "user", "content": "Find areas with Seattle in the name"}]
    })

    messages = result.get("messages", [])
    final_message = str(messages[-1])

    # Should find Seattle areas
    assert "Seattle" in final_message


@skip_if_no_keys
def test_text2sql_agent_handles_invalid_query():
    """Test that agent handles invalid SQL gracefully."""
    agent = create_text2sql_agent()

    result = agent.invoke({
        "messages": [{"role": "user", "content": "DROP TABLE oews_data"}]
    })

    messages = result.get("messages", [])
    final_message = str(messages[-1])

    # Should reject dangerous operation
    assert "not allowed" in final_message.lower() or "error" in final_message.lower()
