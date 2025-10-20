#!/usr/bin/env python
"""
BLS OES Data Downloader

Downloads Occupational Employment and Wage Statistics (OES) data from the Bureau
of Labor Statistics website. Automatically checks for existing downloads and only
downloads missing years.

URL Pattern: https://www.bls.gov/oes/special-requests/oesmXXall.zip
where XX = last 2 digits of the year (e.g., 24 for 2024)

Data is available from 2011 onwards.
"""

import argparse
import sys
import zipfile
from pathlib import Path
from typing import List, Tuple
from datetime import datetime

import requests
from tqdm import tqdm


def get_year_suffix(year: int) -> str:
    """
    Convert a 4-digit year to 2-digit suffix for BLS URL.

    Args:
        year: 4-digit year (e.g., 2024)

    Returns:
        2-digit year suffix (e.g., "24")
    """
    return str(year)[-2:]


def build_download_url(year: int) -> str:
    """
    Build the BLS download URL for a given year.

    Args:
        year: 4-digit year

    Returns:
        Full download URL
    """
    suffix = get_year_suffix(year)
    return f"https://www.bls.gov/oes/special-requests/oesm{suffix}all.zip"


def check_existing_files(data_dir: Path, year: int) -> bool:
    """
    Check if data for a given year already exists in the data directory.

    Args:
        data_dir: Directory where data files are stored
        year: Year to check for

    Returns:
        True if data already exists, False otherwise
    """
    # Look for Excel files that might contain data for this year
    # Common patterns: all_data_M_2024.xlsx, oesm24all.xlsx, etc.
    suffix = get_year_suffix(year)

    patterns = [
        f"*{year}*.xlsx",
        f"*{year}*.xls",
        f"*{suffix}all.xlsx",
        f"*{suffix}all.xls",
    ]

    for pattern in patterns:
        # Check both in root data_dir and in subdirectories
        if list(data_dir.glob(pattern)) or list(data_dir.glob(f"*/{pattern}")):
            return True

    return False


def download_file(url: str, dest_path: Path) -> bool:
    """
    Download a file from a URL with progress bar.

    Args:
        url: URL to download from
        dest_path: Destination file path

    Returns:
        True if successful, False otherwise
    """
    try:
        # Add headers to avoid 403 errors from BLS website
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, stream=True, timeout=30, headers=headers)
        response.raise_for_status()

        total_size = int(response.headers.get('content-length', 0))

        with open(dest_path, 'wb') as f:
            with tqdm(total=total_size, unit='B', unit_scale=True,
                     desc=dest_path.name, leave=False) as pbar:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))

        return True

    except requests.exceptions.RequestException as e:
        print(f"  ✗ Download failed: {e}")
        if dest_path.exists():
            dest_path.unlink()  # Clean up partial download
        return False


def extract_zip(zip_path: Path, extract_dir: Path) -> bool:
    """
    Extract a ZIP file to a directory, flattening the structure.

    Args:
        zip_path: Path to ZIP file
        extract_dir: Directory to extract to

    Returns:
        True if successful, False otherwise
    """
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Get list of files to extract
            file_list = zip_ref.namelist()

            # Extract with progress bar, flattening directory structure
            for file in tqdm(file_list, desc="Extracting", leave=False):
                # Skip directories
                if file.endswith('/'):
                    continue

                # Get just the filename without the path
                filename = Path(file).name

                # Extract to temp location then move to final location
                source = zip_ref.extract(file, extract_dir)
                dest = extract_dir / filename

                # Move file if it's in a subdirectory
                if Path(source) != dest:
                    Path(source).rename(dest)

            # Clean up any empty directories created during extraction
            for item in extract_dir.iterdir():
                if item.is_dir() and not any(item.iterdir()):
                    item.rmdir()

        return True

    except zipfile.BadZipFile as e:
        print(f"  ✗ Extraction failed: Invalid ZIP file - {e}")
        return False
    except Exception as e:
        print(f"  ✗ Extraction failed: {e}")
        return False


