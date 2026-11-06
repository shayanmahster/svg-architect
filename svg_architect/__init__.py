"""
svg-architect: Deterministic Spatial Blueprint & Multi-Pass Synthesis Engine for Generative Vector Graphics.
"""

from .blueprint import SpatialBlueprint, SymmetricAnchor, ZStackManifest, AnatomicalSeam
from .linter import SVGLinter, LintReport
from .generator import ArchitectProtocol
from .analyzer import GeometricAnalyzer, GeometricReport, ShapeBBox, CoverageMap
from .proportions import ProportionTemplate, PROPORTION_PRESETS
from .lighting import LightingModel, LightSource
from .harmony import ColorHarmonyEngine, PaletteReport, ColorInfo
from .codebook import StyleCodebook, SVGAtom
from .pipeline import MultiPassPipeline, PipelineConfig, PassStage, StageConfig, StageResult
from .critic import VisionCriticLoop, VisionCriticConfig, CritiqueResult

__version__ = "0.2.0"

__all__ = [
    "SpatialBlueprint",
    "SymmetricAnchor",
    "ZStackManifest",
    "AnatomicalSeam",
    "SVGLinter",
    "LintReport",
    "ArchitectProtocol",
    "GeometricAnalyzer",
    "GeometricReport",
    "ShapeBBox",
    "CoverageMap",
    "ProportionTemplate",
    "PROPORTION_PRESETS",
    "LightingModel",
    "LightSource",
    "ColorHarmonyEngine",
    "PaletteReport",
    "ColorInfo",
    "StyleCodebook",
    "SVGAtom",
    "MultiPassPipeline",
    "PipelineConfig",
    "PassStage",
    "StageConfig",
    "StageResult",
    "VisionCriticLoop",
    "VisionCriticConfig",
    "CritiqueResult",
]
