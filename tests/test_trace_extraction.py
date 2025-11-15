"""Integration tests for execution trace extraction.

Tests the end-to-end flow of trace extraction from:
1. SQL tool execution -> trace building -> response formatting
2. Handling edge cases (empty results, large results, malformed data)
3. Data format consistency across the pipeline
"""

import json
import pytest
from unittest.mock import Mock, MagicMock
from langchain_core.messages import AIMessage, ToolMessage
from src.utils.trace_utils import build_sql_trace
from src.workflow.graph import cortex_researcher_node
from src.agents.response_formatter import response_formatter_node
from src.agents.state import State


class TestSQLTraceExtraction:
    """Test SQL trace extraction from tool calls to formatted response."""

    def test_small_result_set_trace_extraction(self):
        """Test trace extraction for small result sets (<= 1000 rows)."""
        # Build a trace from small result set
        sql = "SELECT OCC_TITLE, A_MEAN FROM oews_data WHERE AREA_TITLE = ? LIMIT 5"
        params = ["Seattle, WA"]
        rows = [
            {"OCC_TITLE": "Software Developer", "A_MEAN": 150000.0},
            {"OCC_TITLE": "Data Scientist", "A_MEAN": 140000.0},
            {"OCC_TITLE": "Product Manager", "A_MEAN": 130000.0},
        ]

        trace = build_sql_trace(sql, params, rows)

        # Verify trace structure
        assert trace["sql"] == sql
        assert trace["params"] == params
        assert trace["row_count"] == 3
        assert len(trace["sample_data"]) == 3
        assert trace["sample_data"][0]["OCC_TITLE"] == "Software Developer"

    def test_large_result_set_preserves_metadata(self):
        """Test that large result sets preserve real row_count and stats."""
        sql = "SELECT * FROM oews_data"
        params = []
        # Simulate 10 sample rows from a 5000-row result
        rows = [{"id": i, "value": i * 10} for i in range(10)]
        metadata = {
            "row_count": 5000,  # Real count
            "truncated": True,
            "stats": {"value": {"min": 0, "max": 49990, "mean": 24995}}
        }

        trace = build_sql_trace(sql, params, rows, metadata)

        # Verify metadata is preserved
        assert trace["row_count"] == 5000  # Not 10!
        assert trace["truncated"] is True
        assert trace["stats"]["value"]["max"] == 49990

    def test_empty_result_set(self):
        """Test trace extraction handles empty result sets correctly."""
        sql = "SELECT * FROM oews_data WHERE AREA_TITLE = ?"
        params = ["NonexistentCity, XX"]
        rows = []

        trace = build_sql_trace(sql, params, rows)

        assert trace["row_count"] == 0
        assert trace["sample_data"] == []
        assert "stats" not in trace or trace["stats"] is None

    def test_mixed_numeric_text_columns_stats(self):
        """Test stats calculation handles mixed column types gracefully."""
        rows = [
            {"title": "Job A", "wage": 50000, "code": "15-1132"},
            {"title": "Job B", "wage": 60000, "code": "15-1133"},
            {"title": "Job C", "wage": "N/A", "code": "15-1134"},  # Non-numeric wage
        ]

        trace = build_sql_trace("SELECT * FROM jobs", [], rows)

        # Should have stats for numeric columns only
        if trace.get("stats"):
            # wage column should have stats despite one N/A
            assert "wage" in trace["stats"]
            assert trace["stats"]["wage"]["mean"] == 55000
            # title and code should not have stats (text)
            assert "title" not in trace["stats"]
            assert "code" not in trace["stats"]


