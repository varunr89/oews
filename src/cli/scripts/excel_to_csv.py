"""High-performance Excel to CSV batch converter."""

from __future__ import annotations

import argparse
import logging
import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Optional, Tuple

from tqdm import tqdm

try:  # pragma: no cover - optional dependency import guard
    import polars as pl
except ImportError:  # pragma: no cover - handled by CLI validation
    pl = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

DEFAULT_FILE_WORKERS: Optional[int] = None
DEFAULT_SHEET_WORKERS = 4


@dataclass(slots=True)
class ConversionResult:
    """Result of converting a single Excel file."""

    excel_file: str
    success: bool
    sheets_converted: int
    sheets_failed: int
    sheets_skipped: int
    message: str
    duration: float


def sanitize_sheet_name(sheet_name: str) -> str:
    """Return a filesystem-safe sheet name."""
    stripped = sheet_name.strip()
    cleaned = "".join(c if c.isalnum() or c in {" ", "_", "-"} else "_" for c in stripped)
    cleaned = cleaned.replace(" ", "_")
    return cleaned or "sheet"


def _read_sheet_with_polars(excel_path: str, sheet_name: str):
    if pl is None:
        raise RuntimeError("Polars is not available")
    try:
        return pl.read_excel(excel_path, sheet_name=sheet_name, engine="fastexcel")
    except Exception:
        return pl.read_excel(excel_path, sheet_name=sheet_name)


def _read_sheet_with_pandas(excel_path: str, sheet_name: str):
    import pandas as pd

    return pd.read_excel(excel_path, sheet_name=sheet_name, engine="openpyxl")


def convert_sheet_to_csv(
    excel_path: str,
    sheet_name: str,
    output_dir: Path,
    pandas_loader: Optional[Callable[[str, str], object]] = None,
) -> Tuple[str, bool, str]:
    """Convert a single Excel sheet to CSV using Polars or a pandas fallback."""
    safe_name = sanitize_sheet_name(sheet_name) or "sheet"
    csv_path = output_dir / f"{safe_name}.csv"

    loader = pandas_loader or _read_sheet_with_pandas

    try:
        df = _read_sheet_with_polars(excel_path, sheet_name)
        df.write_csv(csv_path)
        return sheet_name, True, "OK"
    except Exception as polars_error:
        try:
            df = loader(excel_path, sheet_name)
            df.to_csv(csv_path, index=False)
            return sheet_name, True, "OK"
        except Exception as pandas_error:
            return (
                sheet_name,
                False,
                f"Polars: {polars_error!s} | Pandas: {pandas_error!s}",
            )


def _discover_sheet_names(excel_path: Path) -> list[str]:
    if pl is not None:
        try:
            workbook = pl.ExcelFile(str(excel_path))
            return workbook.sheet_names()
        except Exception:
            pass

    import pandas as pd

    workbook = pd.ExcelFile(str(excel_path), engine="openpyxl")
    return workbook.sheet_names


def convert_excel_file(
    excel_path: Path,
    output_base_dir: Path,
    max_workers: Optional[int] = DEFAULT_SHEET_WORKERS,
) -> ConversionResult:
    """Convert all sheets in an Excel file using parallel sheet-level workers.

    A process pool is used here because worksheet decoding is CPU bound; the
    worker count defaults to ``DEFAULT_SHEET_WORKERS`` but can be tuned by the
    caller to balance throughput and memory pressure.
    """
    start_time = time.time()
    output_dir = output_base_dir / excel_path.stem
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        sheet_names = _discover_sheet_names(excel_path)
    except Exception as exc:  # pragma: no cover - log path
        duration = time.time() - start_time
        return ConversionResult(
            excel_file=excel_path.name,
            success=False,
            sheets_converted=0,
            sheets_failed=0,
            sheets_skipped=0,
            message=f"Failed to read Excel file: {exc}",
            duration=duration,
        )

    sheets_converted = 0
    sheets_failed = 0
    failed_sheets: list[Tuple[str, str]] = []

    worker_count = max_workers or DEFAULT_SHEET_WORKERS
    with ProcessPoolExecutor(max_workers=worker_count) as executor:
        futures = {
            executor.submit(convert_sheet_to_csv, str(excel_path), sheet_name, output_dir): sheet_name
            for sheet_name in sheet_names
        }

        for future in as_completed(futures):
            sheet_name, success, message = future.result()
            if success:
                sheets_converted += 1
            else:
                sheets_failed += 1
                failed_sheets.append((sheet_name, message))

    duration = time.time() - start_time
    overall_success = sheets_failed == 0
    if overall_success:
        message = f"{sheets_converted} sheets converted in {duration:.2f}s"
    else:
        failed_preview = ", ".join(name for name, _ in failed_sheets[:3])
        message = (
            f"{sheets_converted} converted, {sheets_failed} failed in {duration:.2f}s"
            + (f" | Failed: {failed_preview}" if failed_preview else "")
        )

    return ConversionResult(
        excel_file=excel_path.name,
        success=overall_success,
        sheets_converted=sheets_converted,
        sheets_failed=sheets_failed,
        sheets_skipped=0,
        message=message,
        duration=duration,
    )


