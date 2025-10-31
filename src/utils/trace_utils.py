"""Utilities for building execution traces."""

import json
from typing import Any, Dict, List, Optional


def calculate_column_stats(rows: List[Dict[str, Any]], column: str) -> Optional[Dict[str, Any]]:
    """
    Calculate min/max/avg statistics for a numeric column.

    Args:
        rows: List of result rows
        column: Column name to analyze

    Returns:
        Dict with min, max, avg or None if column is not numeric
    """
    if not rows or column not in rows[0]:
        return None

    values = []
    for row in rows:
        val = row[column]
        # Try to convert to float
        try:
            if val is not None:
                values.append(float(val))
        except (ValueError, TypeError):
            return None  # Not numeric

    if not values:
        return None

    return {
        "min": min(values),
        "max": max(values),
        "avg": sum(values) / len(values)
    }


def build_sql_trace(sql: str, params: List[Any], rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Build execution trace for SQL query.

    Args:
        sql: SQL query string
        params: Query parameters
        rows: Query result rows

    Returns:
        Trace dict with sql, params, row_count, sample_data, stats
    """
    # Calculate statistics for numeric columns
    stats = {}
    if rows:
        for column in rows[0].keys():
            col_stats = calculate_column_stats(rows, column)
            if col_stats:
                stats[column] = col_stats

    return {
        "sql": sql,
        "params": params,
        "row_count": len(rows),
        "sample_data": rows[:10],  # First 10 rows
        "stats": stats if stats else None
    }
