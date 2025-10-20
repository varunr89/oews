"""Unified command-line interface for the OEWS data pipeline."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import click

from src.cli.scripts import (
    analyze_columns,
    download_bls_data,
    excel_to_csv,
    migrate_csv_to_db,
    standardize_csv_columns,
)

LOG_LEVELS = [logging.WARNING, logging.INFO, logging.DEBUG]


def _configure_logging(verbose: int, quiet: bool) -> None:
    level_index = min(verbose, len(LOG_LEVELS) - 1)
    level = LOG_LEVELS[level_index]
    if quiet:
        level = logging.ERROR
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


@click.group()
@click.option("--verbose", "-v", count=True, help="Increase verbosity (use up to -vv)")
@click.option("--quiet", "-q", is_flag=True, help="Only show errors")
@click.pass_context
def cli(ctx: click.Context, verbose: int, quiet: bool) -> None:
    """Run individual pipeline stages or the full migration."""
    _configure_logging(verbose, quiet)
    ctx.obj = {"verbose": verbose, "quiet": quiet}


@cli.command()
@click.option("--root", type=click.Path(path_type=Path), default=analyze_columns.DEFAULT_DATA_ROOT)
@click.option("--output-dir", type=click.Path(path_type=Path), default=analyze_columns.DEFAULT_OUTPUT_DIR)
@click.option("--sample-rows", type=int, default=analyze_columns.DEFAULT_SAMPLE_ROWS)
def analyze(root: Path, output_dir: Path, sample_rows: int) -> None:
    """Inspect headers across the raw CSV corpus."""
    analyze_columns.run(root, sample_rows, output_dir)


@cli.command()
@click.option("--root", type=click.Path(path_type=Path), default=standardize_csv_columns.DEFAULT_DATA_ROOT)
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


@cli.command(name="pipeline")
@click.option("--sample-rows", type=int, default=analyze_columns.DEFAULT_SAMPLE_ROWS)
@click.option("--standardize-workers", type=int, default=standardize_csv_columns.DEFAULT_WORKERS)
@click.option("--migrate-workers", type=int, default=migrate_csv_to_db.DEFAULT_WORKERS)
@click.option("--batch-size", type=int, default=migrate_csv_to_db.DEFAULT_BATCH_SIZE)
@click.option("--root", type=click.Path(path_type=Path), default=analyze_columns.DEFAULT_DATA_ROOT)
@click.option("--output-dir", type=click.Path(path_type=Path), default=analyze_columns.DEFAULT_OUTPUT_DIR)
def pipeline(
    sample_rows: int,
    standardize_workers: int,
    migrate_workers: int,
    batch_size: int,
    root: Path,
    output_dir: Path,
) -> None:
    """Execute analyze → standardize → migrate in sequence."""
    logging.getLogger(__name__).info("1) Analyzing raw CSV headers")
    analyze_columns.run(root, sample_rows, output_dir)

    logging.getLogger(__name__).info("2) Standardizing CSV data into parquet")
    standardize_csv_columns.run(root, output_dir, standardize_workers)

    logging.getLogger(__name__).info("3) Loading parquet data into SQLite")
    migrate_csv_to_db.run(output_dir, output_dir, migrate_workers, batch_size)


@cli.command(name="download-data")
@click.option("--start-year", type=int, default=2011)
@click.option("--end-year", type=int, default=None)
@click.option("--data-dir", type=click.Path(path_type=Path), default=Path("data/raw"))
@click.option("--force", is_flag=True, help="Force re-download even if files exist")
def download_data(start_year: int, end_year: Optional[int], data_dir: Path, force: bool) -> None:
    """Download BLS OEWS data archives."""
    resolved_end_year = end_year or datetime.now().year
    if start_year > resolved_end_year:
        raise click.BadParameter("start-year must be <= end-year")
    download_bls_data.download_bls_data(start_year, resolved_end_year, data_dir, force)


@cli.command(name="excel-to-csv")
@click.option("--input-dir", type=click.Path(path_type=Path), default=Path("data/raw"))
@click.option("--output-dir", type=click.Path(path_type=Path), default=Path("data/csv"))
@click.option("--force", is_flag=True, help="Force re-conversion of already converted files")
@click.option("--keep-originals", is_flag=True, help="Keep original Excel files after conversion")
@click.option("--file-workers", type=int, default=excel_to_csv.DEFAULT_FILE_WORKERS)
@click.option("--sheet-workers", type=int, default=excel_to_csv.DEFAULT_SHEET_WORKERS)
def excel_to_csv_command(
    input_dir: Path,
    output_dir: Path,
    force: bool,
    keep_originals: bool,
    file_workers: Optional[int],
    sheet_workers: Optional[int],
) -> None:
    """Convert Excel workbooks to CSV files."""
    excel_to_csv.batch_convert_excel_to_csv(
        input_dir=input_dir,
        output_dir=output_dir,
        force=force,
        delete_originals=not keep_originals,
        max_file_workers=file_workers,
        max_sheet_workers=sheet_workers,
    )


def main() -> None:  # pragma: no cover - console entry point
    cli(prog_name="oews-migrate")


if __name__ == "__main__":  # pragma: no cover - script entrypoint
    main()
