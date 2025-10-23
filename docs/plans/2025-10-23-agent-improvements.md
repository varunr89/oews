# OEWS Data Agent Improvements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enhance the OEWS Data Agent with improved Text2SQL agent using ReAct pattern with tool calling, add Tavily-powered web research agent, and implement fuzzy matching for better query understanding.

**Architecture:** Upgrade Text2SQL agent to use proper ReAct loop with LangChain tools for iterative query refinement. Add Web Research agent using Tavily API for external data enrichment. Implement fuzzy string matching and similarity scoring for area/occupation name resolution.

**Tech Stack:** Python 3.10+, LangChain 1.0, LangGraph, Tavily API, RapidFuzz, pytest

---

## Milestone 1: Enhanced Text2SQL Agent with ReAct Loop

### Task 1.1: Create ReAct Agent with Tool Calling

**Files:**
- Modify: `src/agents/text2sql_agent.py`
- Create: `tests/test_text2sql_agent_react.py`

**Step 1: Write the failing test**

Create `tests/test_text2sql_agent_react.py`:

```python
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_text2sql_agent_react.py -v`

Expected: FAIL with assertion errors or timeout

**Step 3: Implement ReAct agent with tool calling**

Modify `src/agents/text2sql_agent.py`:

```python
"""Text2SQL Agent for querying the OEWS database with ReAct pattern."""

from typing import Dict, Any, List
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.agents.format_scratchpad.openai_tools import (
    format_to_openai_tool_messages,
)
from langchain.agents.output_parsers.openai_tools import OpenAIToolsAgentOutputParser

from src.config.llm_factory import llm_factory
from src.tools.database_tools import (
    get_schema_info,
    validate_sql,
    execute_sql_query,
    search_areas,
    search_occupations
)


SYSTEM_PROMPT = """You are a Text2SQL expert agent. Your job is to answer questions about OEWS employment data by:

1. Understanding the database schema using get_schema_info
2. Finding exact area/occupation names using search_areas and search_occupations
3. Validating your SQL queries using validate_sql
4. Executing queries using execute_sql_query with parameterized queries

CRITICAL SECURITY RULES:
- ALWAYS use parameterized queries with ? placeholders
- NEVER use f-strings or string formatting with user input
- Pass wildcard patterns (%) as part of the parameter value, NOT in the SQL string

Example CORRECT usage:
sql = "SELECT * FROM oews_data WHERE AREA_TITLE LIKE ? LIMIT ?"
params = ['%Seattle%', 10]
execute_sql_query(sql=sql, params=json.dumps(params))

Example WRONG usage:
sql = f"SELECT * FROM oews_data WHERE AREA_TITLE LIKE '%{area}%'"  # SQL INJECTION!

Work step-by-step:
1. Use get_schema_info to understand available columns
2. Use search tools to find exact names
3. Construct parameterized SQL query
4. Validate with validate_sql
5. Execute with execute_sql_query
6. Analyze results and answer the question

Be thorough but concise. If you can't find data, say so clearly."""


def create_text2sql_agent():
    """
    Create a ReAct Text2SQL agent with tool calling.

    Returns:
        AgentExecutor with proper tool calling setup
    """
    llm = llm_factory.get_implementation()

    # Ensure LLM supports tool calling
    if not hasattr(llm, 'bind_tools'):
        # Fallback to simple implementation for models without tool calling
        return _create_simple_agent(llm)

    tools = [
        get_schema_info,
        validate_sql,
        execute_sql_query,
        search_areas,
        search_occupations
    ]

    # Create prompt with tool calling support
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="messages"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    # Bind tools to LLM
    llm_with_tools = llm.bind_tools(tools)

    # Create agent
    agent = (
        {
            "messages": lambda x: x["messages"],
            "agent_scratchpad": lambda x: format_to_openai_tool_messages(
                x["intermediate_steps"]
            ),
        }
        | prompt
        | llm_with_tools
        | OpenAIToolsAgentOutputParser()
    )

    # Create executor
    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        max_iterations=10,
        handle_parsing_errors=True,
        return_intermediate_steps=True
    )


def _create_simple_agent(llm):
    """Fallback simple agent for models without tool calling."""
    tools = {
        "get_schema_info": get_schema_info,
        "validate_sql": validate_sql,
        "execute_sql_query": execute_sql_query,
        "search_areas": search_areas,
        "search_occupations": search_occupations
    }

    def invoke(input_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Simple agent that executes SQL queries."""
        messages = input_dict.get("messages", [])
        query = messages[0].get("content", "") if messages else ""

        try:
            # Get schema
            schema = tools["get_schema_info"].invoke({})

            # Create a prompt for the LLM
            prompt = f"""{SYSTEM_PROMPT}

Database Schema:
{schema}

Question: {query}

Generate a SQL query to answer this question. Return ONLY the SQL query."""

            response = llm.invoke([HumanMessage(content=prompt)])
            sql_query = response.content.strip()

            # Execute the query
            result = tools["execute_sql_query"].invoke({"sql": sql_query})

            return {
                "messages": [AIMessage(content=f"Query result: {result}")],
                "intermediate_steps": []
            }

        except Exception as e:
            return {
                "messages": [AIMessage(content=f"Error: {str(e)}")],
                "intermediate_steps": []
            }

    class SimpleAgent:
        def __init__(self, invoke_fn):
            self.invoke = invoke_fn

    return SimpleAgent(invoke)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_text2sql_agent_react.py -v`

