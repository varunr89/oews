"""Database tools for Text2SQL agent - SECURE IMPLEMENTATION."""

import sqlparse
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
    Execute a SELECT query on the OEWS database.

    SECURITY: Only SELECT and WITH (CTE) queries are allowed. All other SQL
    statements (DROP, DELETE, UPDATE, INSERT, ALTER, CREATE, TRUNCATE) and
    multi-statement queries are rejected.

    For large result sets (>1000 rows), returns a summary with first 10 rows
    instead of the full dataset to prevent memory issues.

    Args:
        sql: SQL SELECT or WITH query to execute
        params: JSON array of parameters for parameterized query

    Returns:
        JSON string with results or error
    """
    import json

    # SECURITY: Enforce SELECT-only policy using sqlparse
    try:
        statements = sqlparse.parse(sql)
    except Exception as e:
        logger.error("sql_parse_error", extra={
            "data": {"error": str(e), "sql_preview": sql[:100]}
        })
        return json.dumps({
            "success": False,
            "error": f"SQL parsing error: {str(e)}"
        })

    # Reject empty SQL
    if len(statements) == 0:
        return json.dumps({"success": False, "error": "Empty SQL query"})

    # Reject multiple statements (prevents "SELECT 1; DROP TABLE" attacks)
    if len(statements) > 1:
        logger.warning("sql_execution_blocked", extra={
            "data": {"reason": "multiple_statements", "count": len(statements)}
        })
        return json.dumps({
            "success": False,
            "error": "Multiple SQL statements not allowed. Only single SELECT or WITH queries permitted."
        })

    statement = statements[0]

    # Get first token (sqlparse automatically handles whitespace/comments)
    first_token = statement.token_first(skip_ws=True, skip_cm=True)

    if not first_token:
        return json.dumps({"success": False, "error": "Could not parse SQL statement"})

    first_token_value = first_token.value.upper()

    # Allow SELECT and WITH (CTEs)
    if first_token_value not in ('SELECT', 'WITH'):
        logger.warning("sql_execution_blocked", extra={
            "data": {
                "reason": "non_select_statement",
                "first_token": first_token_value,
                "sql_preview": sql[:100]
            }
        })
        return json.dumps({
            "success": False,
            "error": f"Only SELECT and WITH (CTE) queries are allowed. Got: {first_token_value}"
        })

    # For WITH statements, verify they contain SELECT
    if first_token_value == 'WITH':
        sql_upper = sql.upper()
        if 'SELECT' not in sql_upper:
            return json.dumps({
                "success": False,
                "error": "WITH clause must be followed by SELECT"
            })

    # Add defensive LIMIT if not present
    MAX_ROWS_WITHOUT_LIMIT = 10000
    if 'LIMIT' not in sql.upper():
        logger.info("sql_adding_defensive_limit", extra={
            "data": {"original_sql_preview": sql[:100]}
        })
        sql = f"{sql.rstrip().rstrip(';')} LIMIT {MAX_ROWS_WITHOUT_LIMIT}"

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
    from src.database.schema import get_table_list

    # SECURITY: Validate table name against whitelist to prevent SQL injection
    valid_tables = get_table_list()
    if table_name not in valid_tables:
        return json.dumps({
            "success": False,
            "error": f"Invalid table name: {table_name}. Valid tables: {', '.join(valid_tables)}"
        })

    # Safe to use table_name now that it's validated
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