def should_skip_file(excel_path: Path, output_base_dir: Path) -> bool:
    output_dir = output_base_dir / excel_path.stem
    if not output_dir.exists():
        return False
    return any(output_dir.glob("*.csv"))


def batch_convert_excel_to_csv(
    input_dir: Path,
    output_dir: Path,
    force: bool = False,
    delete_originals: bool = True,
    max_file_workers: Optional[int] = DEFAULT_FILE_WORKERS,
    max_sheet_workers: Optional[int] = DEFAULT_SHEET_WORKERS,
) -> Dict[str, ConversionResult]:
    """Batch convert all Excel files in a directory to CSV format."""
    output_dir.mkdir(parents=True, exist_ok=True)

    excel_files = sorted(input_dir.glob("*.xlsx")) + sorted(input_dir.glob("*.xls"))
    if not excel_files:
        logger.info("No Excel files found in %s", input_dir)
        return {}

    files_to_process = []
    for excel_file in excel_files:
        if not force and should_skip_file(excel_file, output_dir):
            logger.debug("Skipping already converted file: %s", excel_file.name)
            continue
        files_to_process.append(excel_file)

    results: Dict[str, ConversionResult] = {}
    successful_files: list[Path] = []

    worker_count = max_file_workers or os.cpu_count() or 4
    with ProcessPoolExecutor(max_workers=worker_count) as executor:
        futures = {
            executor.submit(convert_excel_file, excel_file, output_dir, max_sheet_workers): excel_file
            for excel_file in files_to_process
        }

        with tqdm(total=len(futures), desc="Processing files", unit="file") as progress:
            for future in as_completed(futures):
                excel_file = futures[future]
                try:
                    result = future.result()
                except Exception as exc:  # pragma: no cover - log path
                    logger.exception("Unexpected error converting %s", excel_file)
                    result = ConversionResult(
                        excel_file=excel_file.name,
                        success=False,
                        sheets_converted=0,
                        sheets_failed=0,
                        sheets_skipped=0,
                        message=str(exc),
                        duration=0.0,
                    )

                results[result.excel_file] = result
                if result.success:
                    successful_files.append(excel_file)
                    logger.info("SUCCESS %s", result.message)
                else:
                    logger.error("FAILED %s", result.message)

                progress.update(1)

    if delete_originals and successful_files:
        for excel_file in successful_files:
            try:
                excel_file.unlink()
                logger.debug("Deleted original Excel file %s", excel_file)
            except Exception as exc:  # pragma: no cover - log path
                logger.warning("Could not delete %s: %s", excel_file, exc)

    logger.info("Total files processed: %s", len(files_to_process))
    logger.info(
        "Success: %s | Failed: %s",
        sum(1 for result in results.values() if result.success),
        sum(1 for result in results.values() if not result.success),
    )

    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("data/raw"),
        help="Directory containing Excel files (default: data/raw)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/csv"),
        help="Directory to save CSV files (default: data/csv)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-conversion of already converted files",
    )
    parser.add_argument(
        "--keep-originals",
        action="store_true",
        help="Do not delete original Excel files after conversion",
    )
    parser.add_argument(
        "--file-workers",
        type=int,
        default=DEFAULT_FILE_WORKERS,
        help="Number of parallel workers for processing files (default: CPU count)",
    )
    parser.add_argument(
        "--sheet-workers",
        type=int,
        default=DEFAULT_SHEET_WORKERS,
        help="Number of parallel workers for processing sheets within a file",
    )
    return parser.parse_args()


def main() -> int:  # pragma: no cover - CLI entry point
    args = parse_args()
    results = batch_convert_excel_to_csv(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        force=args.force,
        delete_originals=not args.keep_originals,
        max_file_workers=args.file_workers,
        max_sheet_workers=args.sheet_workers,
    )
    return 0 if all(result.success for result in results.values()) else 1


if __name__ == "__main__":  # pragma: no cover - script entrypoint
    raise SystemExit(main())