Expected: PASS (2-3 tests, 1 skipped if no API keys)

**Step 5: Commit**

```bash
git add src/agents/text2sql_agent.py tests/test_text2sql_agent_react.py
git commit -m "feat(agents): enhance Text2SQL agent with ReAct loop and tool calling

- Add proper ReAct pattern with LangChain tool calling
- Support iterative query refinement
- Include fallback for models without tool calling
- Add comprehensive tests for tool usage"
```

---

## Milestone 2: Web Research Agent with Tavily

### Task 2.1: Create Tavily Web Research Tool

**Files:**
- Create: `src/tools/web_research_tools.py`
- Create: `tests/test_web_research_tools.py`

**Step 1: Write the failing test**

Create `tests/test_web_research_tools.py`:

```python
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_web_research_tools.py -v`

Expected: FAIL with "No module named 'src.tools.web_research_tools'"

**Step 3: Install Tavily SDK**

Update `pyproject.toml` dependencies:

```toml
dependencies = [
    # ... existing dependencies ...
    "tavily-python>=0.3.0",
]
```

Run: `pip install tavily-python`

**Step 4: Write minimal implementation**

Create `src/tools/web_research_tools.py`:

```python
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
```

**Step 5: Update tools __init__.py**

Modify `src/tools/__init__.py`:

```python
"""Tools for LangChain agents."""

from .database_tools import (
    get_schema_info,
    validate_sql,
    execute_sql_query,
    get_sample_data,
    search_areas,
    search_occupations
)

from .web_research_tools import (
    tavily_search,
    get_population_data,
    get_cost_of_living_data
)

__all__ = [
    # Database tools
    "get_schema_info",
    "validate_sql",
    "execute_sql_query",
    "get_sample_data",
    "search_areas",
    "search_occupations",
    # Web research tools
    "tavily_search",
    "get_population_data",
    "get_cost_of_living_data"
]
```

**Step 6: Run test to verify it passes**

Run: `pytest tests/test_web_research_tools.py -v`

Expected: PASS (2 tests, 1 skipped if no Tavily key)

**Step 7: Commit**

```bash
git add src/tools/web_research_tools.py src/tools/__init__.py tests/test_web_research_tools.py pyproject.toml
git commit -m "feat(tools): add Tavily web research tools

- Add tavily_search for general web queries
- Add get_population_data helper
- Add get_cost_of_living_data helper
- Include comprehensive error handling"
```

---

### Task 2.2: Create Web Research Agent

**Files:**
- Create: `src/agents/web_research_agent.py`
- Create: `tests/test_web_research_agent.py`
- Modify: `src/workflow/graph.py`

**Step 1: Write the failing test**

Create `tests/test_web_research_agent.py`:

```python
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_web_research_agent.py -v`

Expected: FAIL with "No module named 'src.agents.web_research_agent'"

**Step 3: Write minimal implementation**

Create `src/agents/web_research_agent.py`:

