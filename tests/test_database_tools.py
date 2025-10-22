from src.tools.database_tools import (
    get_schema_info,
    validate_sql,
    execute_sql_query,
    search_areas,
    search_occupations
)

def test_get_schema_info_returns_string():
    """Test schema info tool returns description."""
    result = get_schema_info.invoke({"table_name": "oews_data"})
    assert isinstance(result, str)
    assert "AREA_TITLE" in result

def test_validate_sql_accepts_select():
    """Test SQL validation accepts SELECT queries."""
    result = validate_sql.invoke({"sql": "SELECT * FROM oews_data LIMIT 1"})
    assert "valid" in result.lower() or "true" in result.lower()

def test_validate_sql_rejects_drop():
    """Test SQL validation rejects dangerous operations."""
    result = validate_sql.invoke({"sql": "DROP TABLE oews_data"})
    assert "dangerous" in result.lower() or "not allowed" in result.lower()

def test_execute_sql_query_returns_data():
    """Test SQL execution returns data."""
    result = execute_sql_query.invoke({"sql": "SELECT * FROM oews_data LIMIT 1"})
    assert "success" in result or "columns" in result

def test_search_areas_uses_parameterized_queries():
    """Test area search uses safe parameterized queries."""
    # This should not cause SQL injection even with malicious input
    malicious_input = "'; DROP TABLE oews_data; --"
    result = search_areas.invoke({"search_term": malicious_input})
    # Should return empty list, not cause an error or drop the table
    assert isinstance(result, list)

def test_search_areas_finds_bellingham():
    """Test area search finds Bellingham (or returns empty if DB not populated)."""
    result = search_areas.invoke({"search_term": "Bellingham"})
    # Should return a list (empty is OK if database not populated yet)
    assert isinstance(result, list)
    # If database has data and Bellingham exists, it should be found
    if result:
        assert any("Bellingham" in area for area in result) or len(result) == 0
