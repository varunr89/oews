"""Load standardized OEWS Parquet files into a SQLite database with tuned settings."""

import argparse
import json
import logging
import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from enum import Enum
from itertools import repeat
from pathlib import Path
from queue import Queue
from threading import Thread
from typing import Dict, Iterable, Optional

import pyarrow as pa
import pyarrow.parquet as pq
from tqdm import tqdm

from src import oews_schema
from ._common import DEFAULT_OUTPUT_DIR

logger = logging.getLogger(__name__)

PARQUET_SUBDIR = "standardized"
DB_FILENAME = "oews.db"
DEFAULT_BATCH_SIZE = 50_000
DEFAULT_WORKERS = max((os.cpu_count() or 4) - 1, 2)

CANONICAL_COLUMNS = oews_schema.CANONICAL_COLUMNS
METADATA_COLUMNS = oews_schema.METADATA_COLUMNS
DB_COLUMNS = CANONICAL_COLUMNS + oews_schema.DB_EXTRA_COLUMNS


class MessageKind(str, Enum):
    BATCH = "batch"
    FILE_DONE = "file_done"
    STOP = "stop"


@dataclass(slots=True)
class BatchMessage:
    kind: MessageKind
    file_path: str
    batch: Optional[pa.RecordBatch] = None
    row_count: int = 0


def load_standardization_report(parquet_root: Path) -> Dict[str, int]:
    report_path = parquet_root / "standardization_report.json"
    if not report_path.exists():
        logger.debug("Standardization report not found at %s", report_path)
        return {}
    with report_path.open(encoding="utf-8") as fh:
        report = json.load(fh)
    return {
        Path(entry["output_file"]).resolve().as_posix(): entry["rows"]
        for entry in report.get("results", [])
    }


def setup_database(db_path: Path) -> sqlite3.Connection:
    if db_path.exists():
        logger.info("Replacing existing database at %s", db_path)
        db_path.unlink()

    conn = sqlite3.connect(db_path, check_same_thread=False)
    pragmas = [
        "PRAGMA journal_mode=OFF;",
        "PRAGMA synchronous=OFF;",
        "PRAGMA temp_store=MEMORY;",
        "PRAGMA locking_mode=EXCLUSIVE;",
        "PRAGMA cache_size=-64000;",
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


def producer(parquet_path: Path, queue: "Queue[BatchMessage]", batch_size: int) -> None:
    parquet_file = pq.ParquetFile(parquet_path)
    total_rows = 0
    for batch in parquet_file.iter_batches(batch_size=batch_size, use_threads=True):
        queue.put(BatchMessage(MessageKind.BATCH, parquet_path.as_posix(), batch=batch))
        total_rows += batch.num_rows
    queue.put(BatchMessage(MessageKind.FILE_DONE, parquet_path.as_posix(), row_count=total_rows))


def first_non_null(values: Iterable[Optional[object]]) -> Optional[object]:
    for value in values:
        if value is not None:
            return value
    return None


def writer(
    queue: "Queue[BatchMessage]",
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
        message = queue.get()
        if message.kind is MessageKind.STOP:
            queue.task_done()
            break

        if message.kind is MessageKind.BATCH and message.batch is not None:
            data = message.batch.to_pydict()
            metadata = {name: data[name] for name in METADATA_COLUMNS}
            survey_years = metadata["_data_year"]
            source_files = metadata["_source_file"]
            source_folders = metadata["_source_folder"]

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

        elif message.kind is MessageKind.FILE_DONE:
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
    queue: "Queue[BatchMessage]" = Queue(maxsize=max(workers * 2, 4))
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

    queue.put(BatchMessage(MessageKind.STOP, file_path=""))
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
    logger.info("Database created: %s", db_path)
    logger.info("Size: %.1f MB", db_size_mb)
    logger.info(
        "Rows: %s spanning %s - %s across %s files",
        f"{summary['total_rows']:,}",
        summary["min_year"],
        summary["max_year"],
        summary["files"],
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


if __name__ == "__main__":  # pragma: no cover - script entrypoint
    args = parse_args()
    run(args.parquet_root, args.output_dir, args.workers, args.batch_size)