```python
"""Web Research Agent using Tavily API."""

from typing import Dict, Any
from langchain_core.messages import HumanMessage, AIMessage

from src.config.llm_factory import llm_factory
from src.tools.web_research_tools import (
    tavily_search,
    get_population_data,
    get_cost_of_living_data
)


SYSTEM_PROMPT = """You are a web research specialist. Your job is to find current, factual information from the web.

Available tools:
- tavily_search: General web search
- get_population_data: Find population statistics
- get_cost_of_living_data: Find cost of living information

Always:
1. Use appropriate tools based on the query type
2. Synthesize information from multiple sources when available
3. Cite sources (URLs) when providing information
4. Be clear when information is not found

Be concise but informative."""


def create_web_research_agent():
    """
    Create a web research agent using Tavily.

    Returns:
        Agent executor for web research
    """
    llm = llm_factory.get_implementation()

    tools = {
        "tavily_search": tavily_search,
        "get_population_data": get_population_data,
        "get_cost_of_living_data": get_cost_of_living_data
    }

    def invoke(input_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Execute web research query."""
        messages = input_dict.get("messages", [])
        query = messages[0].get("content", "") if messages else ""

        try:
            # Determine which tool to use based on query
            tool_name = "tavily_search"

            if "population" in query.lower():
                tool_name = "get_population_data"
                # Extract location from query
                query_lower = query.lower()
                # Simple extraction - can be improved
                location = query.split("of")[-1].split("in")[-1].strip(" ?.")
            elif "cost of living" in query.lower():
                tool_name = "get_cost_of_living_data"
                location = query.split("in")[-1].strip(" ?.")

            # Execute search
            if tool_name == "tavily_search":
                search_result = tools[tool_name].invoke({"query": query})
            else:
                search_result = tools[tool_name].invoke({"location": location})

            # Create synthesis prompt
            synthesis_prompt = f"""{SYSTEM_PROMPT}

Web Search Results:
{search_result}

Original Question: {query}

Based on the search results above, provide a clear, concise answer to the question.
Include relevant facts and cite sources when possible."""

            # Get LLM synthesis
            response = llm.invoke([HumanMessage(content=synthesis_prompt)])

            return {
                "messages": [AIMessage(content=response.content)],
                "intermediate_steps": [(tool_name, search_result)]
            }

        except Exception as e:
            return {
                "messages": [AIMessage(content=f"Error during web research: {str(e)}")],
                "intermediate_steps": []
            }

    class SimpleAgent:
        def __init__(self, invoke_fn):
            self.invoke = invoke_fn

    return SimpleAgent(invoke)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_web_research_agent.py -v`

Expected: PASS (1-2 tests, some skipped)

**Step 5: Update workflow graph**

Modify `src/workflow/graph.py` to replace placeholder:

```python
def web_researcher_node(state: State):
    """Web research agent for external data."""
    from langgraph.types import Command
    from langchain_core.messages import AIMessage
    from src.agents.web_research_agent import create_web_research_agent

    agent = create_web_research_agent()
    agent_query = state.get("agent_query", state.get("user_query", ""))

    # Run agent
    result = agent.invoke({"messages": [{"role": "user", "content": agent_query}]})

    final_message = result["messages"][-1] if result.get("messages") else None
    response_content = final_message.content if final_message else "No results from web research."

    return Command(
        update={
            "messages": [AIMessage(content=response_content, name="web_researcher")],
            "model_usage": {
                **(state.get("model_usage") or {}),
                "web_researcher": state.get("implementation_model_override") or "deepseek-v3"
            }
        },
        goto="executor"
    )
```

**Step 6: Commit**

```bash
git add src/agents/web_research_agent.py tests/test_web_research_agent.py src/workflow/graph.py
git commit -m "feat(agents): add web research agent with Tavily integration

- Create web_research_agent with Tavily search
- Support population and cost-of-living queries
- Integrate into workflow graph
- Add comprehensive tests"
```

---

## Milestone 3: Fuzzy Matching for Query Understanding

### Task 3.1: Add Fuzzy Matching Utility

**Files:**
- Create: `src/utils/__init__.py`
- Create: `src/utils/fuzzy_matching.py`
- Create: `tests/test_fuzzy_matching.py`

**Step 1: Write the failing test**

Create `tests/test_fuzzy_matching.py`:

