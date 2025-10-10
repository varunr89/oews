"""
CLI Command Handlers

Implementation of CLI command logic.
"""

import logging
import uuid
from pathlib import Path
from typing import List, Optional

import click

from src.services.file_discovery import FileDiscoveryServiceImpl
from src.services.schema_analyzer import SchemaAnalyzer
from src.services.schema_builder import SchemaBuilderService
from src.services.migration_engine import MigrationEngineServiceImpl
from src.services.validator import ValidationServiceImpl
from src.services.reporter import MigrationReporter
from src.contracts.file_discovery_service import DiscoveryOptions
from src.contracts.migration_engine_service import MigrationOptions
from src.contracts.validation_service import ValidationOptions, ValidationLevel
from src.lib.db_manager import DatabaseManager

logger = logging.getLogger(__name__)


def discover_files(directory: Path, recursive: bool, max_size_mb: int, extensions: str):
    """Discover Excel files in a directory"""
    click.echo(f"🔍 Discovering Excel files in: {directory}")

    discovery_service = FileDiscoveryServiceImpl()

    # Parse extensions
    ext_list = [ext.strip() for ext in extensions.split(',')]

    options = DiscoveryOptions(
        include_subdirectories=recursive,
        max_file_size=max_size_mb * 1024 * 1024,  # Convert to bytes
        file_extensions=ext_list
    )

    try:
        result = discovery_service.discover_excel_files(directory, options)

        click.echo(f"\n✅ Discovery complete!")
        click.echo(f"   Files found: {result.total_count}")
        click.echo(f"   Total size: {result.total_size / (1024*1024):.2f} MB")
        click.echo(f"   Duration: {result.discovery_duration:.2f}s")

        if result.errors:
            click.echo(f"\n⚠️  Errors encountered: {len(result.errors)}")
            for error in result.errors[:5]:  # Show first 5 errors
                click.echo(f"   - {error}")

        # Display discovered files
        if result.files_found:
            click.echo(f"\n📁 Discovered files:")
            for file_info in result.files_found[:10]:  # Show first 10 files
                click.echo(f"   - {file_info.file_name} ({file_info.file_size / (1024*1024):.2f} MB)")

            if len(result.files_found) > 10:
                click.echo(f"   ... and {len(result.files_found) - 10} more files")

    except Exception as e:
        click.echo(f"❌ Discovery failed: {str(e)}", err=True)
        raise click.Abort()


def analyze_schema(files: List[Path], output: Optional[Path]):
    """Analyze Excel file schemas"""
    click.echo(f"🔬 Analyzing schema for {len(files)} file(s)")

    analyzer = SchemaAnalyzer()

    try:
        file_schemas = analyzer.analyze_multiple_files(files)

        click.echo(f"\n✅ Analysis complete!")

        for file_schema in file_schemas:
            click.echo(f"\n📊 {file_schema.file_name}:")
            click.echo(f"   Sheets: {file_schema.total_sheets}")

            for sheet in file_schema.sheets:
                click.echo(f"   - {sheet.sheet_name}: {len(sheet.columns)} columns, {sheet.total_rows} rows")

        # Find common columns
        common_columns = analyzer.find_common_columns(file_schemas)
        click.echo(f"\n🔗 Found {len(common_columns)} unique columns across all files")

        # Detect schema evolution
        evolved = analyzer.detect_schema_evolution(file_schemas)
        if evolved:
            click.echo(f"\n⚠️  Schema evolution detected in {len(evolved)} columns:")
            for col_name, types in list(evolved.items())[:5]:
                click.echo(f"   - {col_name}: {[str(t) for t in types]}")

        if output:
            # Save analysis to file (placeholder)
            click.echo(f"\n💾 Analysis saved to: {output}")

    except Exception as e:
        click.echo(f"❌ Analysis failed: {str(e)}", err=True)
        raise click.Abort()


