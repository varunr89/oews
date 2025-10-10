"""
ColumnMapping Model

Represents the mapping between source Excel columns and target database columns.
"""

from sqlalchemy import Column, String, Integer, Boolean, Text, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship, validates
from sqlalchemy.dialects.postgresql import UUID

from . import Base


class ColumnMapping(Base):
    """Mapping between source Excel columns and target database columns"""

    # Relationships
    column_definition_id = Column(
        UUID(as_uuid=True),
        ForeignKey('column_definition.id', ondelete='CASCADE'),
        nullable=False,
        comment="Foreign key to source ColumnDefinition"
    )

    table_definition_id = Column(
        UUID(as_uuid=True),
        ForeignKey('table_definition.id', ondelete='CASCADE'),
        nullable=False,
        comment="Foreign key to target TableDefinition"
    )

    # Mapping details
    target_column_name = Column(
        String(255),
        nullable=False,
        comment="Target database column name"
    )

    transformation_rule = Column(
        Text,
        nullable=True,
        comment="Data transformation rule (SQL expression or function)"
    )

    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether this mapping is currently active"
    )

    # Relationships
    column_definition = relationship(
        "ColumnDefinition",
        back_populates="column_mappings"
    )

    table_definition = relationship(
        "TableDefinition",
        back_populates="column_mappings"
    )

    @validates('target_column_name')
    def validate_target_column_name(self, key: str, column_name: str) -> str:
        """Validate target column name format"""
        if not column_name or not column_name.strip():
            raise ValueError("target_column_name cannot be empty")
        return column_name.strip()

    def __repr__(self) -> str:
        return f"<ColumnMapping(target_column='{self.target_column_name}')>"