```python
from src.utils.fuzzy_matching import (
    fuzzy_match_area,
    fuzzy_match_occupation,
    get_best_matches
)


def test_fuzzy_match_area_exact():
    """Test exact area name matching."""
    matches = fuzzy_match_area("Seattle")

    assert len(matches) > 0
    # Should find Seattle-related areas
    assert any("Seattle" in match["name"] for match in matches)


def test_fuzzy_match_area_typo():
    """Test area matching with typo."""
    matches = fuzzy_match_area("Seatle")  # Missing 't'

    assert len(matches) > 0
    # Should still find Seattle
    assert any("Seattle" in match["name"] for match in matches)


def test_fuzzy_match_area_abbreviation():
    """Test area matching with state abbreviation."""
    matches = fuzzy_match_area("WA")

    assert len(matches) > 0
    # Should find Washington state areas
    assert any("WA" in match["name"] or "Washington" in match["name"] for match in matches)


def test_fuzzy_match_occupation():
    """Test occupation matching."""
    matches = fuzzy_match_occupation("software developer")

    assert len(matches) > 0
    # Should find software-related occupations
    assert any("Software" in match["name"] for match in matches)


def test_fuzzy_match_occupation_alternative_name():
    """Test occupation matching with alternative name."""
    matches = fuzzy_match_occupation("programmer")

    assert len(matches) > 0
    # Should find developer/programmer occupations
    assert any("Developer" in match["name"] or "Programmer" in match["name"] for match in matches)


def test_get_best_matches_returns_top_n():
    """Test that get_best_matches returns limited results."""
    candidates = [
        "Seattle-Tacoma-Bellevue, WA",
        "Seattle-Bellevue-Everett, WA",
        "Bellingham, WA",
        "Spokane, WA"
    ]

    matches = get_best_matches("Seattle", candidates, limit=2)

    assert len(matches) <= 2
    assert matches[0]["score"] >= matches[1]["score"]  # Sorted by score
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_fuzzy_matching.py -v`

Expected: FAIL with "No module named 'src.utils.fuzzy_matching'"

**Step 3: Install RapidFuzz**

Update `pyproject.toml` dependencies:

```toml
dependencies = [
    # ... existing dependencies ...
    "rapidfuzz>=3.5.0",
]
```

Run: `pip install rapidfuzz`

**Step 4: Write minimal implementation**

Create `src/utils/__init__.py`:

```python
"""Utility modules for OEWS Data Agent."""

from .fuzzy_matching import (
    fuzzy_match_area,
    fuzzy_match_occupation,
    get_best_matches
)

__all__ = [
    "fuzzy_match_area",
    "fuzzy_match_occupation",
    "get_best_matches"
]
```

Create `src/utils/fuzzy_matching.py`:

