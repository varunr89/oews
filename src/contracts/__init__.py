"""
Service Contracts Package

This package contains abstract base classes that define the contracts
for all services in the OEWS migration application.
"""

from .file_discovery_service import (
    FileDiscoveryService,
    ExcelFileInfo,
    DiscoveryOptions,
    DiscoveryResult
)

from .migration_engine_service import (
    MigrationEngineService,
    MigrationOptions,
    MigrationProgress,
    MigrationResult,
    MigrationStatus,
    ConflictResolution,
    RollbackInfo
)

from .validation_service import (
    ValidationService,
    ValidationLevel,
    ValidationStatus,
    ValidationRule,
    ValidationError,
    ValidationOptions,
    ValidationReport,
    SchemaValidationResult
)

__all__ = [
    # File Discovery
    "FileDiscoveryService",
    "ExcelFileInfo",
    "DiscoveryOptions",
    "DiscoveryResult",

    # Migration Engine
    "MigrationEngineService",
    "MigrationOptions",
    "MigrationProgress",
    "MigrationResult",
    "MigrationStatus",
    "ConflictResolution",
    "RollbackInfo",

    # Validation
    "ValidationService",
    "ValidationLevel",
    "ValidationStatus",
    "ValidationRule",
    "ValidationError",
    "ValidationOptions",
    "ValidationReport",
    "SchemaValidationResult",
]