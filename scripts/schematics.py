#!/usr/bin/env python3
"""
schematics.py — The HTML/CSS/JS schematic thumbnails.

Why schematics exist
--------------------
Ten native visual types have no honest single-glyph stand-in. A gauge-shaped icon for
the KPI visual would tell a reader something false; a 100% stacked column chart is
*defined* by the fact that every column is the same height, which a column glyph cannot
convey because the glyph's whole meaning is height varying.

For those, the gallery draws a small labelled diagram instead of showing an icon.

Why drawn rather than fetched
-----------------------------
The two obvious sources are both unusable. A Desktop screenshot is Windows-only, depends
on DPI and theme, and makes only one machine able to regenerate the gallery. A Microsoft
Learn documentation image is Microsoft's copyrighted content, licensed for internal use
rather than redistribution - the reasoning that already keeps the .pbiviz packages out of
this repository.

So these are drawn from the *concept* of each visual, not traced from a reference. A
normalised stack is columns normalised to equal height because that is what the visual
does; a combo chart is two marks on two axes because that is what it draws. No Microsoft
icon silhouette, card geometry or pixel styling is reproduced. The shapes are generic data
visualisation forms.

These are labelled schematics, not renders, and the gallery says so on every one. That
distinction is load-bearing: a reader must never conclude that a schematic is what the
visual will look like with their data.

All art is inline SVG using `currentColor`, so it themes with the page and needs no assets.
"""
from __future__ import annotations

# Every schematic is a 64x40 viewBox so the grid stays visually even against 24x24 icons.
W, H = 64, 40
_FRAME = 'stroke="currentColor" fill="none" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"'
_BAR = 'fill="currentColor" fill-opacity="0.22" stroke="currentColor" stroke-width="1.2"'
_LINE = 'stroke="currentColor" stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round"'
_SOLID = 'fill="currentColor"'
_DIM = 'fill="currentColor" fill-opacity="0.14"'

# 100%-stacked variants: every column identical in height. The equal heights ARE the
# defining property, which is precisely what a normal column icon denies.
def _stack_vertical(segments: list[float], label_equal: bool = True) -> str:
    total = sum(segments)
    parts, y = [], H - 3
    scale = (H - 8) / total
    for frac in segments:
        hgt = frac * scale
        y -= hgt
        parts.append(f'<rect class="sch-bar" x="16" y="{y:.1f}" width="14" height="{hgt:.1f}"/>')
    top = y
    rule = (f'<line class="sch-rule" x1="12" y1="{top:.1f}" x2="56" y2="{top:.1f}" '
            f'stroke="currentColor" stroke-width="1.2" stroke-dasharray="3 2"/>'
            if label_equal else "")
    base = f'<line class="sch-axis" x1="12" y1="{H-3}" x2="56" y2="{H-3}" stroke="currentColor" stroke-width="1.2"/>'
    cols = "".join(parts)
    rest = "".join(
        f'<rect class="sch-bar" x="{32 + i*7}" y="{H-3 - frac*(H-8):.1f}" width="5" height="{frac*(H-8):.1f}"/>'
        for i, frac in enumerate((0.5, 0.9, 0.35))
    )
    return (f'<line class="sch-axis" x1="{12+18}" y1="{H-3}" x2="{12+18}" y2="4" stroke="currentColor" stroke-width="1.2"/>'
            f'<rect class="sch-bar" x="20" y="10" width="5" height="{H-13:.1f}"/>{rest}{cols}{base}{rule}')


def _stack_horizontal(segments: list[float]) -> str:
    parts, x = [], 8
    scale = (W - 24) / sum(segments)
    for frac in segments:
        wid = frac * scale
        parts.append(f'<rect class="sch-bar" x="{x:.1f}" y="12" width="{wid:.1f}" height="16"/>')
        x += wid
    return "".join(parts) + '<line class="sch-axis" x1="8" y1="34" x2="56" y2="34" stroke="currentColor" stroke-width="1.2"/>'


def _combo(stacked: bool) -> str:
    base = H - 4
    cols = []
    for i, hgt in enumerate((0.45, 0.7, 0.3, 0.6)):
        x = 10 + i * 11
        if stacked:
            split = base - hgt * (H - 14)
            cols.append(f'<rect class="sch-bar" x="{x}" y="{split:.1f}" width="7" height="{(base-split)*0.55:.1f}"/>'
                        f'<rect class="sch-bar" x="{x}" y="{base-(base-split)*0.55:.1f}" width="7" height="{(base-split)*0.45:.1f}"/>')
        else:
            cols.append(f'<rect class="sch-bar" x="{x}" y="{base - hgt*(H-12):.1f}" width="7" height="{hgt*(H-12):.1f}"/>')
    pts = " ".join(f"{10 + i*11 + 3.5},{base - h*(H-16):.1f}" for i, h in enumerate((0.8, 0.55, 0.9, 0.4)))
    return ("".join(cols)
            + f'<line class="sch-axis" x1="8" y1="{base}" x2="56" y2="{base}" stroke="currentColor" stroke-width="1.2"/>'
            + f'<polyline points="{pts}" class="sch-line"/>'
            + f'<circle cx="{10+3*11+3.5:.0f}" cy="{base-0.4*(H-16):.1f}" r="1.7" class="sch-dot"/>')


