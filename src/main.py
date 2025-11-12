"""Main entry point for FastAPI server."""

import uvicorn
import os
from dotenv import load_dotenv


def main():
    # Load environment variables from .env file
    load_dotenv()
    """Start the FastAPI server."""
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    reload = os.getenv("API_RELOAD", "true").lower() == "true"
    workers = int(os.getenv("API_WORKERS", "4"))

    # Workers and reload are mutually exclusive
    if reload:
        workers = None

    uvicorn.run(
        "src.api.endpoints:app",
        host=host,
        port=port,
        reload=reload,
        workers=workers,
        timeout_keep_alive=300,  # 5 minutes keep-alive
        log_level="info"
    )


if __name__ == "__main__":
    main()
