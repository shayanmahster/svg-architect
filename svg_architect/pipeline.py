"""
Multi-Pass Iterative Refinement Pipeline for SVG synthesis.
Deconstructs vector generation into four specialized progressive passes:
Skeleton -> Structural Mass -> Shading & Lighting -> Fine Details.
"""

import re
import xml.etree.ElementTree as ET
from typing import List, Optional, Callable, Dict, Any, Awaitable
from pydantic import BaseModel, Field
from enum import Enum


class PassStage(str, Enum):
    SKELETON = "skeleton"
    STRUCTURE = "structure"
    SHADING = "shading"
    DETAIL = "detail"


class StageResult(BaseModel):
    stage: PassStage
    svg_output: str
    validation_passed: bool
    validation_issues: List[str] = Field(default_factory=list)
    attempt: int = 1
    max_attempts: int = 3


class StageConfig(BaseModel):
    stage: PassStage
    instruction: str
    validation_rules: List[str] = Field(default_factory=list)
    required_elements: List[str] = Field(default_factory=list)


class PipelineConfig(BaseModel):
    subject: str
    style: str = "default"
    canvas_width: int = 500
    canvas_height: int = 500
    max_retries_per_stage: int = 3
    stages: List[StageConfig] = Field(default_factory=list)

    @classmethod
    def default_character_pipeline(cls, subject: str, style: str = "cartoon") -> "PipelineConfig":
        return cls(
            subject=subject,
            style=style,
            stages=[
                StageConfig(
                    stage=PassStage.SKELETON,
                    instruction=f"""Pass 1 (Skeleton): Draw ONLY the wireframe landmarks for '{subject}':
- Use viewBox="0 0 500 500", Center_X = 250.
- Output ONLY <line> elements and <circle r="3"> anchor nodes.
- Mark landmarks: Top of cranium, eyes, chin, neck lock, shoulders, hips, base.
- Strict symmetry: X_R = 500 - X_L. No solid fills, no gradients.""",
                    validation_rules=["At least 6 anchor points", "Center split at X=250", "Valid XML"],
                    required_elements=["circle", "line"],
                ),
                StageConfig(
                    stage=PassStage.STRUCTURE,
                    instruction=f"""Pass 2 (Structural Mass): Fill the primary geometric planes for '{subject}':
- Use previous skeleton as guide.
- Create solid closed <polygon> and <path> elements.
- Split center down X=250 (left lit, right core shadow).
- MANDATORY: Include overlapping neck connector (Y overlap >= 20px) bridging head and shoulders.
- Flat colors only (no gradients yet).""",
                    validation_rules=["At least 4 structural polygons", "Center split verified", "No floating head gaps"],
                    required_elements=["path", "polygon"],
                ),
                StageConfig(
                    stage=PassStage.SHADING,
                    instruction=f"""Pass 3 (Shading & Depth): Add volumetric gradients and optical depth for '{subject}':
- Add <defs> block with linearGradient and radialGradient stops.
- Replace flat fills with gradient references.
- Add feDropShadow or glow filters.
- Apply 3-point lighting model (Key from upper-left, fill from right, rim from top).""",
                    validation_rules=["At least 3 gradients in <defs>", "At least 1 filter definition", "Anti-flat fills"],
                    required_elements=["linearGradient", "filter"],
                ),
                StageConfig(
                    stage=PassStage.DETAIL,
                    instruction=f"""Pass 4 (Detail & Polish): Add fine foreground details and specular highlights for '{subject}':
- Add expressive pupils with white specular glint dots.
- Add subtle 1px rim-light edge paths (opacity 0.4 to 0.7).
- Add character-specific textures, props, or emblems.
- Ensure total DOM nodes >= 40 for crisp production fidelity.""",
                    validation_rules=["Specular highlights found", "DOM nodes >= 40", "100-point hygiene"],
                    required_elements=["circle"],
                ),
            ]
        )


