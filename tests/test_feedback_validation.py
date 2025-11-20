"""Tests for feedback validation functions."""

import pytest
from src.feedback.validation import ValidationError, validate_required_fields


def test_validate_required_fields_success():
    """Test that valid data passes required fields check."""
    data = {
        'category': 'bug',
        'text': 'Test feedback',
        'honeypot': '',
        'timestamp': 1700000000000,
        'id': 'test-1'
    }
    # Should not raise
    validate_required_fields(data)


def test_validate_required_fields_missing_category():
    """Test that missing category raises ValidationError."""
    data = {
        'text': 'Test feedback',
        'honeypot': '',
        'timestamp': 1700000000000,
        'id': 'test-1'
    }
    with pytest.raises(ValidationError, match="Missing required field: category"):
        validate_required_fields(data)


def test_validate_required_fields_missing_text():
    """Test that missing text raises ValidationError."""
    data = {
        'category': 'bug',
        'honeypot': '',
        'timestamp': 1700000000000,
        'id': 'test-1'
    }
    with pytest.raises(ValidationError, match="Missing required field: text"):
        validate_required_fields(data)
