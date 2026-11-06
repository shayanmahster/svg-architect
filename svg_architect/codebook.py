"""
Style DNA Codebook: Reusable, paramaterized SVG micro-atoms for characters, props, and facial features.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class SVGAtom(BaseModel):
    name: str
    category: str  # "eye", "nose", "mouth", "fur", "hat", "emblem"
    style: str     # "looney_tunes", "realistic", "superhero"
    template: str
    parameters: Dict[str, Any] = Field(default_factory=dict)

    def render(self, cx: float, cy: float, scale: float = 1.0, **overrides) -> str:
        params = {**self.parameters, **overrides, "cx": cx, "cy": cy, "scale": scale}
        out = self.template
        for k, v in params.items():
            out = out.replace(f"{{{k}}}", str(v))
        return out


class StyleCodebook(BaseModel):
    atoms: Dict[str, SVGAtom] = Field(default_factory=dict)

    def get_atom(self, name: str) -> Optional[SVGAtom]:
        return self.atoms.get(name)

    def get_by_category(self, category: str, style: Optional[str] = None) -> List[SVGAtom]:
        res = [a for a in self.atoms.values() if a.category == category]
        if style:
            res = [a for a in res if a.style == style]
        return res

    def register(self, atom: SVGAtom):
        self.atoms[atom.name] = atom

    @classmethod
    def default(cls) -> "StyleCodebook":
        cb = cls()

        # Looney Tunes Cartoon Eye
        cb.register(SVGAtom(
            name="looney_eye_oval",
            category="eye",
            style="looney_tunes",
            template="""<g transform="translate({cx}, {cy}) scale({scale})">
  <ellipse cx="0" cy="0" rx="16" ry="30" fill="#ffffff" stroke="#090d16" stroke-width="4"/>
  <path d="M -14,-12 Q 0,-4 14,-12" fill="none" stroke="#090d16" stroke-width="3.5"/>
  <ellipse cx="4" cy="4" rx="7" ry="11" fill="#090d16"/>
  <circle cx="2" cy="0" r="2.5" fill="#ffffff"/>
</g>""",
            parameters={}
        ))

        # Looney Tunes Buck Teeth
        cb.register(SVGAtom(
            name="looney_buck_teeth",
            category="mouth",
            style="looney_tunes",
            template="""<g transform="translate({cx}, {cy}) scale({scale})" stroke="#090d16" stroke-width="3.5">
  <rect x="-12" y="0" width="11" height="18" rx="2" fill="#ffffff"/>
  <rect x="1" y="0" width="11" height="18" rx="2" fill="#ffffff"/>
</g>""",
            parameters={}
        ))

        # Warner Bros Neck Fur Ruff (Anti-Severing Lock)
        cb.register(SVGAtom(
            name="fur_collar_ruff",
            category="fur",
            style="looney_tunes",
            template="""<g transform="translate({cx}, {cy}) scale({scale})">
  <path d="M 0,0 C -15,5 -35,17 -30,31 C -22,35 -10,43 0,53 C 10,43 22,35 30,31 C 35,17 15,5 0,0 Z" 
        fill="{fill_color}" stroke="{stroke_color}" stroke-width="{stroke_width}"/>
  <line x1="0" y1="15" x2="0" y2="47" stroke="#94a3b8" stroke-width="2.5" stroke-linecap="round"/>
</g>""",
            parameters={"fill_color": "#ffffff", "stroke_color": "#090d16", "stroke_width": "4.5"}
        ))

        # Western Gambler Hat (Arthur Morgan style)
        cb.register(SVGAtom(
            name="cowboy_hat_wide",
            category="hat",
            style="realistic",
            template="""<g transform="translate({cx}, {cy}) scale({scale})">
  <!-- Hat Crown -->
  <path d="M -55,-70 C -40,-82 0,-72 0,-72 C 0,-72 40,-82 55,-70 L 78,0 L -78,0 Z" fill="#1f120e"/>
  <!-- Twisted Rope Band -->
  <rect x="-80" y="-8" width="160" height="10" rx="3" fill="#9e7340" stroke="#0d0707" stroke-width="2"/>
  <!-- Asymmetrical Curved Brim -->
  <path d="M -168,27 C -100,5 0,-5 0,-5 C 0,-5 100,-5 168,14 C 110,48 -110,48 -168,27 Z" fill="#140b09" stroke="#0d0707" stroke-width="3"/>
</g>""",
            parameters={}
        ))

        # Spider-Man Chest Emblem
        cb.register(SVGAtom(
            name="spider_emblem",
            category="emblem",
            style="superhero",
            template="""<g transform="translate({cx}, {cy}) scale({scale})">
  <!-- Spider Diamond Core -->
  <path d="M 0,-18 L 8,0 L 0,18 L -8,0 Z" fill="#020617"/>
  <!-- Upper Left Legs -->
  <path d="M -4,-8 Q -28,-32 -48,-18 Q -25,-22 -4,-2" fill="none" stroke="#020617" stroke-width="3" stroke-linecap="round"/>
  <path d="M -6,-2 Q -32,-12 -52,10 Q -28,2 -6,4" fill="none" stroke="#020617" stroke-width="3" stroke-linecap="round"/>
  <!-- Upper Right Legs (Mirror) -->
  <path d="M 4,-8 Q 28,-32 48,-18 Q 25,-22 4,-2" fill="none" stroke="#020617" stroke-width="3" stroke-linecap="round"/>
  <path d="M 6,-2 Q 32,-12 52,10 Q 28,2 6,4" fill="none" stroke="#020617" stroke-width="3" stroke-linecap="round"/>
  <!-- Lower Legs -->
  <path d="M -4,6 Q -26,24 -36,52 Q -18,28 -2,12" fill="none" stroke="#020617" stroke-width="2.5" stroke-linecap="round"/>
  <path d="M 4,6 Q 26,24 36,52 Q 18,28 2,12" fill="none" stroke="#020617" stroke-width="2.5" stroke-linecap="round"/>
</g>""",
            parameters={}
        ))

        return cb
