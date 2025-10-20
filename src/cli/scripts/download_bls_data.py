"""Download BLS OEWS data archives."""

from __future__ import annotations

import argparse
import logging
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import requests
from tqdm import tqdm

logger = logging.getLogger(__name__)


def get_year_suffix(year: int) -> str:
    return str(year)[-2:]


def build_download_url(year: int) -> str:
    suffix = get_year_suffix(year)
    return f"https://www.bls.gov/oes/special-requests/oesm{suffix}all.zip"


def check_existing_files(data_dir: Path, year: int) -> bool:
    suffix = get_year_suffix(year)
    patterns = [
        f"*{year}*.xlsx",
        f"*{year}*.xls",
        f"*{suffix}all.xlsx",
        f"*{suffix}all.xls",
    ]
    for pattern in patterns:
        if list(data_dir.glob(pattern)) or list(data_dir.glob(f"*/{pattern}")):
            return True
    return False


def download_file(url: str, dest_path: Path) -> bool:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/91.0.4472.124 Safari/537.36"
        )
    }
    try:
        response = requests.get(url, stream=True, timeout=30, headers=headers)
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.error("Download failed for %s: %s", url, exc)
        return False

    total_size = int(response.headers.get("content-length", 0))
    with dest_path.open("wb") as fh:
        with tqdm(total=total_size, unit="B", unit_scale=True, desc=dest_path.name, leave=False) as progress:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    fh.write(chunk)
                    progress.update(len(chunk))
    return True


def extract_zip(zip_path: Path, extract_dir: Path) -> bool:
    try:
        with zipfile.ZipFile(zip_path, "r") as archive:
            for member in tqdm(archive.namelist(), desc="Extracting", leave=False):
                if member.endswith("/"):
                    continue
                filename = Path(member).name
                destination = extract_dir / filename
                archive.extract(member, extract_dir)
                extracted_path = extract_dir / member
                if extracted_path != destination:
                    destination.write_bytes(extracted_path.read_bytes())
                    extracted_path.unlink()
        return True
    except zipfile.BadZipFile as exc:
        logger.error("Invalid ZIP file %s: %s", zip_path, exc)
    except Exception as exc:  # pragma: no cover - best effort logging
        logger.error("Extraction failed for %s: %s", zip_path, exc)
    return False


def download_year(year: int, data_dir: Path, force: bool = False) -> Tuple[bool, str]:
    if not force and check_existing_files(data_dir, year):
        return True, f"Year {year}: already downloaded"

    url = build_download_url(year)
    zip_filename = f"oesm{get_year_suffix(year)}all.zip"
    zip_path = data_dir / zip_filename

    logger.info("Downloading %s", url)
    if not download_file(url, zip_path):
        return False, f"Year {year}: download failed"

    logger.info("Extracting %s", zip_path)
    if not extract_zip(zip_path, data_dir):
        return False, f"Year {year}: extraction failed"

    try:
        zip_path.unlink()
    except Exception as exc:  # pragma: no cover - best effort logging
        logger.warning("Could not delete %s: %s", zip_path, exc)

    return True, f"Year {year}: downloaded"


def download_bls_data(start_year: int, end_year: int, data_dir: Path, force: bool = False) -> Dict[str, List[int]]:
    data_dir.mkdir(parents=True, exist_ok=True)

    years = range(start_year, end_year + 1)
    results: Dict[str, List[int]] = {"success": [], "failed": [], "skipped": []}

    logger.info("Downloading OEWS data %s-%s into %s", start_year, end_year, data_dir)
    for year in years:
        success, message = download_year(year, data_dir, force)
        logger.info(message)
        if "already" in message.lower():
            results["skipped"].append(year)
        elif success:
            results["success"].append(year)
        else:
            results["failed"].append(year)

    logger.info(
        "Summary: %s ok, %s skipped, %s failed",
        len(results["success"]),
        len(results["skipped"]),
        len(results["failed"]),
    )
    if results["failed"]:
        logger.warning("Failed years: %s", results["failed"])

    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    current_year = datetime.now().year
    parser.add_argument("--start-year", type=int, default=2011)
    parser.add_argument("--end-year", type=int, default=current_year)
    parser.add_argument("--data-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:  # pragma: no cover - CLI entry point
    args = parse_args()
    if args.start_year > args.end_year:
        raise SystemExit("start-year must be <= end-year")
    if args.start_year < 2011:
        logger.warning("BLS OES data may not be available before 2011")

    download_bls_data(args.start_year, args.end_year, args.data_dir, args.force)
    return 0


if __name__ == "__main__":  # pragma: no cover - script entrypoint
    raise SystemExit(main())
