"""AWA CLI — thin interface over the core library."""

from __future__ import annotations

from pathlib import Path

import click


@click.group()
@click.version_option(package_name="awa")
def cli():
    """AWA — Alteryx Workflow Analyzer & Python Translator."""
    pass


@cli.command()
@click.argument("workflow", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output", "-o",
    type=click.Path(path_type=Path),
    default=None,
    help="Output directory for analysis artifacts.",
)
def analyze(workflow: Path, output: Path | None):
    """Analyze an Alteryx workflow and generate all output artifacts.

    Produces: workflow.json, workflow.py, workflow.svg, workflow.docx, diagnostics.json
    """
    from backend.src.awa.analysis.workflow_analyzer import analyze_workflow

    click.echo(f"Analyzing: {workflow}")

    result = analyze_workflow(workflow, output)

    click.echo(f"Output: {result.output_dir}")
    click.echo(f"  Tools: {len(result.workflow.tools)}")
    click.echo(f"  Connections: {len(result.workflow.connections)}")

    # Summary
    support_counts: dict[str, int] = {}
    for tr in result.translations.values():
        level = tr.support_level.value
        support_counts[level] = support_counts.get(level, 0) + 1

    for level, count in sorted(support_counts.items()):
        click.echo(f"  {level}: {count}")

    click.echo("Done.")


@cli.command()
@click.argument("workflow", type=click.Path(exists=True, path_type=Path))
def inspect(workflow: Path):
    """Inspect a workflow and print its structure without generating files."""
    from backend.src.awa.parser.xml_parser import parse_workflow as parse_wf
    from backend.src.awa.graph.builder import build_graph, execution_order as exec_order

    wf = parse_wf(workflow)
    g = build_graph(wf)
    order = exec_order(g)

    click.echo(f"Workflow: {wf.metadata.name}")
    click.echo(f"Version: {wf.metadata.version}")
    click.echo(f"Tools: {len(wf.tools)}")
    click.echo(f"Connections: {len(wf.connections)}")
    click.echo("")
    click.echo("Execution Order:")
    for tid in order:
        tool = wf.tools[tid]
        click.echo(f"  #{tid} {tool.tool_type} — {tool.name or '(unnamed)'}")


if __name__ == "__main__":
    cli()
