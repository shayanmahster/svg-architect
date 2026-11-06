"""
SVG Linter: Quality & Geometric Sanity Analyzer for AI-generated SVGs.
Evaluates symmetry drift, layer occlusion, gradient density, and flatness penalties.
"""

import re
import xml.etree.ElementTree as ET
from typing import Dict, Any, List
from pydantic import BaseModel


class LintReport(BaseModel):
    is_valid_xml: bool
    total_elements: int
    defs_count: int
    has_center_split: bool
    has_gradients: bool
    has_filters: bool
    byte_size: int
    score_out_of_100: int
    issues: List[str]
    metrics: Dict[str, Any]


class SVGLinter:
    @staticmethod
    def lint(svg_string: str) -> LintReport:
        issues = []
        score = 100

        # XML Parsing check
        is_valid = True
        root = None
        try:
            # Strip namespaces or load standard XML
            clean_svg = re.sub(r'\sxmlns="[^"]+"', '', svg_string, count=1)
            root = ET.fromstring(clean_svg)
        except Exception as e:
            is_valid = False
            issues.append(f"XML Parsing Error: {str(e)}")
            score -= 50

        byte_size = len(svg_string.encode("utf-8"))

        if not is_valid or root is None:
            return LintReport(
                is_valid_xml=False,
                total_elements=0,
                defs_count=0,
                has_center_split=False,
                has_gradients=False,
                has_filters=False,
                byte_size=byte_size,
                score_out_of_100=max(0, score),
                issues=issues,
                metrics={},
            )

        # Count elements
        all_elements = list(root.iter())
        total_elements = len(all_elements)

        # Defs & Gradients check
        defs_elements = root.findall(".//defs")
        defs_children = []
        for d in defs_elements:
            defs_children.extend(list(d))
        defs_count = len(defs_children)

        has_gradients = bool(re.search(r"<(linearGradient|radialGradient)", svg_string))
        has_filters = bool(re.search(r"<(filter|feGaussianBlur|feDropShadow)", svg_string))

        if not has_gradients:
            issues.append("Anti-Flatness Violation: No multi-stop gradients found (flat vector).")
            score -= 20

        if not has_filters:
            issues.append("Depth Warning: No optical filters (feDropShadow / feGaussianBlur) found.")
            score -= 10

        # Check for Painter's algorithm layer order (defs should be near the start)
        first_few = [elem.tag for elem in list(root)[:3]]
        if "defs" not in first_few and defs_count > 0:
            issues.append("Painter's Algorithm Warning: <defs> block is not placed at the very top of the DOM.")
            score -= 5

        # Check Center Splitting (X=250 or X=256 plane split)
        has_center_split = bool(re.search(r'250[, ]|256[, ]', svg_string))
        if not has_center_split:
            issues.append("Symmetry Warning: No central axis anchor points detected.")
            score -= 10

        # Node budget check
        if total_elements < 10:
            issues.append("Low Fidelity: Extremely few vector nodes (< 10 elements).")
            score -= 20

        # Anatomical Continuity Check (detecting severed head / missing neck bridging)
        # Check if head and body/torso IDs or comments exist, and verify bridging connector exists
        lower_svg = svg_string.lower()
        has_head = "head" in lower_svg or "cranium" in lower_svg or "face" in lower_svg
        has_body = "body" in lower_svg or "torso" in lower_svg or "shoulder" in lower_svg
        has_neck = "neck" in lower_svg or "collar" in lower_svg or "throat" in lower_svg or "seam" in lower_svg

        if has_head and has_body and not has_neck:
            issues.append(
                "Anatomical Severing Risk: Character contains head and body layers but lacks an explicit overlapping "
                "neck/collar connector, risking a floating/severed head."
            )
            score -= 10

        score = max(0, min(100, score))

        return LintReport(
            is_valid_xml=True,
            total_elements=total_elements,
            defs_count=defs_count,
            has_center_split=has_center_split,
            has_gradients=has_gradients,
            has_filters=has_filters,
            byte_size=byte_size,
            score_out_of_100=score,
            issues=issues,
            metrics={
                "nodes": total_elements,
                "defs_items": defs_count,
                "size_formatted": f"{byte_size / 1024:.2f} KB" if byte_size > 1024 else f"{byte_size} B",
            },
        )
