import pytest
import os
from src.tools.database_tools import (
    get_schema_info,
    validate_sql,
    execute_sql_query,
    search_areas,
    search_occupations
)

# Check if database is available (either local SQLite or Azure SQL)
HAS_LOCAL_DB = os.path.exists(os.getenv('SQLITE_DB_PATH', 'data/oews.db'))

HAS_AZURE_SQL = all([
    os.getenv('AZURE_SQL_SERVER'),
    os.getenv('AZURE_SQL_DATABASE'),
    os.getenv('AZURE_SQL_USERNAME'),
    os.getenv('AZURE_SQL_PASSWORD')
])

HAS_ANY_DB = HAS_LOCAL_DB or HAS_AZURE_SQL

# Mark tests that require database - skip only if no database is available
skip_if_no_db = pytest.mark.skipif(
    not HAS_ANY_DB,
    reason="No database available. Provide either: (1) local SQLite at data/oews.db, or (2) Azure SQL credentials (AZURE_SQL_SERVER, AZURE_SQL_DATABASE, AZURE_SQL_USERNAME, AZURE_SQL_PASSWORD)"
)

@skip_if_no_db
def test_get_schema_info_returns_string():
    """Test schema info tool returns description."""
    result = get_schema_info.invoke({"table_name": "oews_data"})
    assert isinstance(result, str)
    assert "AREA_TITLE" in result

def test_validate_sql_accepts_select():
    """Test SQL validation accepts SELECT queries (no DB needed)."""
    result = validate_sql.invoke({"sql": "SELECT * FROM oews_data LIMIT 1"})
    assert "valid" in result.lower() or "true" in result.lower()

def test_validate_sql_rejects_drop():
    """Test SQL validation rejects dangerous operations (no DB needed)."""
    result = validate_sql.invoke({"sql": "DROP TABLE oews_data"})
    assert "dangerous" in result.lower() or "not allowed" in result.lower()

@skip_if_no_db
def test_execute_sql_query_returns_data():
    """Test SQL execution returns data."""
    result = execute_sql_query.invoke({"sql": "SELECT * FROM oews_data LIMIT 1"})
    assert "success" in result or "columns" in result

@skip_if_no_db
def test_search_areas_uses_parameterized_queries():
    """Test area search uses safe parameterized queries."""
    # This should not cause SQL injection even with malicious input
    malicious_input = "'; DROP TABLE oews_data; --"
    result = search_areas.invoke({"search_term": malicious_input})
    # Should return empty list, not cause an error or drop the table
    assert isinstance(result, list)

@skip_if_no_db
def test_search_areas_finds_bellingham():
    """Test area search finds Bellingham (or returns empty if DB not populated)."""
    result = search_areas.invoke({"search_term": "Bellingham"})
    # Should return a list (empty is OK if database not populated yet)
    assert isinstance(result, list)
    # If database has data and Bellingham exists, it should be found
    if result:
        assert any("Bellingham" in area for area in result) or len(result) == 0


@pytest.mark.skipif(
    not HAS_AZURE_SQL,
    reason="Requires Azure SQL with full OEWS data (Data and OES OEWS.DP). Local SQLite only has metadata."
)
def test_search_areas_with_typo():
    """Test that search_areas handles typos with fuzzy matching."""
    from src.tools.database_tools import search_areas

    # Search with typo
    result = search_areas.invoke({"search_term": "Seatle"})  # Missing 't'

    assert isinstance(result, list)
    # Should still find Seattle areas
    assert any("Seattle" in area for area in result)


@pytest.mark.skipif(
    not HAS_AZURE_SQL,
    reason="Requires Azure SQL with full OEWS data (Data and OES OEWS.DP). Local SQLite only has metadata."
)
def test_search_occupations_with_alternative_name():
    """Test occupation search with alternative name."""
    from src.tools.database_tools import search_occupations

    result = search_occupations.invoke({"search_term": "programmer"})

    assert isinstance(result, list)
    # Should find software developer related occupations
    assert len(result) > 0