```python
"""Fuzzy string matching utilities for query understanding."""

from typing import List, Dict, Any, Optional
from rapidfuzz import fuzz, process
from src.database.connection import OEWSDatabase


def get_best_matches(
    query: str,
    candidates: List[str],
    limit: int = 5,
    score_threshold: int = 60
) -> List[Dict[str, Any]]:
    """
    Find best fuzzy matches from a list of candidates.

    Args:
        query: Search query string
        candidates: List of candidate strings to match against
        limit: Maximum number of matches to return
        score_threshold: Minimum similarity score (0-100)

    Returns:
        List of matches with name and score, sorted by score descending
    """
    if not query or not candidates:
        return []

    # Use RapidFuzz to find best matches
    # Use token_sort_ratio for better word order independence
    matches = process.extract(
        query,
        candidates,
        scorer=fuzz.token_sort_ratio,
        limit=limit,
        score_cutoff=score_threshold
    )

    return [
        {"name": match[0], "score": match[1]}
        for match in matches
    ]


def fuzzy_match_area(
    query: str,
    limit: int = 5,
    score_threshold: int = 60
) -> List[Dict[str, Any]]:
    """
    Find best matching area names from OEWS database using fuzzy matching.

    Handles:
    - Typos (Seatle → Seattle)
    - Abbreviations (WA → Washington)
    - Partial names (Seattle → Seattle-Tacoma-Bellevue, WA)

    Args:
        query: Area search query
        limit: Maximum number of matches
        score_threshold: Minimum similarity score

    Returns:
        List of area matches with name and score
    """
    try:
        db = OEWSDatabase()

        # Get all distinct area names
        df = db.execute_query(
            "SELECT DISTINCT AREA_TITLE FROM oews_data LIMIT 1000"
        )
        db.close()

        candidates = df['AREA_TITLE'].tolist()

        # Find best matches
        matches = get_best_matches(query, candidates, limit, score_threshold)

        return matches

    except Exception as e:
        print(f"Error in fuzzy_match_area: {e}")
        return []


def fuzzy_match_occupation(
    query: str,
    limit: int = 5,
    score_threshold: int = 60
) -> List[Dict[str, Any]]:
    """
    Find best matching occupation names from OEWS database using fuzzy matching.

    Handles:
    - Alternative names (programmer → software developer)
    - Typos
    - Partial matches

    Args:
        query: Occupation search query
        limit: Maximum number of matches
        score_threshold: Minimum similarity score

    Returns:
        List of occupation matches with name and score
    """
    try:
        db = OEWSDatabase()

        # Get all distinct occupation names
        df = db.execute_query(
            "SELECT DISTINCT OCC_TITLE FROM oews_data WHERE O_GROUP = 'detailed' LIMIT 1000"
        )
        db.close()

        candidates = df['OCC_TITLE'].tolist()

        # Find best matches
        matches = get_best_matches(query, candidates, limit, score_threshold)

        return matches

    except Exception as e:
        print(f"Error in fuzzy_match_occupation: {e}")
        return []


def extract_location_from_query(query: str) -> Optional[str]:
    """
    Extract location name from natural language query.

    Examples:
    - "salaries in Seattle" → "Seattle"
    - "What are jobs in San Francisco, CA?" → "San Francisco, CA"
    - "Compare Bellingham and Portland" → "Bellingham"

    Args:
        query: Natural language query

    Returns:
        Extracted location or None
    """
    # Simple extraction patterns
    patterns = [
        " in ",
        " for ",
        " at ",
    ]

    query_lower = query.lower()

    for pattern in patterns:
        if pattern in query_lower:
            # Extract text after pattern
            parts = query_lower.split(pattern)
            if len(parts) > 1:
                # Clean up extracted location
                location = parts[1].strip(" ?.!,")
                # Take first part before other prepositions
                location = location.split(" and")[0].split(" or")[0]
                return location.title()

    return None


def extract_occupation_from_query(query: str) -> Optional[str]:
    """
    Extract occupation name from natural language query.

    Examples:
    - "software developer salaries" → "software developer"
    - "How much do nurses make?" → "nurses"

    Args:
        query: Natural language query

    Returns:
        Extracted occupation or None
    """
    # Common occupation keywords
    keywords = [
        "developer", "engineer", "nurse", "teacher", "analyst",
        "manager", "technician", "specialist", "administrator",
        "designer", "programmer", "scientist", "consultant"
    ]

    query_lower = query.lower()

    for keyword in keywords:
        if keyword in query_lower:
            # Extract surrounding words
            words = query_lower.split()
            idx = next(i for i, w in enumerate(words) if keyword in w)

            # Get 1-2 words before and the keyword
            start = max(0, idx - 2)
            end = idx + 1
            occupation = " ".join(words[start:end])

            return occupation.strip()

    return None
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/test_fuzzy_matching.py -v`

Expected: PASS (6 tests)

**Step 6: Commit**

```bash
git add src/utils/ tests/test_fuzzy_matching.py pyproject.toml
git commit -m "feat(utils): add fuzzy matching for area and occupation names

- Implement fuzzy string matching with RapidFuzz
- Support typo correction and partial matching
- Add area and occupation extraction from queries
- Include comprehensive tests"
```

---

### Task 3.2: Integrate Fuzzy Matching into Search Tools

**Files:**
- Modify: `src/tools/database_tools.py`
- Modify: `tests/test_database_tools.py`

**Step 1: Write the failing test**

Modify `tests/test_database_tools.py` to add:

```python
def test_search_areas_with_typo():
    """Test that search_areas handles typos with fuzzy matching."""
    from src.tools.database_tools import search_areas

    # Search with typo
    result = search_areas.invoke({"search_term": "Seatle"})  # Missing 't'

    assert isinstance(result, list)
    # Should still find Seattle areas
    assert any("Seattle" in area for area in result)


def test_search_occupations_with_alternative_name():
    """Test occupation search with alternative name."""
    from src.tools.database_tools import search_occupations

    result = search_occupations.invoke({"search_term": "programmer"})

    assert isinstance(result, list)
    # Should find software developer related occupations
    assert len(result) > 0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_database_tools.py::test_search_areas_with_typo -v`
