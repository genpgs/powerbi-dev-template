#!/usr/bin/env python3
"""
verify_html_gallery.py — Assert the gallery's claims hold, rather than trusting them.

Why this exists
---------------
The gallery makes checkable statements: 40 native types, 26 custom visuals, every one with
a use-when and a data role, and a thumbnail for all of them. Each is a thing that can rot
quietly. A visual added to the allowlist and not described shows a blank card. A custom
GUID dropped from report.json leaves a card that points at nothing renderable. A renamed
role leaves a chip showing a name no longer in the package. None of that raises an error
anywhere else in the repo.

This mirrors scripts/verify_gallery_coverage.py: the gallery's coverage is asserted by a
script, not promised in prose.

Assertions
----------
    1. index.html is exactly what scripts/build_html_gallery.py produces (not stale)
    2. every catalog entry has a name, a family and a use-when
    3. every allowed native type and every excluded type is present; exclusions carry a reason
    4. every custom visual GUID matches report.json -> publicCustomVisuals
    5. every custom visual has at least one data role, and it came from a real package
    6. every thumbnail resolves to a file on disk, and none is missing
    7. every schematic-tier type actually has a schematic defined
    8. every collision-tier type records why it shares a glyph
    9. EXCEPTIONS.md is current
    10. the HTML is self-contained and well-formed: embedded JSON parses, every inline SVG
        parses as XML, and there are no remote asset references

Run: python3 scripts/verify_html_gallery.py
"""
from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from schematics import SCHEMATICS  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
ASSETS = REPO / "samples" / "visual-gallery-assets"
CATALOG = ASSETS / "visual-catalog.json"
CONTENT = ASSETS / "content.json"
EXCEPTIONS = ASSETS / "EXCEPTIONS.md"
HTML = REPO / "templates" / "visuals-gallery" / "index.html"
ALLOWLIST = REPO / "templates" / "html-prototype" / "visual-allowlist.json"
REPORT_JSON = (REPO / "samples" / "pbip-visual-gallery" / "VisualGallery.Report"
               / "definition" / "report.json")

FAILURES: list[str] = []
PASSES: list[str] = []


def check(ok: bool, pass_msg: str, fail_msg: str) -> bool:
    (PASSES if ok else FAILURES).append(pass_msg if ok else fail_msg)
    print(f"[{'PASS' if ok else 'FAIL'}] {pass_msg if ok else fail_msg}")
    return ok


def embedded_catalog(html: str) -> dict:
    marker = "window.PBI_VISUAL_CATALOG = "
    i = html.index(marker) + len(marker)
    j = html.index("</script>", i)
    return json.loads(html[i:j].strip().rstrip(";").replace("<\\/", "</"))