def download_year(year: int, data_dir: Path, force: bool = False) -> Tuple[bool, str]:
    """
    Download and extract BLS OES data for a specific year.

    Args:
        year: Year to download
        data_dir: Directory to save data
        force: If True, re-download even if data exists

    Returns:
        Tuple of (success, message)
    """
    # Check if already downloaded
    if not force and check_existing_files(data_dir, year):
        return (True, f"Year {year}: Already downloaded (skipped)")

    url = build_download_url(year)
    zip_filename = f"oesm{get_year_suffix(year)}all.zip"
    zip_path = data_dir / zip_filename

    print(f"\n  Downloading {year}...")
    print(f"  URL: {url}")

    # Download ZIP file
    if not download_file(url, zip_path):
        return (False, f"Year {year}: Download failed")

    # Extract ZIP file
    print(f"  Extracting...")
    if not extract_zip(zip_path, data_dir):
        return (False, f"Year {year}: Extraction failed")

    # Delete ZIP file after successful extraction
    try:
        zip_path.unlink()
        print(f"  ✓ Cleaned up ZIP file")
    except Exception as e:
        print(f"  ⚠ Warning: Could not delete ZIP file - {e}")

    return (True, f"Year {year}: Successfully downloaded and extracted")


def download_bls_data(
    start_year: int,
    end_year: int,
    data_dir: Path,
    force: bool = False
) -> None:
    """
    Download BLS OES data for a range of years.

    Args:
        start_year: First year to download
        end_year: Last year to download
        data_dir: Directory to save data files
        force: If True, re-download even if data exists
    """
    # Ensure data directory exists
    data_dir.mkdir(parents=True, exist_ok=True)

    years = range(start_year, end_year + 1)
    results = {"success": [], "failed": [], "skipped": []}

    print(f"🔽 BLS OES Data Downloader")
    print(f"=" * 50)
    print(f"Year range: {start_year}-{end_year} ({len(years)} years)")
    print(f"Data directory: {data_dir.absolute()}")
    print(f"Force re-download: {force}")
    print(f"=" * 50)

    for year in years:
        success, message = download_year(year, data_dir, force)

        if "skipped" in message.lower():
            results["skipped"].append(year)
            print(f"  ⊘ {message}")
        elif success:
            results["success"].append(year)
            print(f"  ✓ {message}")
        else:
            results["failed"].append(year)
            print(f"  ✗ {message}")

    # Print summary
    print(f"\n{'=' * 50}")
    print(f"📊 Download Summary")
    print(f"=" * 50)
    print(f"Total years: {len(years)}")
    print(f"✓ Successfully downloaded: {len(results['success'])}")
    print(f"⊘ Skipped (already exist): {len(results['skipped'])}")
    print(f"✗ Failed: {len(results['failed'])}")

    if results['success']:
        print(f"\nSuccessfully downloaded: {results['success']}")

    if results['failed']:
        print(f"\nFailed downloads: {results['failed']}")
        print(f"Note: Some years may not be available on the BLS website.")

    print(f"\n📁 Data saved to: {data_dir.absolute()}")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Download BLS OES data for multiple years",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download all years from 2011 to current year
  python download_bls_data.py

  # Download specific year range
  python download_bls_data.py --start-year 2015 --end-year 2020

  # Force re-download even if files exist
  python download_bls_data.py --force

  # Custom data directory
  python download_bls_data.py --data-dir /path/to/data
        """
    )

    current_year = datetime.now().year

    parser.add_argument(
        "--start-year",
        type=int,
        default=2011,
        help="First year to download (default: 2011)"
    )
    parser.add_argument(
        "--end-year",
        type=int,
        default=current_year,
        help=f"Last year to download (default: {current_year})"
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data/raw"),
        help="Directory to save downloaded files (default: data/raw)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-download even if files already exist"
    )

    args = parser.parse_args()

    # Validate year range
    if args.start_year > args.end_year:
        print(f"Error: start-year ({args.start_year}) must be <= end-year ({args.end_year})",
              file=sys.stderr)
        sys.exit(1)

    if args.start_year < 2011:
        print(f"Warning: BLS OES data may not be available before 2011",
              file=sys.stderr)

    try:
        download_bls_data(
            args.start_year,
            args.end_year,
            args.data_dir,
            args.force
        )
    except KeyboardInterrupt:
        print("\n\n⚠ Download interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
