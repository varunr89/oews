from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import sys

import pytest


def test_sanitize_sheet_name_handles_problematic_characters():
    from src.cli.scripts.excel_to_csv import sanitize_sheet_name  # noqa: PLC0415

    assert sanitize_sheet_name("Sheet 1") == "Sheet_1"
    assert sanitize_sheet_name("weird/\\name*") == "weird__name_"
    assert sanitize_sheet_name("  spaced  ") == "spaced"


def test_convert_sheet_to_csv_falls_back_to_pandas(tmp_path, monkeypatch):
    from src.cli.scripts import excel_to_csv  # noqa: PLC0415

    excel_path = tmp_path / "input.xlsx"
    excel_path.write_text("dummy excel placeholder")

    def fake_polars_loader(*_args, **_kwargs):
        raise RuntimeError("polars exploded")

    captured = {}

    class DummyFrame:
        def to_csv(self, path: Path, index: bool) -> None:  # noqa: ARG002
            Path(path).write_text("ok")
            captured["written"] = True

    def fake_pandas_loader(*_args, **_kwargs):
        return DummyFrame()

    monkeypatch.setattr(excel_to_csv, "_read_sheet_with_polars", fake_polars_loader)
    monkeypatch.setattr(excel_to_csv, "_read_sheet_with_pandas", fake_pandas_loader)

    _, success, message = excel_to_csv.convert_sheet_to_csv(
        excel_path=str(excel_path),
        sheet_name="Sheet1",
        output_dir=tmp_path,
    )

    assert success is True
    assert message == "OK"
    assert captured.get("written") is True


def test_batch_convert_no_files(tmp_path, caplog):
    from src.cli.scripts import excel_to_csv  # noqa: PLC0415

    caplog.set_level("INFO")
    results = excel_to_csv.batch_convert_excel_to_csv(
        input_dir=tmp_path,
        output_dir=tmp_path,
        force=False,
        delete_originals=False,
    )

    assert results == {}
    assert "No Excel files found" in caplog.text


def test_convert_excel_file_with_stubbed_executor(tmp_path, monkeypatch):
    from src.cli.scripts import excel_to_csv  # noqa: PLC0415

    excel_path = tmp_path / "workbook.xlsx"
    excel_path.write_text("placeholder")

    monkeypatch.setattr(
        excel_to_csv,
        "_discover_sheet_names",
        lambda _path: ["Sheet1", "Sheet2"],
    )

    def fake_convert(excel_path: str, sheet_name: str, output_dir: Path, pandas_loader=None):
        (output_dir / f"{sheet_name}.csv").write_text("data")
        return sheet_name, True, "OK"

    monkeypatch.setattr(excel_to_csv, "convert_sheet_to_csv", fake_convert)

    class DummyFuture:
        def __init__(self, value):
            self._value = value

        def result(self):
            return self._value

    class DummyExecutor:
        def __init__(self, *args, **kwargs):
            self._futures = []

        def submit(self, fn, *args, **kwargs):
            future = DummyFuture(fn(*args, **kwargs))
            self._futures.append(future)
            return future

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(excel_to_csv, "ProcessPoolExecutor", DummyExecutor)
    monkeypatch.setattr(excel_to_csv, "as_completed", lambda futures: futures)

    result = excel_to_csv.convert_excel_file(excel_path, tmp_path, max_workers=1)

    assert result.success is True
    assert result.sheets_converted == 2


