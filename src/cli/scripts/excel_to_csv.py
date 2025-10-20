#!/usr/bin/env python
"""
High-Performance Excel to CSV Batch Converter

Converts all Excel files in a directory to CSV format using Polars with the
fastexcel (Rust calamine) engine - 10-100x faster than pandas.

Features:
- Multi-level parallelism (files + sheets)
- Uses all CPU cores
- Automatic file discovery
- One folder per Excel file for organization
- Safe deletion only after successful conversion
- Progress tracking with visual feedback
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, Tuple
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
import time

from tqdm import tqdm

# Try to use Polars with fastexcel (Rust-based, fastest)
try:
    import polars as pl
    HAS_POLARS = True
except ImportError:
    HAS_POLARS = False


@dataclass
class ConversionResult:
    """Result of converting a single Excel file."""
    excel_file: str
    success: bool
    sheets_converted: int
    sheets_failed: int
    sheets_skipped: int
    message: str
    duration: float


def convert_sheet_to_csv(
    excel_path: str,
    sheet_name: str,
    output_dir: Path
) -> Tuple[str, bool, str]:
    """
    Convert a single Excel sheet to CSV.
    Uses Polars with fastexcel (Rust-based, fastest) if available, falls back to pandas.

    Args:
        excel_path: Path to Excel file
        sheet_name: Name of sheet to convert
        output_dir: Directory to save CSV file

    Returns:
        Tuple of (sheet_name, success, message)
    """
    try:
        # Import here for multiprocessing compatibility
        import polars as pl

        # Create safe filename from sheet name
        safe_name = "".join(
            c if c.isalnum() or c in (' ', '_', '-') else '_'
            for c in sheet_name
        )
        csv_path = output_dir / f"{safe_name}.csv"

        # Use Polars with fastexcel (Rust-based, fastest)
        try:
            df = pl.read_excel(
                excel_path,
                sheet_name=sheet_name,
                engine='fastexcel'
            )
            df.write_csv(csv_path)
        except Exception:
            # Fall back to default engine if fastexcel fails
            df = pl.read_excel(
                excel_path,
                sheet_name=sheet_name
            )
            df.write_csv(csv_path)

        return (sheet_name, True, "OK")

    except Exception as e:
        # If Polars fails, try pandas fallback
        try:
            import pandas as pd
            df = pd.read_excel(
                excel_path,
                sheet_name=sheet_name,
                engine='openpyxl'
            )
            csv_path = output_dir / f"{safe_name}.csv"
            df.to_csv(csv_path, index=False)
            return (sheet_name, True, "OK")
        except Exception as e2:
            return (sheet_name, False, f"Polars: {str(e)} | Pandas: {str(e2)}")


def convert_excel_file(
    excel_path: Path,
    output_base_dir: Path,
    max_workers: int = 4
) -> ConversionResult:
    """
    Convert all sheets in an Excel file to CSV files using parallel processing.

    Args:
        excel_path: Path to Excel file
        output_base_dir: Base directory for output
        max_workers: Maximum number of parallel workers for sheets

    Returns:
        ConversionResult with details about the conversion
    """
    start_time = time.time()
    excel_name = excel_path.stem  # filename without extension

    # Create output directory for this Excel file
    output_dir = output_base_dir / excel_name
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Get all sheet names from Excel file
        try:
            import polars as pl
            xls = pl.ExcelFile(str(excel_path))
            sheet_names = xls.sheet_names()
        except Exception:
            # Fall back to pandas
            import pandas as pd
            xls_file = pd.ExcelFile(str(excel_path), engine='openpyxl')
            sheet_names = xls_file.sheet_names

    except Exception as e:
        duration = time.time() - start_time
        return ConversionResult(
            excel_file=excel_path.name,
            success=False,
            sheets_converted=0,
            sheets_failed=0,
            sheets_skipped=0,
            message=f"Failed to read Excel file: {str(e)}",
            duration=duration
        )

    # Process sheets in parallel
    sheets_converted = 0
    sheets_failed = 0
    sheets_skipped = 0
    failed_sheets = []

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
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

    # Only consider successful if all sheets converted
    overall_success = sheets_failed == 0

    duration = time.time() - start_time

    if overall_success:
        msg = f"{sheets_converted} sheets converted in {duration:.2f}s"
    else:
        msg = f"{sheets_converted} converted, {sheets_failed} failed in {duration:.2f}s"
        if failed_sheets:
            msg += f" | Failed: {', '.join([f[0] for f in failed_sheets[:3]])}"

    return ConversionResult(
        excel_file=excel_path.name,
        success=overall_success,
        sheets_converted=sheets_converted,
        sheets_failed=sheets_failed,
        sheets_skipped=sheets_skipped,
        message=msg,
        duration=duration
    )


def should_skip_file(excel_path: Path, output_base_dir: Path) -> bool:
    """
    Check if Excel file has already been successfully converted.

    Args:
        excel_path: Path to Excel file
        output_base_dir: Base directory for output

    Returns:
        True if file should be skipped, False otherwise
    """
    output_dir = output_base_dir / excel_path.stem
    if not output_dir.exists():
        return False

    # Check if there are any CSV files in the output directory
    csv_files = list(output_dir.glob("*.csv"))
    return len(csv_files) > 0


def batch_convert_excel_to_csv(
    input_dir: Path,
    output_dir: Path,
    force: bool = False,
    delete_originals: bool = True,
    max_file_workers: int = None,
    max_sheet_workers: int = 4
) -> None:
    """
    Batch convert all Excel files in a directory to CSV format.

    Args:
        input_dir: Directory containing Excel files
        output_dir: Directory to save CSV files (organized by Excel filename)
        force: Force re-conversion of already converted files
        delete_originals: Delete original Excel files after successful conversion
        max_file_workers: Maximum workers for processing files (default: CPU count)
        max_sheet_workers: Maximum workers for processing sheets within a file
    """
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find all Excel files
    excel_files = sorted(input_dir.glob("*.xlsx")) + sorted(input_dir.glob("*.xls"))

    if not excel_files:
        print(f"No Excel files found in {input_dir}")
        return

    # Filter files based on skip detection
    files_to_process = []
    skipped_count = 0

    for excel_file in excel_files:
        if not force and should_skip_file(excel_file, output_dir):
            skipped_count += 1
        else:
            files_to_process.append(excel_file)

    print(f"🔄 Excel to CSV Batch Converter")
    print(f"{'=' * 60}")
    print(f"Input directory: {input_dir.absolute()}")
    print(f"Output directory: {output_dir.absolute()}")
    print(f"Total Excel files: {len(excel_files)}")
    print(f"Files to process: {len(files_to_process)}")
    print(f"Skipped (already converted): {skipped_count}")
    print(f"Delete originals: {delete_originals}")
    print(f"{'=' * 60}\n")

    if not files_to_process:
        print("✓ All files already converted!")
        return

    # Process files in parallel
    results: Dict[str, ConversionResult] = {}
    successful_files = []
    failed_files = []

    with ProcessPoolExecutor(max_workers=max_file_workers) as executor:
        futures = {
            executor.submit(convert_excel_file, excel_file, output_dir, max_sheet_workers): excel_file
            for excel_file in files_to_process
        }

        # Use tqdm for progress tracking
        with tqdm(total=len(futures), desc="Processing files", unit="file") as pbar:
            for future in as_completed(futures):
                excel_file = futures[future]
                try:
                    result = future.result()
                    results[str(excel_file)] = result

                    # Display result
                    status = "✓" if result.success else "✗"
                    print(f"  {status} {result.excel_file}: {result.message}")

                    if result.success:
                        successful_files.append(excel_file)
                    else:
                        failed_files.append(excel_file)

                except Exception as e:
                    print(f"  ✗ {excel_file.name}: Unexpected error - {str(e)}")
                    failed_files.append(excel_file)

                pbar.update(1)

    # Delete original Excel files only if conversion was successful
    deleted_count = 0

    if delete_originals and successful_files:
        print(f"\n🗑️  Cleaning up original Excel files...")
        for excel_file in successful_files:
            try:
                excel_file.unlink()
                deleted_count += 1
                print(f"  ✓ Deleted: {excel_file.name}")
            except Exception as e:
                print(f"  ✗ Could not delete {excel_file.name}: {str(e)}")

    # Print summary
    print(f"\n{'=' * 60}")
    print(f"📊 Conversion Summary")
    print(f"{'=' * 60}")
    print(f"Total files processed: {len(files_to_process)}")
    print(f"✓ Successful: {len(successful_files)}")
    print(f"✗ Failed: {len(failed_files)}")
    print(f"🗑️  Deleted: {deleted_count}")

    if failed_files:
        print(f"\nFailed files:")
        for excel_file in failed_files:
            print(f"  - {excel_file.name}")

    total_duration = sum(result.duration for result in results.values())
    print(f"\n⏱️  Total time: {total_duration:.2f}s")

    if successful_files:
        print(f"📁 CSV files saved to: {output_dir.absolute()}")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Batch convert Excel files to CSV with maximum performance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert all Excel files in data/raw/ to data/csv/
  python excel_to_csv.py

  # Convert with custom directories
  python excel_to_csv.py --input-dir ./excel_files --output-dir ./csv_output

  # Force re-conversion and keep original files
  python excel_to_csv.py --force --keep-originals

  # Adjust parallelism for more performance (use more workers)
  python excel_to_csv.py --file-workers 16 --sheet-workers 8
        """
    )

    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("data/raw"),
        help="Directory containing Excel files (default: data/raw)"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/csv"),
        help="Directory to save CSV files (default: data/csv)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-conversion of already converted files"
    )
    parser.add_argument(
        "--keep-originals",
        action="store_true",
        help="Do not delete original Excel files after conversion"
    )
    parser.add_argument(
        "--file-workers",
        type=int,
        default=None,
        help="Number of parallel workers for processing files (default: CPU count)"
    )
    parser.add_argument(
        "--sheet-workers",
        type=int,
        default=4,
        help="Number of parallel workers for processing sheets within a file (default: 4)"
    )

    args = parser.parse_args()

    try:
        batch_convert_excel_to_csv(
            input_dir=args.input_dir,
            output_dir=args.output_dir,
            force=args.force,
            delete_originals=not args.keep_originals,
            max_file_workers=args.file_workers,
            max_sheet_workers=args.sheet_workers
        )
    except KeyboardInterrupt:
        print("\n\n⚠ Conversion interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
