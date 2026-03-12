"""
greencode/cli/badge.py
━━━━━━━━━━━━━━━━━━━━━
SVG badge generator.
Produces shields.io-compatible badges with live CO₂ data.
Hosted endpoint: greencode.dev/badge/{owner}/{repo}.svg
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional
from .measure import GRADE_LABELS, HISTORY_DIR, BADGE_FILE, load_latest


# ── Badge dimensions ──────────────────────────────────────────────────────────
BADGE_W      = 148
BADGE_H      = 20
LEFT_W       = 82    # "carbon footprint" section
RIGHT_W      = BADGE_W - LEFT_W
FONT         = "DejaVu Sans,Verdana,Geneva,sans-serif"
FONT_SIZE    = 11
TEXT_Y       = 14


# ── Templates ─────────────────────────────────────────────────────────────────

_SVG_TEMPLATE = """\
<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:xlink="http://www.w3.org/1999/xlink"
     width="{total_w}" height="{h}"
     viewBox="0 0 {total_w} {h}" role="img"
     aria-label="carbon footprint: {value}">
  <title>carbon footprint: {value}</title>

  <defs>
    <linearGradient id="gc-s" x2="0" y2="100%">
      <stop offset="0"   stop-color="#bbb" stop-opacity=".1"/>
      <stop offset="1"   stop-opacity=".1"/>
    </linearGradient>
    <clipPath id="gc-r">
      <rect width="{total_w}" height="{h}" rx="3" fill="#fff"/>
    </clipPath>
  </defs>

  <g clip-path="url(#gc-r)">
    <rect width="{left_w}"  height="{h}" fill="#1a1a2e"/>
    <rect x="{left_w}" width="{right_w}" height="{h}" fill="{color}"/>
    <rect width="{total_w}" height="{h}" fill="url(#gc-s)"/>
  </g>

  <g fill="#fff" text-anchor="middle"
     font-family="{font}" font-size="{font_size}">
    <text x="{left_cx}" y="{text_y}"
          fill="#000" opacity=".25">{left_text}</text>
    <text x="{left_cx}" y="{left_ty}">{left_text}</text>
    <text x="{right_cx}" y="{text_y}"
          fill="#000" opacity=".25">{right_text}</text>
    <text x="{right_cx}" y="{right_ty}">{right_text}</text>
  </g>
</svg>"""


# ── Public API ────────────────────────────────────────────────────────────────

def generate(
    grams: float,
    grade: str,
    style: str = "flat",          # flat | flat-square | for-the-badge
    label: str = "carbon",
) -> str:
    """
    Generate an SVG badge string.

    Args:
        grams:  CO₂ in grams
        grade:  'green' | 'yellow' | 'red'
        style:  Badge visual style
        label:  Left-side label text

    Returns:
        SVG string ready to serve as image/svg+xml
    """
    meta       = GRADE_LABELS.get(grade, GRADE_LABELS["red"])
    color      = meta["color"]
    emoji      = meta["emoji"]
    value_text = f"{emoji} {grams:.1f}g CO\u2082"   # e.g. "🌿 4.2g CO₂"
    left_text  = label
    right_text = value_text

    lw = LEFT_W
    rw = RIGHT_W
    tw_total = BADGE_W

    return _SVG_TEMPLATE.format(
        total_w  = tw_total,
        h        = BADGE_H,
        left_w   = lw,
        right_w  = rw,
        color    = color,
        font     = FONT,
        font_size= FONT_SIZE,
        text_y   = TEXT_Y,
        left_text  = left_text,
        right_text = right_text,
        left_cx  = lw // 2,
        right_cx = lw + rw // 2,
        left_ty  = TEXT_Y - 1,
        right_ty = TEXT_Y - 1,
        value    = f"{grams:.1f}g CO2",
    )


def save(svg: str, path: Optional[Path] = None) -> Path:
    """Write SVG to disk. Default: .greencode/badge.svg"""
    out = Path(path) if path else BADGE_FILE
    out.parent.mkdir(exist_ok=True)
    out.write_text(svg, encoding="utf-8")
    return out


def generate_from_latest() -> Optional[str]:
    """Generate badge from the most recent measurement on disk."""
    result = load_latest()
    if not result:
        return None
    return generate(
        grams=result["grams_co2"],
        grade=result["grade"],
    )


def readme_snippet(owner: str, repo: str) -> str:
    """
    Returns the Markdown snippet to paste into README.md.

    Example output:
        [![Carbon](https://greencode.dev/badge/acme/myrepo.svg)](https://greencode.dev)
    """
    url    = f"https://greencode.dev/badge/{owner}/{repo}.svg"
    target = f"https://greencode.dev/u/{owner}/{repo}"
    return f"[![Carbon Footprint]({url})]({target})"


# ── Badge variants ────────────────────────────────────────────────────────────

def generate_all_grades() -> dict[str, str]:
    """Useful for docs: generate sample badges for all three grades."""
    samples = {
        "green":  (4.2,  "green"),
        "yellow": (28.5, "yellow"),
        "red":    (87.3, "red"),
    }
    return {k: generate(g, grade) for k, (g, grade) in samples.items()}
