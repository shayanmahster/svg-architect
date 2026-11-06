"""
CLI interface for svg-architect.
"""

import sys
import os
import http.server
import socketserver
import click
from .linter import SVGLinter
from .generator import ArchitectProtocol


@click.group()
def main():
    """svg-architect: Deterministic Spatial Blueprint Engine for Vector Graphics."""
    pass


@main.command()
@click.argument("svg_file", type=click.Path(exists=True))
def lint(svg_file):
    """Lint and score an SVG file for geometric symmetry, depth, and layer ordering."""
    with open(svg_file, "r", encoding="utf-8") as f:
        content = f.read()

    report = SVGLinter.lint(content)

    click.echo("\n" + "=" * 50)
    click.echo(f" SVG Architect Linter: {os.path.basename(svg_file)}")
    click.echo("=" * 50)
    click.echo(f"Score:            {report.score_out_of_100} / 100")
    click.echo(f"Valid XML:        {'PASS' if report.is_valid_xml else 'FAIL'}")
    click.echo(f"Total DOM Nodes:  {report.total_elements}")
    click.echo(f"Defs Elements:    {report.defs_count}")
    click.echo(f"Gradients Found:  {'YES' if report.has_gradients else 'NO'}")
    click.echo(f"Filters Found:    {'YES' if report.has_filters else 'NO'}")
    click.echo(f"Center Split:     {'YES' if report.has_center_split else 'NO'}")
    click.echo(f"File Size:        {report.metrics.get('size_formatted', '0 B')}")
    click.echo("-" * 50)

    if report.issues:
        click.echo("Identified Issues / Recommendations:")
        for idx, issue in enumerate(report.issues, 1):
            click.echo(f"  {idx}. {issue}")
    else:
        click.echo("Clean Architecture! Zero geometric or ordering violations detected.")
    click.echo("=" * 50 + "\n")


@main.command()
@click.argument("subject")
def prompt(subject):
    """Output the pre-configured Spatial Blueprint prompt for any LLM."""
    wrapped = ArchitectProtocol.wrap_user_prompt(subject)
    click.echo(wrapped)


@main.command()
@click.option("--port", default=8000, help="Port to serve the interactive benchmark dashboard.")
def serve(port):
    """Launch the interactive A/B benchmark viewer in your browser."""
    viewer_dir = os.path.join(os.path.dirname(__file__), "..", "viewer")
    if not os.path.exists(viewer_dir):
        click.echo("Viewer directory not found.", err=True)
        sys.exit(1)

    os.chdir(viewer_dir)
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        click.echo(f"\n🚀 SVG Architect Dashboard running at http://localhost:{port}")
        click.echo("Press Ctrl+C to stop.\n")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            click.echo("\nServer stopped.")


if __name__ == "__main__":
    main()