def test_execute_sql_query_blocks_non_select_statements():
    """Test that execute_sql_query blocks dangerous SQL statements."""
    import json

    dangerous_queries = [
        "DROP TABLE oews_data",
        "DELETE FROM oews_data WHERE 1=1",
        "UPDATE oews_data SET A_MEAN = 0",
        "INSERT INTO oews_data VALUES (1, 2, 3)",
        "ALTER TABLE oews_data ADD COLUMN test TEXT",
        "CREATE TABLE malicious (id INT)",
        "TRUNCATE TABLE oews_data",
        "  drop table oews_data",  # With leading whitespace
        "-- comment\nDROP TABLE oews_data",  # With comment
    ]

    for sql in dangerous_queries:
        result = execute_sql_query.invoke({"sql": sql, "params": "[]"})
        result_data = json.loads(result)
        assert result_data["success"] is False, f"Should block: {sql}"
        assert "SELECT" in result_data["error"] or "WITH" in result_data["error"], \
            f"Error should mention allowed statements: {result_data['error']}"


def test_execute_sql_query_allows_select_with_whitespace():
    """Test that SELECT queries with leading whitespace/comments are allowed."""
    import json

    valid_queries = [
        "SELECT * FROM oews_data LIMIT 1",
        "  SELECT * FROM oews_data LIMIT 1",  # Leading whitespace
        "\nSELECT * FROM oews_data LIMIT 1",  # Leading newline
        "-- comment\nSELECT * FROM oews_data LIMIT 1",  # With comment
        "select * FROM oews_data LIMIT 1",  # Lowercase
    ]

    for sql in valid_queries:
        result = execute_sql_query.invoke({"sql": sql, "params": "[]"})
        result_data = json.loads(result)
        # Should succeed (or fail for other reasons, but not security policy)
        if not result_data["success"]:
            # Error should NOT be our SELECT-only policy rejection
            assert "only select and with" not in result_data["error"].lower(), \
                f"Should not block SELECT query: {sql}"
            assert "not allowed" not in result_data["error"].lower() or "no such table" in result_data["error"].lower(), \
                f"Should not be a policy error for SELECT query: {sql}"


def test_execute_sql_query_allows_cte():
    """Test that WITH (CTE) queries are allowed."""
    import json

    sql = """
    WITH avg_wage AS (
        SELECT AVG(A_MEAN) as avg_val FROM oews_data
    )
    SELECT * FROM avg_wage LIMIT 1
    """
    result = execute_sql_query.invoke({"sql": sql, "params": "[]"})
    result_data = json.loads(result)
    # Should succeed or fail for reasons other than policy
    if not result_data["success"]:
        # Error should NOT be our SELECT-only policy rejection
        assert "only select and with" not in result_data["error"].lower(), \
            "Should not block WITH (CTE) query with policy error"
        assert "with clause must be followed by select" not in result_data["error"].lower(), \
            "Should recognize valid WITH...SELECT pattern"


def test_execute_sql_query_blocks_multiple_statements():
    """Test that multi-statement payloads are blocked."""
    import json

    dangerous_multi = [
        "SELECT 1; DROP TABLE oews_data",
        "SELECT * FROM oews_data; DELETE FROM oews_data",
        "SELECT 1; SELECT 2",  # Even benign multiples blocked
    ]

    for sql in dangerous_multi:
        result = execute_sql_query.invoke({"sql": sql, "params": "[]"})
        result_data = json.loads(result)
        assert result_data["success"] is False, f"Should block multi-statement: {sql}"
        assert "multiple" in result_data["error"].lower() or \
               "single" in result_data["error"].lower(), \
            f"Should mention multiple statements: {result_data['error']}"


def test_execute_sql_query_adds_default_limit():
    """Test that queries without LIMIT get a defensive cap."""
    import json

    sql = "SELECT * FROM oews_data"
    result = execute_sql_query.invoke({"sql": sql, "params": "[]"})
    result_data = json.loads(result)

    if result_data["success"]:
        assert "row_count" in result_data
        # Should not return more than default limit
        assert result_data["row_count"] <= 10000, \
            "Query without LIMIT should be capped"
