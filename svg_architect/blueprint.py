"""
Spatial Blueprint: Mathematical and Topological Coordinate Engine.
Enforces deterministic symmetry, plane-splitting, and Z-stack ordering before rendering.
"""

from typing import List, Tuple, Optional
from pydantic import BaseModel, Field


class SymmetricAnchor(BaseModel):
    name: str
    x_left: float
    y: float
    canvas_width: float = 500.0

    @property
    def x_right(self) -> float:
        """Computes deterministic mirror coordinate: X_R = Width - X_L"""
        return self.canvas_width - self.x_left

    @property
    def mirror_sum(self) -> float:
        return self.x_left + self.x_right

    def as_pair(self) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        return ((self.x_left, self.y), (self.x_right, self.y))


class AnatomicalSeam(BaseModel):
    """Enforces negative overlap and zero-gap continuity between connected anatomical structures."""
    structure_a: str = "Cranium / Jaw"
    structure_b: str = "Torso / Shoulders"
    connector_name: str = "Neck & Collar Bridge"
    a_bottom_y: float = 240.0
    b_top_y: float = 280.0
    connector_top_y: float = 210.0
    connector_bottom_y: float = 300.0
    min_overlap: float = 15.0

    def validate_continuity(self) -> List[str]:
        issues = []
        if self.connector_top_y > self.a_bottom_y - self.min_overlap:
            issues.append(
                f"Severed Gap: {self.connector_name} top (Y={self.connector_top_y}) does not overlap "
                f"{self.structure_a} base (Y={self.a_bottom_y}) by >= {self.min_overlap}px."
            )
        if self.connector_bottom_y < self.b_top_y + self.min_overlap:
            issues.append(
                f"Disconnection: {self.connector_name} bottom (Y={self.connector_bottom_y}) does not overlap "
                f"{self.structure_b} top (Y={self.b_top_y}) by >= {self.min_overlap}px."
            )
        return issues


class ZStackLayer(BaseModel):
    layer_id: int
    name: str
    description: str
    elements: List[str] = Field(default_factory=list)
    gradient_ids: List[str] = Field(default_factory=list)


class ZStackManifest(BaseModel):
    layers: List[ZStackLayer] = Field(default_factory=list)

    @classmethod
    def default_superhero_stack(cls) -> "ZStackManifest":
        return cls(
            layers=[
                ZStackLayer(layer_id=0, name="Atmosphere / Background", description="Canvas rect and radial back-glow"),
                ZStackLayer(layer_id=1, name="Back Silhouette", description="Ears, wings, distant hair or cape mantle"),
                ZStackLayer(layer_id=2, name="Neck & Structural Seams", description="Overlapping neck column, collar ruff, and bridge planes"),
                ZStackLayer(layer_id=3, name="Primary Structural Mass", description="Core cranium / torso split down center axis"),
                ZStackLayer(layer_id=4, name="Faceted Volume & Shading", description="Split planes, brow/nose planes, and textures"),
                ZStackLayer(layer_id=5, name="Focal Foreground Details", description="Eyes, specular glints, emblems and 1px edge rims"),
            ]
        )


class SpatialBlueprint(BaseModel):
    view_box: str = "0 0 500 500"
    canvas_width: float = 500.0
    canvas_height: float = 500.0
    center_x: float = 250.0
    center_y: float = 250.0
    anchors: List[SymmetricAnchor] = Field(default_factory=list)
    seams: List[AnatomicalSeam] = Field(default_factory=list)
    manifest: ZStackManifest = Field(default_factory=ZStackManifest.default_superhero_stack)

    def add_anchor(self, name: str, x_left: float, y: float) -> SymmetricAnchor:
        anchor = SymmetricAnchor(name=name, x_left=x_left, y=y, canvas_width=self.canvas_width)
        self.anchors.append(anchor)
        return anchor

    def add_seam(
        self,
        structure_a: str,
        structure_b: str,
        connector_name: str,
        a_bottom_y: float,
        b_top_y: float,
        connector_top_y: float,
        connector_bottom_y: float,
        min_overlap: float = 15.0,
    ) -> AnatomicalSeam:
        seam = AnatomicalSeam(
            structure_a=structure_a,
            structure_b=structure_b,
            connector_name=connector_name,
            a_bottom_y=a_bottom_y,
            b_top_y=b_top_y,
            connector_top_y=connector_top_y,
            connector_bottom_y=connector_bottom_y,
            min_overlap=min_overlap,
        )
        self.seams.append(seam)
        return seam

    def render_markdown_spec(self) -> str:
        """Generates the technical spatial_blueprint XML block for LLMs."""
        lines = [
            "<spatial_blueprint>",
            f"1. Canvas & Axis:",
            f'   viewBox="{self.view_box}", Center_X = {self.center_x}',
            f"   Mirror Formula: X_R = {self.canvas_width} - X_L (identical Y)",
            "",
            "2. Symmetric Anchor Table:",
            "   +-----------------------------+--------------+---------------+------------------------+",
            "   | Landmark Feature            | Left [X_L,Y] | Right [X_R,Y] | Formula Check (L + R)  |",
            "   +-----------------------------+--------------+---------------+------------------------+",
        ]
        for a in self.anchors:
            lines.append(
                f"   | {a.name:<27} | [{a.x_left:>4.0f}, {a.y:>4.0f}]   | [{a.x_right:>4.0f}, {a.y:>4.0f}]   | {a.x_left + a.x_right:4.0f} (Exact Mirror)  |"
            )
        lines.extend([
            "   +-----------------------------+--------------+---------------+------------------------+",
            "",
            "3. Z-Stack Ordering Manifest:",
        ])
        for layer in self.manifest.layers:
            lines.append(f"   - Layer {layer.layer_id} ({layer.name}): {layer.description}")

        if self.seams:
            lines.extend([
                "",
                "4. Anatomical Continuity & Seam Lock (Zero-Gap Enforced):",
            ])
            for s in self.seams:
                lines.append(
                    f"   - Seam [{s.structure_a} -> {s.structure_b}]: "
                    f"Bridge '{s.connector_name}' extends Y=[{s.connector_top_y:.0f} to {s.connector_bottom_y:.0f}] "
                    f"(Overlap: >= {s.min_overlap:.0f}px past base Y={s.a_bottom_y:.0f} and shoulders Y={s.b_top_y:.0f})"
                )

        lines.append("</spatial_blueprint>")
        return "\n".join(lines)
