from click.testing import CliRunner

import pytest


def test_cli_exposes_expected_commands():
    from src.cli.main import cli  # noqa: PLC0415

    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])

    assert result.exit_code == 0
    for command_name in ("analyze", "standardize", "migrate", "pipeline", "download-data", "excel-to-csv"):
        assert command_name in result.output, f"{command_name} not listed in CLI help output"


@pytest.mark.parametrize(
    "command",
    [
        ("analyze",),
        ("standardize",),
        ("migrate",),
        ("pipeline",),
        ("download-data",),
        ("excel-to-csv",),
    ],
)
def test_each_command_provides_help(command):
    from src.cli.main import cli  # noqa: PLC0415

    runner = CliRunner()
    result = runner.invoke(cli, [*command, "--help"])

    assert result.exit_code == 0
