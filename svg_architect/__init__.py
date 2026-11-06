"""
svg-architect: Deterministic Spatial Blueprint Engine for Generative Vector Graphics.
"""

from .blueprint import SpatialBlueprint, SymmetricAnchor, ZStackManifest
from .linter import SVGLinter, LintReport
from .generator import ArchitectProtocol

__version__ = "0.1.0"
__all__ = [
    "SpatialBlueprint",
    "SymmetricAnchor",
    "ZStackManifest",
    "SVGLinter",
    "LintReport",
    "ArchitectProtocol",
]
