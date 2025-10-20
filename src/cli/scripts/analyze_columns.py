"""Analyze OEWS CSV column layouts and build an inventory for downstream migration."""

from __future__ import annotations

import argparse
import json
import logging
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence

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

DEFAULT_SAMPLE_ROWS = 200


@dataclass
class ColumnSample:
    raw_name: str
    normalized_name: str
    example_values: List[str] = field(default_factory=list)


@dataclass
class FileInventory:
    file_path: str
    folder: str
    year: Optional[int]
    size_bytes: int
    column_count: int
    row_samples: int
    columns: List[ColumnSample]
    suppression_tokens: List[str]


def summarize_file(csv_path: Path, sample_rows: int) -> Optional[FileInventory]:
    header, samples = read_header_and_sample(csv_path, sample_rows)
    if not header:
        logger.warning("Skipping empty or malformed file: %s", csv_path)
        return None

    normalized_columns = [
        ColumnSample(
            raw_name=col,
            normalized_name=normalize_header(col),
            example_values=[
                row[idx] for row in samples[:5] if idx < len(row) and row[idx]
            ],
        )
        for idx, col in enumerate(header)
    ]

    suppression_tokens = sorted(
        {
            value
            for col_idx, _ in enumerate(normalized_columns)
            for value in (row[col_idx] for row in samples if col_idx < len(row))
            if value in COMMON_SUPPRESSION_VALUES
        }
    )

    return FileInventory(
        file_path=str(csv_path),
        folder=csv_path.parent.name,
        year=detect_year(csv_path),
        size_bytes=csv_path.stat().st_size,
        column_count=len(header),
        row_samples=len(samples),
        columns=normalized_columns,
        suppression_tokens=suppression_tokens,
    )


def build_variants(
    inventories: Sequence[FileInventory],
) -> Dict[str, Dict[str, int]]:
    variants: Dict[str, Counter] = defaultdict(Counter)
    for file_info in inventories:
        for column in file_info.columns:
            if not column.normalized_name:
                continue
            variants[column.normalized_name][column.raw_name] += 1
    return {key: dict(counter) for key, counter in variants.items()}


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)


def run(root: Path, sample_rows: int, output_dir: Path) -> int:
    inventories: List[FileInventory] = []
    for csv_file in iter_data_csv_files(root):
        file_inventory = summarize_file(csv_file, sample_rows)
        if file_inventory is None:
            continue
        inventories.append(file_inventory)

    if not inventories:
        logger.warning("No data CSV files found beneath %s", root)
        return 1

    column_variants = build_variants(inventories)

    inventory_payload = [asdict(inv) for inv in inventories]
    variants_payload = {key: variants for key, variants in column_variants.items()}

    inventory_path = output_dir / "column_inventory.json"
    variants_path = output_dir / "column_variants.json"

    write_json(inventory_path, inventory_payload)
    write_json(variants_path, variants_payload)

    logger.info("Analyzed %s data files under %s", len(inventories), root)
    logger.info("Inventory -> %s", inventory_path)
    logger.info("Column variants -> %s", variants_path)
    logger.info("Unique normalized columns: %s", len(column_variants))

    most_common = sorted(
        column_variants.items(), key=lambda item: (-sum(item[1].values()), item[0])
    )[:10]
    for name, variants in most_common:
        total = sum(variants.values())
        sample_variant = max(variants.items(), key=lambda item: item[1])[0]
        logger.debug("%s (%s files) e.g. %s", name, total, sample_variant)

    uncommon = [
        (name, variants)
        for name, variants in column_variants.items()
        if sum(variants.values()) == 1
    ]
    if uncommon:
        for name, variants in sorted(uncommon, key=lambda item: item[0])[:10]:
            variant = list(variants.keys())[0]
            logger.debug("Rare column %s -> %s", name, variant)

    return 0


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
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
        help="Directory where JSON artifacts will be written.",
    )
    parser.add_argument(
        "--sample-rows",
        type=int,
        default=DEFAULT_SAMPLE_ROWS,
        help="Number of data rows to sample per file for diagnostics.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":  # pragma: no cover - script entrypoint
    args = parse_args()
    raise SystemExit(run(args.root, args.sample_rows, args.output_dir))
