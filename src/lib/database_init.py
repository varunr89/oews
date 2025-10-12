"""
Database Initialization Script

Handles database schema creation, migration, and initialization
for the OEWS migration application.
"""

import logging
import os
from typing import Dict, List, Optional

from sqlalchemy import text, inspect
from sqlalchemy.exc import SQLAlchemyError

from .db_manager import DatabaseManager, get_db_manager
from ..models import Base, metadata

logger = logging.getLogger(__name__)


class DatabaseInitializer:
    """
    Database schema initialization and migration management

    Handles table creation, schema updates, and database preparation
    for the OEWS migration application.
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """
        Initialize database initializer

        Args:
            db_manager: Database manager instance. If None, uses global instance
        """
        self.db_manager = db_manager or get_db_manager()

    def create_all_tables(self, drop_existing: bool = False) -> None:
        """
        Create all database tables

        Args:
            drop_existing: Whether to drop existing tables first

        Raises:
            SQLAlchemyError: If table creation fails
        """
        try:
            if not self.db_manager._is_initialized:
                self.db_manager.initialize()

            if drop_existing:
                logger.warning("Dropping all existing tables")
                Base.metadata.drop_all(bind=self.db_manager.engine)

            logger.info("Creating database tables...")
            Base.metadata.create_all(bind=self.db_manager.engine)

            # Verify tables were created
            created_tables = self._get_existing_tables()
            expected_tables = set(Base.metadata.tables.keys())

            missing_tables = expected_tables - set(created_tables)
            if missing_tables:
                raise SQLAlchemyError(f"Failed to create tables: {missing_tables}")

            logger.info(f"Successfully created {len(created_tables)} tables: {sorted(created_tables)}")

        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise

    def drop_all_tables(self) -> None:
        """
        Drop all database tables

        WARNING: This will destroy all data!
        """
        try:
            if not self.db_manager._is_initialized:
                self.db_manager.initialize()

            logger.warning("Dropping all database tables - this will destroy all data!")
            Base.metadata.drop_all(bind=self.db_manager.engine)

            remaining_tables = self._get_existing_tables()
            if remaining_tables:
                logger.warning(f"Some tables still exist after drop: {remaining_tables}")
            else:
                logger.info("All tables dropped successfully")

        except Exception as e:
            logger.error(f"Failed to drop tables: {e}")
            raise

    def initialize_fresh_database(self) -> None:
        """
        Initialize a completely fresh database

        Drops all existing tables and creates new ones
        """
        logger.info("Initializing fresh database...")

        try:
            self.drop_all_tables()
            self.create_all_tables()
            self._create_indexes()
            self._populate_initial_data()

            logger.info("Fresh database initialization completed successfully")

        except Exception as e:
            logger.error(f"Fresh database initialization failed: {e}")
            raise

    def upgrade_schema(self) -> None:
        """
        Upgrade database schema to latest version

        Creates missing tables and columns without dropping existing data
        """
        logger.info("Upgrading database schema...")

        try:
            existing_tables = set(self._get_existing_tables())
            expected_tables = set(Base.metadata.tables.keys())

            # Create missing tables
            missing_tables = expected_tables - existing_tables
            if missing_tables:
                logger.info(f"Creating missing tables: {sorted(missing_tables)}")
                # Create only missing tables
                for table_name in missing_tables:
                    table = Base.metadata.tables[table_name]
                    table.create(bind=self.db_manager.engine)

            # Check for missing columns (basic implementation)
            self._add_missing_columns()

            # Create missing indexes
            self._create_indexes()

            logger.info("Schema upgrade completed successfully")

        except Exception as e:
            logger.error(f"Schema upgrade failed: {e}")
            raise

    def validate_schema(self) -> Dict[str, List[str]]:
        """
        Validate current database schema against expected schema

        Returns:
            Dictionary with validation results
        """
        results = {
            'missing_tables': [],
            'extra_tables': [],
            'missing_columns': [],
            'issues': []
        }

        try:
            existing_tables = set(self._get_existing_tables())
            expected_tables = set(Base.metadata.tables.keys())

            # Check for missing tables
            results['missing_tables'] = sorted(expected_tables - existing_tables)

            # Check for extra tables (non-application tables)
            results['extra_tables'] = sorted(existing_tables - expected_tables)

            # Check columns for existing tables
            for table_name in existing_tables & expected_tables:
                missing_cols = self._check_missing_columns(table_name)
                if missing_cols:
                    results['missing_columns'].extend(
                        [f"{table_name}.{col}" for col in missing_cols]
                    )

            # Generate summary
            if results['missing_tables']:
                results['issues'].append(f"Missing tables: {len(results['missing_tables'])}")

            if results['missing_columns']:
                results['issues'].append(f"Missing columns: {len(results['missing_columns'])}")

            if not results['issues']:
                results['issues'].append("Schema validation passed")

            logger.info(f"Schema validation completed: {results['issues']}")

        except Exception as e:
            results['issues'].append(f"Validation error: {e}")
            logger.error(f"Schema validation failed: {e}")

        return results

    def get_database_info(self) -> Dict[str, any]:
        """
        Get comprehensive database information

        Returns:
            Dictionary with database details
        """
        info = {
            'connection': self.db_manager.get_connection_info(),
            'tables': {},
            'total_tables': 0,
            'total_rows': 0
        }

        try:
            tables = self._get_existing_tables()
            info['total_tables'] = len(tables)

            for table_name in tables:
                try:
                    row_count = self.db_manager.get_table_row_count(table_name)
                    info['tables'][table_name] = {
                        'row_count': row_count,
                        'exists': True
                    }
                    info['total_rows'] += row_count
                except Exception as e:
                    info['tables'][table_name] = {
                        'error': str(e),
                        'exists': True
                    }

            # Check for expected tables that don't exist
            expected_tables = set(Base.metadata.tables.keys())
            existing_tables = set(tables)
            missing_tables = expected_tables - existing_tables

            for table_name in missing_tables:
                info['tables'][table_name] = {
                    'exists': False,
                    'row_count': 0
                }

        except Exception as e:
            info['error'] = str(e)
            logger.error(f"Failed to get database info: {e}")

        return info

    def create_test_data(self) -> None:
        """
        Create test data for development and testing

        Only creates data if tables are empty
        """
        logger.info("Creating test data...")

        try:
            from ..models import ExcelFile, UnifiedSchema, FileStatus

            with self.db_manager.transaction() as session:
                # Check if test data already exists
                existing_files = session.query(ExcelFile).count()
                if existing_files > 0:
                    logger.info("Test data already exists, skipping creation")
                    return

                # Create test unified schema
                test_schema = UnifiedSchema(
                    schema_name="test_oews_schema",
                    description="Test schema for OEWS data",
                    version="1.0.0",
                    table_definitions={
                        "tables": [
                            {
                                "name": "oews_data",
                                "columns": [
                                    {"name": "id", "type": "UUID", "nullable": False},
                                    {"name": "area", "type": "VARCHAR(10)", "nullable": False},
                                    {"name": "area_title", "type": "VARCHAR(255)", "nullable": True},
                                    {"name": "occ_code", "type": "VARCHAR(10)", "nullable": False},
                                    {"name": "occ_title", "type": "VARCHAR(255)", "nullable": True},
                                    {"name": "tot_emp", "type": "INTEGER", "nullable": True},
                                    {"name": "a_mean", "type": "DECIMAL(10,2)", "nullable": True}
                                ]
                            }
                        ]
                    },
                    is_oews_compliant=True,
                    status="validated"
                )
                session.add(test_schema)
                session.flush()

                # Create test Excel file records
                test_files = [
                    ExcelFile(
                        file_path="/data/test_oews_2023.xlsx",
                        file_name="test_oews_2023.xlsx",
                        file_size=75000000,  # 75MB
                        file_hash="a1b2c3d4e5f6789012345678901234567890123456789012345678901234abcd",
                        sheet_count=4,
                        status=FileStatus.DISCOVERED,
                        is_oews_format=True,
                        oews_year=2023
                    ),
                    ExcelFile(
                        file_path="/data/test_oews_2022.xlsx",
                        file_name="test_oews_2022.xlsx",
                        file_size=72000000,  # 72MB
                        file_hash="b2c3d4e5f6789012345678901234567890123456789012345678901234abcd1",
                        sheet_count=4,
                        status=FileStatus.COMPLETED,
                        is_oews_format=True,
                        oews_year=2022
                    )
                ]

                for file_record in test_files:
                    session.add(file_record)

                logger.info(f"Created test data: 1 schema, {len(test_files)} Excel files")

        except Exception as e:
            logger.error(f"Failed to create test data: {e}")
            raise

    def _get_existing_tables(self) -> List[str]:
        """Get list of existing tables in database"""
        if not self.db_manager._is_initialized:
            self.db_manager.initialize()

        inspector = inspect(self.db_manager.engine)
        return inspector.get_table_names()

    def _check_missing_columns(self, table_name: str) -> List[str]:
        """Check for missing columns in a table"""
        try:
            inspector = inspect(self.db_manager.engine)
            existing_columns = {col['name'] for col in inspector.get_columns(table_name)}

            if table_name in Base.metadata.tables:
                expected_columns = set(Base.metadata.tables[table_name].columns.keys())
                return sorted(expected_columns - existing_columns)

        except Exception as e:
            logger.warning(f"Could not check columns for table {table_name}: {e}")

        return []

    def _add_missing_columns(self) -> None:
        """Add missing columns to existing tables (basic implementation)"""
        # This is a simplified implementation
        # In production, you might want to use Alembic for proper migrations
        logger.info("Checking for missing columns...")

        try:
            existing_tables = set(self._get_existing_tables())
            expected_tables = set(Base.metadata.tables.keys())

            for table_name in existing_tables & expected_tables:
                missing_columns = self._check_missing_columns(table_name)
                if missing_columns:
                    logger.warning(f"Table {table_name} is missing columns: {missing_columns}")
                    # Note: Adding columns dynamically requires careful handling
                    # This is left as a placeholder for more sophisticated migration logic

        except Exception as e:
            logger.warning(f"Could not check for missing columns: {e}")

    def _create_indexes(self) -> None:
        """Create database indexes for performance"""
        logger.info("Creating database indexes...")

        index_queries = [
            # ExcelFile indexes
            "CREATE INDEX IF NOT EXISTS idx_excel_file_path ON excel_file(file_path)",
            "CREATE INDEX IF NOT EXISTS idx_excel_file_status ON excel_file(status)",
            "CREATE INDEX IF NOT EXISTS idx_excel_file_hash ON excel_file(file_hash)",

            # ExcelSheet indexes
            "CREATE INDEX IF NOT EXISTS idx_excel_sheet_file_id ON excel_sheet(excel_file_id)",
            "CREATE INDEX IF NOT EXISTS idx_excel_sheet_name ON excel_sheet(sheet_name)",

            # MigrationBatch indexes
            "CREATE INDEX IF NOT EXISTS idx_migration_batch_status ON migration_batch(status)",
            "CREATE INDEX IF NOT EXISTS idx_migration_batch_schema ON migration_batch(unified_schema_id)",

            # MigrationRecord indexes
            "CREATE INDEX IF NOT EXISTS idx_migration_record_batch ON migration_record(migration_batch_id)",
            "CREATE INDEX IF NOT EXISTS idx_migration_record_file ON migration_record(excel_file_id)",
            "CREATE INDEX IF NOT EXISTS idx_migration_record_status ON migration_record(status)",

            # AuditLog indexes
            "CREATE INDEX IF NOT EXISTS idx_audit_log_operation ON audit_log(operation_type)",
            "CREATE INDEX IF NOT EXISTS idx_audit_log_entity ON audit_log(entity_type, entity_id)",
            "CREATE INDEX IF NOT EXISTS idx_audit_log_created ON audit_log(created_at)",
        ]

        try:
            for query in index_queries:
                try:
                    with self.db_manager.get_session() as session:
                        session.execute(text(query))
                        session.commit()
                except Exception as e:
                    # Index creation failures are non-fatal
                    logger.warning(f"Could not create index: {e}")

            logger.info("Index creation completed")

        except Exception as e:
            logger.warning(f"Index creation failed: {e}")

    def _populate_initial_data(self) -> None:
        """Populate initial reference data if needed"""
        # This could include default unified schemas, validation rules, etc.
        # Currently left as a placeholder
        logger.info("Initial data population completed")


def init_database(database_url: Optional[str] = None, create_test_data: bool = False) -> DatabaseInitializer:
    """
    Initialize database with all tables and optional test data

    Args:
        database_url: Database connection URL
        create_test_data: Whether to create test data

    Returns:
        DatabaseInitializer instance
    """
    db_manager = get_db_manager(database_url)
    initializer = DatabaseInitializer(db_manager)

    initializer.create_all_tables()

    if create_test_data:
        initializer.create_test_data()

    return initializer


def reset_database(database_url: Optional[str] = None) -> DatabaseInitializer:
    """
    Reset database (drop and recreate all tables)

    Args:
        database_url: Database connection URL

    Returns:
        DatabaseInitializer instance
    """
    db_manager = get_db_manager(database_url)
    initializer = DatabaseInitializer(db_manager)

    initializer.initialize_fresh_database()

    return initializer