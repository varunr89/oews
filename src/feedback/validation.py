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
