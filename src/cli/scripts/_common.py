"""Utility helpers shared across OEWS CLI scripts."""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Iterable, Optional, Sequence, Tuple

DEFAULT_DATA_ROOT = Path("data/csv")
DEFAULT_OUTPUT_DIR = Path("data")

SKIP_KEYWORDS = (
    "field",
    "description",
    "filler",
    "updatetime",
    "__macosx",
)

HEADER_FOOTNOTE_CHARS = {
    "¹",
    "†",
    "*",
}

COMMON_SUPPRESSION_VALUES = {"", "#", "**", "*", "~"}


def normalize_header(name: str) -> str:
    """Normalize raw header names to a lowercase snake-case key."""
    if not name:
        return ""
    cleaned = name.strip()
    for footnote in HEADER_FOOTNOTE_CHARS:
        cleaned = cleaned.replace(footnote, "")

    cleaned = re.sub(r"[\s]+", "_", cleaned)
    cleaned = cleaned.replace("__", "_")
    cleaned = re.sub(r"[^0-9a-zA-Z_]", "", cleaned)
    cleaned = cleaned.strip("_")
    return cleaned.lower()


def detect_year(path: Path) -> Optional[int]:
    match = re.search(r"(20\d{2})", path.name)
    if not match:
        match = re.search(r"(20\d{2})", str(path.parent))
    return int(match.group(1)) if match else None


def iter_data_csv_files(root: Path) -> Iterable[Path]:
    for folder in sorted(root.glob("*")):
        if not folder.is_dir():
            continue
        for csv_path in sorted(folder.glob("*.csv")):
            lower_name = csv_path.name.lower()
            if any(keyword in lower_name for keyword in SKIP_KEYWORDS):
                continue
            if csv_path.stat().st_size == 0:
                continue
            yield csv_path


def read_header_and_sample(
    csv_path: Path, sample_rows: int
) -> Tuple[Sequence[str], list[list[str]]]:
    with csv_path.open(newline="", encoding="utf-8", errors="ignore") as f:
        reader = csv.reader(f)
        header: Optional[Sequence[str]] = None
        samples: list[list[str]] = []
        for row in reader:
            if header is None:
                header = row
                if not header:
                    return [], []
                continue
            if sample_rows and len(samples) >= sample_rows:
                break
            samples.append(row)
        if header is None:
            return [], []
        return list(header), samples
