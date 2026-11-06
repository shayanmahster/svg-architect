"""
Color Harmony Engine for AI-generated SVGs.
Extracts, converts, and evaluates palettes using HSL color theory and WCAG contrast rules.
"""

import re
import colorsys
from typing import List, Tuple, Optional, Dict, Any
from pydantic import BaseModel, Field


class ColorInfo(BaseModel):
    hex: str
    r: int
    g: int
    b: int
    h: float  # 0.0 - 360.0
    s: float  # 0.0 - 1.0
    l: float  # 0.0 - 1.0


class PaletteReport(BaseModel):
    colors_found: List[ColorInfo]
    unique_hues: int
    dominant_color: Optional[ColorInfo] = None
    contrast_pairs: List[Tuple[str, str, float]] = Field(default_factory=list)
    harmony_type: Optional[str] = None
    saturation_balance: float = 0.5
    issues: List[str] = Field(default_factory=list)


class ColorHarmonyEngine:
    @staticmethod
    def hex_to_rgb(hex_str: str) -> Tuple[int, int, int]:
        clean = hex_str.strip().lstrip("#")
        if len(clean) == 3:
            clean = "".join(c * 2 for c in clean)
        if len(clean) != 6:
            return (128, 128, 128)
        return (int(clean[0:2], 16), int(clean[2:4], 16), int(clean[4:6], 16))

    @staticmethod
    def hex_to_hsl(hex_str: str) -> Tuple[float, float, float]:
        r, g, b = ColorHarmonyEngine.hex_to_rgb(hex_str)
        r_norm, g_norm, b_norm = r / 255.0, g / 255.0, b / 255.0
        h, l, s = colorsys.rgb_to_hls(r_norm, g_norm, b_norm)
        return (round(h * 360.0, 1), round(s, 3), round(l, 3))

    @staticmethod
    def relative_luminance(r: int, g: int, b: int) -> float:
        def adjust(c: float) -> float:
            c = c / 255.0
            return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
        return 0.2126 * adjust(r) + 0.7152 * adjust(g) + 0.0722 * adjust(b)

    @staticmethod
    def contrast_ratio(c1_hex: str, c2_hex: str) -> float:
        r1, g1, b1 = ColorHarmonyEngine.hex_to_rgb(c1_hex)
        r2, g2, b2 = ColorHarmonyEngine.hex_to_rgb(c2_hex)
        l1 = ColorHarmonyEngine.relative_luminance(r1, g1, b1)
        l2 = ColorHarmonyEngine.relative_luminance(r2, g2, b2)
        lighter = max(l1, l2)
        darker = min(l1, l2)
        return round((lighter + 0.05) / (darker + 0.05), 2)

    @staticmethod
    def extract_colors(svg_string: str) -> List[str]:
        """Finds all hex color strings inside SVG attributes and style declarations."""
        matches = re.findall(r'#(?:[0-9a-fA-F]{3}){1,2}\b', svg_string)
        # Normalize to 6-char lowercase hex
        normalized = []
        for m in matches:
            hex_body = m.lstrip("#").lower()
            if len(hex_body) == 3:
                hex_body = "".join(c * 2 for c in hex_body)
            if len(hex_body) == 6:
                normalized.append(f"#{hex_body}")
        # Retain order of occurrence without immediate duplicates
        seen = set()
        result = []
        for c in normalized:
            if c not in seen:
                seen.add(c)
                result.append(c)
        return result

    @staticmethod
    def analyze_palette(svg_string: str) -> PaletteReport:
        raw_colors = ColorHarmonyEngine.extract_colors(svg_string)
        if not raw_colors:
            return PaletteReport(
                colors_found=[],
                unique_hues=0,
                issues=["Zero hex colors extracted from SVG."]
            )

        color_infos: List[ColorInfo] = []
        for hex_code in raw_colors:
            r, g, b = ColorHarmonyEngine.hex_to_rgb(hex_code)
            h, s, l = ColorHarmonyEngine.hex_to_hsl(hex_code)
            color_infos.append(ColorInfo(hex=hex_code, r=r, g=g, b=b, h=h, s=s, l=l))

        # Check unique hues (group within 15 degrees)
        hues = [c.h for c in color_infos if c.s > 0.15 and 0.05 < c.l < 0.95]
        unique_hues = len(set(round(h / 20.0) for h in hues))

        # Saturation balance
        avg_sat = sum(c.s for c in color_infos) / len(color_infos)

        issues = []
        if avg_sat > 0.90:
            issues.append("Oversaturation: Palette lacks resting desaturated/neutral anchor tones.")
        elif avg_sat < 0.10:
            issues.append("Under-saturation: Vector appears nearly monochrome grayscale.")

        # Harmony detection
        harmony_type = "eclectic"
        if len(hues) >= 2:
            min_hue = min(hues)
            max_hue = max(hues)
            diff = abs(max_hue - min_hue)
            if diff < 45 or diff > 315:
                harmony_type = "analogous"
            elif 150 < diff < 210:
                harmony_type = "complementary"
            elif 100 < diff < 140:
                harmony_type = "triadic"
            elif len(hues) <= 1:
                harmony_type = "monochromatic"

        # Check contrast with background or between successive colors
        contrast_pairs = []
        if len(raw_colors) >= 2:
            for i in range(min(5, len(raw_colors) - 1)):
                c1, c2 = raw_colors[i], raw_colors[i + 1]
                ratio = ColorHarmonyEngine.contrast_ratio(c1, c2)
                contrast_pairs.append((c1, c2, ratio))

        return PaletteReport(
            colors_found=color_infos,
            unique_hues=unique_hues,
            dominant_color=color_infos[0] if color_infos else None,
            contrast_pairs=contrast_pairs,
            harmony_type=harmony_type,
            saturation_balance=round(avg_sat, 2),
            issues=issues
        )

    @staticmethod
    def suggest_palette(mood: str = "vibrant") -> List[str]:
        """Provides harmonized 5-swatch palette schemes (Primary, Secondary, Accent, Shadow, Highlight)."""
        palettes: Dict[str, List[str]] = {
            "vibrant": ["#dc2626", "#ea580c", "#facc15", "#1e1b4b", "#ffffff"],
            "looney_tunes": ["#dc2626", "#ea580c", "#808ea4", "#090d16", "#ffffff"],
            "western": ["#a8070c", "#ffae00", "#1a0d0a", "#9e7340", "#fef3c7"],
            "dark_knight": ["#0b0f19", "#1e293b", "#38bdf8", "#020617", "#94a3b8"],
            "comic_hero": ["#ef4444", "#3b82f6", "#0f172a", "#fef08a", "#ffffff"],
            "pastel": ["#fbcfe8", "#c7d2fe", "#fef08a", "#475569", "#ffffff"],
            "noir": ["#000000", "#18181b", "#71717a", "#ffffff", "#e4e4e7"]
        }
        return palettes.get(mood.lower(), palettes["vibrant"])
