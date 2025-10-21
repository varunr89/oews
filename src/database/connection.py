"""Database connection abstraction for SQLite and Azure SQL with connection pooling."""

import os
from typing import Literal, Optional, Tuple, Any
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool, NullPool


class OEWSDatabase:
    """
    Database abstraction layer for OEWS data.

    Supports both SQLite (development) and Azure SQL (production).
    Uses SQLAlchemy for connection pooling and parameterized queries.

    SECURITY: All queries must use parameterized queries to prevent SQL injection.
    """

    def __init__(self, environment: Optional[Literal['dev', 'prod']] = None):
        """
        Initialize database connection with pooling.

        Args:
            environment: 'dev' for SQLite, 'prod' for Azure SQL.
                        If None, uses DATABASE_ENV environment variable.
        """
        self.environment = environment or os.getenv('DATABASE_ENV', 'dev')
        self.engine = self._create_engine()

    def _create_engine(self):
        """
        Create SQLAlchemy engine with appropriate pooling.

        Returns:
            SQLAlchemy engine with connection pooling
        """
        if self.environment == 'dev':
            # SQLite: Use NullPool (SQLite doesn't handle concurrent connections well)
            db_path = os.getenv('SQLITE_DB_PATH', 'data/oews.db')
            connection_string = f'sqlite:///{db_path}'
            return create_engine(
                connection_string,
                poolclass=NullPool,  # No pooling for SQLite
                connect_args={'check_same_thread': False}
            )

        elif self.environment == 'prod':
            # Azure SQL: Use QueuePool for production
            server = os.getenv('AZURE_SQL_SERVER')
            database = os.getenv('AZURE_SQL_DATABASE')
            username = os.getenv('AZURE_SQL_USERNAME')
            password = os.getenv('AZURE_SQL_PASSWORD')

            # Use pyodbc driver for Azure SQL
            connection_string = (
                f'mssql+pyodbc://{username}:{password}@{server}/{database}'
                f'?driver=ODBC+Driver+18+for+SQL+Server'
            )
            return create_engine(
                connection_string,
                poolclass=QueuePool,
                pool_size=5,          # Max 5 connections in pool
                max_overflow=10,      # Allow up to 15 connections total
                pool_pre_ping=True,   # Verify connections before use
                pool_recycle=3600     # Recycle connections after 1 hour
            )
        else:
            raise ValueError(f"Invalid environment: {self.environment}")

    def execute_query(
        self,
        sql: str,
        params: Optional[Tuple[Any, ...]] = None
    ) -> pd.DataFrame:
        """
        Execute SQL query with parameters and return results as DataFrame.

        SECURITY: Uses parameterized queries to prevent SQL injection.
        All user input MUST be passed via the params argument, never
        via string formatting.

        Args:
            sql: SQL query string with ? placeholders for parameters
            params: Tuple of parameter values (optional)

        Returns:
            pandas DataFrame with query results

        Example:
            # CORRECT - parameterized query:
            db.execute_query(
                "SELECT * FROM oews_data WHERE AREA_TITLE LIKE ? LIMIT ?",
                params=('%Washington%', 10)
            )

            # WRONG - SQL injection vulnerable:
            area = user_input
            db.execute_query(f"SELECT * FROM oews_data WHERE AREA_TITLE LIKE '%{area}%'")
        """
        with self.engine.connect() as conn:
            if params:
                # For SQLite with pandas, we need to use raw connection
                # SQLAlchemy's text() expects named parameters, but we use ? placeholders
                # Use the underlying raw DBAPI connection for positional parameters
                result = pd.read_sql_query(sql, conn.connection, params=params)
            else:
                result = pd.read_sql_query(text(sql), conn)
        return result

    def close(self):
        """Dispose of the connection pool."""
        if self.engine:
            self.engine.dispose()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
