"""Tests for parsing utilities."""

import pytest
from src.utils.parse_utils import extract_json_from_marker


class TestExtractJsonFromMarker:
    """Tests for extract_json_from_marker utility."""

    def test_extract_simple_object(self):
        """Test extracting simple JSON object."""
        text = "Some text\nMARKER: {\"key\": \"value\"}\nMore text"
        result = extract_json_from_marker(text, "MARKER:")

        assert result == {"key": "value"}

    def test_extract_nested_objects(self):
        """Test extracting JSON with nested objects."""
        text = 'MARKER: {"outer": {"inner": {"deep": "value"}}}'
        result = extract_json_from_marker(text, "MARKER:")

        assert result == {"outer": {"inner": {"deep": "value"}}}

    def test_extract_with_escaped_quotes(self):
        """Test extracting JSON with escaped quotes in strings."""
        text = 'MARKER: {"key": "value with \\"quotes\\""}'
        result = extract_json_from_marker(text, "MARKER:")

        assert result == {"key": "value with \"quotes\""}

    def test_extract_array(self):
        """Test extracting JSON array."""
        text = 'MARKER: [{"a": 1}, {"b": 2}]'
        result = extract_json_from_marker(text, "MARKER:")

        assert result == [{"a": 1}, {"b": 2}]

    def test_extract_from_middle_of_text(self):
        """Test extracting JSON from middle of text."""
        text = "Some preamble\nMARKER: {\"data\": 123}\nTrailing text here"
        result = extract_json_from_marker(text, "MARKER:")

        assert result == {"data": 123}

    def test_extract_with_leading_whitespace(self):
        """Test extracting with leading whitespace."""
        text = 'MARKER:   \n  {"key": "value"}'
        result = extract_json_from_marker(text, "MARKER:")

        assert result == {"key": "value"}

    def test_malformed_json_returns_none(self):
        """Test that malformed JSON returns None."""
        text = "MARKER: {invalid json}"
        result = extract_json_from_marker(text, "MARKER:")

        assert result is None

    def test_marker_not_found_returns_none(self):
        """Test that missing marker returns None."""
        text = "Some text without marker"
        result = extract_json_from_marker(text, "MARKER:")

        assert result is None

    def test_empty_after_marker_returns_none(self):
        """Test that empty content after marker returns None."""
        text = "Some text MARKER:"
        result = extract_json_from_marker(text, "MARKER:")

        assert result is None

    def test_multiple_markers_extracts_first(self):
        """Test that with multiple markers, first is extracted."""
        text = 'First: MARKER: {"first": 1}\nSecond: MARKER: {"second": 2}'
        result = extract_json_from_marker(text, "MARKER:")

        assert result == {"first": 1}

    def test_extract_complex_nested_structure(self):
        """Test extracting complex nested structure."""
        data = {
            "sql": "SELECT * FROM table",
            "params": [1, 2, 3],
            "results": {
                "rows": [
                    {"name": "Alice", "age": 30},
                    {"name": "Bob", "age": 25}
                ],
                "count": 2
            }
        }
        import json as json_module
        text = f"Results: MARKER: {json_module.dumps(data)}"
        result = extract_json_from_marker(text, "MARKER:")

        assert result == data

    def test_extract_with_special_characters(self):
        """Test extracting JSON with special characters."""
        text = 'MARKER: {"special": "value with !@#$%^&*()"}'
        result = extract_json_from_marker(text, "MARKER:")

        assert result == {"special": "value with !@#$%^&*()"}

    def test_extract_with_unicode(self):
        """Test extracting JSON with unicode characters."""
        text = 'MARKER: {"name": "José", "city": "São Paulo"}'
        result = extract_json_from_marker(text, "MARKER:")

        assert result == {"name": "José", "city": "São Paulo"}

    def test_extract_empty_object(self):
        """Test extracting empty JSON object."""
        text = "MARKER: {}"
        result = extract_json_from_marker(text, "MARKER:")

        assert result == {}

    def test_extract_empty_array(self):
        """Test extracting empty JSON array."""
        text = "MARKER: []"
        result = extract_json_from_marker(text, "MARKER:")

        assert result == []

    def test_extract_with_newlines_in_json(self):
        """Test extracting JSON with newlines."""
        text = """MARKER: {
            "key": "value",
            "nested": {"inner": 123}
        }"""
        result = extract_json_from_marker(text, "MARKER:")

        assert result == {"key": "value", "nested": {"inner": 123}}

    def test_extract_with_numeric_values(self):
        """Test extracting JSON with various numeric types."""
        text = 'MARKER: {"int": 42, "float": 3.14, "negative": -100, "zero": 0}'
        result = extract_json_from_marker(text, "MARKER:")

        assert result == {"int": 42, "float": 3.14, "negative": -100, "zero": 0}

    def test_extract_with_boolean_values(self):
        """Test extracting JSON with boolean values."""
        text = 'MARKER: {"true_val": true, "false_val": false, "null_val": null}'
        result = extract_json_from_marker(text, "MARKER:")

        assert result == {"true_val": True, "false_val": False, "null_val": None}

    def test_extract_different_marker_strings(self):
        """Test extraction with different marker strings."""
        # Test with EXECUTION_TRACE marker
        text1 = 'EXECUTION_TRACE: {"type": "sql"}'
        result1 = extract_json_from_marker(text1, "EXECUTION_TRACE:")
        assert result1 == {"type": "sql"}

        # Test with CHART_SPEC marker
        text2 = 'CHART_SPEC: {"type": "bar"}'
        result2 = extract_json_from_marker(text2, "CHART_SPEC:")
        assert result2 == {"type": "bar"}

    def test_unclosed_brace_returns_none(self):
        """Test that unclosed braces return None."""
        text = "MARKER: {\"key\": \"value\""
        result = extract_json_from_marker(text, "MARKER:")

        assert result is None

    def test_extra_text_after_json_is_ignored(self):
        """Test that extra text after JSON is ignored."""
        text = 'MARKER: {"key": "value"} and more text after'
        result = extract_json_from_marker(text, "MARKER:")

        assert result == {"key": "value"}

    def test_string_with_escaped_newline(self):
        """Test extracting string with escaped newline."""
        text = r'MARKER: {"text": "line1\nline2"}'
        result = extract_json_from_marker(text, "MARKER:")

        assert result == {"text": "line1\nline2"}
