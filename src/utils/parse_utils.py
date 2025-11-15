"""Parsing utilities for extracting structured data from text."""

import json
from typing import Optional, Union, Dict, List, Any


def extract_json_from_marker(
    text: str,
    marker: str
) -> Optional[Union[Dict[str, Any], List[Any]]]:
    """
    Extract JSON data from text after a marker string.

    Handles:
    - Nested objects and arrays
    - Escaped quotes in strings
    - Leading/trailing whitespace
    - Malformed JSON (returns None)

    Args:
        text: Text containing marker and JSON
        marker: Marker string (e.g., "EXECUTION_TRACE:", "CHART_SPEC:")

    Returns:
        Parsed JSON object/array, or None if not found or invalid

    Example:
        >>> text = "Result: MARKER: {\"key\": \"value\"}"
        >>> extract_json_from_marker(text, "MARKER:")
        {"key": "value"}
    """
    # Find marker
    marker_pos = text.find(marker)
    if marker_pos == -1:
        return None

    # Start after marker
    json_start = marker_pos + len(marker)
    json_text = text[json_start:].strip()

    if not json_text:
        return None

    # Find end of JSON by counting braces/brackets with proper string tracking
    brace_count = 0
    in_string = False
    escape_next = False
    json_end = 0

    for i, char in enumerate(json_text):
        # Handle string escaping
        if escape_next:
            escape_next = False
            continue

        if char == '\\' and in_string:
            escape_next = True
            continue

        # Track string boundaries
        if char == '"':
            in_string = not in_string
            continue

        # Only count braces/brackets outside of strings
        if not in_string:
            if char == '{' or char == '[':
                brace_count += 1
            elif char == '}' or char == ']':
                brace_count -= 1
                if brace_count == 0:
                    json_end = i + 1
                    break

    if json_end == 0:
        # No closing brace/bracket found
        return None

    # Extract and parse JSON
    json_text = json_text[:json_end]

    try:
        return json.loads(json_text)
    except json.JSONDecodeError:
        return None
