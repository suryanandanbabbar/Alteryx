"""CLI integration tests using Click's CliRunner."""

import json
from pathlib import Path
from click.testing import CliRunner

from awa.cli.main import cli


FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


class TestCLI:
    """Test CLI commands."""

    def test_cli_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "analyze" in result.output
        assert "inspect" in result.output

    def test_cli_inspect(self):
        runner = CliRunner()
        fixture = FIXTURES_DIR / "basic" / "simple_filter.yxmd"
        result = runner.invoke(cli, ["inspect", str(fixture)])
        assert result.exit_code == 0
        assert "Workflow: simple_filter" in result.output
        assert "Tools: 3" in result.output
        assert "Connections: 2" in result.output
        assert "DbFileInput" in result.output
        assert "Filter" in result.output
        assert "DbFileOutput" in result.output

    def test_cli_analyze(self, tmp_path):
        runner = CliRunner()
        fixture = FIXTURES_DIR / "basic" / "simple_filter.yxmd"
        out_dir = tmp_path / "cli_analysis"
        result = runner.invoke(cli, ["analyze", str(fixture), "--output", str(out_dir)])
        assert result.exit_code == 0
        assert "Analyzing:" in result.output
        assert "Done." in result.output

        assert (out_dir / "workflow.json").exists()
        assert (out_dir / "workflow.py").exists()
        assert (out_dir / "workflow.md").exists()
        assert (out_dir / "diagnostics.json").exists()

        with open(out_dir / "workflow.json") as f:
            data = json.load(f)
        assert data["metadata"]["name"] == "simple_filter"
