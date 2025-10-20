"""Normalize OEWS CSV files into a canonical schema and persist as Parquet."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import polars as pl
from tqdm import tqdm

from src import oews_schema
from ._common import (
    COMMON_SUPPRESSION_VALUES,
    DEFAULT_DATA_ROOT,
    DEFAULT_OUTPUT_DIR,
    detect_year,
    iter_data_csv_files,
    normalize_header,
    read_header_and_sample,
)

logger = logging.getLogger(__name__)

OUTPUT_SUBDIR = "standardized"
DEFAULT_WORKERS = max(os.cpu_count() or 4, 4)

CANONICAL_COLUMNS = oews_schema.CANONICAL_COLUMNS
COLUMN_CANONICAL_MAP = oews_schema.COLUMN_CANONICAL_MAP
DEFAULT_COLUMN_VALUES = oews_schema.COLUMN_DEFAULTS
NUMERIC_COLUMN_TYPES = oews_schema.POLARS_NUMERIC_TYPES
METADATA_COLUMNS = oews_schema.METADATA_COLUMNS


@dataclass
class StandardizationResult:
    source_file: str
    output_file: str
    rows: int
    columns: int
    canonical_columns: List[str]
    extra_columns: List[str]
    added_columns: List[str]
    dropped_columns: Dict[str, List[str]] = field(default_factory=dict)
    year: Optional[int] = None


def build_rename_plan(columns: Iterable[str]) -> tuple[Dict[str, str], Dict[str, List[str]], List[str]]:
    rename_map: Dict[str, str] = {}
    duplicates: Dict[str, List[str]] = {}
    drop_columns: List[str] = []
    seen: set[str] = set()

    for column in columns:
        normalized = normalize_header(column)
        canonical = COLUMN_CANONICAL_MAP.get(normalized)
        if not canonical:
            canonical = normalized.upper() if normalized else column.upper()

        if canonical in seen:
            duplicates.setdefault(canonical, []).append(column)
            drop_columns.append(column)
            continue

        rename_map[column] = canonical
        seen.add(canonical)

    return rename_map, duplicates, drop_columns


def sanitize_numeric_column(column: str, dtype: "pl.DataType") -> pl.Expr:
    sentinel_values = list(COMMON_SUPPRESSION_VALUES)
    str_col = pl.col(column).cast(pl.Utf8).str.strip_chars()
    return (
        pl.when(str_col.is_null() | str_col.is_in(sentinel_values))
        .then(None)
        .otherwise(str_col)
        .cast(dtype)
        .alias(column)
    )


def standardize_file(csv_path: Path, output_root: Path) -> StandardizationResult:
    header, _ = read_header_and_sample(csv_path, sample_rows=1)
    schema_overrides = [pl.Utf8] * len(header) if header else None

    df = pl.read_csv(
        csv_path,
        null_values=[val for val in COMMON_SUPPRESSION_VALUES if val],
        schema_overrides=schema_overrides,
        infer_schema_length=1000,
        try_parse_dates=False,
        low_memory=False,
        rechunk=True,
    )

    rename_map, duplicates, drop_columns = build_rename_plan(df.columns)

    if drop_columns:
        df = df.drop(drop_columns)

    df = df.rename(rename_map)

    missing_exprs = []
    missing_columns = []
    for column in CANONICAL_COLUMNS:
        if column not in df.columns:
            missing_columns.append(column)
            default_value = DEFAULT_COLUMN_VALUES.get(column)
            missing_exprs.append(pl.lit(default_value).alias(column))

    if missing_exprs:
        df = df.with_columns(missing_exprs)

    numeric_exprs = [
        sanitize_numeric_column(column, dtype)
        for column, dtype in NUMERIC_COLUMN_TYPES.items()
        if column in df.columns
    ]
    if numeric_exprs:
        df = df.with_columns(numeric_exprs)

    year = detect_year(csv_path)

    df = df.with_columns(
        [
            pl.lit(csv_path.name).alias("_source_file"),
            pl.lit(csv_path.parent.name).alias("_source_folder"),
            pl.lit(year).alias("_data_year"),
        ]
    )

    canonical_order = [col for col in CANONICAL_COLUMNS if col in df.columns]
    extra_columns = [
        col for col in df.columns if col not in canonical_order and col not in METADATA_COLUMNS
    ]

    df = df.select(canonical_order + extra_columns + METADATA_COLUMNS)

    output_dir = output_root / csv_path.parent.name
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{csv_path.stem}.parquet"
    df.write_parquet(output_path, compression="zstd")

    return StandardizationResult(
        source_file=str(csv_path),
        output_file=str(output_path),
        rows=df.height,
        columns=df.width,
        canonical_columns=canonical_order,
        extra_columns=extra_columns,
        added_columns=missing_columns,
        dropped_columns=duplicates,
        year=year,
    )


def run(root: Path, output_dir: Path, workers: int) -> int:
    csv_files = list(iter_data_csv_files(root))
    if not csv_files:
        logger.warning("No CSV files found under %s", root)
        return 1

    target_root = output_dir / OUTPUT_SUBDIR
    target_root.mkdir(parents=True, exist_ok=True)

    results: List[StandardizationResult] = []
    errors: List[Dict[str, str]] = []

    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_map = {
            executor.submit(standardize_file, csv_path, target_root): csv_path
            for csv_path in csv_files
        }

        for future in tqdm(as_completed(future_map), total=len(future_map), desc="Standardizing"):
            csv_path = future_map[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as exc:  # pragma: no cover - logging path
                errors.append({"file": str(csv_path), "error": str(exc)})
                logger.exception("Failed to standardize %s", csv_path)

    report = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source_root": str(root),
        "output_root": str(target_root),
        "files_processed": len(results),
        "files_failed": len(errors),
        "total_rows": sum(r.rows for r in results),
        "schema_version": oews_schema.SCHEMA_VERSION,
        "results": [asdict(r) for r in sorted(results, key=lambda r: r.source_file)],
        "errors": errors,
    }

    report_path = target_root / "standardization_report.json"
    with report_path.open("w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)

    logger.info("Wrote standardized parquet files to %s", target_root)
    logger.info("Report -> %s", report_path)

    if errors:
        for error in errors:
            logger.error("%s: %s", error["file"], error["error"])
        return 1

    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_DATA_ROOT,
        help="Root directory containing year folders with CSV files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory where standardized parquet files will be written.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help="Number of worker threads to use for parallel processing.",
    )
    return parser.parse_args()


if __name__ == "__main__":  # pragma: no cover - script entrypoint
    args = parse_args()
    exit_code = run(args.root, args.output_dir, args.workers)
    raise SystemExit(exit_code)
