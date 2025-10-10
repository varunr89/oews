"""
Database Connection Manager

Provides centralized database connection management, session handling,
and transaction utilities for the OEWS migration application.
"""

import os
import logging
from contextlib import contextmanager
from typing import Any, Dict, Generator, Optional, List
from urllib.parse import urlparse

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.pool import QueuePool

from ..models import Base, metadata

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Centralized database connection and session management

    Provides connection pooling, session management, transaction handling,
    and database utilities following constitutional performance requirements.
    """

    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize database manager

        Args:
            database_url: Database connection URL. If None, uses DATABASE_URL env var
        """
        self.database_url = database_url or os.getenv('DATABASE_URL', 'sqlite:///oews_migration.db')
        self.engine: Optional[Engine] = None
        self.SessionLocal: Optional[sessionmaker] = None
        self._is_initialized = False

    def initialize(self) -> None:
        """Initialize database engine and session factory"""
        if self._is_initialized:
            return

        try:
            # Configure engine based on database type
            engine_kwargs = self._get_engine_config()
            self.engine = create_engine(self.database_url, **engine_kwargs)

            # Test connection
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))

            # Create session factory
            self.SessionLocal = sessionmaker(
                bind=self.engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False
            )

            self._is_initialized = True
            logger.info(f"Database initialized successfully: {self._get_db_type()}")

        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def _get_engine_config(self) -> Dict[str, Any]:
        """Get engine configuration based on database type and performance requirements"""
        db_type = self._get_db_type()

        base_config = {
            'echo': os.getenv('SQL_ECHO', 'false').lower() == 'true',
            'pool_pre_ping': True,  # Verify connections before use
            'pool_recycle': 3600,   # Recycle connections every hour
        }

        if db_type == 'sqlite':
            # SQLite configuration for development
            base_config.update({
                'connect_args': {
                    'check_same_thread': False,
                    'timeout': 30,  # 30 second timeout
                },
                'poolclass': None,  # SQLite doesn't need pooling
            })
        else:
            # PostgreSQL/other database configuration for production
            base_config.update({
                'poolclass': QueuePool,
                'pool_size': 10,        # Constitutional requirement: handle concurrent operations
                'max_overflow': 20,     # Allow burst capacity
                'pool_timeout': 30,     # 30 second timeout
                'connect_args': {
                    'connect_timeout': int(os.getenv('DB_CONNECTION_TIMEOUT', '30')),
                }
            })

        return base_config

    def _get_db_type(self) -> str:
        """Get database type from URL"""
        parsed = urlparse(self.database_url)
        return parsed.scheme.split('+')[0]  # Handle dialects like postgresql+psycopg2

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Get a database session with automatic cleanup

        Yields:
            SQLAlchemy session

        Usage:
            with db_manager.get_session() as session:
                # Use session here
                pass
        """
        if not self._is_initialized:
            self.initialize()

        session = self.SessionLocal()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @contextmanager
    def transaction(self) -> Generator[Session, None, None]:
        """
        Get a database session with automatic transaction management

        Automatically commits on success, rolls back on exception.

        Yields:
            SQLAlchemy session within a transaction

        Usage:
            with db_manager.transaction() as session:
                # Database operations here
                # Automatically committed on success
                pass
        """
        with self.get_session() as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    def execute_query(self, query: str, params: Optional[Dict] = None) -> List[Dict]:
        """
        Execute a raw SQL query and return results

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            List of result dictionaries

        Performance: Must complete in <1 second per constitutional requirement
        """
        start_time = self._get_current_time()

        try:
            with self.get_session() as session:
                result = session.execute(text(query), params or {})
                rows = []

                if result.returns_rows:
                    # Convert results to dictionaries
                    columns = result.keys()
                    for row in result:
                        rows.append(dict(zip(columns, row)))

                duration = self._get_current_time() - start_time
                if duration > 1.0:  # Constitutional requirement: <1 second
                    logger.warning(f"Query exceeded performance target: {duration:.2f}s")

                return rows

        except SQLAlchemyError as e:
            logger.error(f"Query execution failed: {e}")
            raise

    def bulk_insert(self, model_class, records: List[Dict], batch_size: int = 1000) -> int:
        """
        Perform bulk insert for large datasets

        Args:
            model_class: SQLAlchemy model class
            records: List of record dictionaries
            batch_size: Number of records per batch

        Returns:
            Number of records inserted

        Optimized for constitutional memory constraints (<1.75GB)
        """
        if not records:
            return 0

        total_inserted = 0

        try:
            with self.transaction() as session:
                # Process in batches to manage memory usage
                for i in range(0, len(records), batch_size):
                    batch = records[i:i + batch_size]

                    # Use bulk_insert_mappings for performance
                    session.bulk_insert_mappings(model_class, batch)
                    total_inserted += len(batch)

                    # Log progress for large operations
                    if len(records) > 10000 and i % (batch_size * 10) == 0:
                        logger.info(f"Bulk insert progress: {total_inserted}/{len(records)} records")

                logger.info(f"Bulk insert completed: {total_inserted} records")
                return total_inserted

        except Exception as e:
            logger.error(f"Bulk insert failed: {e}")
            raise

    def save(self, instance) -> Any:
        """
        Save a model instance

        Args:
            instance: Model instance to save

        Returns:
            The saved instance with populated ID
        """
        try:
            with self.transaction() as session:
                session.add(instance)
                session.flush()  # Get the ID without committing
                session.refresh(instance)
                return instance

        except IntegrityError as e:
            logger.error(f"Integrity constraint violation: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to save instance: {e}")
            raise

    def update(self, instance) -> Any:
        """
        Update a model instance

        Args:
            instance: Model instance to update

        Returns:
            The updated instance
        """
        try:
            with self.transaction() as session:
                session.merge(instance)
                return instance

        except Exception as e:
            logger.error(f"Failed to update instance: {e}")
            raise

    def delete(self, instance) -> None:
        """
        Delete a model instance

        Args:
            instance: Model instance to delete
        """
        try:
            with self.transaction() as session:
                # Re-attach to session if needed
                if instance not in session:
                    instance = session.merge(instance)
                session.delete(instance)

        except Exception as e:
            logger.error(f"Failed to delete instance: {e}")
            raise

    def get_by_id(self, model_class, record_id: Any):
        """
        Get a record by ID

        Args:
            model_class: SQLAlchemy model class
            record_id: Record ID

        Returns:
            Model instance or None if not found
        """
        try:
            with self.get_session() as session:
                return session.get(model_class, record_id)

        except Exception as e:
            logger.error(f"Failed to get record by ID: {e}")
            raise

    def list_tables(self) -> List[str]:
        """
        Get list of all tables in the database

        Returns:
            List of table names
        """
        try:
            if not self._is_initialized:
                self.initialize()

            return list(self.engine.table_names())

        except Exception as e:
            logger.error(f"Failed to list tables: {e}")
            raise

    def table_exists(self, table_name: str) -> bool:
        """
        Check if a table exists

        Args:
            table_name: Name of the table

        Returns:
            True if table exists, False otherwise
        """
        try:
            return table_name in self.list_tables()

        except Exception as e:
            logger.error(f"Failed to check table existence: {e}")
            return False

    def get_table_row_count(self, table_name: str) -> int:
        """
        Get row count for a table

        Args:
            table_name: Name of the table

        Returns:
            Number of rows in the table
        """
        try:
            result = self.execute_query(f"SELECT COUNT(*) as count FROM {table_name}")
            return result[0]['count'] if result else 0

        except Exception as e:
            logger.error(f"Failed to get row count for {table_name}: {e}")
            return 0

    def vacuum_database(self) -> None:
        """
        Perform database vacuum/optimization

        Useful after large data operations to reclaim space and update statistics
        """
        try:
            db_type = self._get_db_type()

            if db_type == 'sqlite':
                with self.engine.connect() as conn:
                    conn.execute(text("VACUUM"))
                logger.info("SQLite VACUUM completed")

            elif db_type == 'postgresql':
                # Note: VACUUM cannot be run inside a transaction
                with self.engine.connect() as conn:
                    conn.execute(text("VACUUM ANALYZE"))
                logger.info("PostgreSQL VACUUM ANALYZE completed")

        except Exception as e:
            logger.warning(f"Database vacuum failed: {e}")

    def get_connection_info(self) -> Dict[str, Any]:
        """
        Get database connection information

        Returns:
            Dictionary with connection details
        """
        if not self._is_initialized:
            return {'status': 'not_initialized'}

        try:
            db_type = self._get_db_type()
            info = {
                'database_type': db_type,
                'url': self.database_url.split('@')[-1] if '@' in self.database_url else self.database_url,
                'pool_size': getattr(self.engine.pool, 'size', 'N/A'),
                'checked_out': getattr(self.engine.pool, 'checkedout', 'N/A'),
                'status': 'connected'
            }

            # Test connection
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                info['connection_test'] = 'success'

            return info

        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }

    def close(self) -> None:
        """Close database connections and cleanup resources"""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connections closed")

        self._is_initialized = False

    def _get_current_time(self) -> float:
        """Get current time for performance measurement"""
        import time
        return time.time()

    def __enter__(self):
        """Context manager entry"""
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_db_manager(database_url: Optional[str] = None) -> DatabaseManager:
    """
    Get the global database manager instance

    Args:
        database_url: Database URL (only used for first initialization)

    Returns:
        DatabaseManager instance
    """
    global _db_manager

    if _db_manager is None:
        _db_manager = DatabaseManager(database_url)

    return _db_manager


def initialize_database(database_url: Optional[str] = None) -> DatabaseManager:
    """
    Initialize the global database manager

    Args:
        database_url: Database connection URL

    Returns:
        Initialized DatabaseManager instance
    """
    db_manager = get_db_manager(database_url)
    db_manager.initialize()
    return db_manager


def close_database() -> None:
    """Close the global database manager"""
    global _db_manager

    if _db_manager:
        _db_manager.close()
        _db_manager = None