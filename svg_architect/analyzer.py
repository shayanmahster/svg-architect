"""
Geometric Analyzer — coordinate-space analysis of SVG geometry.

This module provides real mathematical parsing of SVG shapes (paths, polygons,
circles, ellipses, rects) and produces geometric reports including bounding
boxes, vertical coverage maps, symmetry drift scores, proportion analysis,
and disconnection detection.

All analysis operates directly on parsed coordinate data — no keyword
matching or heuristics on tag names.

Usage::

    from svg_architect.analyzer import GeometricAnalyzer

    analyzer = GeometricAnalyzer()
    report = analyzer.analyze(svg_string)
    print(report.symmetry_score)
    print(report.disconnections)
"""

from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class ShapeBBox(BaseModel):
    """Axis-aligned bounding box for a single SVG shape element."""

    element_tag: str
    element_id: Optional[str] = None
    min_x: float
    min_y: float
    max_x: float
    max_y: float
    center_x: float
    center_y: float


class CoverageMap(BaseModel):
    """
    Vertical coverage map for the SVG canvas.

    For each Y pixel row (0 .. height-1), ``coverage[y]`` is ``True`` when
    there is filled geometry crossing the center axis (X ∈ [240, 260]).
    Gaps of ≥ 8 px in this coverage indicate severed / disconnected regions.
    """

    height: int = 500
    coverage: List[bool] = Field(default_factory=list)
    gaps: List[Tuple[int, int]] = Field(default_factory=list)


class GeometricReport(BaseModel):
    """Full geometric analysis report for an SVG document."""

    shapes: List[ShapeBBox] = Field(default_factory=list)
    coverage: CoverageMap = Field(default_factory=CoverageMap)
    symmetry_score: float = 0.0
    head_to_body_ratio: Optional[float] = None
    disconnections: List[Tuple[int, int]] = Field(default_factory=list)
    issues: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# SVG path ``d``-attribute parser
# ---------------------------------------------------------------------------

# Regex that splits a ``d`` attribute into (command_letter, numeric_args).
_CMD_RE = re.compile(r"([MmLlHhVvCcSsQqTtAaZz])")
_NUM_RE = re.compile(
    r"[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?"
)


