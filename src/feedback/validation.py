"""Validation functions for feedback submissions."""

import re
import time
from typing import Optional


class ValidationError(Exception):
    """Raised when validation fails."""
    pass


class HoneypotTriggered(Exception):
    """Raised when honeypot field is filled (bot detected)."""
    pass


def validate_required_fields(data: dict) -> None:
    """
    Validate that all required fields are present.

    Args:
        data: Request data dictionary

    Raises:
        ValidationError: If any required field is missing
    """
    required = ['category', 'text', 'honeypot', 'timestamp', 'id']
    for field in required:
        if field not in data:
            raise ValidationError(f"Missing required field: {field}")


def validate_honeypot(honeypot: str) -> None:
    """
    Check honeypot field for bot detection.

    Args:
        honeypot: Honeypot field value (should be empty for humans)

    Raises:
        HoneypotTriggered: If honeypot contains any non-empty value
    """
    # Check if non-empty (including whitespace-only strings)
    if honeypot != "" and honeypot.strip() == "":
        # Whitespace-only is suspicious
        raise HoneypotTriggered("Honeypot field was filled")

    if honeypot.strip() != "":
        raise HoneypotTriggered("Honeypot field was filled")


def validate_text_length(text: str) -> str:
    """
    Validate text length and return trimmed text.

    Args:
        text: Feedback text to validate

    Returns:
        Trimmed text

    Raises:
        ValidationError: If text is too short or too long
    """
    trimmed = text.strip()

    if len(trimmed) < 10:
        raise ValidationError("Text must be at least 10 characters")

    if len(trimmed) > 2000:
        raise ValidationError("Text must not exceed 2000 characters")

    return trimmed


def validate_email(email: Optional[str]) -> str:
    """
    Validate email format if provided.

    Args:
        email: Optional email address

    Returns:
        Validated email or empty string

    Raises:
        ValidationError: If email format is invalid
    """
    if not email or email.strip() == "":
        return ""

    EMAIL_REGEX = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'

    if not re.match(EMAIL_REGEX, email.strip()):
        raise ValidationError("Invalid email format")

    return email.strip()


VALID_CATEGORIES = ['bug', 'feature', 'improvement', 'documentation', 'question']


def validate_category(category: str) -> str:
    """
    Validate category is in allowed list.

    Args:
        category: Feedback category

    Returns:
        Validated category

    Raises:
        ValidationError: If category is not in allowed list
    """
    if category.lower() not in VALID_CATEGORIES:
        raise ValidationError(
            f"Invalid category. Must be one of: {', '.join(VALID_CATEGORIES)}"
        )

    return category.lower()


def validate_id_format(id_value: str) -> str:
    """
    Validate ID format (alphanumeric, dashes, underscores only).

    Args:
        id_value: Feedback submission ID

    Returns:
        Validated ID

    Raises:
        ValidationError: If ID format is invalid
    """
    ID_REGEX = r'^[a-zA-Z0-9_-]+$'

    if not re.match(ID_REGEX, id_value):
        raise ValidationError("Invalid ID format")

    return id_value


def validate_timestamp(timestamp: int) -> int:
    """
    Validate timestamp is not negative and not too far in future.

    Args:
        timestamp: Unix timestamp in milliseconds

    Returns:
        Validated timestamp

    Raises:
        ValidationError: If timestamp is invalid
    """
    try:
        timestamp_value = int(timestamp)
    except (ValueError, TypeError):
        raise ValidationError("Invalid timestamp format")

    if timestamp_value < 0:
        raise ValidationError("Timestamp cannot be negative")

    # Allow 60 second grace period for clock skew
    current_time = int(time.time() * 1000)
    if timestamp_value > current_time + 60000:
        raise ValidationError("Timestamp cannot be in the future")

    return timestamp_value
