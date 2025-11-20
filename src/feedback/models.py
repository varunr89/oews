"""Pydantic models for feedback API."""

from pydantic import BaseModel
from typing import Optional


class FeedbackRequest(BaseModel):
    """Request model for feedback submission."""
    category: str
    text: str
    email: Optional[str] = ""
    honeypot: str
    timestamp: int
    id: str


class FeedbackResponse(BaseModel):
    """Success response for feedback submission."""
    success: bool
    message: str


class FeedbackErrorResponse(BaseModel):
    """Error response for feedback submission."""
    error: str