class MultiPassPipeline:
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.history: List[StageResult] = []
        self.current_svg: str = ""

    def stages(self) -> List[StageConfig]:
        return self.config.stages

    def build_prompt(self, stage: StageConfig, previous_svg: str = "") -> str:
        prompt_parts = [
            f"=== MULTI-PASS SVG SYNTHESIS: STAGE [{stage.stage.value.upper()}] ===",
            f"Target Subject: {self.config.subject} (Style: {self.config.style})",
            "",
            stage.instruction,
        ]
        if previous_svg.strip():
            prompt_parts.extend([
                "",
                "--- PREVIOUS STAGE SVG CONTEXT ---",
                previous_svg.strip(),
                "-----------------------------------",
                "Produce the updated/evolved production <svg> XML block adhering strictly to the current stage."
            ])
        return "\n".join(prompt_parts)

    def validate_stage(self, stage: StageConfig, svg_output: str, attempt: int = 1) -> StageResult:
        issues = []
        clean_xml = re.sub(r'\sxmlns="[^"]+"', '', svg_output, count=1)

        try:
            root = ET.fromstring(clean_xml)
        except Exception as e:
            return StageResult(
                stage=stage.stage,
                svg_output=svg_output,
                validation_passed=False,
                validation_issues=[f"XML Parsing Syntax Error: {str(e)}"],
                attempt=attempt,
                max_attempts=self.config.max_retries_per_stage
            )

        # Check required tags
        all_tags = [elem.tag for elem in root.iter()]
        for req in stage.required_elements:
            if not any(req in t for t in all_tags):
                issues.append(f"Missing required element <{req}> for stage {stage.stage.value}.")

        # Check center split
        if "250" not in svg_output:
            issues.append("Central symmetry axis (X=250) not detected in coordinate stream.")

        # Stage specific checks
        if stage.stage == PassStage.SKELETON:
            circles = [e for e in all_tags if "circle" in e]
            if len(circles) < 4:
                issues.append(f"Too few skeleton anchor points: found {len(circles)}, required >= 4.")

        elif stage.stage == PassStage.STRUCTURE:
            # Check for neck bridging
            lower_svg = svg_output.lower()
            if ("head" in lower_svg or "skull" in lower_svg) and ("body" in lower_svg or "torso" in lower_svg):
                if not any(k in lower_svg for k in ["neck", "collar", "ruff", "throat", "seam"]):
                    issues.append("Missing explicit neck/collar bridge element between head and torso.")

        elif stage.stage == PassStage.SHADING:
            defs_grads = bool(re.search(r"<(linearGradient|radialGradient)", svg_output))
            if not defs_grads:
                issues.append("No gradients found in shading stage.")

        passed = len(issues) == 0
        return StageResult(
            stage=stage.stage,
            svg_output=svg_output,
            validation_passed=passed,
            validation_issues=issues,
            attempt=attempt,
            max_attempts=self.config.max_retries_per_stage
        )

    def advance(self, result: StageResult) -> bool:
        self.history.append(result)
        if result.validation_passed:
            self.current_svg = result.svg_output
            return True
        return False

    async def run(self, generator_fn: Callable[[str], Awaitable[str]]) -> str:
        """Runs the complete multi-pass pipeline asynchronously using an LLM callback."""
        svg_accumulator = ""
        for stage in self.config.stages:
            for attempt in range(1, self.config.max_retries_per_stage + 1):
                prompt = self.build_prompt(stage, svg_accumulator)
                raw_response = await generator_fn(prompt)

                # Extract SVG
                svg_match = re.search(r"<svg.*?</svg>", raw_response, re.DOTALL)
                svg_code = svg_match.group(0) if svg_match else raw_response

                result = self.validate_stage(stage, svg_code, attempt=attempt)
                if self.advance(result):
                    svg_accumulator = result.svg_output
                    break
        return self.current_svg
