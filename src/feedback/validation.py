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
