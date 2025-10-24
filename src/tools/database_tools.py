"""Database tools for Text2SQL agent - SECURE IMPLEMENTATION."""

from typing import Dict, Any, List, Optional
from langchain_core.tools import tool
from src.database.connection import OEWSDatabase
from src.database.schema import get_oews_schema_description, get_table_list
from src.utils.logger import setup_workflow_logger

logger = setup_workflow_logger("oews.workflow.tools")


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

    For large result sets (>1000 rows), returns a summary with first 10 rows
    instead of the full dataset to prevent memory issues.

    Returns JSON string with columns, data, row count, and SQL query.

    Args:
        sql: SQL SELECT query with ? placeholders
        params: Optional JSON string of parameters (e.g., '["Seattle", 10]')

    Returns:
        JSON string with query results or summary

    Example:
        execute_sql_query(
            sql="SELECT * FROM oews_data WHERE AREA_TITLE LIKE ? LIMIT ?",
            params='["%Seattle%", 10]'
        )
    """
    import json

    # LOG: SQL execution start
    logger.debug("sql_execution_start", extra={
        "data": {
            "sql": sql,
            "params": params,
            "has_params": params is not None
        }
    })

    try:
        # Parse params if provided
        params_tuple = None
        if params:
            params_list = json.loads(params)
            params_tuple = tuple(params_list)

            logger.debug("sql_params_parsed", extra={
                "data": {
                    "params_count": len(params_list),
                    "params": params_list
                }
            })

        db = OEWSDatabase()
        df = db.execute_query(sql, params=params_tuple)
        db.close()

        row_count = len(df)

        # LOG: Query success
        logger.debug("sql_execution_success", extra={
            "data": {
                "row_count": row_count,
                "columns": df.columns.tolist() if row_count > 0 else [],
                "sample_data": df.head(3).to_dict('records') if row_count > 0 else []
            }
        })

        # Handle large result sets
        if row_count > 1000:
            # Return summary instead of full data
            result = {
                "success": True,
                "truncated": True,
                "summary": (
                    f"Query returned {row_count:,} rows (showing first 10). "
                    f"Full dataset available in agent memory for analysis."
                ),
                "columns": df.columns.tolist(),
                "sample_data": df.head(10).values.tolist(),
                "row_count": row_count,
                "sql": sql,
                "params": params,
                "stats": {
                    # Provide statistics for numeric columns
                    col: {
                        "min": float(df[col].min()),
                        "max": float(df[col].max()),
                        "mean": float(df[col].mean()),
                        "median": float(df[col].median())
                    }
                    for col in df.select_dtypes(include=['number']).columns[:5]
                }
            }
        else:
            # Return full data for small results
            result = {
                "success": True,
                "truncated": False,
                "columns": df.columns.tolist(),
                "data": df.values.tolist(),
                "row_count": row_count,
                "sql": sql,
                "params": params
            }

        return json.dumps(result, indent=2)

    except Exception as e:
        # LOG: Query error
        logger.error("sql_execution_error", extra={
            "data": {
                "error": str(e),
                "error_type": type(e).__name__,
                "sql": sql,
                "params": params
            }
        })

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
    ENHANCEMENT: Uses fuzzy matching for typo correction.

    Example: search_areas("Seatle") returns Seattle areas despite typo

    Args:
        search_term: Text to search for in area names

    Returns:
        List of matching area names (up to 20, sorted by relevance)
    """
    import json
    from src.utils.fuzzy_matching import fuzzy_match_area

    # LOG: Search start
    logger.debug("search_areas_start", extra={
        "data": {"search_term": search_term}
    })

    # First try fuzzy matching for better results
    fuzzy_matches = fuzzy_match_area(search_term, limit=20)

    if fuzzy_matches:
        # LOG: Fuzzy matches found
        logger.debug("search_areas_fuzzy_match", extra={
            "data": {
                "matches_count": len(fuzzy_matches),
                "top_match": fuzzy_matches[0] if fuzzy_matches else None
            }
        })
        # Return fuzzy match results (already sorted by relevance)
        return [match["name"] for match in fuzzy_matches]

    # Fallback to SQL LIKE search
    logger.debug("search_areas_sql_fallback", extra={
        "data": {"reason": "no_fuzzy_matches"}
    })

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

    # LOG: Search start
    logger.debug("search_occupations_start", extra={
        "data": {"search_term": search_term}
    })

    # First try fuzzy matching
    fuzzy_matches = fuzzy_match_occupation(search_term, limit=20)

    if fuzzy_matches:
        # LOG: Fuzzy matches found
        logger.debug("search_occupations_fuzzy_match", extra={
            "data": {
                "matches_count": len(fuzzy_matches),
                "top_match": fuzzy_matches[0] if fuzzy_matches else None
            }
        })
        return [match["name"] for match in fuzzy_matches]

    # Fallback to SQL LIKE search
    logger.debug("search_occupations_sql_fallback", extra={
        "data": {"reason": "no_fuzzy_matches"}
    })

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
