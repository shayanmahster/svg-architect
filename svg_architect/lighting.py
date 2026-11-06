"""
Physics-based 3-point lighting model for SVG shading and gradients.
Simulates key, fill, and rim light sources to produce physically convincing vector gradients.
"""

import math
from typing import Tuple, List, Optional
from pydantic import BaseModel, Field


def hex_to_rgb(hex_str: str) -> Tuple[int, int, int]:
    clean = hex_str.strip().lstrip("#")
    if len(clean) == 3:
        clean = "".join(c * 2 for c in clean)
    if len(clean) != 6:
        return (128, 128, 128)
    return (int(clean[0:2], 16), int(clean[2:4], 16), int(clean[4:6], 16))


def rgb_to_hex(r: int, g: int, b: int) -> str:
    r = max(0, min(255, int(r)))
    g = max(0, min(255, int(g)))
    b = max(0, min(255, int(b)))
    return f"#{r:02x}{g:02x}{b:02x}"


def lighten_color(hex_str: str, percent: float) -> str:
    r, g, b = hex_to_rgb(hex_str)
    factor = 1.0 + percent
    return rgb_to_hex(r * factor, g * factor, b * factor)


def darken_color(hex_str: str, percent: float) -> str:
    r, g, b = hex_to_rgb(hex_str)
    factor = max(0.0, 1.0 - percent)
    return rgb_to_hex(r * factor, g * factor, b * factor)


def mix_colors(c1: str, c2: str, weight: float = 0.5) -> str:
    r1, g1, b1 = hex_to_rgb(c1)
    r2, g2, b2 = hex_to_rgb(c2)
    w = max(0.0, min(1.0, weight))
    r = r1 * (1 - w) + r2 * w
    g = g1 * (1 - w) + g2 * w
    b = b1 * (1 - w) + b2 * w
    return rgb_to_hex(r, g, b)


class LightSource(BaseModel):
    name: str = "key"
    x: float = 150.0
    y: float = 100.0
    intensity: float = 1.0
    color: str = "#ffffff"


class LightingModel(BaseModel):
    """Virtual 3-point studio lighting for deterministic SVG vector shading."""
    key_light: LightSource = Field(default_factory=lambda: LightSource(name="key", x=150.0, y=100.0, intensity=1.0, color="#ffffff"))
    fill_light: LightSource = Field(default_factory=lambda: LightSource(name="fill", x=400.0, y=200.0, intensity=0.4, color="#e0e8ff"))
    rim_light: LightSource = Field(default_factory=lambda: LightSource(name="rim", x=250.0, y=50.0, intensity=0.6, color="#ffffff"))

    def compute_gradient_angle(self, polygon_center_x: float, polygon_center_y: float) -> float:
        """Computes linearGradient vector angle (degrees) pointing away from key light."""
        dx = polygon_center_x - self.key_light.x
        dy = polygon_center_y - self.key_light.y
        angle = math.degrees(math.atan2(dy, dx))
        return (angle + 360) % 360

    def compute_shadow_intensity(self, polygon_center_x: float, polygon_center_y: float) -> float:
        """Distance-based shadow intensity factor (0.0 fully lit, 1.0 deep shadow)."""
        dist_key = math.hypot(polygon_center_x - self.key_light.x, polygon_center_y - self.key_light.y)
        max_dist = 500.0
        normalized = min(1.0, dist_key / max_dist)
        return round(normalized * (1.0 - self.fill_light.intensity * 0.3), 3)

    def compute_highlight_color(self, base_color: str, polygon_center_x: float, polygon_center_y: float) -> str:
        dist_key = math.hypot(polygon_center_x - self.key_light.x, polygon_center_y - self.key_light.y)
        proximity = max(0.0, 1.0 - (dist_key / 400.0))
        boost = proximity * 0.35 * self.key_light.intensity
        tinted = mix_colors(base_color, self.key_light.color, weight=proximity * 0.25)
        return lighten_color(tinted, boost)

    def compute_shadow_color(self, base_color: str, polygon_center_x: float, polygon_center_y: float) -> str:
        shadow_factor = self.compute_shadow_intensity(polygon_center_x, polygon_center_y)
        return darken_color(base_color, shadow_factor * 0.5)

    def generate_gradient_pair(
        self,
        gradient_id: str,
        base_color: str,
        cx: float,
        cy: float,
        is_linear: bool = True
    ) -> str:
        """Generates a complete <linearGradient> SVG string with physically calculated angles and stop colors."""
        lit_color = self.compute_highlight_color(base_color, cx, cy)
        shadow_color = self.compute_shadow_color(base_color, cx, cy)
        angle = self.compute_gradient_angle(cx, cy)

        rad = math.radians(angle)
        x1 = round(50 - 50 * math.cos(rad), 1)
        y1 = round(50 - 50 * math.sin(rad), 1)
        x2 = round(50 + 50 * math.cos(rad), 1)
        y2 = round(50 + 50 * math.sin(rad), 1)

        return (
            f'<linearGradient id="{gradient_id}" x1="{x1}%" y1="{y1}%" x2="{x2}%" y2="{y2}%">\n'
            f'  <stop offset="0%" stop-color="{lit_color}"/>\n'
            f'  <stop offset="60%" stop-color="{base_color}"/>\n'
            f'  <stop offset="100%" stop-color="{shadow_color}"/>\n'
            f'</linearGradient>'
        )

    @classmethod
    def cinematic_preset(cls) -> "LightingModel":
        """Dramatic high-contrast side-lit cinematic rig."""
        return cls(
            key_light=LightSource(name="key", x=80, y=120, intensity=1.2, color="#fff4e0"),
            fill_light=LightSource(name="fill", x=440, y=300, intensity=0.25, color="#3b82f6"),
            rim_light=LightSource(name="rim", x=250, y=20, intensity=0.85, color="#38bdf8"),
        )

    @classmethod
    def cartoon_preset(cls) -> "LightingModel":
        """Vibrant, front-lit Looney Tunes / Disney aesthetic with soft shadows."""
        return cls(
            key_light=LightSource(name="key", x=180, y=80, intensity=0.9, color="#ffffff"),
            fill_light=LightSource(name="fill", x=350, y=180, intensity=0.55, color="#f1f5f9"),
            rim_light=LightSource(name="rim", x=250, y=30, intensity=0.4, color="#fef08a"),
        )

    @classmethod
    def noir_preset(cls) -> "LightingModel":
        """Extreme contrast graphic novel / Frank Miller lighting."""
        return cls(
            key_light=LightSource(name="key", x=50, y=50, intensity=1.5, color="#ffffff"),
            fill_light=LightSource(name="fill", x=450, y=450, intensity=0.1, color="#0f172a"),
            rim_light=LightSource(name="rim", x=250, y=10, intensity=1.0, color="#ffffff"),
        )
