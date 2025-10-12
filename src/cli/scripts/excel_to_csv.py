#!/usr/bin/env env python
"""
Fast Excel to CSV converter using parallel processing.
Handles large Excel files efficiently by processing sheets in parallel.
"""

import argparse
import sys
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
import pandas as pd


def convert_sheet(excel_path: str, sheet_name: str, output_dir: Path) -> tuple[str, bool, str]:
    """
    Convert a single Excel sheet to CSV.

    Args:
        excel_path: Path to Excel file
        sheet_name: Name of sheet to convert
        output_dir: Directory to save CSV files

    Returns:
        Tuple of (sheet_name, success, message)
    """
    try:
        df = pd.read_excel(excel_path, sheet_name=sheet_name, engine='openpyxl')

        # Create safe filename from sheet name
        safe_name = "".join(c if c.isalnum() or c in (' ', '_', '-') else '_' for c in sheet_name)
        csv_path = output_dir / f"{safe_name}.csv"

        df.to_csv(csv_path, index=False)
        return (sheet_name, True, f"Converted to {csv_path}")
    except Exception as e:
        return (sheet_name, False, f"Error: {str(e)}")


def convert_excel_to_csv(excel_path: Path, output_dir: Path = None, max_workers: int = None) -> None:
    """
    Convert all sheets in an Excel file to CSV files using parallel processing.

    Args:
        excel_path: Path to Excel file
        output_dir: Directory to save CSV files (defaults to same dir as Excel file)
        max_workers: Maximum number of parallel workers (defaults to CPU count)
    """
    if not excel_path.exists():
        print(f"Error: File not found: {excel_path}", file=sys.stderr)
        sys.exit(1)

    if output_dir is None:
        output_dir = excel_path.parent

    output_dir.mkdir(parents=True, exist_ok=True)

    # Get all sheet names
    print(f"Reading {excel_path}...")
    excel_file = pd.ExcelFile(excel_path, engine='openpyxl')
    sheet_names = excel_file.sheet_names
    print(f"Found {len(sheet_names)} sheet(s)")

    # Process sheets in parallel
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(convert_sheet, str(excel_path), sheet_name, output_dir): sheet_name
            for sheet_name in sheet_names
        }

        for future in as_completed(futures):
            sheet_name, success, message = future.result()
            status = "[OK]" if success else "[FAIL]"
            print(f"{status} {sheet_name}: {message}")

    print(f"\nDone! CSV files saved to: {output_dir}")


def main():
    parser = argparse.ArgumentParser(
        description="Convert Excel files to CSV with parallel processing for speed"
    )
    parser.add_argument(
        "excel_file",
        type=Path,
        help="Path to Excel file (.xlsx or .xls)"
    )
    parser.add_argument(
        "-o", "--output-dir",
        type=Path,
        help="Output directory for CSV files (default: same as Excel file)"
    )
    parser.add_argument(
        "-w", "--workers",
        type=int,
        help="Number of parallel workers (default: CPU count)"
    )

    args = parser.parse_args()

    convert_excel_to_csv(args.excel_file, args.output_dir, args.workers)


if __name__ == "__main__":
    main()
