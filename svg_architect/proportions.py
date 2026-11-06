"""
Proportion Templates — art-style reference proportions for figure analysis.

Each :class:`ProportionTemplate` captures canonical ratios for a particular
art style (e.g. Looney Tunes, Disney Classic, Chibi) and can validate a
:class:`~svg_architect.analyzer.GeometricReport` against those expectations.

Usage::

    from svg_architect.proportions import PROPORTION_PRESETS
    from svg_architect.analyzer import GeometricAnalyzer

    report = GeometricAnalyzer().analyze(svg_string)
    warnings = PROPORTION_PRESETS["chibi"].validate_against(report)
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from svg_architect.analyzer import GeometricReport


# ---------------------------------------------------------------------------
# ProportionTemplate
# ---------------------------------------------------------------------------

class ProportionTemplate(BaseModel):
    """Canonical body-proportion template for a given art style.

    Attributes
    ----------
    style:
        Human-readable style name (e.g. ``"looney_tunes"``).
    head_to_body_ratio:
        Expected height of the head divided by the height of the body
        (excluding the head).  Higher values → bigger heads.
    eye_line_fraction:
        Fraction of head height (measured from the top of the head) at
        which the eye line is expected.  0.5 = eyes at the midpoint.
    shoulder_to_head_width:
        Width of the shoulder span divided by the width of the head.
        Values < 1.0 indicate narrow shoulders relative to head (chibi);
        values > 2.0 indicate broad comic-book shoulders.
    head_region:
        ``(y_start_frac, y_end_frac)`` — vertical fraction of the full
        canvas height where the head region is expected.
    torso_region:
        ``(y_start_frac, y_end_frac)`` for the torso.
    leg_region:
        ``(y_start_frac, y_end_frac)`` for the legs.
    """

    style: str
    head_to_body_ratio: float
    eye_line_fraction: float
    shoulder_to_head_width: float
    head_region: Tuple[float, float]
    torso_region: Tuple[float, float]
    leg_region: Tuple[float, float]

    # ---- Tolerance knobs (not style-specific) ----
    _RATIO_TOLERANCE: float = 0.40  # ±40 % relative tolerance on ratios
    _REGION_TOLERANCE: float = 0.10  # ±10 % absolute tolerance on region fractions

    def validate_against(
        self,
        report: GeometricReport,
        canvas_height: float = 500.0,
    ) -> List[str]:
        """Check whether a :class:`GeometricReport` matches this template.

        Parameters
        ----------
        report:
            The geometric analysis report to validate.
        canvas_height:
            Canvas height in pixels — used to convert absolute Y values
            into fractions.

        Returns
        -------
        List[str]
            Human-readable warning messages for each proportion that falls
            outside the expected range.  An empty list means the report is
            consistent with this art style.
        """
        warnings: List[str] = []

        # --- Head-to-body ratio -------------------------------------------
        if report.head_to_body_ratio is not None:
            expected = self.head_to_body_ratio
            actual = report.head_to_body_ratio
            lo = expected * (1.0 - self._RATIO_TOLERANCE)
            hi = expected * (1.0 + self._RATIO_TOLERANCE)
            if actual < lo or actual > hi:
                warnings.append(
                    f"[{self.style}] Head-to-body ratio {actual:.2f} is outside "
                    f"expected range [{lo:.2f}, {hi:.2f}] for this style."
                )

        # --- Geometry region checks ---------------------------------------
        if report.shapes:
            # Find the overall figure extent from the bounding boxes.
            all_min_y = min(s.min_y for s in report.shapes)
            all_max_y = max(s.max_y for s in report.shapes)
            figure_height = all_max_y - all_min_y
            if figure_height > 0:
                figure_top_frac = all_min_y / canvas_height
                figure_bot_frac = all_max_y / canvas_height

                # Check whether the figure's top aligns with the expected
                # head region start.
                head_start_expected = self.head_region[0]
                if abs(figure_top_frac - head_start_expected) > self._REGION_TOLERANCE:
                    warnings.append(
                        f"[{self.style}] Figure top ({figure_top_frac:.2f}) deviates "
                        f"from expected head-region start ({head_start_expected:.2f})."
                    )

                # Check whether the figure's bottom aligns with the expected
                # leg region end.
                leg_end_expected = self.leg_region[1]
                if abs(figure_bot_frac - leg_end_expected) > self._REGION_TOLERANCE:
                    warnings.append(
                        f"[{self.style}] Figure bottom ({figure_bot_frac:.2f}) deviates "
                        f"from expected leg-region end ({leg_end_expected:.2f})."
                    )

        # --- Symmetry check -----------------------------------------------
        if report.symmetry_score > 0.5:
            warnings.append(
                f"[{self.style}] Symmetry drift ({report.symmetry_score:.2f}) is high; "
                f"most {self.style} figures should be roughly symmetric."
            )

        # --- Disconnections -----------------------------------------------
        if report.disconnections:
            total_gap = sum(
                (end - start + 1) for start, end in report.disconnections
            )
            warnings.append(
                f"[{self.style}] {len(report.disconnections)} vertical "
                f"disconnection(s) totalling {total_gap}px detected. "
                f"The figure may have severed geometry."
            )

        return warnings


# ---------------------------------------------------------------------------
# Preset proportion templates
# ---------------------------------------------------------------------------

PROPORTION_PRESETS: Dict[str, ProportionTemplate] = {
    "looney_tunes": ProportionTemplate(
        style="looney_tunes",
        head_to_body_ratio=0.40,
        eye_line_fraction=0.55,
        shoulder_to_head_width=0.9,
        head_region=(0.02, 0.30),
        torso_region=(0.30, 0.58),
        leg_region=(0.58, 0.95),
    ),
    "disney_classic": ProportionTemplate(
        style="disney_classic",
        head_to_body_ratio=0.35,
        eye_line_fraction=0.50,
        shoulder_to_head_width=1.2,
        head_region=(0.02, 0.25),
        torso_region=(0.25, 0.55),
        leg_region=(0.55, 0.95),
    ),
    "realistic_portrait": ProportionTemplate(
        style="realistic_portrait",
        head_to_body_ratio=0.22,
        eye_line_fraction=0.45,
        shoulder_to_head_width=2.2,
        head_region=(0.02, 0.16),
        torso_region=(0.16, 0.50),
        leg_region=(0.50, 0.95),
    ),
    "chibi": ProportionTemplate(
        style="chibi",
        head_to_body_ratio=0.55,
        eye_line_fraction=0.60,
        shoulder_to_head_width=0.6,
        head_region=(0.02, 0.40),
        torso_region=(0.40, 0.65),
        leg_region=(0.65, 0.95),
    ),
    "anime": ProportionTemplate(
        style="anime",
        head_to_body_ratio=0.30,
        eye_line_fraction=0.50,
        shoulder_to_head_width=1.4,
        head_region=(0.02, 0.22),
        torso_region=(0.22, 0.52),
        leg_region=(0.52, 0.95),
    ),
    "comic_book": ProportionTemplate(
        style="comic_book",
        head_to_body_ratio=0.18,
        eye_line_fraction=0.42,
        shoulder_to_head_width=2.5,
        head_region=(0.02, 0.14),
        torso_region=(0.14, 0.45),
        leg_region=(0.45, 0.95),
    ),
}
