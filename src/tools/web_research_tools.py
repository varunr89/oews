"""Web research tools using Tavily API."""

import os
from typing import Optional
from langchain_core.tools import tool


@tool
def tavily_search(query: str, max_results: int = 5) -> str:
    """
    Search the web for current information using Tavily.

    Use this when you need external data not in the OEWS database,
    such as:
    - Current population statistics
    - Recent news or trends
    - Cost of living data
    - Industry reports

    Args:
        query: Search query string
        max_results: Maximum number of results (default 5)

    Returns:
        Formatted string with search results
    """
    api_key = os.getenv('TAVILY_API_KEY')

    if not api_key:
        return "Error: TAVILY_API_KEY not found in environment. Please configure API key."

    try:
        from tavily import TavilyClient

        client = TavilyClient(api_key=api_key)

        # Search with context
        response = client.search(
            query=query,
            max_results=max_results,
            include_answer=True,
            include_raw_content=False
        )

        # Format results
        if not response.get('results'):
            return f"No results found for query: {query}"

        # Include the AI-generated answer if available
        output = []
        if response.get('answer'):
            output.append(f"Summary: {response['answer']}\n")

        output.append(f"Web Search Results for '{query}':\n")

        for i, result in enumerate(response['results'][:max_results], 1):
            title = result.get('title', 'No title')
            url = result.get('url', '')
            content = result.get('content', '')[:200]  # First 200 chars

            output.append(f"{i}. {title}")
            output.append(f"   URL: {url}")
            output.append(f"   {content}...")
            output.append("")

        return "\n".join(output)

    except ImportError:
        return "Error: tavily-python package not installed. Run: pip install tavily-python"
    except Exception as e:
        return f"Error searching web: {str(e)}"


@tool
def get_population_data(location: str) -> str:
    """
    Get current population data for a location using web search.

    Args:
        location: City, state, or metro area name

    Returns:
        Population information
    """
    query = f"{location} population 2024 census data"
    return tavily_search.invoke({"query": query, "max_results": 3})


@tool
def get_cost_of_living_data(location: str) -> str:
    """
    Get cost of living information for a location.

    Args:
        location: City or metro area name

    Returns:
        Cost of living information
    """
    query = f"{location} cost of living index 2024"
    return tavily_search.invoke({"query": query, "max_results": 3})
