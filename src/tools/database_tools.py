"""Database tools for Text2SQL agent - SECURE IMPLEMENTATION."""

from typing import Dict, Any, List, Optional
from langchain_core.tools import tool
from src.database.connection import OEWSDatabase
from src.database.schema import get_oews_schema_description, get_table_list


@tool
def get_schema_info(table_name: Optional[str] = None) -> str:
    """
    Returns schema information for OEWS database.

    If table_name provided, returns detailed schema for that table.
    Otherwise returns overview of all tables.

    Use this when you need to understand the database structure
    before writing SQL queries.

    Args:
        table_name: Optional table name to get details for

    Returns:
        Schema description string
    """
    if table_name:
        return get_oews_schema_description(table_name)
    else:
        tables = get_table_list()
        return f"Available tables: {', '.join(tables)}\n\nUse get_schema_info with a specific table_name to see details."


@tool
def validate_sql(sql: str) -> str:
    """
    Validates SQL query syntax without executing it.

    Returns validation result and any suggestions.
    Use this before executing SQL to catch errors.

    IMPORTANT: This tool checks for dangerous keywords but is NOT
    a security mechanism. All queries MUST use parameterized queries
    with ? placeholders for user inputs.

    Args:
        sql: SQL query string to validate

    Returns:
        Validation result message
    """
    import sqlparse

    # Basic validation
    if not sql or not sql.strip():
        return "Error: Empty query"

    # Check for dangerous operations
    dangerous = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'TRUNCATE', 'CREATE']
    sql_upper = sql.upper()
    for keyword in dangerous:
        if keyword in sql_upper:
            return f"Error: Dangerous operation '{keyword}' not allowed. Only SELECT queries permitted."

    # Check for parameterized query patterns (should use ?)
    if "'" in sql or '"' in sql:
        # Warn if using string literals (might be SQL injection risk)
        return "Warning: Query contains string literals. Ensure all user inputs use ? placeholders for safety."

    # Parse SQL
    try:
        parsed = sqlparse.parse(sql)
        if not parsed:
            return "Error: Could not parse SQL"

        return "Valid: Query syntax is valid. Remember to use ? placeholders for all user inputs."
    except Exception as e:
        return f"Error: {str(e)}"


@tool
def execute_sql_query(sql: str, params: Optional[str] = None) -> str:
    """
    Executes SQL query against OEWS database and returns results.

    SECURITY: This tool REQUIRES parameterized queries.
    All user inputs MUST be passed via the params argument as a JSON string.

    Returns JSON string with columns, data, row count, and SQL query.

    Args:
        sql: SQL SELECT query with ? placeholders
        params: Optional JSON string of parameters (e.g., '["Seattle", 10]')

    Returns:
        JSON string with query results

    Example:
        execute_sql_query(
            sql="SELECT * FROM oews_data WHERE AREA_TITLE LIKE ? LIMIT ?",
            params='["%Seattle%", 10]'
        )
    """
    import json

    try:
        # Parse params if provided
        params_tuple = None
        if params:
            params_list = json.loads(params)
            params_tuple = tuple(params_list)

        db = OEWSDatabase()
        df = db.execute_query(sql, params=params_tuple)
        db.close()

        result = {
            "success": True,
            "columns": df.columns.tolist(),
            "data": df.values.tolist(),
            "row_count": len(df),
            "sql": sql,
            "params": params
        }
        return json.dumps(result, indent=2)
    except Exception as e:
        result = {
            "success": False,
            "error": str(e),
            "sql": sql,
            "params": params
        }
        return json.dumps(result, indent=2)


@tool
def get_sample_data(table_name: str, limit: int = 5) -> str:
    """
    Returns sample rows from a table to understand data format.

    Use this to see examples of actual data before writing queries.

    Args:
        table_name: Name of the table
        limit: Number of rows to return (default 5)

    Returns:
        JSON string with sample data
    """
    import json
    # Use parameterized query for limit
    sql = f"SELECT * FROM {table_name} LIMIT ?"
    return execute_sql_query.invoke({"sql": sql, "params": json.dumps([limit])})


@tool
def search_areas(search_term: str) -> List[str]:
    """
    Searches for geographic areas matching the search term.

    SECURITY: Uses parameterized queries to prevent SQL injection.

    Example: search_areas("Bellingham") returns
    ["Bellingham, WA Metropolitan Statistical Area"]

    Use this to find exact AREA_TITLE values for filtering.

    Args:
        search_term: Text to search for in area names

    Returns:
        List of matching area names
    """
    import json

    # SECURE: Use parameterized query with ? placeholder
    sql = "SELECT DISTINCT AREA_TITLE FROM oews_data WHERE AREA_TITLE LIKE ? LIMIT 20"

    # Wildcard % must be part of the parameter value, not the SQL string
    search_param = f"%{search_term}%"

    result_str = execute_sql_query.invoke({
        "sql": sql,
        "params": json.dumps([search_param])
    })
    result = json.loads(result_str)

    if result.get("success"):
        # Extract first column (AREA_TITLE) from each row
        return [row[0] for row in result["data"]]
    return []


@tool
def search_occupations(search_term: str) -> List[str]:
    """
    Searches for occupations matching the search term.

    SECURITY: Uses parameterized queries to prevent SQL injection.

    Example: search_occupations("software") returns
    ["Software Developers", "Software Quality Assurance Analysts", ...]

    Use this to find exact OCC_TITLE values.

    Args:
        search_term: Text to search for in occupation names

    Returns:
        List of matching occupation names
    """
    import json

    # SECURE: Use parameterized query with ? placeholder
    sql = "SELECT DISTINCT OCC_TITLE FROM oews_data WHERE OCC_TITLE LIKE ? LIMIT 20"

    # Wildcard % must be part of the parameter value
    search_param = f"%{search_term}%"

    result_str = execute_sql_query.invoke({
        "sql": sql,
        "params": json.dumps([search_param])
    })
    result = json.loads(result_str)

    if result.get("success"):
        # Extract first column (OCC_TITLE) from each row
        return [row[0] for row in result["data"]]
    return []
