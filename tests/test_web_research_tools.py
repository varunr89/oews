import pytest
import os
from src.tools.web_research_tools import tavily_search


skip_if_no_tavily = pytest.mark.skipif(
    not os.getenv('TAVILY_API_KEY'),
    reason="No Tavily API key configured"
)


@skip_if_no_tavily
def test_tavily_search_returns_results():
    """Test that Tavily search returns web results."""
    result = tavily_search.invoke({
        "query": "Seattle median income 2024"
    })

    assert isinstance(result, str)
    assert len(result) > 0
    # Should contain some relevant information
    assert "Seattle" in result or "income" in result or "$" in result


@skip_if_no_tavily
def test_tavily_search_handles_no_results():
    """Test that Tavily handles queries with no results gracefully."""
    result = tavily_search.invoke({
        "query": "xyzabc123nonexistent456"
    })

    assert isinstance(result, str)
    # Should indicate no results found
    assert "no results" in result.lower() or "not found" in result.lower()


def test_tavily_search_requires_api_key():
    """Test that Tavily search validates API key presence."""
    import os
    old_key = os.environ.get('TAVILY_API_KEY')

    try:
        # Remove key temporarily
        if 'TAVILY_API_KEY' in os.environ:
            del os.environ['TAVILY_API_KEY']

        # Should handle missing key gracefully
        result = tavily_search.invoke({"query": "test"})
        assert "api key" in result.lower() or "error" in result.lower()

    finally:
        # Restore key
        if old_key:
            os.environ['TAVILY_API_KEY'] = old_key