def parse_svg_path(d: str) -> List[Tuple[float, float]]:
    """Parse an SVG path ``d`` attribute and return key coordinates.

    Handles **M, m, L, l, H, h, V, v, C, c, S, s, Q, q, T, t, A, a, Z, z**
    commands.  For curves the control-points *and* endpoints are included so
    bounding-box estimation captures the full extent of the curve.

    Parameters
    ----------
    d:
        The ``d`` attribute string from an ``<svg:path>`` element.

    Returns
    -------
    List[Tuple[float, float]]
        Extracted (x, y) coordinates (absolute canvas space).
    """
    if not d:
        return []

    points: List[Tuple[float, float]] = []
    cur_x, cur_y = 0.0, 0.0
    start_x, start_y = 0.0, 0.0  # for Z command

    # Split into tokens: each token is (command, numbers_string)
    tokens = _CMD_RE.split(d)
    # tokens[0] is any text before the first command (usually empty)
    i = 1  # skip leading text
    while i < len(tokens):
        cmd = tokens[i]
        nums_str = tokens[i + 1] if i + 1 < len(tokens) else ""
        nums = [float(n) for n in _NUM_RE.findall(nums_str)]
        i += 2

        relative = cmd.islower()
        cmd_upper = cmd.upper()

        idx = 0
        # Some commands are implicitly repeatable.
        consumed_at_least_once = False
        while idx < len(nums) or not consumed_at_least_once:
            consumed_at_least_once = True

            if cmd_upper == "M":
                # moveto: (x, y)
                if idx + 1 >= len(nums) and idx > 0:
                    break
                if idx + 1 >= len(nums):
                    break
                x, y = nums[idx], nums[idx + 1]
                idx += 2
                if relative:
                    x += cur_x
                    y += cur_y
                cur_x, cur_y = x, y
                start_x, start_y = x, y
                points.append((cur_x, cur_y))
                # Subsequent coordinate pairs after M are treated as L.
                if relative:
                    cmd = "l"
                    cmd_upper = "L"
                else:
                    cmd = "L"
                    cmd_upper = "L"

            elif cmd_upper == "L":
                if idx + 1 >= len(nums):
                    break
                x, y = nums[idx], nums[idx + 1]
                idx += 2
                if relative:
                    x += cur_x
                    y += cur_y
                cur_x, cur_y = x, y
                points.append((cur_x, cur_y))

            elif cmd_upper == "H":
                if idx >= len(nums):
                    break
                x = nums[idx]
                idx += 1
                if relative:
                    x += cur_x
                cur_x = x
                points.append((cur_x, cur_y))

            elif cmd_upper == "V":
                if idx >= len(nums):
                    break
                y = nums[idx]
                idx += 1
                if relative:
                    y += cur_y
                cur_y = y
                points.append((cur_x, cur_y))

            elif cmd_upper == "C":
                # cubic Bézier: x1 y1 x2 y2 x y
                if idx + 5 >= len(nums):
                    break
                coords = nums[idx : idx + 6]
                idx += 6
                if relative:
                    abs_coords = [
                        coords[0] + cur_x, coords[1] + cur_y,
                        coords[2] + cur_x, coords[3] + cur_y,
                        coords[4] + cur_x, coords[5] + cur_y,
                    ]
                else:
                    abs_coords = list(coords)
                # Include control points for bbox estimation.
                points.append((abs_coords[0], abs_coords[1]))
                points.append((abs_coords[2], abs_coords[3]))
                points.append((abs_coords[4], abs_coords[5]))
                cur_x, cur_y = abs_coords[4], abs_coords[5]

            elif cmd_upper == "S":
                # smooth cubic Bézier: x2 y2 x y
                if idx + 3 >= len(nums):
                    break
                coords = nums[idx : idx + 4]
                idx += 4
                if relative:
                    abs_coords = [
                        coords[0] + cur_x, coords[1] + cur_y,
                        coords[2] + cur_x, coords[3] + cur_y,
                    ]
                else:
                    abs_coords = list(coords)
                points.append((abs_coords[0], abs_coords[1]))
                points.append((abs_coords[2], abs_coords[3]))
                cur_x, cur_y = abs_coords[2], abs_coords[3]

            elif cmd_upper == "Q":
                # quadratic Bézier: x1 y1 x y
                if idx + 3 >= len(nums):
                    break
                coords = nums[idx : idx + 4]
                idx += 4
                if relative:
                    abs_coords = [
                        coords[0] + cur_x, coords[1] + cur_y,
                        coords[2] + cur_x, coords[3] + cur_y,
                    ]
                else:
                    abs_coords = list(coords)
                points.append((abs_coords[0], abs_coords[1]))
                points.append((abs_coords[2], abs_coords[3]))
                cur_x, cur_y = abs_coords[2], abs_coords[3]

            elif cmd_upper == "T":
                # smooth quadratic Bézier: x y
                if idx + 1 >= len(nums):
                    break
                x, y = nums[idx], nums[idx + 1]
                idx += 2
                if relative:
                    x += cur_x
                    y += cur_y
                cur_x, cur_y = x, y
                points.append((cur_x, cur_y))

            elif cmd_upper == "A":
                # arc: rx ry x-rotation large-arc sweep x y
                if idx + 6 >= len(nums):
                    break
                # We only care about the endpoint for bounding-box purposes.
                rx = nums[idx]
                ry = nums[idx + 1]
                # x_rotation = nums[idx + 2]  (unused for bbox)
                # large_arc = nums[idx + 3]
                # sweep = nums[idx + 4]
                x = nums[idx + 5]
                y = nums[idx + 6]
                idx += 7
                if relative:
                    x += cur_x
                    y += cur_y
                # Approximate arc extent: include endpoint and offset by radii
                # from both current and end positions for conservative bbox.
                points.append((cur_x - rx, cur_y - ry))
                points.append((cur_x + rx, cur_y + ry))
                points.append((x - rx, y - ry))
                points.append((x + rx, y + ry))
                points.append((x, y))
                cur_x, cur_y = x, y

            elif cmd_upper == "Z":
                cur_x, cur_y = start_x, start_y
                break  # Z takes no arguments

            else:
                # Unknown command — skip
                break

    return points


# ---------------------------------------------------------------------------
# Shape extraction helpers
# ---------------------------------------------------------------------------

_SVG_NS = "http://www.w3.org/2000/svg"
_SHAPE_TAGS_LOCAL = {"path", "polygon", "polyline", "circle", "ellipse", "rect", "line"}


def _strip_ns(tag: str) -> str:
    """Remove the namespace URI from an Element tag, returning the local name."""
    if tag.startswith("{"):
        return tag.split("}", 1)[1]
    return tag


