"""
Normalize OEWS CSV files into a canonical schema and persist as Parquet.

This script leverages Polars for high-throughput processing: each input CSV is
transformed in parallel, column headers are harmonized, missing fields receive
defaults, suppression tokens are coerced to nulls, and the result is written to
``data/standardized/<folder>/<file>.parquet`` (by default).

The accompanying ``standardization_report.json`` summarizes the work performed
per file—renamed columns, additions, and any extra fields carried forward.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import polars as pl
from tqdm import tqdm

try:
    from ._common import (
        DEFAULT_DATA_ROOT,
        DEFAULT_OUTPUT_DIR,
        COMMON_SUPPRESSION_VALUES,
        detect_year,
        iter_data_csv_files,
        normalize_header,
        read_header_and_sample,
    )
except ImportError:  # pragma: no cover - script entrypoint fallback
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[3]))
    from src.cli.scripts._common import (  # type: ignore
        DEFAULT_DATA_ROOT,
        DEFAULT_OUTPUT_DIR,
        COMMON_SUPPRESSION_VALUES,
        detect_year,
        iter_data_csv_files,
        normalize_header,
        read_header_and_sample,
    )

OUTPUT_SUBDIR = "standardized"
DEFAULT_WORKERS = max(os.cpu_count() or 4, 4)

STANDARD_COLUMNS = [
    "AREA",
    "AREA_TITLE",
    "AREA_TYPE",
    "PRIM_STATE",
    "NAICS",
    "NAICS_TITLE",
    "I_GROUP",
    "OWN_CODE",
    "OCC_CODE",
    "OCC_TITLE",
    "O_GROUP",
    "TOT_EMP",
    "EMP_PRSE",
    "JOBS_1000",
    "LOC_QUOTIENT",
    "PCT_TOTAL",
    "PCT_RPT",
    "H_MEAN",
    "A_MEAN",
    "MEAN_PRSE",
    "H_PCT10",
    "H_PCT25",
    "H_MEDIAN",
    "H_PCT75",
    "H_PCT90",
    "A_PCT10",
    "A_PCT25",
    "A_MEDIAN",
    "A_PCT75",
    "A_PCT90",
    "ANNUAL",
    "HOURLY",
]

COLUMN_CANONICAL_MAP: Dict[str, str] = {
    "area": "AREA",
    "area_title": "AREA_TITLE",
    "area_type": "AREA_TYPE",
    "prim_state": "PRIM_STATE",
    "primary_state": "PRIM_STATE",
    "naics": "NAICS",
    "naic": "NAICS",
    "naics_title": "NAICS_TITLE",
    "own_code": "OWN_CODE",
    "ownership_code": "OWN_CODE",
    "occ_code": "OCC_CODE",
    "occ_code1": "OCC_CODE",
    "occcode": "OCC_CODE",
    "occ_title": "OCC_TITLE",
    "occtitle": "OCC_TITLE",
    "o_group": "O_GROUP",
    "group": "O_GROUP",
    "i_group": "I_GROUP",
    "igroup": "I_GROUP",
    "tot_emp": "TOT_EMP",
    "total_emp": "TOT_EMP",
    "emp_prse": "EMP_PRSE",
    "jobs_1000": "JOBS_1000",
    "jobs_1000_orig": "JOBS_1000",
    "jobs_per_1000": "JOBS_1000",
    "loc_quotient": "LOC_QUOTIENT",
    "loc_quotiont": "LOC_QUOTIENT",
    "loc_q": "LOC_QUOTIENT",
    "pct_total": "PCT_TOTAL",
    "pct_tot": "PCT_TOTAL",
    "pcttotal": "PCT_TOTAL",
    "pct_rpt": "PCT_RPT",
    "percent_reporting": "PCT_RPT",
    "h_mean": "H_MEAN",
    "hourly_mean": "H_MEAN",
    "a_mean": "A_MEAN",
    "annual_mean": "A_MEAN",
    "mean_prse": "MEAN_PRSE",
    "h_pct10": "H_PCT10",
    "h_pct25": "H_PCT25",
    "h_median": "H_MEDIAN",
    "h_pct75": "H_PCT75",
    "h_pct90": "H_PCT90",
    "a_pct10": "A_PCT10",
    "a_pct25": "A_PCT25",
    "a_median": "A_MEDIAN",
    "a_pct75": "A_PCT75",
    "a_pct90": "A_PCT90",
    "annual": "ANNUAL",
    "hourly": "HOURLY",
}

# Defaults for columns that may not exist in older vintages.
DEFAULT_COLUMN_VALUES: Dict[str, Optional[str]] = {
    "I_GROUP": "cross-industry",
    "PRIM_STATE": None,
    "PCT_RPT": None,
}

# Numeric columns that need coercion after renaming.
NUMERIC_COLUMN_TYPES = {
    "AREA_TYPE": pl.Int16,
    "TOT_EMP": pl.Int64,
    "EMP_PRSE": pl.Float64,
    "JOBS_1000": pl.Float64,
    "LOC_QUOTIENT": pl.Float64,
    "PCT_TOTAL": pl.Float64,
    "PCT_RPT": pl.Float64,
    "H_MEAN": pl.Float64,
    "A_MEAN": pl.Float64,
    "MEAN_PRSE": pl.Float64,
    "H_PCT10": pl.Float64,
    "H_PCT25": pl.Float64,
    "H_MEDIAN": pl.Float64,
    "H_PCT75": pl.Float64,
    "H_PCT90": pl.Float64,
    "A_PCT10": pl.Float64,
    "A_PCT25": pl.Float64,
    "A_MEDIAN": pl.Float64,
    "A_PCT75": pl.Float64,
    "A_PCT90": pl.Float64,
}

METADATA_COLUMNS = ["_source_file", "_source_folder", "_data_year"]


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


def build_rename_plan(columns: Iterable[str]):
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


def sanitize_numeric_column(column: str, dtype: pl.DataType) -> pl.Expr:
    # Convert to string for suppression detection, then back to numeric dtype.
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
    for column in STANDARD_COLUMNS:
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

    canonical_order = [col for col in STANDARD_COLUMNS if col in df.columns]
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
        print(f"No CSV files found under {root}")
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

    report = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source_root": str(root),
        "output_root": str(target_root),
        "files_processed": len(results),
        "files_failed": len(errors),
        "total_rows": sum(r.rows for r in results),
        "results": [asdict(r) for r in sorted(results, key=lambda r: r.source_file)],
        "errors": errors,
    }

    report_path = target_root / "standardization_report.json"
    with report_path.open("w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)

    print(f"Wrote standardized parquet files to {target_root}")
    print(f"Report -> {report_path}")

    if errors:
        print("\nEncountered errors:")
        for error in errors:
            print(f"  {error['file']}: {error['error']}")
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


if __name__ == "__main__":
    args = parse_args()
    exit_code = run(args.root, args.output_dir, args.workers)
    raise SystemExit(exit_code)
