"""Tests for feedback validation functions."""

import pytest
from src.feedback.validation import ValidationError, HoneypotTriggered, validate_required_fields, validate_honeypot, validate_text_length


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


def test_validate_honeypot_empty():
    """Test that empty honeypot passes."""
    validate_honeypot('')  # Should not raise


def test_validate_honeypot_filled():
    """Test that filled honeypot raises HoneypotTriggered."""
    with pytest.raises(HoneypotTriggered):
        validate_honeypot('spam@spam.com')


def test_validate_honeypot_whitespace():
    """Test that whitespace-only honeypot raises HoneypotTriggered."""
    with pytest.raises(HoneypotTriggered):
        validate_honeypot('  ')


def test_validate_text_length_valid():
    """Test that valid text passes."""
    result = validate_text_length("This is a valid feedback text")
    assert result == "This is a valid feedback text"


def test_validate_text_length_trims_whitespace():
    """Test that whitespace is trimmed."""
    result = validate_text_length("  Valid text  ")
    assert result == "Valid text"


def test_validate_text_length_too_short():
    """Test that short text raises ValidationError."""
    with pytest.raises(ValidationError, match="at least 10 characters"):
        validate_text_length("short")


def test_validate_text_length_too_long():
    """Test that long text raises ValidationError."""
    with pytest.raises(ValidationError, match="2000 characters"):
        validate_text_length("a" * 2001)
