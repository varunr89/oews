import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_azure_clients() -> dict[str, MagicMock]:
    """Provide mocked Azure SDK clients used across contract tests."""
    credential = MagicMock(name="AzureCliCredential")
    sql_client = MagicMock(name="SqlManagementClient")
    resource_client = MagicMock(name="ResourceManagementClient")

    return {
        "credential": credential,
        "sql_client": sql_client,
        "resource_client": resource_client,
    }


@pytest.fixture
def sqlite_test_db(tmp_path: Path) -> Path:
    """Create a throwaway SQLite database populated with a sample table."""
    db_path = tmp_path / "test.db"
    connection = sqlite3.connect(db_path)
    try:
        connection.execute(
            """
            CREATE TABLE occupations (
                id INTEGER PRIMARY KEY,
                occupation TEXT NOT NULL,
                salary REAL
            )
            """
        )
        connection.executemany(
            "INSERT INTO occupations (occupation, salary) VALUES (?, ?)",
            [
                ("Data Scientist", 120000.0),
                ("Statistician", 95000.0),
                ("Economist", 105000.0),
            ],
        )
        connection.commit()
    finally:
        connection.close()

    return db_path


@contextmanager
def _mock_connection(name: str) -> Generator[MagicMock, None, None]:
    """Shared helper to provide a mock DB API compliant connection."""
    connection = MagicMock(name=name)
    cursor = MagicMock(name=f"{name}.cursor")
    connection.cursor.return_value.__enter__.return_value = cursor
    connection.__enter__.return_value = connection
    connection.__exit__.return_value = False
    try:
        yield connection
    finally:
        # No teardown work required for pure mocks, but keep hook for future use.
        pass


@pytest.fixture
def mock_pyodbc_connection() -> Generator[MagicMock, None, None]:
    """Yield a mocked pyodbc connection with context manager behavior."""
    with _mock_connection("pyodbc_connection") as connection:
        yield connection


@pytest.fixture
def mock_pymssql_connection() -> Generator[MagicMock, None, None]:
    """Yield a mocked pymssql connection with context manager behavior."""
    with _mock_connection("pymssql_connection") as connection:
        yield connection
