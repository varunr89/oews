"""
Unified Database Schema Builder Service

Creates consolidated SQL schemas from analyzed Excel structures.
Maps to FR-003: System MUST create a unified database schema that accommodates
all data fields found across all Excel files.
"""

import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import uuid

from sqlalchemy import String, Integer, Float, Boolean, DateTime, Date, Text
from sqlalchemy.orm import Session

from src.services.schema_analyzer import SchemaAnalyzer, FileSchema
from src.models.unified_schema import UnifiedSchema
from src.models.table_definition import TableDefinition
from src.models.column_definition import ColumnDefinition
from src.lib.db_manager import DatabaseManager

logger = logging.getLogger(__name__)


class SchemaBuilderService:
    """
    Unified database schema builder service

    Creates consolidated database schemas from analyzed Excel files,
    handling schema evolution and multi-file structures.
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """
        Initialize schema builder

        Args:
            db_manager: Database manager instance (optional)
        """
        self.schema_analyzer = SchemaAnalyzer()
        self.db_manager = db_manager or DatabaseManager()
        self.logger = logging.getLogger(__name__)

    def build_unified_schema(
        self,
        file_paths: List[Path],
        schema_name: str,
        description: Optional[str] = None,
        sample_size: int = 1000
    ) -> UnifiedSchema:
        """
        Build a unified schema from multiple Excel files

        Args:
            file_paths: List of Excel file paths to analyze
            schema_name: Name for the unified schema
            description: Schema description
            sample_size: Number of rows to sample for type inference

        Returns:
            UnifiedSchema instance

        Raises:
            ValueError: If files cannot be analyzed or schema cannot be created
        """
        self.logger.info(f"Building unified schema '{schema_name}' from {len(file_paths)} files")

        try:
            # Analyze all files
            file_schemas = self.schema_analyzer.analyze_multiple_files(file_paths, sample_size)

            if not file_schemas:
                raise ValueError("No files could be analyzed")

            # Get unified column list
            unified_columns = self.schema_analyzer.get_unified_column_list(file_schemas)

            # Detect schema evolution
            evolved_columns = self.schema_analyzer.detect_schema_evolution(file_schemas)
            if evolved_columns:
                self.logger.warning(
                    f"Schema evolution detected in {len(evolved_columns)} columns. "
                    f"Using most permissive type."
                )

            # Create unified schema model
            unified_schema = self._create_unified_schema_model(
                schema_name=schema_name,
                description=description or f"Unified schema for {len(file_paths)} OEWS files",
                unified_columns=unified_columns,
                evolved_columns=evolved_columns,
                source_files=[str(fp) for fp in file_paths]
            )

            self.logger.info(
                f"Created unified schema with {len(unified_columns)} columns "
                f"from {len(file_schemas)} files"
            )

            return unified_schema

        except Exception as e:
            self.logger.error(f"Failed to build unified schema: {str(e)}")
            raise ValueError(f"Cannot build unified schema: {str(e)}")

    def _create_unified_schema_model(
        self,
        schema_name: str,
        description: str,
        unified_columns: List[Dict[str, Any]],
        evolved_columns: Dict[str, List[Any]],
        source_files: List[str]
    ) -> UnifiedSchema:
        """
        Create UnifiedSchema model instance

        Args:
            schema_name: Name of the schema
            description: Schema description
            unified_columns: List of unified columns
            evolved_columns: Columns with type evolution
            source_files: Source file paths

        Returns:
            UnifiedSchema instance
        """
        # Resolve type conflicts for evolved columns
        resolved_types = self._resolve_type_conflicts(evolved_columns)

        # Build table definitions JSON
        table_defs = self._build_table_definitions(unified_columns, resolved_types)

        # Create unified schema model
        unified_schema = UnifiedSchema(
            id=uuid.uuid4(),
            schema_name=schema_name,
            description=description,
            version="1.0.0",
            table_definitions=table_defs,
            source_files_count=len(source_files),
            total_columns=len(unified_columns),
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        return unified_schema

    def _resolve_type_conflicts(
        self,
        evolved_columns: Dict[str, List[Any]]
    ) -> Dict[str, Any]:
        """
        Resolve type conflicts for columns with schema evolution

        Strategy: Use the most permissive type
        - Text > String
        - Float > Integer
        - String > Boolean

        Args:
            evolved_columns: Dictionary of columns with multiple types

        Returns:
            Dictionary mapping column names to resolved types
        """
        resolved_types = {}

        for column_name, types in evolved_columns.items():
            # Convert types to strings for comparison
            type_strs = [str(t) for t in types]

            # Resolution logic (most permissive wins)
            if any('TEXT' in t.upper() for t in type_strs):
                resolved_types[column_name] = Text
            elif any('FLOAT' in t.upper() or 'NUMERIC' in t.upper() for t in type_strs):
                resolved_types[column_name] = Float
            elif any('VARCHAR' in t.upper() or 'STRING' in t.upper() for t in type_strs):
                resolved_types[column_name] = String(255)
            elif any('INTEGER' in t.upper() for t in type_strs):
                resolved_types[column_name] = Integer
            elif any('DATETIME' in t.upper() for t in type_strs):
                resolved_types[column_name] = DateTime
            elif any('DATE' in t.upper() for t in type_strs):
                resolved_types[column_name] = Date
            elif any('BOOLEAN' in t.upper() for t in type_strs):
                resolved_types[column_name] = Boolean
            else:
                # Default to Text for unknown conflicts
                resolved_types[column_name] = Text

            self.logger.debug(
                f"Resolved type conflict for '{column_name}': "
                f"{type_strs} -> {resolved_types[column_name]}"
            )

        return resolved_types

    def _build_table_definitions(
        self,
        unified_columns: List[Dict[str, Any]],
        resolved_types: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Build table definitions from unified columns

        Args:
            unified_columns: List of unified column definitions
            resolved_types: Resolved types for evolved columns

        Returns:
            Dictionary with table definitions
        """
        # For OEWS data, we'll create a single main table with all columns
        # In a more complex scenario, this could split into multiple tables

        columns_def = []

        for col_info in unified_columns:
            column_name = col_info['name']

            # Use resolved type if available, otherwise use original type
            sql_type = resolved_types.get(column_name, col_info['sql_type'])

            # Convert SQLAlchemy type to string representation
            type_str = self._sqlalchemy_type_to_string(sql_type)

            # Ensure nullable is a native Python bool (not numpy.bool_)
            nullable_value = col_info.get('nullable', True)
            if hasattr(nullable_value, 'item'):  # numpy types have .item() method
                nullable_value = nullable_value.item()

            column_def = {
                'name': column_name,
                'type': type_str,
                'nullable': bool(nullable_value),
                'data_pattern': col_info.get('data_pattern', 'unknown'),
                'source_files': col_info.get('source_files', [])
            }

            columns_def.append(column_def)

        table_definitions = {
            'tables': [
                {
                    'name': 'oews_data',
                    'display_name': 'OEWS Employment and Wage Data',
                    'description': 'Main table containing all OEWS employment and wage statistics',
                    'columns': columns_def
                }
            ]
        }

        return table_definitions

    def _sqlalchemy_type_to_string(self, sql_type: Any) -> str:
        """
        Convert SQLAlchemy type to string representation

        Args:
            sql_type: SQLAlchemy type object

        Returns:
            String representation of type
        """
        if isinstance(sql_type, type):
            # It's a type class
            return sql_type.__name__
        else:
            # It's an instance
            type_str = str(sql_type)
            # Clean up the string
            if '(' in type_str:
                return type_str.split('(')[0].upper()
            return type_str.upper()

    def save_schema_to_database(
        self,
        unified_schema: UnifiedSchema,
        session: Optional[Session] = None
    ) -> UnifiedSchema:
        """
        Save unified schema to database

        Args:
            unified_schema: UnifiedSchema instance to save
            session: Database session (optional, will create if not provided)

        Returns:
            Saved UnifiedSchema instance with ID
        """
        if session is not None:
            # Use provided session
            try:
                session.add(unified_schema)
                session.commit()
                session.refresh(unified_schema)

                self.logger.info(
                    f"Saved unified schema '{unified_schema.schema_name}' to database "
                    f"with ID: {unified_schema.id}"
                )

                return unified_schema

            except Exception as e:
                session.rollback()
                self.logger.error(f"Failed to save schema to database: {str(e)}")
                raise
        else:
            # Create a new session using context manager
            with self.db_manager.get_session() as session:
                try:
                    session.add(unified_schema)
                    session.commit()
                    session.refresh(unified_schema)

                    self.logger.info(
                        f"Saved unified schema '{unified_schema.schema_name}' to database "
                        f"with ID: {unified_schema.id}"
                    )

                    return unified_schema

                except Exception as e:
                    session.rollback()
                    self.logger.error(f"Failed to save schema to database: {str(e)}")
                    raise

    def get_schema_by_name(self, schema_name: str) -> Optional[UnifiedSchema]:
        """
        Retrieve a schema by name

        Args:
            schema_name: Name of the schema

        Returns:
            UnifiedSchema instance or None if not found
        """
        with self.db_manager.get_session() as session:
            schema = session.query(UnifiedSchema).filter(
                UnifiedSchema.schema_name == schema_name
            ).first()

            if schema:
                self.logger.debug(f"Found schema '{schema_name}' with ID: {schema.id}")
            else:
                self.logger.debug(f"Schema '{schema_name}' not found")

            return schema

    def create_database_tables(
        self,
        unified_schema: UnifiedSchema,
        drop_existing: bool = False
    ) -> None:
        """
        Create actual database tables from unified schema definition

        Args:
            unified_schema: UnifiedSchema with table definitions
            drop_existing: Whether to drop existing tables

        Raises:
            ValueError: If schema is invalid or tables cannot be created
        """
        self.logger.info(f"Creating database tables for schema '{unified_schema.schema_name}'")

        try:
            # Extract table definitions
            table_defs = unified_schema.table_definitions

            if not table_defs:
                raise ValueError("No table definitions found in schema")

            # For each table definition, create the actual table
            tables = table_defs.get('tables', [])
            for table_def in tables:
                self._create_table_from_definition(table_def, drop_existing)

            self.logger.info(
                f"Successfully created {len(table_defs)} tables from schema"
            )

        except Exception as e:
            self.logger.error(f"Failed to create database tables: {str(e)}")
            raise ValueError(f"Cannot create database tables: {str(e)}")

    def _create_table_from_definition(
        self,
        table_def: Dict[str, Any],
        drop_existing: bool = False
    ) -> None:
        """
        Create a database table from a table definition

        Args:
            table_def: Table definition dictionary
            drop_existing: Whether to drop existing table

        Note: This is a placeholder implementation. In production, you would
        use SQLAlchemy's Table and MetaData to dynamically create tables.
        """
        table_name = table_def.get('name')
        columns = table_def.get('columns', [])

        self.logger.info(
            f"Creating table '{table_name}' with {len(columns)} columns "
            f"(drop_existing={drop_existing})"
        )

        # This would be implemented using SQLAlchemy's dynamic table creation
        # For now, it's a placeholder since we have models defined
        self.logger.warning(
            "Dynamic table creation is not fully implemented. "
            "Using predefined models from src/models/"
        )
