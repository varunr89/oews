"""Convenience CLI to run the OEWS ingestion pipeline end-to-end."""

from __future__ import annotations

from pathlib import Path

import click

from . import analyze_columns
from . import migrate_csv_to_db
from . import standardize_csv_columns


@click.group()
def cli() -> None:
    """Run individual pipeline stages or the full migration."""


@cli.command()
@click.option("--root", type=click.Path(path_type=Path), default=analyze_columns.DEFAULT_DATA_ROOT)
@click.option("--output-dir", type=click.Path(path_type=Path), default=analyze_columns.DEFAULT_OUTPUT_DIR)
@click.option("--sample-rows", type=int, default=analyze_columns.DEFAULT_SAMPLE_ROWS)
def analyze(root: Path, output_dir: Path, sample_rows: int) -> None:
    """Inspect headers across the raw CSV corpus."""
    analyze_columns.run(root, sample_rows, output_dir)


@cli.command()
@click.option("--root", type=click.Path(path_type=Path), default=analyze_columns.DEFAULT_DATA_ROOT)
@click.option("--output-dir", type=click.Path(path_type=Path), default=standardize_csv_columns.DEFAULT_OUTPUT_DIR)
@click.option("--workers", type=int, default=standardize_csv_columns.DEFAULT_WORKERS)
def standardize(root: Path, output_dir: Path, workers: int) -> None:
    """Standardize CSVs and emit parquet files."""
    standardize_csv_columns.run(root, output_dir, workers)


@cli.command()
@click.option("--parquet-root", type=click.Path(path_type=Path), default=migrate_csv_to_db.DEFAULT_OUTPUT_DIR)
@click.option("--output-dir", type=click.Path(path_type=Path), default=migrate_csv_to_db.DEFAULT_OUTPUT_DIR)
@click.option("--workers", type=int, default=migrate_csv_to_db.DEFAULT_WORKERS)
@click.option("--batch-size", type=int, default=migrate_csv_to_db.DEFAULT_BATCH_SIZE)
def migrate(parquet_root: Path, output_dir: Path, workers: int, batch_size: int) -> None:
    """Load parquet data into SQLite."""
    migrate_csv_to_db.run(parquet_root, output_dir, workers, batch_size)


@cli.command(name="all")
@click.option("--sample-rows", type=int, default=analyze_columns.DEFAULT_SAMPLE_ROWS)
@click.option("--standardize-workers", type=int, default=standardize_csv_columns.DEFAULT_WORKERS)
@click.option("--migrate-workers", type=int, default=migrate_csv_to_db.DEFAULT_WORKERS)
@click.option("--batch-size", type=int, default=migrate_csv_to_db.DEFAULT_BATCH_SIZE)
def run_all(sample_rows: int, standardize_workers: int, migrate_workers: int, batch_size: int) -> None:
    """Execute analyze → standardize → migrate in sequence."""
    root = analyze_columns.DEFAULT_DATA_ROOT
    output_dir = analyze_columns.DEFAULT_OUTPUT_DIR

    click.echo("1) Analyzing raw CSV headers…")
    analyze_columns.run(root, sample_rows, output_dir)

    click.echo("2) Standardizing CSV data into parquet…")
    standardize_csv_columns.run(root, output_dir, standardize_workers)

    click.echo("3) Loading parquet data into SQLite…")
    migrate_csv_to_db.run(output_dir, output_dir, migrate_workers, batch_size)


if __name__ == "__main__":
    cli()
