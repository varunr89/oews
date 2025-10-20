"""
Load standardized OEWS Parquet files into a SQLite database with tuned settings.

Key features
------------
* Uses a producer/consumer pipeline so parquet decoding happens on multiple
  threads while a dedicated writer performs batched inserts.
* Applies SQLite performance pragmas (journal disabled, synchronous off,
  exclusive locking) and wraps the migration in a single bulk transaction.
* Tracks per-file metadata in the ``data_vintages`` table and reports progress
  with a row-level progress bar.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from itertools import repeat
from pathlib import Path
from queue import Queue
from threading import Thread
from typing import Dict, Iterable, Optional

import pyarrow as pa
import pyarrow.parquet as pq
from tqdm import tqdm

try:
    from ._common import DEFAULT_OUTPUT_DIR
except ImportError:  # pragma: no cover - script entrypoint fallback
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[3]))
    from src.cli.scripts._common import DEFAULT_OUTPUT_DIR  # type: ignore

PARQUET_SUBDIR = "standardized"
DB_FILENAME = "oews.db"
DEFAULT_BATCH_SIZE = 50_000
DEFAULT_WORKERS = max((os.cpu_count() or 4) - 1, 2)

CANONICAL_COLUMNS = [
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

METADATA_COLUMNS = ["_data_year", "_source_file", "_source_folder"]

DB_COLUMNS = CANONICAL_COLUMNS + [
    "SURVEY_YEAR",
    "SURVEY_MONTH",
    "SOURCE_FILE",
    "SOURCE_FOLDER",
]


@dataclass
class BatchMessage:
    kind: str  # "batch", "file_done", "stop"
    file_path: str
    batch: Optional["pa.RecordBatch"] = None
    row_count: int = 0


def load_standardization_report(parquet_root: Path) -> Dict[str, int]:
    report_path = parquet_root / "standardization_report.json"
    if not report_path.exists():
        return {}
    with report_path.open(encoding="utf-8") as fh:
        report = json.load(fh)
    return {
        Path(entry["output_file"]).resolve().as_posix(): entry["rows"]
        for entry in report.get("results", [])
    }


def setup_database(db_path: Path) -> sqlite3.Connection:
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(db_path, check_same_thread=False)
    pragmas = [
        "PRAGMA journal_mode=OFF;",
        "PRAGMA synchronous=OFF;",
        "PRAGMA temp_store=MEMORY;",
        "PRAGMA locking_mode=EXCLUSIVE;",
        "PRAGMA cache_size=-64000;",  # negative => kibibytes in memory
    ]
    for pragma in pragmas:
        conn.execute(pragma)

    conn.execute(
        """
        CREATE TABLE oews_data (
            AREA TEXT,
            AREA_TITLE TEXT,
            AREA_TYPE INTEGER,
            PRIM_STATE TEXT,
            NAICS TEXT,
            NAICS_TITLE TEXT,
            I_GROUP TEXT,
            OWN_CODE TEXT,
            OCC_CODE TEXT,
            OCC_TITLE TEXT,
            O_GROUP TEXT,
            TOT_EMP INTEGER,
            EMP_PRSE REAL,
            JOBS_1000 REAL,
            LOC_QUOTIENT REAL,
            PCT_TOTAL REAL,
            PCT_RPT REAL,
            H_MEAN REAL,
            A_MEAN REAL,
            MEAN_PRSE REAL,
            H_PCT10 REAL,
            H_PCT25 REAL,
            H_MEDIAN REAL,
            H_PCT75 REAL,
            H_PCT90 REAL,
            A_PCT10 REAL,
            A_PCT25 REAL,
            A_MEDIAN REAL,
            A_PCT75 REAL,
            A_PCT90 REAL,
            ANNUAL TEXT,
            HOURLY TEXT,
            SURVEY_YEAR INTEGER,
            SURVEY_MONTH TEXT,
            SOURCE_FILE TEXT,
            SOURCE_FOLDER TEXT,
            IMPORTED_AT TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    conn.execute(
        """
        CREATE TABLE data_vintages (
            SOURCE_FILE TEXT PRIMARY KEY,
            SOURCE_FOLDER TEXT,
            SURVEY_YEAR INTEGER,
            ROW_COUNT INTEGER,
            IMPORTED_AT TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    return conn


def create_indexes(conn: sqlite3.Connection) -> None:
    index_statements = [
        "CREATE INDEX idx_oews_area_year ON oews_data(AREA, SURVEY_YEAR);",
        "CREATE INDEX idx_oews_occ_year ON oews_data(OCC_CODE, SURVEY_YEAR);",
        "CREATE INDEX idx_oews_naics_year ON oews_data(NAICS, SURVEY_YEAR);",
        "CREATE INDEX idx_oews_year ON oews_data(SURVEY_YEAR);",
        "CREATE INDEX idx_oews_area_occ_year ON oews_data(AREA, OCC_CODE, SURVEY_YEAR);",
    ]
    for statement in index_statements:
        conn.execute(statement)


def producer(
    parquet_path: Path,
    queue: Queue,
    batch_size: int,
) -> None:
    parquet_file = pq.ParquetFile(parquet_path)
    total_rows = 0
    for batch in parquet_file.iter_batches(batch_size=batch_size, use_threads=True):
        queue.put(BatchMessage("batch", parquet_path.as_posix(), batch=batch))
        total_rows += batch.num_rows
    queue.put(BatchMessage("file_done", parquet_path.as_posix(), row_count=total_rows))


def first_non_null(values: Iterable[Optional[object]]) -> Optional[object]:
    for value in values:
        if value is not None:
            return value
    return None


def writer(
    queue: Queue,
    conn: sqlite3.Connection,
    progress: tqdm,
    file_stats: Dict[str, Dict[str, Optional[object]]],
) -> None:
    insert_sql = f"""
        INSERT INTO oews_data ({', '.join(DB_COLUMNS)})
        VALUES ({', '.join(['?'] * len(DB_COLUMNS))});
    """
    cursor = conn.cursor()

    while True:
        message: BatchMessage = queue.get()
        if message.kind == "stop":
            queue.task_done()
            break

        if message.kind == "batch" and message.batch is not None:
            data = message.batch.to_pydict()
            survey_years = data["_data_year"]
            source_files = data["_source_file"]
            source_folders = data["_source_folder"]

            rows_iter = zip(
                *(data[column] for column in CANONICAL_COLUMNS),
                survey_years,
                repeat("May", message.batch.num_rows),
                source_files,
                source_folders,
            )

            cursor.executemany(insert_sql, rows_iter)
            progress.update(message.batch.num_rows)

            stats = file_stats.setdefault(
                message.file_path,
                {
                    "rows": 0,
                    "survey_year": None,
                    "source_file": None,
                    "source_folder": None,
                },
            )
            stats["rows"] += message.batch.num_rows
            if stats["survey_year"] is None:
                stats["survey_year"] = first_non_null(survey_years)
            if stats["source_file"] is None:
                stats["source_file"] = first_non_null(source_files)
            if stats["source_folder"] is None:
                stats["source_folder"] = first_non_null(source_folders)

        elif message.kind == "file_done":
            stats = file_stats.setdefault(
                message.file_path,
                {
                    "rows": 0,
                    "survey_year": None,
                    "source_file": None,
                    "source_folder": None,
                },
            )
            stats["expected_rows"] = message.row_count

        queue.task_done()

    cursor.close()


def load_parquet_files(
    parquet_files: Iterable[Path],
    conn: sqlite3.Connection,
    workers: int,
    batch_size: int,
    expected_rows: Optional[int],
) -> Dict[str, Dict[str, Optional[object]]]:
    queue: Queue = Queue(maxsize=workers * 2)
    file_stats: Dict[str, Dict[str, Optional[object]]] = {}
    progress = tqdm(total=expected_rows, unit="rows", desc="Loading to SQLite")

    writer_thread = Thread(target=writer, args=(queue, conn, progress, file_stats), daemon=True)
    writer_thread.start()

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(producer, parquet_path, queue, batch_size)
            for parquet_path in parquet_files
        ]
        for future in as_completed(futures):
            future.result()

    queue.put(BatchMessage("stop", file_path=""))
    queue.join()
    writer_thread.join()
    progress.close()
    return file_stats


def insert_data_vintages(conn: sqlite3.Connection, stats: Dict[str, Dict[str, Optional[object]]]) -> None:
    payload = []
    for file_path, info in stats.items():
        payload.append(
            (
                info.get("source_file"),
                info.get("source_folder"),
                info.get("survey_year"),
                info.get("rows"),
            )
        )
    conn.executemany(
        """
        INSERT OR REPLACE INTO data_vintages (SOURCE_FILE, SOURCE_FOLDER, SURVEY_YEAR, ROW_COUNT)
        VALUES (?, ?, ?, ?);
        """,
        payload,
    )


def summarize(conn: sqlite3.Connection) -> Dict[str, object]:
    row = conn.execute(
        """
        SELECT
            COUNT(*) AS total_rows,
            COUNT(DISTINCT SOURCE_FILE) AS files,
            MIN(SURVEY_YEAR) AS min_year,
            MAX(SURVEY_YEAR) AS max_year
        FROM oews_data;
        """
    ).fetchone()
    return {
        "total_rows": row[0],
        "files": row[1],
        "min_year": row[2],
        "max_year": row[3],
    }


def run(parquet_root: Path, output_dir: Path, workers: int, batch_size: int) -> None:
    parquet_dir = parquet_root / PARQUET_SUBDIR if parquet_root.is_dir() else parquet_root
    parquet_files = sorted(p for p in parquet_dir.rglob("*.parquet"))
    if not parquet_files:
        raise FileNotFoundError(f"No parquet files found under {parquet_dir}")

    db_path = output_dir / DB_FILENAME
    conn = setup_database(db_path)
    conn.execute("BEGIN IMMEDIATE;")

    try:
        report_mapping = load_standardization_report(parquet_dir)
        expected_rows = (
            sum(report_mapping.get(p.resolve().as_posix(), 0) for p in parquet_files)
            if report_mapping
            else None
        )

        stats = load_parquet_files(parquet_files, conn, workers, batch_size, expected_rows)
        insert_data_vintages(conn, stats)
        create_indexes(conn)
        conn.commit()

        summary = summarize(conn)

    except Exception:
        conn.rollback()
        conn.close()
        raise

    conn.close()

    db_size_mb = db_path.stat().st_size / 1024 / 1024
    print(f"\nDatabase created: {db_path}")
    print(f"Size: {db_size_mb:.1f} MB")
    print(
        f"Rows: {summary['total_rows']:,} spanning {summary['min_year']} - {summary['max_year']} "
        f"across {summary['files']} files"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--parquet-root",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory containing the standardized parquet output.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory where the SQLite database should be written.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help="Number of worker threads used to decode parquet files.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help="Number of rows per batch when streaming parquet into SQLite.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(args.parquet_root, args.output_dir, args.workers, args.batch_size)
