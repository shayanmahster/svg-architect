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
from .analyzer import GeometricAnalyzer
from .harmony import ColorHarmonyEngine
from .pipeline import PipelineConfig


@click.group()
def main():
    """svg-architect: Deterministic Spatial Blueprint & Multi-Pass Synthesis Engine."""
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
@click.argument("svg_file", type=click.Path(exists=True))
def analyze(svg_file):
    """Run geometric coordinate-space analysis (shape count, coverage, symmetry drift, disconnections)."""
    with open(svg_file, "r", encoding="utf-8") as f:
        content = f.read()

    analyzer = GeometricAnalyzer()
    report = analyzer.analyze(content)

    click.echo("\n" + "=" * 50)
    click.echo(f" Geometric Coordinate Analysis: {os.path.basename(svg_file)}")
    click.echo("=" * 50)
    click.echo(f"Shapes Extracted:       {len(report.shapes)}")
    click.echo(f"Symmetry Drift Score:   {report.symmetry_score:.2f} / 1.00")
    click.echo(f"Head/Body Ratio:        {f'{report.head_to_body_ratio:.2f}' if report.head_to_body_ratio else 'N/A'}")
    click.echo(f"Vertical Disconnections: {len(report.disconnections)}")

    if report.disconnections:
        click.echo("\n  Detected Gaps / Severed Seams:")
        for g_start, g_end in report.disconnections:
            click.echo(f"    - Y=[{g_start} to {g_end}] ({g_end - g_start}px gap)")
    else:
        click.echo("  Continuity: 100% continuous coverage along central axis.")

    if report.issues:
        click.echo("\nIssues:")
        for idx, iss in enumerate(report.issues, 1):
            click.echo(f"  {idx}. {iss}")
    click.echo("=" * 50 + "\n")


@main.command()
@click.argument("svg_file", type=click.Path(exists=True))
def harmony(svg_file):
    """Analyze color palette harmony, saturation balance, and WCAG contrast."""
    with open(svg_file, "r", encoding="utf-8") as f:
        content = f.read()

    report = ColorHarmonyEngine.analyze_palette(content)

    click.echo("\n" + "=" * 50)
    click.echo(f" Color Harmony Report: {os.path.basename(svg_file)}")
    click.echo("=" * 50)
    click.echo(f"Colors Found:       {len(report.colors_found)}")
    click.echo(f"Unique Hues:        {report.unique_hues}")
    click.echo(f"Harmony Scheme:     {report.harmony_type.upper() if report.harmony_type else 'N/A'}")
    click.echo(f"Saturation Balance: {report.saturation_balance:.2f} (0=flat gray, 1=max saturated)")

    if report.dominant_color:
        click.echo(f"Dominant Tone:      {report.dominant_color.hex}")

    if report.contrast_pairs:
        click.echo("\nContrast Ratios (WCAG):")
        for c1, c2, ratio in report.contrast_pairs:
            status = "PASS (>= 4.5)" if ratio >= 4.5 else "LOW"
            click.echo(f"  {c1} vs {c2}: {ratio}:1 [{status}]")

    if report.issues:
        click.echo("\nPalette Issues:")
        for idx, iss in enumerate(report.issues, 1):
            click.echo(f"  {idx}. {iss}")
    click.echo("=" * 50 + "\n")


@main.command()
@click.argument("subject")
@click.option("--style", default="cartoon", help="Art style (cartoon, realistic, superhero, etc.)")
def pipeline(subject, style):
    """Output the 4-pass iterative synthesis prompts for an LLM."""
    cfg = PipelineConfig.default_character_pipeline(subject=subject, style=style)
    click.echo("\n" + "=" * 60)
    click.echo(f" 🚀 SVG Architect 4-Pass Pipeline: {subject}")
    click.echo("=" * 60)
    for idx, stage in enumerate(cfg.stages, 1):
        click.echo(f"\n--- PASS {idx}: {stage.stage.value.upper()} ---")
        click.echo(stage.instruction)
        click.echo(f"Quality Gates: {', '.join(stage.validation_rules)}")
    click.echo("\n" + "=" * 60 + "\n")


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
