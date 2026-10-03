#!/usr/bin/env python3
"""
vendor_native_icons.py — Vendor a chart-type icon for every native visual type.

Why this exists
---------------
The gallery needs a thumbnail per native visual. The obvious sources are both unusable:

  * Screenshots of Power BI Desktop. Renderable only on a Windows machine with the
    Desktop Bridge, and DPI/theme dependent, so the committed art would drift with
    whatever machine last regenerated it.
  * Microsoft Learn documentation images. Those are Microsoft's copyrighted content,
    licensed for internal use rather than redistribution - the same reasoning that
    keeps the .pbiviz packages out of this repo (docs/POWER_BI_VISUAL_COVERAGE.md).

Permissively licensed chart-type glyphs sidestep both: they are small vector art
explicitly licensed for redistribution, they inherit `currentColor` so they theme with
the gallery, and they are a *label* for a chart type rather than a claim about what a
particular Desktop build renders. The last point matters - a screenshot asserts "this is
what you will get", whereas an icon asserts only "this is the shape".

Tabler Icons is used: MIT, which obliges us to retain the copyright notice and nothing
else. No NOTICE file, no modified-file marking, unlike Apache 2.0.

Three tiers, and the distinction is load-bearing
-----------------------------------------------
    icon        an honest single-glyph stand-in exists
    schematic   no glyph can honestly represent it, so the gallery draws a labelled
                CSS diagram instead (see build_html_gallery.py)
    collision   no distinct glyph exists, so a sibling type shares an icon. The reason
                is recorded per type below and in icons/icons.lock.json, because a
                silently shared icon reads as "these are the same visual".

Deliberately NOT reproduced here: Microsoft's own icon silhouettes, exact card geometry
or pixel styling. These are generic chart forms; drawing them generically keeps the
gallery clear of the documentation-image problem entirely.

Reproducibility
---------------
Both sources are pinned to exact commits, and each vendored file is written verbatim
from upstream, so `sha256(file)` equals `sha256(upstream file)`. That is what makes the
lock file worth having: it is a claim a reviewer can check, not a bookkeeping artefact.

Usage:
    python3 scripts/vendor_native_icons.py            # vendor, verifying against the lock
    python3 scripts/vendor_native_icons.py --refresh # re-download, then rewrite the lock
    python3 scripts/vendor_native_icons.py --check    # verify on-disk against the lock only
    python3 scripts/vendor_native_icons.py --mapping  # print the tier for every type
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ICONS = REPO / "samples" / "visual-gallery-assets" / "icons"
LOCK = ICONS / "icons.lock.json"
ALLOWLIST = REPO / "templates" / "html-prototype" / "visual-allowlist.json"

# Pinned 2026-10-03. Both are recorded in the lock file; --refresh re-pins deliberately.
TABLER_REPO = "tabler/tabler-icons"
TABLER_SHA = "74929e50416e2b7c0abb8368cdc74bdcb2560ab6"
TABLER_LICENSE_URL = f"https://raw.githubusercontent.com/{TABLER_REPO}/{TABLER_SHA}/LICENSE"
ICON_URL = f"https://raw.githubusercontent.com/{TABLER_REPO}/{TABLER_SHA}/icons/outline/{{name}}.svg"
ATTRIBUTION = "Tabler Icons (c) 2020-2026 Pawel Kuna - MIT License - https://github.com/tabler/tabler-icons"

UA = "powerbi-dev-template/vendor_native_icons (repo tooling; not a browser)"

# visualType -> (icon name, tier, reason)
#
# reason is mandatory for `schematic` and `collision` tiers and empty for `icon`: it is
# what stops a shared or approximated glyph from being read as a factual claim.
ICONS_FOR_TYPE: dict[str, tuple[str, str, str]] = {
    # Cartesian. Category on the axis, measure on the value axis.
    "columnChart":                  ("chart-column", "icon", ""),
    "clusteredColumnChart":         ("chart-dots", "icon", ""),
    "barChart":                     ("chart-bar", "icon", ""),
    "clusteredBarChart":            ("chart-bar", "collision",
                                    "No distinct glyph exists for the clustered variant; the bar form is the same "
                                    "chart with a second field split into series. Use the combo schematic to see "
                                    "that difference."),
    "lineChart":                    ("chart-line", "icon", ""),
    "areaChart":                    ("chart-area", "icon", ""),
    "stackedAreaChart":             ("chart-area", "collision",
                                    "No distinct glyph exists for the stacked variant; the outline is identical "
                                    "and only the fill segmentation differs."),
    "hundredPercentStackedAreaChart": ("chart-area", "schematic",
                                    "100% stacking normalises every column to the same height, which is the one "
                                    "thing the chart-area outline cannot convey. Drawn as a normalised stack."),
    "hundredPercentStackedColumnChart": ("chart-column", "schematic",
                                    "Same reason as the area variant: normalisation removes the height cue the "
                                    "column glyph relies on. Drawn as a normalised stack."),
    "hundredPercentStackedBarChart": ("chart-bar", "schematic",
                                    "Same reason as the column variant. Drawn as a normalised stack."),
    "lineClusteredColumnComboChart": ("chart-line", "schematic",
                                    "A combo is two marks on two axes at once, which no single glyph represents. "
                                    "Drawn as columns with an overlaid line."),
    "lineStackedColumnComboChart": ("chart-line", "schematic",
                                    "As above, with a stacked column mark instead of a clustered one."),
    "ribbonChart":                  ("chart-arrows", "schematic",
                                    "A ribbon ranks categories and carries the second-highest value as a trailing "
                                    "band, which is neither a bar chart nor a stacked one. Drawn as ranked ribbons."),
    "waterfallChart":               ("chart-arrows", "icon", ""),

    # Distribution and part-to-whole.
    "pieChart":                     ("chart-pie", "icon", ""),
    "donutChart":                   ("chart-donut", "icon", ""),
    "treemap":                      ("chart-treemap", "icon", ""),
    "funnel":                       ("chart-funnel", "icon", ""),
    "scatterChart":                 ("chart-scatter", "icon", ""),

    # Table and matrix.
    "tableEx":                      ("table", "icon", ""),
    "pivotTable":                   ("layout-grid", "icon", ""),

    # KPI family.
    "cardVisual":                   ("square", "icon", ""),
    "gauge":                        ("gauge", "icon", ""),
    "kpi":                          ("target-arrow", "schematic",
                                    "A KPI is a value plus a status indicator plus a target, which reads as a "
                                    "single arrow. Drawn as a value tile with a state and a goal."),
    "scorecard":                    ("target", "collision",
                                    "Excluded type. Shares the target glyph with the KPI family; see the "
                                    "not-authorable reason in the catalog."),

    # AI and decomposition.
    "decompositionTreeVisual":      ("hierarchy-2", "icon", ""),
    "keyDriversVisual":             ("trending-up", "schematic",
                                    "Key influencers is a list of drivers each labelled increasing or decreasing, "
                                    "which no glyph encodes. Drawn as signed driver rows."),
    "narrative":                    ("typography", "schematic",
                                    "Narrative output is prose with a headline and insight lines. Drawn as a "
                                    "narrative card."),
    "aiNarratives":                 ("typography", "schematic",
                                    "Excluded type, but the same shape as narrative. Drawn identically."),

    # Maps.
    "map":                          ("map", "icon", ""),
    "filledMap":                    ("map-2", "icon", ""),
    "shapeMap":                     ("world", "icon", ""),
    "azureMap":                     ("map", "collision",
                                    "Excluded type. Shares the map glyph; the reason it cannot be authored here "
                                    "is a missing Azure Maps account, not its appearance."),

    # Filtering. One glyph per control is honest because they are distinct controls.
    "slicer":                       ("filter", "icon", ""),
    "listSlicer":                   ("list", "icon", ""),
    "advancedSlicerVisual":         ("filter-2", "icon", ""),
    "filterSlicer":                 ("filter-2", "collision",
                                    "Excluded type. Shares the button-slicer glyph; its Desktop availability is "
                                    "unverified rather than its appearance."),
    "textSlicer":                   ("filter", "collision",
                                    "Excluded type. Shares the slicer glyph. It is withheld because it is not a "
                                    "verified alias for the Input slicer, which is a binding question."),
    "qnaVisual":                    ("message", "icon", ""),

    # Media, shapes, navigation. No data roles, so there is no chart to depict.
    "textbox":                      ("typography", "icon", ""),
    "shape":                        ("square", "icon", ""),
    "basicShape":                   ("circle", "icon", ""),
    "image":                        ("photo", "icon", ""),
    "actionButton":                 ("navigation", "icon", ""),
    "pageNavigator":                ("chevron-right", "icon", ""),
    "bookmarkNavigator":            ("book", "icon", ""),

    # Legacy and unsupported types. Kept so the gallery can say *why* they are absent
    # with the same visual weight as everything it does support.
    "card":                         ("square", "collision",
                                    "Legacy. Shares the cardVisual glyph; use cardVisual instead."),
    "multiRowCard":                 ("list", "collision",
                                    "Legacy. Use cardVisual with several values in Data."),
    "table":                        ("table", "collision",
                                    "Legacy. Use tableEx."),
    "matrix":                       ("layout-grid", "collision",
                                    "Legacy. Use pivotTable."),
    "accessibleTable":              ("table", "collision",
                                    "Excluded type. Desktop availability unverified."),
    "animatedNumber":               ("percentage", "collision",
                                    "Excluded type. Desktop availability unverified."),
    "dataQueryVisual":              ("report", "collision",
                                    "Excluded type. Desktop availability unverified."),
    "heatMap":                      ("chart-grid-dots", "collision",
                                    "Excluded type. Desktop availability unverified; Power BI's heatMap "
                                    "catalog entry is distinct from conditional formatting on any other visual."),
    "realTimeLineChart":            ("chart-line", "collision",
                                    "Excluded type. Desktop availability unverified."),
    "pythonVisual":                 ("code", "collision",
                                    "Excluded type. Needs a Python runtime, not an appearance question."),
    "scriptVisual":                 ("math", "collision",
                                    "Excluded type. Needs an R runtime, not an appearance question."),
    "rdlVisual":                    ("file-text", "collision",
                                    "Excluded type. Needs a separate paginated report definition."),
}


class Fail(Exception):
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch(url: str) -> bytes:
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60) as r:
            return r.read()
    except urllib.error.HTTPError as exc:
        raise Fail(f"HTTP {exc.code} for {url}") from exc
    except urllib.error.URLError as exc:
        raise Fail(f"network error for {url}: {exc.reason}") from exc


def write_attribution(lock: dict) -> None:
    """Emit ATTRIBUTION.md from the lock so the notice cannot drift from what is on disk.

    MIT condition 1 requires the copyright notice to travel with copies and substantial
    portions. That is satisfied by LICENSE-tabler-icons.txt sitting next to the icons and
    by this file naming the source, the exact commit and the license.
    """
    src = lock["_source"]
    entries = {k: v for k, v in lock.items() if not k.startswith("_")}
    tiers: dict[str, list[str]] = {}
    for vt, m in entries.items():
        tiers.setdefault(m["tier"], []).append(vt)

    lines = [
        "# Third-party assets in this folder",
        "",
        "Generated by `scripts/vendor_native_icons.py --refresh`. Do not hand-edit.",
        "",
        "## Tabler Icons",
        "",
        f"- **Upstream:** {src['repo']}",
        f"- **Commit:** `{src['commit']}`",
        f"- **Path:** `{src['path']}`",
        f"- **License:** {src['license']} — full text in [`{src['licenseFile']}`]({src['licenseFile']})",
        f"- **Attribution:** {src['attribution']}",
        "",
        "Files are written **verbatim from upstream**, so `sha256(<file>.svg)` here equals",
        "`sha256(<file>.svg)` in the repository above at that commit. That equality is what",
        "makes `icons.lock.json` a checkable claim rather than bookkeeping, and it is",
        "verified by `scripts/vendor_native_icons.py --check`.",
        "",
        "The icons are used as **labels for a chart type**, not as depictions of what any",
        "particular Power BI build renders. No Microsoft icon silhouette, card geometry or",
        "pixel styling has been reproduced here.",
        "",
        "## What each file is for",
        "",
        "One file per native PBIR `visualType`, named after the type. Three tiers, because",
        "an honest icon does not exist for every visual and a silently wrong one is worse",
        "than an admitted gap:",
        "",
        "| Tier | Count | Meaning |",
        "|---|---|---|",
    ]
    blurb = {
        "icon": "A single glyph represents this visual type honestly.",
        "schematic": "No glyph is honest, so the gallery draws a labelled CSS diagram instead.",
        "collision": "No distinct glyph exists, so a sibling type shares this icon. The reason is recorded per type.",
    }
    for tier in ("icon", "schematic", "collision"):
        lines.append(f"| `{tier}` | {len(tiers.get(tier, []))} | {blurb[tier]} |")

    for tier in ("schematic", "collision"):
        names = sorted(tiers.get(tier, []))
        if not names:
            continue
        lines += ["", f"### `{tier}` — {len(names)} type(s)", ""]
        for vt in names:
            m = entries[vt]
            lines.append(f"- **`{vt}`** → `tabler:{m['icon']}` — {m['reason']}")
    lines.append("")
    (ICONS / "ATTRIBUTION.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")


def expected_types() -> set[str]:
    """Every native visual type the catalog must illustrate: allowed plus excluded."""
    doc = json.loads(ALLOWLIST.read_text(encoding="utf-8"))
    return set(doc["native"]["allowed"]) | set(doc["excludedNative"])


def vendor(refresh: bool) -> int:
    ICONS.mkdir(parents=True, exist_ok=True)
    lock: dict = {}
    failures = 0

    if refresh or not LOCK.is_file():
        used = sorted({v[0] for v in ICONS_FOR_TYPE.values()})
        print(f"[INFO] downloading {len(used)} icon(s) from {TABLER_REPO}@{TABLER_SHA[:12]}")

        # Fetched concurrently: 40 sequential requests to raw.githubusercontent.com is
        # dominated by per-request latency and overruns a default timeout. The pool is
        # bounded well below any rate limit these static files are served under.
        bodies: dict[str, bytes] = {}
        errors: dict[str, str] = {}
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = {pool.submit(fetch, ICON_URL.format(name=n)): n for n in used}
            for fut in as_completed(futures):
                name = futures[fut]
                try:
                    bodies[name] = fut.result()
                except Fail as exc:
                    errors[name] = str(exc)
        for name, msg in sorted(errors.items()):
            print(f"[FAIL] {name}: {msg}")
        failures += len(errors)
        try:
            lic = fetch(TABLER_LICENSE_URL)
            (ICONS / "LICENSE-tabler-icons.txt").write_bytes(lic)
        except Fail as exc:
            print(f"[FAIL] tabler LICENSE: {exc}")
            failures += 1

        for vt, (name, tier, reason) in sorted(ICONS_FOR_TYPE.items()):
            if name not in bodies:
                continue
            (ICONS / f"{vt}.svg").write_bytes(bodies[name])
            lock[vt] = {
                "icon": name,
                "tier": tier,
                "reason": reason,
                "file": f"{vt}.svg",
                "sha256": sha256(bodies[name]),
                "bytes": len(bodies[name]),
            }

        lock["_source"] = {
            "iconSet": "Tabler Icons",
            "repo": f"https://github.com/{TABLER_REPO}",
            "commit": TABLER_SHA,
            "path": "icons/outline/{name}.svg",
            "license": "MIT",
            "attribution": ATTRIBUTION,
            "licenseFile": "LICENSE-tabler-icons.txt",
            "vendoredVerbatim": True,
        }
        LOCK.write_text(json.dumps(lock, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8", newline="\n")
        write_attribution(lock)
        print(f"[PASS] wrote {len([k for k in lock if not k.startswith('_')])} icon(s) + lock + attribution")

    if failures:
        return 1

    # Verify on-disk against the lock, and report anything unmapped.
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    entries = {k: v for k, v in lock.items() if not k.startswith("_")}
    bad = 0
    for vt, meta in sorted(entries.items()):
        f = ICONS / meta["file"]
        if not f.is_file():
            print(f"[FAIL] {vt}: missing {meta['file']}")
            bad += 1
        elif sha256(f.read_bytes()) != meta["sha256"]:
            print(f"[FAIL] {vt}: on-disk SHA-256 differs from the lock")
            bad += 1

    want = expected_types()
    missing = want - set(entries)
    extra = set(entries) - want
    if missing:
        print(f"[FAIL] {len(missing)} native type(s) with no thumbnail: {sorted(missing)}")
        bad += 1
    if extra:
        print(f"[WARN] {len(extra)} vendored icon(s) for types not in the allowlist: {sorted(extra)}")

    tiers: dict[str, int] = {}
    for m in entries.values():
        tiers[m["tier"]] = tiers.get(m["tier"], 0) + 1
    total_bytes = sum(m["bytes"] for m in entries.values())

    if bad:
        print(f"\n[FAIL] {bad} problem(s).")
        return 1

    print(f"[PASS] {len(entries)} native type(s) vendored, {total_bytes:,} B total")
    print("       " + "  ".join(f"{t}={n}" for t, n in sorted(tiers.items())))
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--refresh", action="store_true", help="re-download and rewrite the lock file")
    ap.add_argument("--check", action="store_true", help="verify on-disk files against the lock; download nothing")
    ap.add_argument("--mapping", action="store_true", help="print every type with its icon and tier, then exit")
    args = ap.parse_args(argv)

    if args.mapping:
        width = max(len(k) for k in ICONS_FOR_TYPE)
        for vt, (name, tier, reason) in sorted(ICONS_FOR_TYPE.items(), key=lambda kv: (kv[1][1], kv[0])):
            line = f"{vt:<{width}}  {tier:<10} tabler:{name}"
            print(line)
            if reason:
                print(f"{'':<{width}}  {'':<10} {reason}")
        print(f"\n{len(ICONS_FOR_TYPE)} type(s): "
              + "  ".join(f"{t}={sum(1 for v in ICONS_FOR_TYPE.values() if v[1] == t)}"
                          for t in sorted({v[1] for v in ICONS_FOR_TYPE.values()})))
        return 0

    return vendor(args.refresh)


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except Fail as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        raise SystemExit(1)