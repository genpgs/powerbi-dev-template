#!/usr/bin/env python3
"""
verify_gallery_coverage.py — Assert the gallery actually covers the allowlist.

The coverage claims in docs/POWER_BI_VISUAL_COVERAGE.md are easy to make and easy
to let rot: add a visual to the allowlist, forget the gallery, and the docs now
overstate what the project demonstrates. This turns those claims into checks.

Assertions:
  1. Every allowed native visual type appears somewhere in the gallery.
  2. No excluded type (legacy, deprecated, unverified or hosted) appears in the
     gallery. This is the rule the authoring reference states as "never create
     legacy visual types", so it is worth enforcing mechanically.
  3. Every custom visual GUID in the manifest appears in the gallery.
  4. report.json publicCustomVisuals equals the set of custom GUIDs actually used
     by a visual. A dangling entry here is silent in Desktop - the visual is
     declared but nothing references it.

Run: python3 scripts/verify_gallery_coverage.py
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ALLOWLIST = REPO / "templates" / "html-prototype" / "visual-allowlist.json"
MANIFEST = REPO / "samples" / "visual-gallery-assets" / "manifest.csv"
PAGES = REPO / "samples" / "pbip-visual-gallery" / "VisualGallery.Report" / "definition" / "pages"
REPORT_JSON = REPO / "samples" / "pbip-visual-gallery" / "VisualGallery.Report" / "definition" / "report.json"

FAILURES: list[str] = []
PASSES: list[str] = []


def check(ok: bool, pass_msg: str, fail_msg: str) -> bool:
    (PASSES if ok else FAILURES).append(pass_msg if ok else fail_msg)
    print(f"[{'PASS' if ok else 'FAIL'}] {pass_msg if ok else fail_msg}")
    return ok


def visual_types_in_gallery() -> list[str]:
    types: list[str] = []
    for path in PAGES.glob("*/visuals/*/visual.json"):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            FAILURES.append(f"unreadable visual.json at {path}: {exc}")
            continue
        vt = (doc.get("visual") or {}).get("visualType")
        if vt:
            types.append(vt)
    return types


def main() -> int:
    if not ALLOWLIST.is_file():
        print(f"[FAIL] allowlist missing: {ALLOWLIST}. Run scripts/generate_visual_allowlist.py")
        return 1
    allowlist = json.loads(ALLOWLIST.read_text(encoding="utf-8"))
    allowed_native = set(allowlist["native"]["allowed"])
    excluded = set(allowlist["excludedNative"])
    custom_allowed = {c["guid"] for c in allowlist["custom"]}

    used = set(visual_types_in_gallery())
    native_used = used & allowed_native
    custom_used = used & custom_allowed

    check(
        allowed_native <= used,
        f"all {len(allowed_native)} allowed native type(s) appear in the gallery",
        f"{len(allowed_native - used)} allowed native type(s) missing from the gallery: "
        f"{sorted(allowed_native - used)}",
    )
    check(
        not (excluded & used),
        "no excluded type appears in the gallery",
        f"excluded type(s) present in the gallery: {sorted(excluded & used)}",
    )
    check(
        custom_allowed <= used,
        f"all {len(custom_allowed)} custom visual(s) appear in the gallery",
        f"{len(custom_allowed - used)} custom visual(s) missing from the gallery: "
        f"{sorted(custom_allowed - used)}",
    )
    check(
        not (used - allowed_native - custom_allowed),
        "the gallery declares no type outside the allowlist",
        f"undeclared type(s) in the gallery: {sorted(used - allowed_native - custom_allowed)}",
    )

    # report.json must declare exactly the custom visuals the report uses.
    if REPORT_JSON.is_file():
        doc = json.loads(REPORT_JSON.read_text(encoding="utf-8"))
        declared = set(doc.get("publicCustomVisuals") or [])
        check(
            declared == custom_used,
            f"report.json publicCustomVisuals matches the {len(custom_used)} custom visual(s) in use",
            f"report.json publicCustomVisuals is out of sync; "
            f"declared-but-unused={sorted(declared - custom_used)} "
            f"used-but-undeclared={sorted(custom_used - declared)}",
        )
    else:
        check(False, "", f"report.json not found: {REPORT_JSON}")

    print()
    print(f"[INFO] gallery uses {len(native_used)} native type(s) and {len(custom_used)} custom visual(s)")
    if FAILURES:
        print(f"[FAIL] {len(FAILURES)} check(s) failed, {len(PASSES)} passed.")
        return 1
    print(f"[PASS] All {len(PASSES)} coverage check(s) passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())