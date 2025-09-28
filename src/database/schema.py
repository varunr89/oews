"""
Database schema creation and initialization.
"""

import logging
from sqlalchemy import text
from config.database import db_config
from config.constants import OWNERSHIP_TYPES
from .models import Base, OwnershipType
from .connection import DatabaseManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SchemaManager:
    """Manages database schema creation and initialization."""

    def __init__(self):
        self.db_manager = DatabaseManager()

    def create_schema(self):
        """Create all database tables and indexes."""
        try:
            logger.info("Creating database schema...")

            # Create all tables from ORM models
            Base.metadata.create_all(bind=self.db_manager.get_engine())

            logger.info("Database schema created successfully")

            # Initialize lookup data
            self._initialize_lookup_data()

        except Exception as e:
            logger.error(f"Failed to create schema: {e}")
            raise

    def drop_schema(self):
        """Drop all database tables."""
        try:
            logger.info("Dropping database schema...")
            Base.metadata.drop_all(bind=self.db_manager.get_engine())
            logger.info("Database schema dropped successfully")
        except Exception as e:
            logger.error(f"Failed to drop schema: {e}")
            raise

    def _initialize_lookup_data(self):
        """Initialize lookup tables with reference data."""
        try:
            logger.info("Initializing lookup data...")
            self._load_ownership_types()
            logger.info("Lookup data initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize lookup data: {e}")
            raise

    def _load_ownership_types(self):
        """Load ownership type reference data."""
        with self.db_manager.get_session() as session:
            # Check if data already exists
            existing_count = session.query(OwnershipType).count()
            if existing_count > 0:
                logger.info(f"Ownership types already loaded ({existing_count} records)")
                return

            # Load ownership types from constants
            for own_code, description in OWNERSHIP_TYPES.items():
                ownership_type = OwnershipType(
                    own_code=own_code,
                    own_description=description
                )
                session.add(ownership_type)

            logger.info(f"Loaded {len(OWNERSHIP_TYPES)} ownership types")

    def check_schema_exists(self) -> bool:
        """Check if the database schema exists."""
        try:
            from sqlalchemy import text
            with self.db_manager.get_session() as session:
                # Try to query one of the main tables
                session.execute(text("SELECT 1 FROM ownership_types LIMIT 1"))
                return True
        except Exception:
            return False

    def get_schema_info(self) -> dict:
        """Get information about the current schema."""
        info = {
            "schema_exists": self.check_schema_exists(),
            "tables": [],
            "total_records": {}
        }

        if info["schema_exists"]:
            try:
                with self.db_manager.get_session() as session:
                    # Get table information
                    from .models import GeographicArea, Occupation, Industry, OwnershipType, EmploymentWageData, DataVintage

                    tables = [
                        ("geographic_areas", GeographicArea),
                        ("occupations", Occupation),
                        ("industries", Industry),
                        ("ownership_types", OwnershipType),
                        ("employment_wage_data", EmploymentWageData),
                        ("data_vintages", DataVintage)
                    ]

                    for table_name, model_class in tables:
                        try:
                            count = session.query(model_class).count()
                            info["tables"].append(table_name)
                            info["total_records"][table_name] = count
                        except Exception as e:
                            logger.warning(f"Could not get count for {table_name}: {e}")

            except Exception as e:
                logger.error(f"Error getting schema info: {e}")

        return info

# Global schema manager instance
schema_manager = SchemaManager()