def _parse_points_attr(points_str: str) -> List[Tuple[float, float]]:
    """Parse an SVG ``points`` attribute (used by ``<polygon>`` / ``<polyline>``)."""
    nums = [float(n) for n in _NUM_RE.findall(points_str)]
    return [(nums[i], nums[i + 1]) for i in range(0, len(nums) - 1, 2)]


def _apply_transform_to_bbox(
    element: ET.Element,
    min_x: float,
    min_y: float,
    max_x: float,
    max_y: float,
) -> Tuple[float, float, float, float]:
    """Apply a simple ``translate(tx, ty)`` transform to a bounding box.

    Only handles the ``translate`` form — the most common in generated SVGs.
    More complex transforms (rotate, scale, matrix) are ignored for
    performance; a full matrix pipeline is overkill for proportion analysis.
    """
    transform = element.get("transform", "")
    m = re.search(r"translate\(\s*([^,\s]+)[\s,]+([^)]+)\)", transform)
    if m:
        tx, ty = float(m.group(1)), float(m.group(2))
        return min_x + tx, min_y + ty, max_x + tx, max_y + ty
    # Single-value translate
    m = re.search(r"translate\(\s*([^)]+)\)", transform)
    if m:
        vals = [float(v) for v in _NUM_RE.findall(m.group(1))]
        if len(vals) >= 2:
            return min_x + vals[0], min_y + vals[1], max_x + vals[0], max_y + vals[1]
        elif len(vals) == 1:
            return min_x + vals[0], min_y, max_x + vals[0], max_y
    return min_x, min_y, max_x, max_y


def _extract_shape_bbox(element: ET.Element) -> Optional[ShapeBBox]:
    """Compute the bounding box for a single SVG shape element.

    Returns ``None`` if the element does not contain recognisable geometry.
    """
    tag = _strip_ns(element.tag)
    eid = element.get("id")

    xs: List[float] = []
    ys: List[float] = []

    if tag == "path":
        d = element.get("d", "")
        pts = parse_svg_path(d)
        if not pts:
            return None
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]

    elif tag in ("polygon", "polyline"):
        pts_str = element.get("points", "")
        pts = _parse_points_attr(pts_str)
        if not pts:
            return None
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]

    elif tag == "circle":
        cx = float(element.get("cx", "0"))
        cy = float(element.get("cy", "0"))
        r = float(element.get("r", "0"))
        xs = [cx - r, cx + r]
        ys = [cy - r, cy + r]

    elif tag == "ellipse":
        cx = float(element.get("cx", "0"))
        cy = float(element.get("cy", "0"))
        rx = float(element.get("rx", "0"))
        ry = float(element.get("ry", "0"))
        xs = [cx - rx, cx + rx]
        ys = [cy - ry, cy + ry]

    elif tag == "rect":
        x = float(element.get("x", "0"))
        y = float(element.get("y", "0"))
        w = float(element.get("width", "0"))
        h = float(element.get("height", "0"))
        xs = [x, x + w]
        ys = [y, y + h]

    elif tag == "line":
        x1 = float(element.get("x1", "0"))
        y1 = float(element.get("y1", "0"))
        x2 = float(element.get("x2", "0"))
        y2 = float(element.get("y2", "0"))
        xs = [x1, x2]
        ys = [y1, y2]

    else:
        return None

    if not xs or not ys:
        return None

    mn_x, mx_x = min(xs), max(xs)
    mn_y, mx_y = min(ys), max(ys)

    # Apply ancestor translate transforms (walk up is not possible with ET,
    # but the element itself may carry one).
    mn_x, mn_y, mx_x, mx_y = _apply_transform_to_bbox(element, mn_x, mn_y, mx_x, mx_y)

    return ShapeBBox(
        element_tag=tag,
        element_id=eid,
        min_x=mn_x,
        min_y=mn_y,
        max_x=mx_x,
        max_y=mx_y,
        center_x=(mn_x + mx_x) / 2.0,
        center_y=(mn_y + mx_y) / 2.0,
    )


# ---------------------------------------------------------------------------
# GeometricAnalyzer
# ---------------------------------------------------------------------------

