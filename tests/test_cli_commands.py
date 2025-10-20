from __future__ import annotations

from click.testing import CliRunner

from src.cli import main as cli_main


def test_cli_commands_delegate(monkeypatch):
    called = {}

    def mark(name):
        def _inner(*_args, **_kwargs):
            called[name] = called.get(name, 0) + 1
            return 0

        return _inner

    monkeypatch.setattr(cli_main.analyze_columns, "run", mark("analyze"))
    monkeypatch.setattr(cli_main.standardize_csv_columns, "run", mark("standardize"))
    monkeypatch.setattr(cli_main.migrate_csv_to_db, "run", mark("migrate"))
    monkeypatch.setattr(cli_main.download_bls_data, "download_bls_data", mark("download"))
    monkeypatch.setattr(cli_main.excel_to_csv, "batch_convert_excel_to_csv", mark("excel"))

    runner = CliRunner()
    runner.invoke(cli_main.cli, ["analyze"])
    runner.invoke(cli_main.cli, ["standardize"])
    runner.invoke(cli_main.cli, ["migrate"])
    runner.invoke(cli_main.cli, ["pipeline"])
    runner.invoke(cli_main.cli, ["download-data", "--end-year", "2011"])
    runner.invoke(cli_main.cli, ["excel-to-csv"])

    assert called["analyze"] == 2  # pipeline invokes analyze as well
    assert called["standardize"] == 2
    assert called["migrate"] == 2
    assert called["download"] == 1
    assert called["excel"] == 1
