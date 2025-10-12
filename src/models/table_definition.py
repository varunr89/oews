"""
TableDefinition Model

Represents individual table definitions within a unified schema.
"""

from typing import Any, Dict, List, Optional

from sqlalchemy import Column, String, Integer, Boolean, Text, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship, validates
from sqlalchemy.dialects.postgresql import UUID, JSON

from . import Base


class TableDefinition(Base):
    """Individual table definition within a unified schema"""

    # Parent relationship
    unified_schema_id = Column(
        UUID(as_uuid=True),
        ForeignKey('unified_schema.id', ondelete='CASCADE'),
        nullable=False,
        comment="Foreign key to UnifiedSchema"
    )

    # Table identification
    table_name = Column(
        String(100),
        nullable=False,
        comment="Name of the database table"
    )

    display_name = Column(
        String(255),
        nullable=True,
        comment="Human-readable table name"
    )

    description = Column(
        Text,
        nullable=True,
        comment="Description of table purpose"
    )

    # Table structure
    column_definitions = Column(
        JSON,
        nullable=False,
        comment="Column definitions as JSON"
    )

    primary_key_columns = Column(
        JSON,
        nullable=True,
        comment="List of primary key column names"
    )

    indexes = Column(
        JSON,
        nullable=True,
        comment="Index definitions as JSON"
    )

    # Relationships
    unified_schema = relationship(
        "UnifiedSchema",
        back_populates="table_definitions_rel"
    )

    column_mappings = relationship(
        "ColumnMapping",
        back_populates="table_definition",
        cascade="all, delete-orphan",
        lazy="select"
    )

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "LENGTH(table_name) > 0",
            name="valid_table_name"
        ),
    )

    @validates('table_name')
    def validate_table_name(self, key: str, table_name: str) -> str:
        """Validate table name format"""
        if not table_name or not table_name.strip():
            raise ValueError("table_name cannot be empty")

        import re
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', table_name):
            raise ValueError("table_name must be a valid database identifier")

        return table_name.strip()

    def __repr__(self) -> str:
        return f"<TableDefinition(table_name='{self.table_name}')>"