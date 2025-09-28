"""
Database configuration and connection settings.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool
from .settings import Settings

# SQLAlchemy base class for ORM models
Base = declarative_base()

class DatabaseConfig:
    """Database configuration and engine management."""

    def __init__(self):
        self.settings = Settings()
        self.engine = None
        self.SessionLocal = None
        self._initialize_engine()

    def _initialize_engine(self):
        """Initialize the database engine based on configuration."""
        database_url = self.settings.get_database_url()

        if self.settings.is_sqlite():
            # SQLite-specific configuration
            self.engine = create_engine(
                database_url,
                echo=self.settings.DATABASE_ECHO,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
            )
        else:
            # PostgreSQL configuration
            self.engine = create_engine(
                database_url,
                echo=self.settings.DATABASE_ECHO,
                pool_size=self.settings.DATABASE_POOL_SIZE,
                max_overflow=self.settings.DATABASE_MAX_OVERFLOW,
                pool_pre_ping=True,  # Verify connections before use
            )

        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )

    def get_engine(self):
        """Get the database engine."""
        return self.engine

    def get_session(self):
        """Get a new database session."""
        return self.SessionLocal()

    def create_tables(self):
        """Create all tables defined in the models."""
        Base.metadata.create_all(bind=self.engine)

    def drop_tables(self):
        """Drop all tables (use with caution!)."""
        Base.metadata.drop_all(bind=self.engine)

    def test_connection(self) -> bool:
        """Test the database connection."""
        try:
            from sqlalchemy import text
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

# Global database configuration instance
db_config = DatabaseConfig()