def _ribbon() -> str:
    rows = []
    for r in range(3):
        y = 7 + r * 11
        widths = ((30, 22, 26, 18), (22, 26, 18, 24), (18, 24, 30, 20))[r]
        x = 8
        segs = []
        for w in widths:
            segs.append(f'<rect class="sch-bar" x="{x}" y="{y}" width="{w}" height="8" rx="1"/>')
            x += w
        rows.append("".join(segs))
    return "".join(rows) + '<line class="sch-axis" x1="8" y1="36" x2="56" y2="36" stroke="currentColor" stroke-width="1.2"/>'


def _kpi() -> str:
    return (
        '<rect class="sch-panel" x="6" y="6" width="52" height="28" rx="2"/>'
        f'<rect class="sch-solid" x="10" y="11" width="16" height="5" rx="1"/>'
        f'<rect class="sch-solid" x="10" y="20" width="26" height="8" rx="1"/>'
        f'<rect class="sch-bar" x="42" y="20" width="12" height="8" rx="1"/>'
        f'<line class="sch-axis" x1="42" y1="24" x2="58" y2="24" stroke="currentColor" stroke-width="1.2" stroke-dasharray="2 2"/>'
    )


def _key_drivers() -> str:
    rows = []
    for i, (label, up) in enumerate((("+", True), ("+", True), ("-", False))):
        y = 7 + i * 9
        rows.append(f'<rect class="sch-solid" x="8" y="{y}" width="6" height="6" rx="1"/>')
        bar = (f'<rect class="sch-bar" x="18" y="{y}" width="{26 - i*4}" height="6" rx="1"/>'
               if up else
               f'<rect class="sch-bar" x="18 - {10-i*2}" y="{y}" width="{10-i*2}" height="6" rx="1"/>')
        axis = f'<line class="sch-axis" x1="18" y1="{y-2}" x2="18" y2="{y+8}" stroke="currentColor" stroke-width="1"/>'
        rows.append(bar + axis)
    return "".join(rows)


def _narrative() -> str:
    return (
        '<rect class="sch-panel" x="6" y="5" width="52" height="30" rx="2"/>'
        f'<rect class="sch-solid" x="10" y="9" width="22" height="4" rx="1"/>'
        f'<rect class="sch-bar" x="10" y="17" width="44" height="3" rx="1"/>'
        f'<rect class="sch-bar" x="10" y="23" width="36" height="3" rx="1"/>'
        f'<rect class="sch-bar" x="10" y="29" width="24" height="3" rx="1"/>'
    )


SCHEMATICS: dict[str, str] = {
    "hundredPercentStackedAreaChart": _stack_vertical([0.45, 0.3, 0.25]),
    "hundredPercentStackedColumnChart": _stack_vertical([0.4, 0.35, 0.25]),
    "hundredPercentStackedBarChart": _stack_horizontal([0.45, 0.3, 0.25]),
    "lineClusteredColumnComboChart": _combo(stacked=False),
    "lineStackedColumnComboChart": _combo(stacked=True),
    "ribbonChart": _ribbon(),
    "kpi": _kpi(),
    "keyDriversVisual": _key_drivers(),
    "narrative": _narrative(),
    "aiNarratives": _narrative(),
}

CSS = """
.thumb-schem{stroke:currentColor}
.thumb-schem .sch-bar{fill:currentColor;fill-opacity:.20;stroke:currentColor;stroke-width:1.1}
.thumb-schem .sch-solid{fill:currentColor;fill-opacity:.85}
.thumb-schem .sch-line{stroke:currentColor;stroke-width:1.8;fill:none;stroke-linecap:round;stroke-linejoin:round}
.thumb-schem .sch-dot{fill:currentColor}
.thumb-schem .sch-panel,.thumb-schem .sch-rule{stroke:currentColor;stroke-width:1.1;fill:none;stroke-opacity:.55}
.thumb-schem .sch-axis{stroke:currentColor;stroke-opacity:.5;stroke-width:1.2}
"""


def svg_for(visual_type: str) -> str | None:
    """Inline SVG markup for a schematic type, or None if it has none."""
    body = SCHEMATICS.get(visual_type)
    if body is None:
        return None
    return (f'<svg class="thumb-schem" viewBox="0 0 {W} {H}" width="64" height="40" '
            f'role="img" aria-hidden="true" focusable="false">{body}</svg>')


def known() -> set[str]:
    return set(SCHEMATICS)