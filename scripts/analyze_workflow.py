#!/usr/bin/env python3
"""Analyze workflow execution logs for debugging."""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime


def load_logs(log_file: str = "logs/workflow_debug.log", num_lines: int = None) -> List[Dict[str, Any]]:
    """
    Load logs from file.

    Args:
        log_file: Path to log file
        num_lines: Number of lines to load from end (None = all)

    Returns:
        List of parsed log entries
    """
    log_path = Path(log_file)

    if not log_path.exists():
        print(f"❌ Log file not found: {log_file}")
        return []

    with open(log_path) as f:
        lines = f.readlines()

    if num_lines:
        lines = lines[-num_lines:]

    logs = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            logs.append(json.loads(line))
        except json.JSONDecodeError:
            print(f"⚠️  Could not parse line: {line[:50]}...")

    return logs


def display_workflow_execution(logs: List[Dict[str, Any]]):
    """
    Display workflow execution in readable format.

    Args:
        logs: List of log entries
    """
    print("\n" + "=" * 100)
    print("WORKFLOW EXECUTION TRACE")
    print("=" * 100 + "\n")

    print(f"{'Component':<30} | {'Event':<35} | {'Data'}")
    print("-" * 100)

    for log in logs:
        component = log.get('component', 'unknown')
        event = log.get('event', 'unknown')
        data = log.get('data', {})

        # Format data for display
        if isinstance(data, dict):
            if 'sql' in data:
                data_str = f"SQL: {data['sql'][:50]}..."
            elif 'row_count' in data:
                data_str = f"Rows: {data['row_count']}"
            elif 'query' in data:
                data_str = f"Query: {data['query'][:50]}..."
            elif 'plan' in data:
                data_str = f"Plan: {len(data['plan'])} steps"
            else:
                data_str = str(data)[:50]
        else:
            data_str = str(data)[:50]

        # Truncate if too long
        if len(data_str) > 50:
            data_str = data_str[:47] + "..."

        print(f"{component:<30} | {event:<35} | {data_str}")


def analyze_text2sql_execution(logs: List[Dict[str, Any]]):
    """
    Analyze Text2SQL agent execution specifically.

    Args:
        logs: List of log entries
    """
    print("\n" + "=" * 100)
    print("TEXT2SQL AGENT ANALYSIS")
    print("=" * 100 + "\n")

    # Filter for text2sql logs
    text2sql_logs = [log for log in logs if 'text2sql' in log.get('component', '')]

    if not text2sql_logs:
        print("❌ No Text2SQL agent logs found")
        return

    for log in text2sql_logs:
        event = log.get('event', '')
        data = log.get('data', {})

        if event == 'agent_input':
            print(f"📥 INPUT QUERY:")
            print(f"   {data.get('query', 'N/A')}\n")

        elif event == 'sql_generated':
            print(f"🔍 GENERATED SQL:")
            print(f"   {data.get('sql', 'N/A')}\n")

        elif event == 'query_results':
            print(f"📊 QUERY RESULTS:")
            print(f"   Success: {data.get('success', False)}")
            print(f"   Row count: {data.get('row_count', 0)}")
            if data.get('row_count', 0) > 0:
                print(f"   Preview: {str(data.get('result_preview', ''))[:100]}...")
            print()


def compare_with_expected_sql(logs: List[Dict[str, Any]], expected_sql: str):
    """
    Compare generated SQL with expected SQL.

    Args:
        logs: List of log entries
        expected_sql: Expected SQL query
    """
    print("\n" + "=" * 100)
    print("SQL COMPARISON")
    print("=" * 100 + "\n")

    # Find generated SQL
    for log in logs:
        if log.get('event') == 'sql_generated':
            actual_sql = log.get('data', {}).get('sql', '')

            print("EXPECTED SQL:")
            print(expected_sql)
            print("\nACTUAL SQL:")
            print(actual_sql)
            print("\nMATCH:", "✅ YES" if actual_sql.strip() == expected_sql.strip() else "❌ NO")

            return

    print("❌ No SQL generation found in logs")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Analyze workflow execution logs")
    parser.add_argument("--lines", "-n", type=int, default=50, help="Number of log lines to analyze")
    parser.add_argument("--text2sql-only", action="store_true", help="Show only Text2SQL analysis")
    parser.add_argument("--compare-sql", type=str, help="Expected SQL to compare against")

    args = parser.parse_args()

    # Load logs
    logs = load_logs(num_lines=args.lines)

    if not logs:
        print("❌ No logs found")
        sys.exit(1)

    print(f"✅ Loaded {len(logs)} log entries")

    # Display based on options
    if args.text2sql_only:
        analyze_text2sql_execution(logs)
    else:
        display_workflow_execution(logs)
        analyze_text2sql_execution(logs)

    # Compare SQL if provided
    if args.compare_sql:
        compare_with_expected_sql(logs, args.compare_sql)


if __name__ == "__main__":
    main()
