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
