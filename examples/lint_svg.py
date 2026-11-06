"""
Example: Linting SVGs with SVG-Architect.
"""

import os
import sys

# Ensure local package is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from svg_architect.linter import SVGLinter

samples_dir = os.path.join(os.path.dirname(__file__), "..", "viewer", "samples")

for filename in sorted(os.listdir(samples_dir)):
    if filename.endswith(".svg"):
        filepath = os.path.join(samples_dir, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        report = SVGLinter.lint(content)
        print(f"\n[{filename}]")
        print(f"  Score:       {report.score_out_of_100}/100")
        print(f"  Nodes:       {report.total_elements}")
        print(f"  Defs/Glow:   {report.defs_count}")
        print(f"  Size:        {report.metrics.get('size_formatted')}")
        if report.issues:
            print(f"  Issues:      {', '.join(report.issues)}")
        else:
            print(f"  Status:      CLEAN ARCHITECTURE")
