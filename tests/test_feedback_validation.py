"""Tests for feedback validation functions."""

import pytest
from src.feedback.validation import ValidationError, HoneypotTriggered, validate_required_fields, validate_honeypot, validate_text_length, validate_email, validate_category, validate_id_format


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


def test_validate_email_valid():
    """Test that valid email passes."""
    result = validate_email("user@example.com")
    assert result == "user@example.com"


def test_validate_email_empty():
    """Test that empty email is allowed."""
    result = validate_email("")
    assert result == ""

    result = validate_email(None)
    assert result == ""


def test_validate_email_invalid_formats():
    """Test that invalid email formats raise ValidationError."""
    invalid_emails = [
        "notanemail",
        "@example.com",
        "user@",
        "user @example.com",
        "user@.com"
    ]

    for email in invalid_emails:
        with pytest.raises(ValidationError, match="Invalid email format"):
            validate_email(email)


def test_validate_category_valid():
    """Test that valid categories pass."""
    valid_categories = ['bug', 'feature', 'improvement', 'documentation', 'question']

    for category in valid_categories:
        result = validate_category(category)
        assert result == category


def test_validate_category_invalid():
    """Test that invalid category raises ValidationError."""
    with pytest.raises(ValidationError, match="Invalid category"):
        validate_category("invalid")


def test_validate_id_format_valid():
    """Test that valid ID formats pass."""
    valid_ids = ['local-123', 'test_456', 'abc-def_123', 'test123']

    for id_value in valid_ids:
        result = validate_id_format(id_value)
        assert result == id_value


def test_validate_id_format_invalid():
    """Test that invalid ID formats raise ValidationError."""
    invalid_ids = ['local@123', 'test 456', 'abc!def', '']

    for id_value in invalid_ids:
        with pytest.raises(ValidationError, match="Invalid ID format"):
            validate_id_format(id_value)
