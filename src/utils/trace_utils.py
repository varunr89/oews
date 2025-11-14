"""Utilities for building execution traces."""

import json
from typing import Any, Dict, List, Optional


def calculate_column_stats(rows: List[Dict[str, Any]], column: str) -> Optional[Dict[str, Any]]:
    """
    Calculate min/max/mean statistics for a numeric column.

    More robust than strict type checking - collects numeric values and skips non-numeric.
    Returns stats if at least 50% of values are numeric, None otherwise.

    Args:
        rows: List of result rows
        column: Column name to analyze

    Returns:
        Dict with min, max, mean or None if column is not sufficiently numeric
    """
    if not rows or column not in rows[0]:
        return None

    values = []
    total_count = 0

    for row in rows:
        val = row[column]
        total_count += 1

        # Try to convert to float, skip if not possible
        try:
            if val is not None:
                values.append(float(val))
        except (ValueError, TypeError):
            continue  # Skip non-numeric values

    if not values:
        return None

    # Require at least 50% of values to be numeric to consider column numeric
    if len(values) < total_count * 0.5:
        return None

    return {
        "min": min(values),
        "max": max(values),
        "mean": sum(values) / len(values),
        "count": len(values)  # How many numeric values found
    }


def build_sql_trace(
    sql: str,
    params: List[Any],
    rows: List[Dict[str, Any]],
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Build execution trace for SQL query.

    Args:
        sql: SQL query string
        params: Query parameters
        rows: Query result rows (may be sample for large result sets)
        metadata: Optional metadata from SQL tool response (row_count, truncated, stats)

    Returns:
        Trace dict with sql, params, row_count, sample_data, stats
    """
    # Use metadata if provided (for large result sets), otherwise compute from rows
    if metadata:
        row_count = metadata.get("row_count", len(rows))
        truncated = metadata.get("truncated", False)
        stats = metadata.get("stats", None)
    else:
        row_count = len(rows)
        truncated = False
        stats = {}
        # Calculate statistics for numeric columns
        if rows:
            for column in rows[0].keys():
                col_stats = calculate_column_stats(rows, column)
                if col_stats:
                    stats[column] = col_stats
        stats = stats if stats else None

    trace = {
        "sql": sql,
        "params": params,
        "row_count": row_count,
        "sample_data": rows[:10],  # First 10 rows
    }

    if stats:
        trace["stats"] = stats

    if truncated:
        trace["truncated"] = truncated

    return trace
