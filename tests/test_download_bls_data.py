from __future__ import annotations

import io
import zipfile

from src.cli.scripts import download_bls_data


class _FakeResponse:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self.headers = {"content-length": str(len(payload))}

    def raise_for_status(self) -> None:  # noqa: D401 - no-op
        return

    def iter_content(self, chunk_size: int):  # noqa: D401 - generator
        yield self.payload


def test_download_year_with_mocked_request(tmp_path, monkeypatch):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("sample.xlsx", "dummy")
    buffer.seek(0)

    monkeypatch.setattr(
        download_bls_data.requests,
        "get",
        lambda *args, **kwargs: _FakeResponse(buffer.getvalue()),
    )

    success, message = download_bls_data.download_year(2024, tmp_path, force=True)
    assert success is True
    assert "downloaded" in message
    assert (tmp_path / "sample.xlsx").exists()


def test_download_year_skips_when_exists(tmp_path):
    from src.cli.scripts import download_bls_data  # noqa: PLC0415

    existing = tmp_path / "2024_report.xlsx"
    existing.write_text("present")

    success, message = download_bls_data.download_year(2024, tmp_path, force=False)

    assert success is True
    assert "already" in message.lower()


def test_download_year_handles_request_error(tmp_path, monkeypatch):
    from src.cli.scripts import download_bls_data  # noqa: PLC0415
    from requests import RequestException

    def fake_get(*_args, **_kwargs):
        raise RequestException("boom")

    monkeypatch.setattr(download_bls_data.requests, "get", fake_get)

    success, message = download_bls_data.download_year(2024, tmp_path, force=True)

    assert success is False
    assert "failed" in message.lower()


def test_extract_zip_flattens_nested_members(tmp_path):
    from src.cli.scripts import download_bls_data  # noqa: PLC0415

    zip_path = tmp_path / "archive.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("nested/sample.xlsx", "data")

    extract_dir = tmp_path / "extract"
    extract_dir.mkdir()

    assert download_bls_data.extract_zip(zip_path, extract_dir) is True
    assert (extract_dir / "sample.xlsx").exists()


def test_download_bls_data_summary(monkeypatch, tmp_path):
    from src.cli.scripts import download_bls_data  # noqa: PLC0415

    calls = {"count": 0}

    def fake_download_year(year, *_args, **_kwargs):
        calls["count"] += 1
        if year % 2 == 0:
            return True, f"Year {year}: downloaded"
        return False, f"Year {year}: download failed"

    monkeypatch.setattr(download_bls_data, "download_year", fake_download_year)

    results = download_bls_data.download_bls_data(2020, 2022, tmp_path, force=False)

    assert calls["count"] == 3
    assert results["success"] == [2020, 2022]
    assert results["failed"] == [2021]
