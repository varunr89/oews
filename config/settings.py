"""
Application configuration settings for the OEWS Streamlit app.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings:
    """Application settings configuration."""

    # Database Configuration
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "sqlite:///data/oews.db"  # Default to SQLite in data directory
    )
    DATABASE_POOL_SIZE = int(os.getenv("DATABASE_POOL_SIZE", "5"))
    DATABASE_MAX_OVERFLOW = int(os.getenv("DATABASE_MAX_OVERFLOW", "10"))
    DATABASE_ECHO = os.getenv("DATABASE_ECHO", "False").lower() == "true"

    # Application Configuration
    APP_NAME = "OEWS Data Explorer"
    APP_VERSION = "1.0.0"
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"

    # Data Configuration
    DATA_DIRECTORY = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    EXCEL_FILE_PATTERN = "*.xlsx"

    # Streamlit Configuration
    STREAMLIT_SERVER_PORT = int(os.getenv("STREAMLIT_SERVER_PORT", "8501"))
    STREAMLIT_SERVER_ADDRESS = os.getenv("STREAMLIT_SERVER_ADDRESS", "localhost")
    STREAMLIT_SERVER_HEADLESS = os.getenv("STREAMLIT_SERVER_HEADLESS", "false").lower() == "true"

    # Cache Configuration
    CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))  # 1 hour default

    @classmethod
    def get_database_url(cls) -> str:
        """Get the database URL with proper formatting."""
        return cls.DATABASE_URL

    @classmethod
    def is_production(cls) -> bool:
        """Check if running in production environment."""
        return not cls.DEBUG and "sqlite" not in cls.DATABASE_URL.lower()

    @classmethod
    def is_sqlite(cls) -> bool:
        """Check if using SQLite database."""
        return "sqlite" in cls.DATABASE_URL.lower()

    @classmethod
    def get_data_files(cls) -> list:
        """Get list of data files in the data directory."""
        import glob
        pattern = os.path.join(cls.DATA_DIRECTORY, cls.EXCEL_FILE_PATTERN)
        return glob.glob(pattern)