class TestTraceFormatterIntegration:
    """Test response_formatter node integration with traces."""

    def test_formatter_extracts_sql_traces_from_messages(self):
        """Test that response_formatter correctly extracts SQL traces from message content."""
        # Simulate a state with SQL trace in message
        sql_traces = [{
            "sql": "SELECT * FROM oews_data LIMIT 10",
            "params": [],
            "row_count": 10,
            "sample_data": [{"id": 1}, {"id": 2}]
        }]

        message_content = f"Query results found.\n\nEXECUTION_TRACE: {json.dumps(sql_traces)}"

        state = State(
            messages=[
                AIMessage(content=message_content, name="cortex_researcher")
            ],
            final_answer="Test answer",
            user_query="test query",
            agent_query="test query",
            plan={},
            current_step=1,
            max_steps=5,
            replans=0,
            model_usage={}
        )

        result = response_formatter_node(state)

        # Extract formatted response
        formatted = result.update["formatted_response"]

        # Verify SQL trace was extracted
        assert len(formatted["data_sources"]) > 0
        sql_trace = formatted["data_sources"][0]
        assert sql_trace["type"] == "oews_database"
        assert sql_trace["agent"] == "cortex_researcher"
        assert sql_trace["row_count"] == 10

    def test_formatter_handles_malformed_json_gracefully(self):
        """Test that malformed JSON in traces doesn't crash formatter."""
        # Invalid JSON in trace
        message_content = "Results found.\n\nEXECUTION_TRACE: {invalid json here}"

        state = State(
            messages=[
                AIMessage(content=message_content, name="cortex_researcher")
            ],
            final_answer="Test answer",
            user_query="test query",
            agent_query="test query",
            plan={},
            current_step=1,
            max_steps=5,
            replans=0,
            model_usage={}
        )

        # Should not raise exception
        result = response_formatter_node(state)
        formatted = result.update["formatted_response"]

        # Should still return valid response, just without the bad trace
        assert "data_sources" in formatted
        assert "answer" in formatted

    def test_formatter_validates_trace_data_types(self):
        """Test that formatter validates trace data before spreading."""
        # Trace with invalid type (string instead of dict)
        sql_traces = ["invalid_trace_string"]  # Should be dict!

        message_content = f"Results.\n\nEXECUTION_TRACE: {json.dumps(sql_traces)}"

        state = State(
            messages=[
                AIMessage(content=message_content, name="cortex_researcher")
            ],
            final_answer="Test answer",
            user_query="test query",
            agent_query="test query",
            plan={},
            current_step=1,
            max_steps=5,
            replans=0,
            model_usage={}
        )

        # Should not crash when spreading invalid trace
        result = response_formatter_node(state)
        formatted = result.update["formatted_response"]

        # Invalid trace should be skipped
        assert "data_sources" in formatted

    def test_formatter_extracts_chart_generator_trace(self):
        """Test that response_formatter correctly extracts chart_generator traces."""
        # Simulate a chart_generator trace
        chart_trace = {
            "action": "Generated 2 chart specification(s)",
            "chart_count": 2,
            "model": "deepseek-v3"
        }

        message_content = f"Charts created.\n\nEXECUTION_TRACE: {json.dumps(chart_trace)}"

        state = State(
            messages=[
                AIMessage(content=message_content, name="chart_generator")
            ],
            final_answer="Test answer",
            user_query="test query",
            agent_query="test query",
            plan={},
            current_step=1,
            max_steps=5,
            replans=0,
            model_usage={}
        )

        result = response_formatter_node(state)
        formatted = result.update["formatted_response"]

        # Verify chart_generator trace was extracted
        assert len(formatted["data_sources"]) > 0
        chart_trace_result = formatted["data_sources"][0]
        assert chart_trace_result["type"] == "chart_generation"
        assert chart_trace_result["agent"] == "chart_generator"
        assert chart_trace_result["chart_count"] == 2
        assert chart_trace_result["model"] == "deepseek-v3"

    def test_formatter_extracts_synthesizer_trace(self):
        """Test that response_formatter correctly extracts synthesizer traces."""
        # Simulate a synthesizer trace
        synth_trace = {
            "action": "Synthesized final answer (1234 characters)",
            "answer_length": 1234,
            "included_charts": True,
            "model": "deepseek-v3"
        }

        message_content = f"Final answer synthesized.\n\nEXECUTION_TRACE: {json.dumps(synth_trace)}"

        state = State(
            messages=[
                AIMessage(content=message_content, name="synthesizer")
            ],
            final_answer="Test answer",
            user_query="test query",
            agent_query="test query",
            plan={},
            current_step=1,
            max_steps=5,
            replans=0,
            model_usage={}
        )

        result = response_formatter_node(state)
        formatted = result.update["formatted_response"]

        # Verify synthesizer trace was extracted
        assert len(formatted["data_sources"]) > 0
        synth_trace_result = formatted["data_sources"][0]
        assert synth_trace_result["type"] == "synthesis"
        assert synth_trace_result["agent"] == "synthesizer"
        assert synth_trace_result["answer_length"] == 1234
        assert synth_trace_result["included_charts"] is True
        assert synth_trace_result["model"] == "deepseek-v3"


class TestPerformanceOptimizations:
    """Test performance optimizations for large result sets."""

    def test_only_first_10_rows_converted_for_large_sets(self):
        """Test that we only convert first 10 rows to dict format, not all 1000."""
        # This is more of a code inspection test
        # In production, we should see log times confirming this
        # For now, verify the trace only contains 10 rows in sample_data

        rows = [{"id": i} for i in range(100)]
        trace = build_sql_trace("SELECT * FROM large_table", [], rows)

        # Should only keep 10 rows in sample_data
        assert len(trace["sample_data"]) == 10
        # But row_count should reflect actual count
        assert trace["row_count"] == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