def main() -> int:
    if not HTML.is_file():
        print(f"[FAIL] {HTML.relative_to(REPO)} does not exist. Run scripts/build_html_gallery.py")
        return 1
    html = HTML.read_text(encoding="utf-8")

    # 1. not stale -- defer to the generator so there is one definition of correct
    import build_html_gallery
    try:
        expected = build_html_gallery.build()
    except build_html_gallery.Fail as exc:
        print(f"[FAIL] generator could not rebuild the gallery: {exc}")
        return 1
    check(html == expected,
          "index.html matches scripts/build_html_gallery.py output",
          "index.html is stale. Run scripts/build_html_gallery.py")

    doc = json.loads(CATALOG.read_text(encoding="utf-8"))
    allow = json.loads(ALLOWLIST.read_text(encoding="utf-8"))
    visuals = doc["visuals"]
    by_type = {v["visualType"]: v for v in visuals}

    # 2. no blank cards
    blank = [v["visualType"] for v in visuals
             if not v.get("name") or not v.get("family") or not v.get("useWhen")]
    check(not blank,
          f"all {len(visuals)} visuals have a name, a family and a use-when",
          f"{len(blank)} visual(s) missing name/family/useWhen: {blank[:8]}")

    # 3. allowlist parity, both directions
    allowed = set(allow["native"]["allowed"])
    excluded = set(allow["excludedNative"])
    native_in_cat = {v["visualType"] for v in visuals if v["kind"] in ("native", "excluded")}
    check(allowed <= native_in_cat,
          f"all {len(allowed)} allowed native type(s) are in the catalog",
          f"{len(allowed - native_in_cat)} allowed native type(s) absent from the catalog: "
          f"{sorted(allowed - native_in_cat)}")
    check(excluded <= native_in_cat,
          f"all {len(excluded)} excluded type(s) are described, with a reason",
          f"{len(excluded - native_in_cat)} excluded type(s) absent from the catalog: "
          f"{sorted(excluded - native_in_cat)}")

    no_reason = [t for t in sorted(excluded)
                 if by_type.get(t, {}).get("kind") != "excluded" or not by_type[t].get("exclusionReason")]
    check(not no_reason,
          "every excluded type carries a non-empty exclusion reason",
          f"excluded type(s) with no reason: {no_reason}")

    # 4. custom GUIDs vs the renderable report
    catalog_guids = {v["visualType"] for v in visuals if v["kind"] == "custom"}
    declared = set(json.loads(REPORT_JSON.read_text(encoding="utf-8")).get("publicCustomVisuals") or [])
    check(catalog_guids == declared,
          f"the {len(catalog_guids)} custom visual GUID(s) match report.json publicCustomVisuals",
          f"catalog and report.json disagree; "
          f"catalog-only={sorted(catalog_guids - declared)} report-only={sorted(declared - catalog_guids)}")

    # 5. roles came from a real package, not a guess
    no_roles = [v["visualType"] for v in visuals if v["kind"] == "custom" and not v.get("roles")]
    check(not no_roles,
          f"every custom visual has data roles ({sum(1 for v in visuals if v.get('rolesAreCanonical'))} read from a .pbiviz)",
          f"custom visual(s) with no roles: {no_roles}")
    unproven = [v["visualType"] for v in visuals if v["kind"] == "custom" and not v.get("rolesAreCanonical")]
    check(not unproven,
          "every custom visual's roles are canonical (captured from the package)",
          f"roles for {unproven} came from the allowlist, not a package. "
          "Run scripts/fetch_gallery_assets.py then scripts/build_visual_catalog.py")

    # 6. thumbnails resolve
    gallery_base = HTML.parent
    bad_thumb: list[str] = []
    for v in visuals:
        t = v["thumbnail"]
        if t["tier"] == "missing":
            bad_thumb.append(f"{v['visualType']}: tier=missing")
            continue
        if t.get("kind") == "image" and t.get("src"):
            if not (gallery_base / f"../../samples/visual-gallery-assets/{t['src']}").resolve().is_file():
                bad_thumb.append(f"{v['visualType']}: {t['src']} not found")
        elif t.get("src"):
            if not (ASSETS / "icons" / Path(t["src"]).name).is_file():
                bad_thumb.append(f"{v['visualType']}: {t['src']} not found")
    check(not bad_thumb,
          f"every one of {len(visuals)} thumbnails resolves to a file on disk",
          f"unresolvable thumbnail(s): {bad_thumb[:8]}")

    # 7. schematics actually exist
    want_schem = {v["visualType"] for v in visuals if v["thumbnail"]["tier"] == "schematic"}
    have = want_schem & set(SCHEMATICS)
    check(want_schem == have,
          f"all {len(want_schem)} schematic-tier type(s) have a drawing in scripts/schematics.py",
          f"schematic declared in the catalog but not drawn: {sorted(want_schem - have)}; "
          f"drawn but not declared: {sorted(set(SCHEMATICS) - want_schem)}")

    # 8. collisions are explained
    unreasoned = [v["visualType"] for v in visuals
                  if v["thumbnail"]["tier"] == "collision" and not v["thumbnail"].get("reason")]
    check(not unreasoned,
          "every shared-glyph (collision) type records why it shares a glyph",
          f"collision(s) with no reason recorded: {unreasoned}")

    # 9. exceptions report is current
    n_flagged = sum(1 for v in visuals if v["thumbnail"]["tier"] in ("schematic", "collision", "missing"))
    check(EXCEPTIONS.is_file() and f"{n_flagged} of {len(visuals)} visuals" in EXCEPTIONS.read_text(encoding="utf-8"),
          f"EXCEPTIONS.md is current ({n_flagged} flagged)",
          f"EXCEPTIONS.md is stale; expected {n_flagged} flagged of {len(visuals)}. "
          "Run scripts/build_html_gallery.py")

    # 10. self-contained and well-formed
    try:
        embedded = embedded_catalog(html)
        ok_json = len(embedded["visuals"]) == len(visuals)
    except (ValueError, KeyError) as exc:
        ok_json = False
        print(f"       embedded catalog error: {exc}")
    check(ok_json,
          f"the embedded catalog parses and carries all {len(visuals)} visuals",
          "the embedded catalog does not parse or is out of step with visual-catalog.json")

    svgs = re.findall(r'<svg class="thumb-(?:icon|schem)".*?</svg>', html, re.S)
    bad_svg = []
    for frag in svgs:
        try:
            ET.fromstring(frag)
        except ET.ParseError as exc:
            bad_svg.append(str(exc))
    check(not bad_svg,
          f"all {len(svgs)} inline SVG thumbnails parse as well-formed XML",
          f"{len(bad_svg)} inline SVG(s) are malformed: {bad_svg[:3]}")

    remote = re.findall(r'(?:src|href)="https?://[^"]+', html)
    check(not remote,
          "no remote asset references -- the page works offline from file://",
          f"{len(remote)} remote asset reference(s) would break offline use: {remote[:3]}")

    photos = re.findall(r'<img class="thumb-photo" src="([^"]+)"', html)
    unresolved = [s for s in photos if not (gallery_base / s).resolve().is_file()]
    check(not unresolved,
          f"all {len(photos)} <img> references resolve relative to index.html",
          f"unresolvable <img> reference(s): {unresolved[:5]}")

    # counts in the catalog must match the rows, so the header cannot lie
    recount = {
        "native": sum(1 for v in visuals if v["kind"] == "native"),
        "excluded": sum(1 for v in visuals if v["kind"] == "excluded"),
        "custom": sum(1 for v in visuals if v["kind"] == "custom"),
    }
    check(doc["counts"]["native"] == recount["native"]
          and doc["counts"]["excluded"] == recount["excluded"]
          and doc["counts"]["custom"] == recount["custom"],
          f"catalog counts agree with its own rows ({recount['native']} native, "
          f"{recount['custom']} custom, {recount['excluded']} excluded)",
          f"catalog counts disagree with its rows: header says {doc['counts']}, rows say {recount}")

    print()
    if FAILURES:
        print(f"[FAIL] {len(FAILURES)} check(s) failed, {len(PASSES)} passed.")
        return 1
    print(f"[PASS] All {len(PASSES)} gallery check(s) passed for {len(visuals)} visuals.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())