def test_batch_convert_processes_files(tmp_path, monkeypatch):
    from src.cli.scripts import excel_to_csv  # noqa: PLC0415

    excel_file = tmp_path / "book.xlsx"
    excel_file.write_text("placeholder")

    conversion_result = excel_to_csv.ConversionResult(
        excel_file=excel_file.name,
        success=True,
        sheets_converted=1,
        sheets_failed=0,
        sheets_skipped=0,
        message="ok",
        duration=0.1,
    )

    monkeypatch.setattr(
        excel_to_csv,
        "convert_excel_file",
        lambda excel_path, output_dir, max_sheet_workers=None: conversion_result,
    )

    class DummyFuture(SimpleNamespace):
        def result(self):
            return self.value

        def __hash__(self):
            return id(self)

    class DummyExecutor:
        def __init__(self, *args, **kwargs):
            pass

        def submit(self, fn, *args, **kwargs):
            return DummyFuture(value=fn(*args, **kwargs))

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(excel_to_csv, "ProcessPoolExecutor", DummyExecutor)
    monkeypatch.setattr(excel_to_csv, "as_completed", lambda futures: futures)

    results = excel_to_csv.batch_convert_excel_to_csv(
        input_dir=tmp_path,
        output_dir=tmp_path,
        force=False,
        delete_originals=True,
    )

    assert results[excel_file.name].success is True


def test_convert_excel_file_reports_failure(tmp_path, monkeypatch):
    from src.cli.scripts import excel_to_csv  # noqa: PLC0415

    excel_path = tmp_path / "broken.xlsx"
    excel_path.write_text("placeholder")

    def explode(_path):
        raise RuntimeError("kaput")

    monkeypatch.setattr(excel_to_csv, "_discover_sheet_names", explode)

    result = excel_to_csv.convert_excel_file(excel_path, tmp_path, max_workers=1)

    assert result.success is False
    assert "Failed to read Excel file" in result.message


def test_read_sheet_with_polars_fallback(monkeypatch):
    from src.cli.scripts import excel_to_csv  # noqa: PLC0415

    if excel_to_csv.pl is None:  # pragma: no cover - environment guard
        pytest.skip("polars not available")

    calls = []

    class DummyFrame:
        pass

    def fake_read_excel(*args, **kwargs):
        calls.append(kwargs.get("engine"))
        if kwargs.get("engine") == "fastexcel":
            raise ValueError("boom")
        return DummyFrame()

    monkeypatch.setattr(excel_to_csv.pl, "read_excel", fake_read_excel)

    frame = excel_to_csv._read_sheet_with_polars("workbook.xlsx", "Sheet1")

    assert isinstance(frame, DummyFrame)
    assert calls == ["fastexcel", None]


def test_read_sheet_with_pandas(monkeypatch):
    from src.cli.scripts import excel_to_csv  # noqa: PLC0415

    dummy_module = SimpleNamespace(read_excel=lambda *args, **kwargs: "frame")
    monkeypatch.setitem(sys.modules, "pandas", dummy_module)

    frame = excel_to_csv._read_sheet_with_pandas("workbook.xlsx", "Sheet1")

    assert frame == "frame"


def test_batch_convert_skips_existing(tmp_path, monkeypatch):
    from src.cli.scripts import excel_to_csv  # noqa: PLC0415

    excel_file = tmp_path / "existing.xlsx"
    excel_file.write_text("placeholder")
    output_dir = tmp_path
    (output_dir / "existing").mkdir()
    (output_dir / "existing" / "Sheet1.csv").write_text("done")

    monkeypatch.setattr(excel_to_csv, "should_skip_file", lambda *_args: True)

    class DummyExecutor:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def submit(self, *args, **kwargs):  # pragma: no cover - not used
            raise AssertionError("submit should not be called when skipping")

    monkeypatch.setattr(excel_to_csv, "ProcessPoolExecutor", DummyExecutor)

    results = excel_to_csv.batch_convert_excel_to_csv(
        input_dir=tmp_path,
        output_dir=output_dir,
        force=False,
        delete_originals=False,
    )

    assert results == {}


def test_parse_args_accepts_cli_options(monkeypatch):
    from src.cli.scripts import excel_to_csv  # noqa: PLC0415

    argv = [
        "excel_to_csv",
        "--input-dir",
        "input",
        "--output-dir",
        "out",
        "--force",
        "--keep-originals",
        "--file-workers",
        "2",
        "--sheet-workers",
        "3",
    ]
    monkeypatch.setattr(sys, "argv", argv)

    args = excel_to_csv.parse_args()

    assert args.force is True
    assert args.keep_originals is True
    assert args.file_workers == 2
    assert args.sheet_workers == 3
