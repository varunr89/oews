"""FastAPI endpoints for feedback submission."""

from fastapi import APIRouter, HTTPException
from src.feedback.models import FeedbackRequest, FeedbackResponse
from src.feedback.validation import (
    ValidationError,
    HoneypotTriggered,
    validate_required_fields,
    validate_honeypot,
    validate_text_length,
    validate_email,
    validate_category,
    validate_id_format,
    validate_timestamp
)
from src.feedback.github_client import GitHubClient, GitHubAPIError
from src.utils.logger import setup_workflow_logger


# Create router
router = APIRouter()

# Setup logger
feedback_logger = setup_workflow_logger("oews.feedback")

# GitHub client (will be initialized at startup)
github_client = None


def init_github_client():
    """Initialize GitHub client (call at startup)."""
    global github_client
    try:
        github_client = GitHubClient()
        feedback_logger.info("GitHub client initialized successfully")
    except ValueError as e:
        feedback_logger.error(f"Failed to initialize GitHub client: {e}")
        raise


@router.post("/feedback/submit", response_model=FeedbackResponse)
async def submit_feedback(request: FeedbackRequest):
    """
    Submit feedback to GitHub via repository_dispatch.

    Args:
        request: Feedback submission request

    Returns:
        Success response

    Raises:
        HTTPException: If validation fails or GitHub API call fails
    """
    try:
        # Validate required fields
        validate_required_fields(request.model_dump())

        # Check honeypot (return fake success if triggered)
        try:
            validate_honeypot(request.honeypot)
        except HoneypotTriggered:
            feedback_logger.warning(f"Honeypot triggered: id={request.id}")
            return FeedbackResponse(
                success=True,
                message="Feedback submitted successfully"
            )

        # Validate remaining fields
        validated_text = validate_text_length(request.text)
        validated_email = validate_email(request.email)
        validated_category = validate_category(request.category)
        validate_id_format(request.id)
        validate_timestamp(request.timestamp)

        # Prepare payload for GitHub
        payload = {
            'category': validated_category,
            'text': validated_text,
            'email': validated_email,
            'honeypot': request.honeypot,
            'timestamp': request.timestamp,
            'id': request.id
        }

        # Call GitHub API
        if github_client is None:
            raise HTTPException(
                status_code=503,
                detail="GitHub client not initialized"
            )

        await github_client.trigger_dispatch(payload)

        # Log success
        feedback_logger.info(
            f"Feedback submitted: id={request.id}, category={validated_category}"
        )

        return FeedbackResponse(
            success=True,
            message="Feedback submitted successfully"
        )

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except GitHubAPIError as e:
        feedback_logger.error(f"GitHub API error: id={request.id}, error={str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to submit feedback to GitHub"
        )

    except Exception as e:
        feedback_logger.error(f"Unexpected error: id={request.id}, error={str(e)}")
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred"
        )
