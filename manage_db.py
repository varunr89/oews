#!/usr/bin/env python3
"""
Database management CLI tool for OEWS application.
"""

import click
import sys
import os

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from database import schema_manager, data_loader, db_manager

@click.group()
def cli():
    """OEWS Database Management Tool"""
    pass

@cli.command()
def init():
    """Initialize the database schema."""
    click.echo("Initializing database schema...")

    try:
        # Check if database is accessible
        if not db_manager.is_connected():
            click.echo("Database connection failed!")
            return

        # Create schema
        schema_manager.create_schema()
        click.echo("Database schema initialized successfully!")

        # Show schema info
        info = schema_manager.get_schema_info()
        click.echo(f"Created {len(info['tables'])} tables")

    except Exception as e:
        click.echo(f"Failed to initialize schema: {e}")

@cli.command()
def reset():
    """Reset the database (drop and recreate all tables)."""
    if click.confirm("WARNING: This will delete all data. Are you sure?"):
        try:
            schema_manager.drop_schema()
            schema_manager.create_schema()
            click.echo("Database reset successfully!")
        except Exception as e:
            click.echo(f"Failed to reset database: {e}")

@cli.command()
def status():
    """Show database status and statistics."""
    try:
        # Database connection info
        db_info = db_manager.get_database_info()
        click.echo("Database Status:")
        click.echo(f"  Connected: {'Yes' if db_info['connected'] else 'No'}")
        click.echo(f"  Database Type: {'SQLite' if db_info['is_sqlite'] else 'PostgreSQL'}")
        click.echo(f"  Environment: {'Production' if db_info['is_production'] else 'Development'}")

        # Schema info
        if db_info['connected']:
            schema_info = schema_manager.get_schema_info()
            click.echo(f"\nSchema Info:")
            click.echo(f"  Schema Exists: {'Yes' if schema_info['schema_exists'] else 'No'}")

            if schema_info['schema_exists']:
                click.echo(f"  Tables: {len(schema_info['tables'])}")
                for table, count in schema_info['total_records'].items():
                    click.echo(f"    {table}: {count:,} records")

    except Exception as e:
        click.echo(f"Error getting status: {e}")

@cli.command()
def load_data():
    """Load all Excel files into the database."""
    click.echo("Loading OEWS data from Excel files...")

    try:
        # Check if schema exists
        if not schema_manager.check_schema_exists():
            click.echo("Database schema not found. Run 'python manage_db.py init' first.")
            return

        # Load data
        stats = data_loader.load_all_files()

        click.echo("Data loading completed!")
        click.echo(f"Loading Statistics:")
        click.echo(f"  Files processed: {stats['files_processed']}")
        click.echo(f"  Total records: {stats['total_records']:,}")
        click.echo(f"  Skipped records: {stats['skipped_records']:,}")
        click.echo(f"  Dimension records:")
        for dim, count in stats['dimension_records'].items():
            click.echo(f"    {dim}: {count:,}")

    except Exception as e:
        click.echo(f"Failed to load data: {e}")

@cli.command()
@click.argument('file_path')
def load_file(file_path):
    """Load a specific Excel file into the database."""
    click.echo(f"Loading file: {file_path}")

    try:
        if not os.path.exists(file_path):
            click.echo(f"File not found: {file_path}")
            return

        data_loader.load_file(file_path)
        click.echo("File loaded successfully!")

    except Exception as e:
        click.echo(f"Failed to load file: {e}")

@cli.command()
def test_connection():
    """Test database connection."""
    try:
        if db_manager.is_connected():
            click.echo("Database connection successful!")
        else:
            click.echo("Database connection failed!")
    except Exception as e:
        click.echo(f"Connection test error: {e}")

if __name__ == "__main__":
    cli()