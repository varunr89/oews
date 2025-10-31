"""Tests for trace utilities."""

import pytest
from src.utils.trace_utils import calculate_column_stats, build_sql_trace


def test_calculate_column_stats_numeric():
    """Test statistics calculation for numeric column."""
    rows = [
        {"salary": 50000, "name": "Alice"},
        {"salary": 60000, "name": "Bob"},
        {"salary": 70000, "name": "Carol"}
    ]

    stats = calculate_column_stats(rows, "salary")

    assert stats is not None
    assert stats["min"] == 50000
    assert stats["max"] == 70000
    assert stats["avg"] == 60000


def test_calculate_column_stats_non_numeric():
    """Test that non-numeric columns return None."""
    rows = [
        {"name": "Alice"},
        {"name": "Bob"}
    ]

    stats = calculate_column_stats(rows, "name")

    assert stats is None


def test_calculate_column_stats_empty_rows():
    """Test empty rows return None."""
    stats = calculate_column_stats([], "salary")
    assert stats is None


def test_calculate_column_stats_missing_column():
    """Test missing column returns None."""
    rows = [{"salary": 50000}]
    stats = calculate_column_stats(rows, "bonus")
    assert stats is None


def test_build_sql_trace():
    """Test building complete SQL trace."""
    sql = "SELECT * FROM oews_data WHERE area = ?"
    params = ["Seattle"]
    rows = [
        {"occupation": "Nurse", "salary": 80000},
        {"occupation": "Developer", "salary": 120000}
    ]

    trace = build_sql_trace(sql, params, rows)

    assert trace["sql"] == sql
    assert trace["params"] == params
    assert trace["row_count"] == 2
    assert len(trace["sample_data"]) == 2
    assert trace["stats"] is not None
    assert "salary" in trace["stats"]
    assert trace["stats"]["salary"]["min"] == 80000
    assert trace["stats"]["salary"]["max"] == 120000


def test_build_sql_trace_limits_sample_data():
    """Test that sample data is limited to 10 rows."""
    sql = "SELECT * FROM test"
    params = []
    rows = [{"id": i} for i in range(20)]

    trace = build_sql_trace(sql, params, rows)

    assert trace["row_count"] == 20
    assert len(trace["sample_data"]) == 10


def test_build_sql_trace_no_stats_for_non_numeric():
    """Test that non-numeric columns don't produce stats."""
    sql = "SELECT name FROM users"
    params = []
    rows = [{"name": "Alice"}, {"name": "Bob"}]

    trace = build_sql_trace(sql, params, rows)

    assert trace["stats"] is None
