"""
Vision Critic Feedback Loop for Generative Vector Graphics.
Implements the render -> rasterize -> visual inspect -> targeted repair loop.
"""

import re
from typing import List, Optional, Callable, Dict, Any, Awaitable
from pydantic import BaseModel, Field


class CritiqueResult(BaseModel):
    score: float = 7.0  # 1.0 to 10.0
    issues: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    iteration: int = 1


class VisionCriticConfig(BaseModel):
    max_iterations: int = 3
    min_acceptable_score: float = 8.5
    subject_description: str = ""
    target_style: str = "production vector"


class VisionCriticLoop:
    """Framework for render -> critique -> fix -> repeat refinement.
    Decoupled from underlying rendering engines (cairosvg/playwright) and Vision LLMs."""

    def __init__(self, config: VisionCriticConfig):
        self.config = config
        self.history: List[CritiqueResult] = []

    def build_critique_prompt(self, subject: str, style: str = "") -> str:
        return f"""You are a master vector graphic art director and visual quality critic.
Analyze the rendered image of the SVG generation for the subject: "{subject}" (Style: {style or self.config.target_style}).

Evaluate rigorously on 6 criteria:
1. Anatomical Accuracy & Continuity (Are proportions correct? Are head/neck/body seamlessly attached without floating gaps?)
2. Center Symmetry & Alignment (Is facial geometry aligned down the center?)
3. Shading & Volumetric Depth (Are lighting gradients physically convincing, or flat and cartoonish?)
4. Detail Density & Polish (Are eyes, specular highlights, and edge rims crisp?)
5. Character Recognizability (Does it instantly match the iconic subject?)
6. Cleanliness (Are there any stray lines or clipping artifacts?)

Provide your critique in this exact format:
SCORE: <number from 1.0 to 10.0>
ISSUES:
- <issue 1>
- <issue 2>
SUGGESTIONS:
- <suggestion 1>
- <suggestion 2>"""

    def parse_critique_response(self, response_text: str, iteration: int = 1) -> CritiqueResult:
        score = 7.0
        score_match = re.search(r'SCORE:\s*([0-9]+(?:\.[0-9]+)?)', response_text, re.IGNORECASE)
        if score_match:
            try:
                score = float(score_match.group(1))
            except ValueError:
                score = 7.0

        issues = []
        suggestions = []

        issues_block = re.search(r'ISSUES:(.*?)(?:SUGGESTIONS:|$)', response_text, re.DOTALL | re.IGNORECASE)
        if issues_block:
            issues = [line.strip("- *").strip() for line in issues_block.group(1).split("\n") if line.strip("- *").strip()]

        sugg_block = re.search(r'SUGGESTIONS:(.*?)$', response_text, re.DOTALL | re.IGNORECASE)
        if sugg_block:
            suggestions = [line.strip("- *").strip() for line in sugg_block.group(1).split("\n") if line.strip("- *").strip()]

        return CritiqueResult(
            score=min(10.0, max(0.0, score)),
            issues=issues,
            suggestions=suggestions,
            iteration=iteration
        )

    def build_fix_prompt(self, current_svg: str, critique: CritiqueResult) -> str:
        issues_formatted = "\n".join(f"- {iss}" for iss in critique.issues)
        sugg_formatted = "\n".join(f"- {sug}" for sug in critique.suggestions)

        return f"""The visual art director reviewed the rendered SVG (Score: {critique.score:.1f}/10.0) and identified these specific defects:

ISSUES DETECTED:
{issues_formatted}

ACTIONABLE SUGGESTIONS:
{sugg_formatted}

CURRENT SVG CODE:
```xml
{current_svg}
```

Task: Fix the issues identified above in the SVG code while preserving all existing valid structure and gradients.
Output the complete, corrected production <svg> XML block."""

    async def refine(
        self,
        initial_svg: str,
        render_fn: Callable[[str], Awaitable[bytes]],
        vision_fn: Callable[[bytes, str], Awaitable[str]],
        fix_fn: Callable[[str, str], Awaitable[str]],
    ) -> str:
        """Executes the multi-turn visual critique and repair loop."""
        current_svg = initial_svg

        for iteration in range(1, self.config.max_iterations + 1):
            # 1. Render SVG to bitmap PNG bytes
            png_bytes = await render_fn(current_svg)

            # 2. Ask Vision LLM to critique
            prompt = self.build_critique_prompt(self.config.subject_description, self.config.target_style)
            critique_raw = await vision_fn(png_bytes, prompt)
            critique = self.parse_critique_response(critique_raw, iteration=iteration)
            self.history.append(critique)

            # 3. Check termination criteria
            if critique.score >= self.config.min_acceptable_score or not critique.issues:
                break

            # 4. Generate targeted fix
            fix_prompt = self.build_fix_prompt(current_svg, critique)
            repaired_svg_raw = await fix_fn(current_svg, fix_prompt)

            svg_match = re.search(r"<svg.*?</svg>", repaired_svg_raw, re.DOTALL)
            if svg_match:
                current_svg = svg_match.group(0)

        return current_svg
