from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from src.cli.scripts import _common, analyze_columns, migrate_csv_to_db, standardize_csv_columns


def _write_sample_csv(csv_dir: Path) -> Path:
    csv_dir.mkdir(parents=True, exist_ok=True)
    csv_path = csv_dir / "sample.csv"
    csv_path.write_text(
        "AREA,AREA_TITLE,OCC_CODE,OCC_TITLE,TOT_EMP\n"
        "000000,Test Area,11-1011,Manager,42\n"
    )
    return csv_path


def test_end_to_end_standardize_and_migrate(tmp_path, caplog):
    caplog.set_level(logging.INFO)

    raw_root = tmp_path / "csv"
    sample_csv = _write_sample_csv(raw_root / "2024")

    analyze_status = analyze_columns.run(raw_root, sample_rows=10, output_dir=tmp_path)
    assert analyze_status == 0
    assert (tmp_path / "column_inventory.json").exists()
    assert (tmp_path / "column_variants.json").exists()

    standardize_status = standardize_csv_columns.run(raw_root, tmp_path, workers=1)
    assert standardize_status == 0
    parquet_path = tmp_path / standardize_csv_columns.OUTPUT_SUBDIR / "2024" / f"{sample_csv.stem}.parquet"
    assert parquet_path.exists()

    migrate_csv_to_db.run(tmp_path, tmp_path, workers=1, batch_size=10)
    db_path = tmp_path / migrate_csv_to_db.DB_FILENAME
    assert db_path.exists()

    # Verify migrated data is present
    with sqlite3.connect(db_path) as conn:
        cur = conn.execute("SELECT COUNT(*) FROM oews_data")
        assert cur.fetchone()[0] == 1


def test_iter_data_csv_files_skips_non_data(tmp_path):
    data_root = tmp_path
    (data_root / "2024").mkdir()
    (data_root / "2024" / "data.csv").write_text("col\n1\n")
    (data_root / "2024" / "filler_description.csv").write_text("")
    (data_root / "2024" / "empty.csv").touch()

    files = list(_common.iter_data_csv_files(data_root))
    assert len(files) == 1
    assert files[0].name == "data.csv"

    normalized = _common.normalize_header("Area Title*")
    assert normalized == "area_title"


def test_build_rename_plan_handles_duplicates():
    rename_map, duplicates, drops = standardize_csv_columns.build_rename_plan([
        "Area",
        "area",
        "OCC Title",
    ])

    assert rename_map["Area"] == "AREA"
    assert duplicates["AREA"] == ["area"]
    assert "area" in drops