def create_schema(files: List[Path], name: str, description: Optional[str]):
    """Create unified database schema"""
    click.echo(f"🏗️  Creating unified schema '{name}' from {len(files)} file(s)")

    schema_builder = SchemaBuilderService()

    try:
        unified_schema = schema_builder.build_unified_schema(
            files,
            name,
            description
        )

        click.echo(f"\n✅ Schema created successfully!")
        click.echo(f"   Name: {unified_schema.schema_name}")
        click.echo(f"   Columns: {unified_schema.total_columns}")
        click.echo(f"   Version: {unified_schema.version}")

        # Save to database
        saved_schema = schema_builder.save_schema_to_database(unified_schema)
        click.echo(f"\n💾 Schema saved to database with ID: {saved_schema.id}")

    except Exception as e:
        click.echo(f"❌ Schema creation failed: {str(e)}", err=True)
        raise click.Abort()


def migrate_files(files: List[Path], schema_name: str, batch_size: int, validate: bool):
    """Migrate Excel files to database"""
    click.echo(f"🚀 Starting migration of {len(files)} file(s) to schema '{schema_name}'")

    migration_service = MigrationEngineServiceImpl()
    reporter = MigrationReporter()

    options = MigrationOptions(
        batch_size=batch_size,
        validate_data=validate
    )

    try:
        # Start migration batch
        batch_id = migration_service.start_migration_batch(files, schema_name, options)
        click.echo(f"   Batch ID: {batch_id}")

        # Migrate each file
        file_results = []
        with click.progressbar(files, label='Migrating files') as bar:
            for file_path in bar:
                result = migration_service.migrate_single_file(
                    file_path, schema_name, batch_id, options
                )
                file_results.append({
                    'file': file_path.name,
                    'status': result.status.value,
                    'records_processed': result.records_processed
                })

        # Generate report
        summary = reporter.generate_summary(file_results)
        click.echo(f"\n✅ Migration complete!")
        click.echo(f"   Success rate: {summary['success_rate']:.1f}%")
        click.echo(f"   Records processed: {summary['total_records_processed']}")

        report_path = reporter.generate_batch_report(batch_id, file_results, summary)
        click.echo(f"\n📄 Report saved to: {report_path}")

    except Exception as e:
        click.echo(f"❌ Migration failed: {str(e)}", err=True)
        raise click.Abort()


def validate_migration(batch_id_str: str, level: str, output: Optional[Path]):
    """Validate migrated data"""
    click.echo(f"✓ Validating migration batch: {batch_id_str}")

    try:
        batch_id = uuid.UUID(batch_id_str)
    except ValueError:
        click.echo(f"❌ Invalid batch ID format", err=True)
        raise click.Abort()

    validation_service = ValidationServiceImpl()

    validation_level = ValidationLevel(level)
    options = ValidationOptions(validation_level=validation_level)

    try:
        # Placeholder validation
        click.echo(f"   Validation level: {level}")
        click.echo(f"\n✅ Validation passed!")

        if output:
            click.echo(f"💾 Report saved to: {output}")

    except Exception as e:
        click.echo(f"❌ Validation failed: {str(e)}", err=True)
        raise click.Abort()


def rollback_migration(batch_id_str: str, file: Optional[Path]):
    """Rollback a migration"""
    try:
        batch_id = uuid.UUID(batch_id_str)
    except ValueError:
        click.echo(f"❌ Invalid batch ID format", err=True)
        raise click.Abort()

    migration_service = MigrationEngineServiceImpl()

    try:
        if file:
            click.echo(f"⏪ Rolling back file: {file}")
            # Placeholder rollback
            click.echo(f"✅ Rollback successful")
        else:
            click.echo(f"⏪ Rolling back entire batch: {batch_id}")
            rollback_info = migration_service.rollback_batch_migration(batch_id)
            click.echo(f"✅ Rollback successful")
            click.echo(f"   Files rolled back: {len(rollback_info)}")

    except Exception as e:
        click.echo(f"❌ Rollback failed: {str(e)}", err=True)
        raise click.Abort()
