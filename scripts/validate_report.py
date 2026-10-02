#!/usr/bin/env python3
"""
validate_report.py — Offline PBIR layout checks that complement
scripts/validate_pbir_schema.py (schema/JSON shape) and
`powerbi-report-author validate` (PBIR contracts).

Checks:
  GAP-14  Canvas-level layout: overlap, out-of-bounds, off-canvas positions.
          These are invisible to schema validation — every file is structurally
          valid while the page is unusable.
  GAP-17  cardVisual minimum height. The callout value and label can be clipped
          at render time while the visual passes every schema validator.

Usage: python3 scripts/validate_report.py [path-to-.Report-dir ...]

With no arguments, discovers every `.Report` folder under the current directory,
skipping any that `.gitignore` excludes (see scripts/pbir_discovery.py).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pbir_discovery  # noqa: E402

TOLERANCE = 0  # exact-pixel overlap detection

FAIL = 0
WARN = 0


def fail(msg: str) -> None:
    global FAIL
    FAIL += 1
    print(f"[FAIL] {msg}")


def warn(msg: str) -> None:
    global WARN
    WARN += 1
    print(f"[WARN] {msg}")


def ok(msg: str) -> None:
    print(f"[PASS] {msg}")


def rect(pos: dict) -> tuple[float, float, float, float]:
    return (
        float(pos["x"]),
        float(pos["y"]),
        float(pos["x"]) + float(pos["width"]),
        float(pos["y"]) + float(pos["height"]),
    )


def overlaps(a: tuple, b: tuple) -> bool:
    return not (a[2] <= b[0] + TOLERANCE or b[2] <= a[0] + TOLERANCE
                or a[3] <= b[1] + TOLERANCE or b[3] <= a[1] + TOLERANCE)


# ── GAP-17: cardVisual height helpers ─────────────────────────────────────────

def _pbir_num(obj: dict, *keys: str, default: float = 0.0) -> float:
    """Navigate a nested dict by keys, then parse a PBIR Literal number.

    PBIR stores numeric formatting values as:
        {"expr": {"Literal": {"Value": "20D"}}}   (double)
        {"expr": {"Literal": {"Value": "4L"}}}    (long / integer)
    The type suffix is stripped before conversion. Returns ``default`` when the
    key path is absent or the value cannot be parsed as a float.
    """
    try:
        for k in keys:
            obj = obj[k]  # type: ignore[assignment]
        raw = obj.get("expr", {}).get("Literal", {}).get("Value", "")  # type: ignore[union-attr]
        return float(str(raw).rstrip("DLdl "))
    except (AttributeError, KeyError, TypeError, ValueError):
        return default


def _pbir_bool(obj: dict, *keys: str, default: bool = False) -> bool:
    """Navigate a nested dict by keys, then parse a PBIR Literal boolean."""
    try:
        for k in keys:
            obj = obj[k]  # type: ignore[assignment]
        raw = obj.get("expr", {}).get("Literal", {}).get("Value", "")  # type: ignore[union-attr]
        return str(raw).lower() in ("true", "1")
    except (AttributeError, KeyError, TypeError, ValueError):
        return default


def _render(font_size_pt: float) -> float:
    """Approximate rendered line height: ceil(fs * 1.5), matching PBI card sizing."""
    return math.ceil(font_size_pt * 1.5)


def check_card_height(vdir: Path, v: dict, page_name: str) -> None:
    """Warn (GAP-17) if a cardVisual's height is insufficient for its content.

    Minimum height formula (from the gap register §12):

        required = border*2
                 + vco_pad_top + vco_pad_bottom
                 + (render(title_fs) + space_below_title) * title_visible
                 + content_pad_top + content_pad_bottom
                 + render(value_fs)
                 + vertical_spacing
                 + render(max(label_fs, 12))   # label always renders ≥ 12pt
                 + accent_bar_width

    Only properties *explicitly set* in the visual JSON are used; everything
    else defaults to 0. This is intentionally conservative — we only flag cases
    where the author set values that provably make the card too short. When
    values are inherited from the theme (unknown at static analysis time),
    the check is silent.
    """
    visual = v.get("visual", {})
    if visual.get("visualType") != "cardVisual":
        return

    pos = v.get("position", {})
    height = float(pos.get("height", 0))
    if not height:
        return

    objs = visual.get("objects", {})
    vc = visual.get("visualContainerObjects", {})

    # VCO border
    border = _pbir_num(vc, "border", "borderWidth", default=0.0)

    # VCO padding — prefer explicit top/bottom; fall back to paddingUniform
    vco_unif = _pbir_num(vc, "padding", "paddingUniform", default=0.0)
    vco_top = _pbir_num(vc, "padding", "paddingTop", default=vco_unif)
    vco_bot = _pbir_num(vc, "padding", "paddingBottom", default=vco_unif)

    # Title — only counted when explicitly shown
    title_show = _pbir_bool(objs, "title", "show", default=False)
    title_fs = _pbir_num(objs, "title", "fontSize", default=12.0)

    # Content padding — prefer explicit top/bottom; fall back to paddingUniform
    pad_unif = _pbir_num(objs, "padding", "paddingUniform", default=0.0)
    pad_top = _pbir_num(objs, "padding", "paddingTop", default=pad_unif)
    pad_bot = _pbir_num(objs, "padding", "paddingBottom", default=pad_unif)

    # Callout value font size
    value_fs = _pbir_num(objs, "calloutValue", "fontSize", default=0.0)

    # Vertical spacing between value and label
    v_spacing = _pbir_num(objs, "spacing", "verticalSpacing", default=0.0)

    # Label — always renders regardless of label.show; effective minimum is 12pt
    label_fs = max(_pbir_num(objs, "label", "fontSize", default=12.0), 12.0)

    # Accent bar — only counted when explicitly shown
    accent_show = _pbir_bool(objs, "accentBar", "show", default=False)
    accent_w = _pbir_num(objs, "accentBar", "width", default=0.0) if accent_show else 0.0

    required = (
        border * 2
        + vco_top + vco_bot
        + (_render(title_fs) + 0) * (1 if title_show else 0)
        + pad_top + pad_bot
        + _render(value_fs)
        + v_spacing
        + _render(label_fs)
        + accent_w
    )

    if required > height:
        warn(
            f"Page '{page_name}': cardVisual '{vdir.name}' may clip "
            f"(min≈{required:.0f}px, actual={height:.0f}px) — "
            f"value={value_fs:.0f}pt label={label_fs:.0f}pt; "
            "reduce font size or increase card height (GAP-17)"
        )


# ── Page check ─────────────────────────────────────────────────────────────────

def check_page(page_file: Path) -> None:
    page = json.loads(page_file.read_text())
    name = page.get("displayName", page_file.parent.name)
    page_w = float(page.get("width", 1280))
    page_h = float(page.get("height", 720))
    ok(f"Page '{name}': canvas {int(page_w)}x{int(page_h)}")

    visuals_dir = page_file.parent / "visuals"
    if not visuals_dir.is_dir():
        warn(f"Page '{name}': no visuals directory")
        return

    boxes: list[tuple[str, tuple, int]] = []
    for vdir in sorted(visuals_dir.iterdir()):
        vfile = vdir / "visual.json"
        if not vfile.is_file():
            continue
        v = json.loads(vfile.read_text())
        pos = v.get("position")
        if not pos:
            fail(f"Page '{name}': visual '{vdir.name}' has no position block")
            continue
        r = rect(pos)

        # Bounds checks (GAP-14)
        if pos["x"] < 0 or pos["y"] < 0:
            fail(f"Page '{name}': '{vdir.name}' has negative position "
                 f"({pos['x']}, {pos['y']})")
        if r[2] > page_w or r[3] > page_h:
            fail(f"Page '{name}': '{vdir.name}' extends past the canvas "
                 f"(right={r[2]:.0f} bottom={r[3]:.0f}, canvas {int(page_w)}x{int(page_h)})")
        boxes.append((vdir.name, r, int(pos.get("z", 0))))

        # Card height check (GAP-17)
        check_card_height(vdir, v, name)

    # Overlap — skipping pairs that differ in z (deliberate stacking) (GAP-14)
    errored = False
    for i, (n1, r1, z1) in enumerate(boxes):
        for n2, r2, z2 in boxes[i + 1:]:
            if z1 != z2:
                continue
            if overlaps(r1, r2):
                fail(f"Page '{name}': '{n1}' (z={z1}) overlaps '{n2}' (z={z2})")
                errored = True

    if not errored:
        ok(f"Page '{name}': {len(boxes)} visuals, layout bounds and overlaps clean")


def main() -> int:
    if len(sys.argv) > 1:
        report_dirs = [Path(p) for p in sys.argv[1:]]
    else:
        report_dirs = pbir_discovery.report_dirs(Path("."))
        if not report_dirs:
            print("[FAIL] No .Report directory found.")
            return 1

    for report_dir in report_dirs:
        if not report_dir.is_dir():
            print(f"[FAIL] Not a directory: {report_dir}")
            return 1

        print(f"Validating PBIR layout for {report_dir}\n")
        pages_dir = report_dir / "definition" / "pages"
        if not pages_dir.is_dir():
            print(f"[FAIL] No pages directory under {report_dir}")
            return 1

        for page_file in sorted(pages_dir.glob("*/page.json")):
            check_page(page_file)

    print()
    if FAIL:
        print(f"[FAIL] {FAIL} layout error(s), {WARN} warning(s).")
        return 1
    print(f"[PASS] PBIR layout validation passed ({WARN} warning(s)).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
