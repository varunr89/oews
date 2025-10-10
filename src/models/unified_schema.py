"""
UnifiedSchema Model

Represents a unified database schema that accommodates multiple Excel file structures.
Maps to schema consolidation and database design requirements.
"""

import json
from typing import Any, Dict, List, Optional

from sqlalchemy import Column, String, Integer, Boolean, Text, CheckConstraint
from sqlalchemy.orm import relationship, validates
from sqlalchemy.dialects.postgresql import JSON

from . import Base


class UnifiedSchema(Base):
    """
    Represents a unified database schema that accommodates multiple Excel file structures

    This model captures the consolidated schema design that can handle
    data from multiple OEWS Excel files with potentially different structures.
    """

    # Schema identification
    schema_name = Column(
        String(100),
        nullable=False,
        unique=True,
        comment="Name of the unified schema"
    )

    description = Column(
        Text,
        nullable=True,
        comment="Description of the schema purpose and scope"
    )

    version = Column(
        String(20),
        nullable=False,
        default="1.0.0",
        comment="Schema version for change tracking"
    )

    # Schema structure
    table_definitions = Column(
        JSON,
        nullable=False,
        comment="Complete table and column definitions as JSON"
    )

    # Schema metadata
    source_files_count = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of Excel files this schema accommodates"
    )

    total_columns = Column(
        Integer,
        nullable=True,
        comment="Total number of columns across all tables"
    )

    # OEWS-specific metadata
    oews_years_covered = Column(
        JSON,
        nullable=True,
        comment="Array of OEWS data years this schema covers"
    )

    is_oews_compliant = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether schema follows OEWS standard structure"
    )

    # Schema status
    status = Column(
        String(20),
        nullable=False,
        default="draft",
        comment="Schema status: draft, validated, deployed, deprecated"
    )

    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether this schema is currently active"
    )

    # Validation and quality
    validation_errors = Column(
        JSON,
        nullable=True,
        comment="Schema validation errors and warnings"
    )

    compatibility_score = Column(
        Integer,
        nullable=True,
        comment="Schema compatibility score (0-100)"
    )

    # Relationships
    table_definitions_rel = relationship(
        "TableDefinition",
        back_populates="unified_schema",
        cascade="all, delete-orphan",
        lazy="select"
    )

    migration_batches = relationship(
        "MigrationBatch",
        back_populates="unified_schema",
        cascade="all, delete-orphan",
        lazy="select"
    )

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "source_files_count >= 0",
            name="valid_source_files_count"
        ),
        CheckConstraint(
            "total_columns IS NULL OR total_columns > 0",
            name="valid_total_columns"
        ),
        CheckConstraint(
            "compatibility_score IS NULL OR (compatibility_score >= 0 AND compatibility_score <= 100)",
            name="valid_compatibility_score"
        ),
        CheckConstraint(
            "status IN ('draft', 'validated', 'deployed', 'deprecated')",
            name="valid_status"
        )
    )

    @validates('schema_name')
    def validate_schema_name(self, key: str, schema_name: str) -> str:
        """Validate schema name format"""
        if not schema_name or not schema_name.strip():
            raise ValueError("schema_name cannot be empty")

        # Check for valid database identifier format
        import re
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', schema_name):
            raise ValueError("schema_name must be a valid database identifier")

        return schema_name.strip()

    @validates('table_definitions')
    def validate_table_definitions(self, key: str, definitions: Any) -> Dict:
        """Validate table definitions structure"""
        if isinstance(definitions, str):
            try:
                definitions = json.loads(definitions)
            except json.JSONDecodeError:
                raise ValueError("table_definitions must be valid JSON")

        if not isinstance(definitions, dict):
            raise ValueError("table_definitions must be a JSON object")

        # Validate basic structure
        if 'tables' not in definitions:
            raise ValueError("table_definitions must contain 'tables' key")

        tables = definitions['tables']
        if not isinstance(tables, list):
            raise ValueError("'tables' must be an array")

        # Validate each table definition
        for table in tables:
            if not isinstance(table, dict):
                raise ValueError("Each table definition must be an object")

            required_fields = ['name', 'columns']
            for field in required_fields:
                if field not in table:
                    raise ValueError(f"Table definition missing required field: {field}")

        return definitions

    def get_table_definitions_dict(self) -> Dict[str, Any]:
        """Get table definitions as dictionary"""
        if isinstance(self.table_definitions, str):
            try:
                return json.loads(self.table_definitions)
            except json.JSONDecodeError:
                return {}

        return self.table_definitions or {}

    def get_table_names(self) -> List[str]:
        """Get list of table names in the schema"""
        definitions = self.get_table_definitions_dict()
        tables = definitions.get('tables', [])
        return [table.get('name', '') for table in tables if isinstance(table, dict)]

    def get_table_definition(self, table_name: str) -> Optional[Dict[str, Any]]:
        """Get definition for a specific table"""
        definitions = self.get_table_definitions_dict()
        tables = definitions.get('tables', [])

        for table in tables:
            if isinstance(table, dict) and table.get('name') == table_name:
                return table

        return None

    def add_table_definition(self, table_def: Dict[str, Any]) -> None:
        """Add a new table definition to the schema"""
        definitions = self.get_table_definitions_dict()

        if 'tables' not in definitions:
            definitions['tables'] = []

        # Check if table already exists
        existing_names = {table.get('name') for table in definitions['tables']}
        if table_def.get('name') in existing_names:
            raise ValueError(f"Table '{table_def.get('name')}' already exists in schema")

        definitions['tables'].append(table_def)
        self.table_definitions = definitions

        # Update column count
        self._update_column_count()

    def remove_table_definition(self, table_name: str) -> bool:
        """Remove a table definition from the schema"""
        definitions = self.get_table_definitions_dict()
        tables = definitions.get('tables', [])

        original_count = len(tables)
        definitions['tables'] = [
            table for table in tables
            if table.get('name') != table_name
        ]

        if len(definitions['tables']) < original_count:
            self.table_definitions = definitions
            self._update_column_count()
            return True

        return False

    def _update_column_count(self) -> None:
        """Update total column count based on table definitions"""
        definitions = self.get_table_definitions_dict()
        tables = definitions.get('tables', [])

        total = 0
        for table in tables:
            if isinstance(table, dict):
                columns = table.get('columns', [])
                if isinstance(columns, list):
                    total += len(columns)

        self.total_columns = total

    def validate_oews_compliance(self) -> List[str]:
        """
        Validate schema compliance with OEWS standards

        Returns:
            List of compliance issues (empty if compliant)
        """
        issues = []
        definitions = self.get_table_definitions_dict()
        tables = definitions.get('tables', [])

        # Check for required OEWS tables
        table_names = {table.get('name', '').lower() for table in tables}

        if 'oews_data' not in table_names and 'employment_data' not in table_names:
            issues.append("Missing main OEWS data table")

        # Check for standard OEWS columns in main data table
        main_table = None
        for table in tables:
            table_name = table.get('name', '').lower()
            if 'oews' in table_name or 'employment' in table_name:
                main_table = table
                break

        if main_table:
            columns = main_table.get('columns', [])
            column_names = {col.get('name', '').upper() for col in columns if isinstance(col, dict)}

            required_oews_columns = {
                'AREA', 'AREA_TITLE', 'OCC_CODE', 'OCC_TITLE',
                'TOT_EMP', 'A_MEAN', 'H_MEAN'
            }

            missing_columns = required_oews_columns - column_names
            if missing_columns:
                issues.append(f"Missing required OEWS columns: {sorted(missing_columns)}")

        return issues

    def calculate_compatibility_score(self, source_schemas: List[Dict]) -> int:
        """
        Calculate compatibility score with source schemas

        Args:
            source_schemas: List of source schema definitions

        Returns:
            Compatibility score from 0-100
        """
        if not source_schemas:
            return 100

        total_score = 0
        schema_def = self.get_table_definitions_dict()

        for source_schema in source_schemas:
            score = self._calculate_single_compatibility(schema_def, source_schema)
            total_score += score

        return int(total_score / len(source_schemas))

    def _calculate_single_compatibility(self, unified_schema: Dict, source_schema: Dict) -> float:
        """Calculate compatibility score with a single source schema"""
        if not source_schema.get('columns'):
            return 100.0

        source_columns = set(col.get('name', '') for col in source_schema.get('columns', []))
        unified_tables = unified_schema.get('tables', [])

        # Find best matching table
        best_coverage = 0.0
        for table in unified_tables:
            table_columns = set(col.get('name', '') for col in table.get('columns', []))
            coverage = len(source_columns & table_columns) / len(source_columns) if source_columns else 1.0
            best_coverage = max(best_coverage, coverage)

        return best_coverage * 100

    def get_oews_years_list(self) -> List[int]:
        """Get list of OEWS years covered by this schema"""
        if not self.oews_years_covered:
            return []

        if isinstance(self.oews_years_covered, str):
            try:
                years = json.loads(self.oews_years_covered)
            except json.JSONDecodeError:
                return []
        else:
            years = self.oews_years_covered

        if isinstance(years, list):
            return [year for year in years if isinstance(year, int)]

        return []

    def add_oews_year(self, year: int) -> None:
        """Add an OEWS year to the coverage list"""
        years = self.get_oews_years_list()
        if year not in years:
            years.append(year)
            years.sort()
            self.oews_years_covered = years

    def generate_sql_ddl(self, database_type: str = "postgresql") -> str:
        """
        Generate SQL DDL statements for the schema

        Args:
            database_type: Target database type (postgresql, sqlite, mysql)

        Returns:
            SQL DDL statements
        """
        definitions = self.get_table_definitions_dict()
        tables = definitions.get('tables', [])

        ddl_statements = []
        ddl_statements.append(f"-- Unified Schema: {self.schema_name}")
        ddl_statements.append(f"-- Version: {self.version}")
        ddl_statements.append(f"-- Generated: {self.created_at}")
        ddl_statements.append("")

        for table in tables:
            table_ddl = self._generate_table_ddl(table, database_type)
            if table_ddl:
                ddl_statements.append(table_ddl)
                ddl_statements.append("")

        return "\n".join(ddl_statements)

    def _generate_table_ddl(self, table_def: Dict, database_type: str) -> str:
        """Generate DDL for a single table"""
        table_name = table_def.get('name', '')
        columns = table_def.get('columns', [])

        if not table_name or not columns:
            return ""

        ddl_lines = [f"CREATE TABLE {table_name} ("]

        column_definitions = []
        for col in columns:
            if isinstance(col, dict):
                col_ddl = self._generate_column_ddl(col, database_type)
                if col_ddl:
                    column_definitions.append(f"  {col_ddl}")

        ddl_lines.extend([",\n".join(column_definitions)])
        ddl_lines.append(");")

        return "\n".join(ddl_lines)

    def _generate_column_ddl(self, col_def: Dict, database_type: str) -> str:
        """Generate DDL for a single column"""
        name = col_def.get('name', '')
        data_type = col_def.get('type', 'VARCHAR(255)')
        nullable = col_def.get('nullable', True)
        default = col_def.get('default')

        if not name:
            return ""

        parts = [name, data_type]

        if not nullable:
            parts.append("NOT NULL")

        if default is not None:
            if isinstance(default, str):
                parts.append(f"DEFAULT '{default}'")
            else:
                parts.append(f"DEFAULT {default}")

        return " ".join(parts)

    def __repr__(self) -> str:
        """String representation of the UnifiedSchema"""
        return f"<UnifiedSchema(schema_name='{self.schema_name}', tables={len(self.get_table_names())}, status='{self.status}')>"