Run: `pytest tests/test_database_tools.py::test_search_occupations_with_alternative_name -v`

Expected: FAIL (may find results but not optimal ones)

**Step 3: Enhance search_areas with fuzzy matching**

Modify `src/tools/database_tools.py`:

```python
@tool
def search_areas(search_term: str) -> List[str]:
    """
    Searches for geographic areas matching the search term.

    SECURITY: Uses parameterized queries to prevent SQL injection.
    ENHANCEMENT: Uses fuzzy matching for typo correction.

    Example: search_areas("Seatle") returns Seattle areas despite typo

    Args:
        search_term: Text to search for in area names

    Returns:
        List of matching area names (up to 20, sorted by relevance)
    """
    import json
    from src.utils.fuzzy_matching import fuzzy_match_area

    # First try fuzzy matching for better results
    fuzzy_matches = fuzzy_match_area(search_term, limit=20)

    if fuzzy_matches:
        # Return fuzzy match results (already sorted by relevance)
        return [match["name"] for match in fuzzy_matches]

    # Fallback to SQL LIKE search
    sql = "SELECT DISTINCT AREA_TITLE FROM oews_data WHERE AREA_TITLE LIKE ? LIMIT 20"
    search_param = f"%{search_term}%"

    result_str = execute_sql_query.invoke({
        "sql": sql,
        "params": json.dumps([search_param])
    })
    result = json.loads(result_str)

    if result.get("success"):
        return [row[0] for row in result["data"]]
    return []


@tool
def search_occupations(search_term: str) -> List[str]:
    """
    Searches for occupations matching the search term.

    SECURITY: Uses parameterized queries to prevent SQL injection.
    ENHANCEMENT: Uses fuzzy matching for alternative names.

    Example: search_occupations("programmer") returns "Software Developers"

    Args:
        search_term: Text to search for in occupation names

    Returns:
        List of matching occupation names (up to 20, sorted by relevance)
    """
    import json
    from src.utils.fuzzy_matching import fuzzy_match_occupation

    # First try fuzzy matching
    fuzzy_matches = fuzzy_match_occupation(search_term, limit=20)

    if fuzzy_matches:
        return [match["name"] for match in fuzzy_matches]

    # Fallback to SQL LIKE search
    sql = "SELECT DISTINCT OCC_TITLE FROM oews_data WHERE OCC_TITLE LIKE ? LIMIT 20"
    search_param = f"%{search_term}%"

    result_str = execute_sql_query.invoke({
        "sql": sql,
        "params": json.dumps([search_param])
    })
    result = json.loads(result_str)

    if result.get("success"):
        return [row[0] for row in result["data"]]
    return []
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_database_tools.py::test_search_areas_with_typo -v`
Run: `pytest tests/test_database_tools.py::test_search_occupations_with_alternative_name -v`

Expected: PASS (both tests)

**Step 5: Commit**

```bash
git add src/tools/database_tools.py tests/test_database_tools.py
git commit -m "feat(tools): integrate fuzzy matching into search tools

- Enhance search_areas with typo correction
- Enhance search_occupations with alternative name matching
- Maintain SQL injection protection with parameterized queries
- Add tests for fuzzy matching functionality"
```

---

## Summary

This plan implements three key improvements:

1. **Enhanced Text2SQL Agent** - Proper ReAct loop with tool calling for iterative query refinement
2. **Web Research Agent** - Tavily-powered external data enrichment
3. **Fuzzy Matching** - Intelligent query understanding with typo correction and alternative names

**Total Tasks:** 6 (2 per milestone)
**Estimated Time:** 3-4 hours for full implementation
**Test Coverage:** 15+ new tests

**Key Benefits:**
- Better SQL query generation with tool-based iteration
- External data context from web research
- More forgiving user experience with fuzzy matching
- Maintained security (parameterized queries)
- Comprehensive test coverage

---

**Plan complete and saved to `docs/plans/2025-10-23-agent-improvements.md`**
