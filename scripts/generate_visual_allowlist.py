#!/usr/bin/env python3
"""
generate_visual_allowlist.py — Emit the HTML mockup's allowed-visual contract.

Why this is generated
---------------------
The mockup at templates/html-prototype/dashboard-template.html may only offer the
visuals and slicers this project actually supports. Writing that list by hand
guarantees it drifts: add a visual to the gallery, forget the mockup, and the
prototype quietly keeps offering something the report cannot render.

So the list is generated from the two real sources of truth:

  * native types  -> `powerbi-report-author catalog list`
  * custom types  -> samples/visual-gallery-assets/manifest.csv, with roles read
                     from each .pbiviz package's capabilities.dataRoles

Excluded native types are listed explicitly with a reason, so the omission is a
decision on record rather than an oversight. Legacy types are never offered: use
the modern replacement instead.

Outputs:
    templates/html-prototype/visual-allowlist.json   the contract
    (stdout)                                        a summary

Run: python3 scripts/generate_visual_allowlist.py
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MANIFEST = REPO / "samples" / "visual-gallery-assets" / "manifest.csv"
PBIVIZ = REPO / "samples" / "visual-gallery-assets" / "PBIVIZ"
OUT = REPO / "templates" / "html-prototype" / "visual-allowlist.json"

# Native types deliberately withheld from the mockup, with the reason. Every entry
# is a judgement call worth being able to audit later.
EXCLUDED_NATIVE = {
    # Deprecated: use the replacement.
    "card": "Legacy. Use cardVisual.",
    "multiRowCard": "Legacy. Use cardVisual with several values in Data.",
    "table": "Legacy. Use tableEx.",
    "matrix": "Legacy. Use pivotTable.",
    # Needs a provisioned Azure Maps account, so it renders empty in a
    # self-contained sample. Demonstrated types are Bing Maps map / filledMap
    # plus shapeMap, which need no account.
    "azureMap": "Requires a provisioned Azure Maps account; not authorable in a self-contained sample.",
    # Superseded for this sample and did not render. `narrative` summarises a
    # page or visual placed beside it and is the type used instead.
    "aiNarratives": "Smart narrative did not render in Desktop; the sample uses `narrative` instead.",
    # Known-unsupported or misleading catalog entries. Listing them would invite
    # exactly the wrong authoring decision.
    "qnaVisual": "Q&A is not supported in PBIR authoring and is scheduled for deprecation (December 2026).",
    "accessibleTable": "Catalogued but Desktop availability unverified.",
    "animatedNumber": "Catalogued but Desktop availability unverified.",
    "dataQueryVisual": "Catalogued but Desktop availability unverified.",
    "filterSlicer": "Catalogued but Desktop availability unverified.",
    "heatMap": "Catalogued but Desktop availability unverified.",
    "realTimeLineChart": "Catalogued but Desktop availability unverified.",
    "textSlicer": "Not a verified alias of the Input slicer. Do not substitute it.",
    "scorecard": "Catalogued, but its mapping to the current Desktop experience is unconfirmed.",
    # Hosted or licensed capabilities rather than report visuals.
    "pythonVisual": "Needs a Python runtime; not authorable as a plain sample.",
    "scriptVisual": "Needs an R runtime; not authorable as a plain sample.",
    "rdlVisual": "Requires a separate paginated report definition.",
}

# Types Desktop authorises but the CLI catalog does not list, so the allowlist has
# to declare them explicitly rather than inherit them from the catalog.
EXTRA_NATIVE = {
    "narrative": "Present in Desktop and authorable through PBIR, but absent from the CLI catalog. Narrative summarises a page or visual placed beside it, which is what the sample uses in place of aiNarratives.",
}

# Visual types that take no data roles. Used to explain blank-looking mockups.
NO_ROLE_TYPES = {
    "textbox", "shape", "basicShape", "image", "pageNavigator", "bookmarkNavigator",
    "actionButton", "keyDriversVisual",
}


def _cli_command() -> list[str]:
    """How to invoke the report-author CLI on this platform.

    On Windows an npm global install exposes a bare extensionless shell script,
    a .cmd shim and a .ps1 shim. CreateProcess (what subprocess uses) will not
    execute any of those by bare name, so resolve to the .cmd explicitly. On
    Linux and macOS the bare name works.
    """
    import shutil

    exe = shutil.which("powerbi-report-author") or shutil.which("powerbi-report-author.cmd")
    if exe:
        return [exe]
    if sys.platform == "win32":
        appdata = Path(os.environ.get("APPDATA", "")) / "npm"
        for candidate in (appdata / "powerbi-report-author.cmd", appdata / "powerbi-report-author.ps1"):
            if candidate.is_file():
                if candidate.suffix == ".ps1":
                    return ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(candidate)]
                return [str(candidate)]
    raise SystemExit(
        "[FAIL] powerbi-report-author not found on PATH. "
        "Install it with: npm install -g @microsoft/powerbi-report-authoring-cli"
    )


def _catalog_list() -> dict:
    proc = subprocess.run(
        _cli_command() + ["catalog", "list"],
        capture_output=True, text=True, cwd=REPO, timeout=120,
    )
    if proc.returncode != 0:
        raise SystemExit(f"[FAIL] catalog list failed: {proc.stderr.strip()}")
    return json.loads(proc.stdout)["data"]


def native_types() -> list[str]:
    data = _catalog_list()
    return sorted(({*data["visualTypes"], *EXTRA_NATIVE} - set(EXCLUDED_NATIVE)))


def deprecated_map() -> list[dict]:
    return _catalog_list().get("deprecated", [])


def custom_visuals() -> list[dict]:
    if not MANIFEST.is_file():
        raise SystemExit(f"[FAIL] manifest not found: {MANIFEST}")
    out = []
    with MANIFEST.open(newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            guid = (row.get("VisualGuid") or "").strip()
            pkg = PBIVIZ / (row.get("PBIVIZ") or "").strip()
            roles: list[str] = []
            if pkg.is_file():
                try:
                    with zipfile.ZipFile(pkg) as zf:
                        entry = next(n for n in zf.namelist() if n.endswith(".pbiviz.json"))
                        caps = json.loads(zf.read(entry).decode("utf-8-sig"))
                    roles = [
                        {"name": r["name"], "kind": r.get("kind", ""), "required": bool(r.get("required"))}
                        for r in caps.get("capabilities", {}).get("dataRoles", [])
                    ]
                except (zipfile.BadZipFile, StopIteration, json.JSONDecodeError, KeyError) as exc:
                    print(f"[WARN] {row['Visual']}: could not read roles ({exc})", file=sys.stderr)
            out.append({
                "name": row["Visual"].strip(),
                "guid": guid,
                "version": (row.get("Version") or "").strip(),
                "publisher": (row.get("Publisher") or "").strip(),
                "roles": roles,
            })
    return sorted(out, key=lambda r: r["name"])


def slicer_contract() -> dict:
    """Slicer types and the data.mode values of the classic slicer."""
    return {
        "types": [
            {"type": "slicer", "modes": ["Basic", "Dropdown", "Between", "Before", "After", "Relative", "RelativeTime"]},
            {"type": "listSlicer", "modes": []},
            {"type": "advancedSlicerVisual", "modes": []},
        ],
        "customFilterVisuals": [
            {"guid": "ChicletSlicer1448559807354", "name": "Chiclet Slicer"},
            {"guid": "Timeline1447991079100", "name": "Timeline Slicer"},
            {"guid": "textFilter25A4896A83E0487089E2B90C9AE57C8A", "name": "Text Filter"},
        ],
        "unsupported": [
            {"name": "Input slicer", "reason": "No matching type in the report-author catalog, and textSlicer is not a verified alias. Author it in Desktop."},
        ],
    }


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args(argv)

    natives = native_types()
    customs = custom_visuals()

    doc = {
        "_comment": (
            "Allowed visual and slicer contract for templates/html-prototype. "
            "Generated by scripts/generate_visual_allowlist.py - do not edit by hand. "
            "Regenerate after adding a visual to the gallery or to the CLI catalog."
        ),
        "generatedFrom": {
            "nativeTypes": "powerbi-report-author catalog list",
            "customVisuals": "samples/visual-gallery-assets/manifest.csv + each .pbiviz capabilities.dataRoles",
        },
        "canvas": {"width": 1920, "height": 1080, "margin": 32, "gutter": 24},
        "native": {
            "allowed": natives,
            "noRoleTypes": sorted(t for t in NO_ROLE_TYPES if t in natives),
        },
        "excludedNative": EXCLUDED_NATIVE,
        "custom": customs,
        "slicers": slicer_contract(),
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")

    # A second, browser-loadable copy. The mockup is opened straight off disk, and
    # fetch() of a sibling file is blocked by CORS on file:// URLs - a classic
    # <script src> is not. Same content, assigned to window so the page's checker
    # can reach it without a server.
    js_out = args.out.with_suffix(".js")
    payload = json.dumps(doc, indent=2, ensure_ascii=False)
    js_out.write_text(
        "// GENERATED by scripts/generate_visual_allowlist.py - do not edit.\n"
        f"// Canonical copy: {args.out.name}\n"
        f"window.PBI_VISUAL_ALLOWLIST = {payload};\n",
        encoding="utf-8",
        newline="\n",
    )

    print(f"[PASS] {len(natives)} native type(s), {len(customs)} custom visual(s) -> {args.out.relative_to(REPO)}")
    print(f"[PASS] browser wrapper -> {js_out.relative_to(REPO)}")
    print(f"[PASS] {len(EXCLUDED_NATIVE)} native type(s) excluded with a recorded reason")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))