class GeometricAnalyzer:
    """Perform coordinate-space geometric analysis on SVG documents.

    This analyzer parses the raw SVG XML, extracts every shape element,
    computes bounding boxes, and derives several higher-level metrics:

    * **Vertical Coverage Map** — boolean array indicating filled geometry
      along the canvas center axis for each pixel row.
    * **Symmetry Drift Score** — 0.0 (perfectly symmetric about X = 250)
      to 1.0 (no mirrored counterparts found).
    * **Proportion Analysis** — head-region vs. body-region height ratio.
    * **Disconnection Detection** — Y-gaps ≥ 8 px in the coverage map,
      often indicative of severed heads / floating limbs.

    Parameters
    ----------
    canvas_width:
        Assumed canvas width in px (default 500).
    canvas_height:
        Assumed canvas height in px (default 500).
    center_band:
        ``(x_min, x_max)`` defining the center axis band used for the
        vertical coverage map.  Defaults to ``(240, 260)``.
    gap_threshold:
        Minimum gap size in px to be flagged as a disconnection.
    """

    def __init__(
        self,
        canvas_width: int = 500,
        canvas_height: int = 500,
        center_band: Tuple[int, int] = (240, 260),
        gap_threshold: int = 8,
    ) -> None:
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height
        self.center_band = center_band
        self.gap_threshold = gap_threshold

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(self, svg_content: str) -> GeometricReport:
        """Run a full geometric analysis on the given SVG string.

        Parameters
        ----------
        svg_content:
            A complete SVG document as a UTF-8 string.

        Returns
        -------
        GeometricReport
            Aggregated analysis results.
        """
        root = ET.fromstring(svg_content)
        shapes = self._extract_all_shapes(root)

        coverage = self._build_coverage_map(shapes)
        symmetry = self._compute_symmetry_drift(shapes)
        ratio = self._compute_head_body_ratio(coverage)
        disconnections = coverage.gaps
        issues = self._compile_issues(coverage, symmetry, ratio, disconnections)

        return GeometricReport(
            shapes=shapes,
            coverage=coverage,
            symmetry_score=symmetry,
            head_to_body_ratio=ratio,
            disconnections=disconnections,
            issues=issues,
        )

    # ------------------------------------------------------------------
    # Shape extraction
    # ------------------------------------------------------------------

    def _extract_all_shapes(self, root: ET.Element) -> List[ShapeBBox]:
        """Recursively find every shape element in the SVG tree."""
        shapes: List[ShapeBBox] = []
        for elem in root.iter():
            local = _strip_ns(elem.tag)
            if local in _SHAPE_TAGS_LOCAL:
                bbox = _extract_shape_bbox(elem)
                if bbox is not None:
                    shapes.append(bbox)
        return shapes

    # ------------------------------------------------------------------
    # Vertical coverage map
    # ------------------------------------------------------------------

    def _build_coverage_map(self, shapes: List[ShapeBBox]) -> CoverageMap:
        """Build a boolean coverage array for the center-axis band.

        For every Y in ``[0, canvas_height)``, the entry is ``True`` if *any*
        shape's bounding box overlaps both the Y row and the center band
        ``[center_band[0], center_band[1]]`` in X.
        """
        height = self.canvas_height
        coverage = [False] * height
        x_lo, x_hi = self.center_band

        for shape in shapes:
            # Check X overlap with center band.
            if shape.max_x < x_lo or shape.min_x > x_hi:
                continue
            # Mark covered Y rows.
            y_start = max(0, int(math.floor(shape.min_y)))
            y_end = min(height - 1, int(math.floor(shape.max_y)))
            for y in range(y_start, y_end + 1):
                coverage[y] = True

        gaps = self._detect_gaps(coverage, height)

        return CoverageMap(height=height, coverage=coverage, gaps=gaps)

    # ------------------------------------------------------------------
    # Disconnection detection
    # ------------------------------------------------------------------

    def _detect_gaps(
        self, coverage: List[bool], height: int
    ) -> List[Tuple[int, int]]:
        """Find contiguous runs of ``False`` in the coverage that are ≥ ``gap_threshold``.

        Only considers gaps that are *between* covered regions (i.e. leading
        and trailing uncovered rows at the top/bottom of the canvas are
        excluded).
        """
        # Find first and last covered row.
        first_covered: Optional[int] = None
        last_covered: Optional[int] = None
        for y in range(height):
            if coverage[y]:
                if first_covered is None:
                    first_covered = y
                last_covered = y

        if first_covered is None or last_covered is None:
            return []  # No geometry at all.

        gaps: List[Tuple[int, int]] = []
        in_gap = False
        gap_start = 0
        for y in range(first_covered, last_covered + 1):
            if not coverage[y]:
                if not in_gap:
                    gap_start = y
                    in_gap = True
            else:
                if in_gap:
                    gap_len = y - gap_start
                    if gap_len >= self.gap_threshold:
                        gaps.append((gap_start, y - 1))
                    in_gap = False

        # Close any trailing gap (up to last_covered).
        if in_gap:
            gap_len = (last_covered + 1) - gap_start
            if gap_len >= self.gap_threshold:
                gaps.append((gap_start, last_covered))

        return gaps

    # ------------------------------------------------------------------
    # Symmetry drift
    # ------------------------------------------------------------------

    def _compute_symmetry_drift(self, shapes: List[ShapeBBox]) -> float:
        """Compute a symmetry drift score in [0.0, 1.0].

        For each shape, the algorithm mirrors its center across the vertical
        axis ``X = canvas_width / 2`` and searches for the nearest shape
        center on the other side.  The drift is the average normalised
        distance of each shape to its closest mirror partner.

        A score of **0.0** means perfect bilateral symmetry; **1.0** means
        no mirror counterparts were found at all.
        """
        if not shapes:
            return 0.0

        axis_x = self.canvas_width / 2.0
        max_dist = self.canvas_width / 2.0  # normalisation reference

        total_drift = 0.0
        count = 0

        for shape in shapes:
            mirror_cx = 2.0 * axis_x - shape.center_x
            mirror_cy = shape.center_y

            best_dist = float("inf")
            for other in shapes:
                if other is shape:
                    continue
                dist = math.hypot(
                    other.center_x - mirror_cx,
                    other.center_y - mirror_cy,
                )
                if dist < best_dist:
                    best_dist = dist

            if best_dist == float("inf"):
                # Only one shape — consider it maximally drifted.
                total_drift += 1.0
            else:
                total_drift += min(best_dist / max_dist, 1.0)
            count += 1

        return total_drift / count if count else 0.0

    # ------------------------------------------------------------------
    # Proportion analysis
    # ------------------------------------------------------------------

    def _compute_head_body_ratio(self, coverage: CoverageMap) -> Optional[float]:
        """Estimate a head-to-body height ratio from the coverage map.

        Strategy
        --------
        1. Find the first covered row (top of geometry).
        2. Find the first *significant* gap (≥ ``gap_threshold``) or, if none,
           estimate the head region as the top 25 % of covered extent.
        3. Head height = rows from first covered to gap start.
           Body height = rows from gap end to last covered.
        4. Return head / body.

        Returns ``None`` when there is insufficient geometry to estimate.
        """
        cov = coverage.coverage
        height = coverage.height

        first_covered: Optional[int] = None
        last_covered: Optional[int] = None
        for y in range(height):
            if cov[y]:
                if first_covered is None:
                    first_covered = y
                last_covered = y

        if first_covered is None or last_covered is None:
            return None

        total_extent = last_covered - first_covered + 1
        if total_extent < 2:
            return None

        # If there is a gap (neck), use it to split head / body.
        if coverage.gaps:
            gap_start, gap_end = coverage.gaps[0]
            head_height = gap_start - first_covered
            body_height = last_covered - gap_end
            if head_height > 0 and body_height > 0:
                return head_height / body_height

        # Fallback: estimate head as top 25 % of total extent.
        head_height = int(total_extent * 0.25)
        body_height = total_extent - head_height
        if body_height > 0:
            return head_height / body_height

        return None

    # ------------------------------------------------------------------
    # Issue compilation
    # ------------------------------------------------------------------

    @staticmethod
    def _compile_issues(
        coverage: CoverageMap,
        symmetry: float,
        ratio: Optional[float],
        disconnections: List[Tuple[int, int]],
    ) -> List[str]:
        """Compile a human-readable list of detected issues."""
        issues: List[str] = []

        if disconnections:
            for gap_start, gap_end in disconnections:
                gap_size = gap_end - gap_start + 1
                issues.append(
                    f"Vertical disconnection of {gap_size}px detected "
                    f"between Y={gap_start} and Y={gap_end}. "
                    f"Possible severed/floating geometry."
                )

        if symmetry > 0.35:
            issues.append(
                f"High symmetry drift ({symmetry:.2f}). "
                f"Geometry may be noticeably asymmetric about the center axis."
            )

        covered_count = sum(coverage.coverage)
        if covered_count < 50:
            issues.append(
                f"Very sparse vertical coverage ({covered_count}/{coverage.height} rows). "
                f"The figure may be too small or off-center."
            )

        if ratio is not None and ratio > 0.6:
            issues.append(
                f"Head-to-body ratio ({ratio:.2f}) is unusually large. "
                f"The head may be disproportionately oversized."
            )

        return issues
