"""
Database connection management for the OEWS application.
"""

import logging
from contextlib import contextmanager
from typing import Optional, Generator

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from config.database import db_config
from config.settings import Settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    """High-level database management interface."""

    def __init__(self):
        self.db_config = db_config
        self.settings = Settings()

    def is_connected(self) -> bool:
        """Test if database connection is working."""
        try:
            return self.db_config.test_connection()
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Context manager for database sessions.
        Automatically handles session lifecycle and error handling.
        """
        session = self.db_config.get_session()
        try:
            yield session
            session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error: {e}")
            raise
        except Exception as e:
            session.rollback()
            logger.error(f"Unexpected error: {e}")
            raise
        finally:
            session.close()

    def create_all_tables(self):
        """Create all database tables."""
        try:
            self.db_config.create_tables()
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise

    def drop_all_tables(self):
        """Drop all database tables (use with caution!)."""
        try:
            self.db_config.drop_tables()
            logger.info("Database tables dropped successfully")
        except Exception as e:
            logger.error(f"Failed to drop tables: {e}")
            raise

    def get_engine(self):
        """Get the database engine for direct access."""
        return self.db_config.get_engine()

    def execute_raw_sql(self, sql: str, params: Optional[dict] = None):
        """Execute raw SQL with optional parameters."""
        try:
            from sqlalchemy import text
            with self.get_session() as session:
                result = session.execute(text(sql), params or {})
                return result
        except Exception as e:
            logger.error(f"Failed to execute SQL: {e}")
            raise

    def get_database_info(self) -> dict:
        """Get information about the database configuration."""
        return {
            "database_url": self.settings.get_database_url(),
            "is_sqlite": self.settings.is_sqlite(),
            "is_production": self.settings.is_production(),
            "connected": self.is_connected()
        }

# Global database manager instance
db_manager = DatabaseManager()