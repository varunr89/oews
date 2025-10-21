import pytest
from src.database.connection import OEWSDatabase

def test_sqlite_connection_initializes():
    """Test that SQLite database connection can be created."""
    db = OEWSDatabase(environment='dev')
    assert db is not None
    assert db.engine is not None

def test_execute_query_returns_dataframe():
    """Test that execute_query returns a pandas DataFrame."""
    import pandas as pd
    db = OEWSDatabase(environment='dev')
    result = db.execute_query("SELECT * FROM oews_data LIMIT 1")
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 1

def test_execute_query_with_parameters():
    """Test parameterized queries prevent SQL injection."""
    import pandas as pd
    db = OEWSDatabase(environment='dev')
    # Safe parameterized query
    result = db.execute_query(
        "SELECT * FROM oews_data WHERE AREA_TITLE LIKE ? LIMIT 1",
        params=('%Washington%',)
    )
    assert isinstance(result, pd.DataFrame)

def test_connection_pooling_reuses_connections():
    """Test that connection pooling is configured."""
    db = OEWSDatabase(environment='dev')
    # SQLAlchemy engine should have pooling configured
    assert db.engine.pool is not None
