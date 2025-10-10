"""
OEWS Migration CLI - Main Entry Point

Command-line interface for OEWS Excel to SQL database migration.
"""

import click
import logging
from pathlib import Path

from src.cli.config import config
from src.cli.commands import (
    discover_files,
    analyze_schema,
    create_schema,
    migrate_files,
    validate_migration,
    rollback_migration
)

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.log_level),
    format=config.log_format
)

logger = logging.getLogger(__name__)


@click.group()
@click.version_option(version='1.0.0')
@click.option('--debug', is_flag=True, help='Enable debug mode')
def cli(debug):
    """OEWS Excel to SQL Database Migration Tool"""
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
        config.set('DEBUG', 'true')
        logger.debug("Debug mode enabled")


@cli.command()
@click.argument('directory', type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option('--recursive/--no-recursive', default=True, help='Include subdirectories')
@click.option('--max-size', type=int, default=100, help='Max file size in MB')
@click.option('--extensions', default='.xlsx,.xls', help='File extensions to search for')
def discover(directory, recursive, max_size, extensions):
    """Discover Excel files in a directory"""
    discover_files(directory, recursive, max_size, extensions)


@cli.command()
@click.argument('files', nargs=-1, type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option('--output', type=click.Path(path_type=Path), help='Output file for analysis results')
def analyze(files, output):
    """Analyze Excel file schemas"""
    analyze_schema(list(files), output)


@cli.command('create-schema')
@click.argument('files', nargs=-1, type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option('--name', required=True, help='Schema name')
@click.option('--description', help='Schema description')
def create_schema_cmd(files, name, description):
    """Create unified database schema from Excel files"""
    create_schema(list(files), name, description)


@cli.command()
@click.argument('files', nargs=-1, type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option('--schema', required=True, help='Target schema name')
@click.option('--batch-size', type=int, default=10000, help='Batch size for processing')
@click.option('--validate/--no-validate', default=True, help='Run validation after migration')
def migrate(files, schema, batch_size, validate):
    """Migrate Excel files to database"""
    migrate_files(list(files), schema, batch_size, validate)


@cli.command()
@click.argument('batch-id', type=str)
@click.option('--level', type=click.Choice(['basic', 'comprehensive', 'exhaustive']), default='comprehensive')
@click.option('--output', type=click.Path(path_type=Path), help='Output file for validation report')
def validate(batch_id, level, output):
    """Validate migrated data"""
    validate_migration(batch_id, level, output)


@cli.command()
@click.argument('batch-id', type=str)
@click.option('--file', type=click.Path(path_type=Path), help='Rollback specific file only')
@click.confirmation_option(prompt='Are you sure you want to rollback this migration?')
def rollback(batch_id, file):
    """Rollback a migration"""
    rollback_migration(batch_id, file)


if __name__ == '__main__':
    cli()
