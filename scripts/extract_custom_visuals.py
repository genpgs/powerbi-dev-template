#!/usr/bin/env python3
"""
extract_custom_visuals.py — Register the gallery's custom visual packages locally.

Why this exists
---------------
A PBIP report binds a custom visual by GUID, in two places:

  * report.json  -> publicCustomVisuals[]
  * visual.json  -> visual.visualType

Desktop additionally needs the package payload itself, under
`<Report>/CustomVisuals/<guid>/`. This script unzips each `.pbiviz` from the
local staging folder into exactly that layout, and writes the GUID list into
report.json.

Nothing here is committed. The packages are publisher binaries (Microsoft
AppSource listings), and bundling them in this repository is a licensing
decision that is not ours to make — see docs/POWER_BI_VISUAL_COVERAGE.md.
`.gitignore` excludes `**/CustomVisuals/` and `*.pbiviz`, so running this
produces an untracked working-tree state that Desktop can render and that a
clone cannot.

Run:
    python3 scripts/extract_custom_visuals.py
    python3 scripts/extract_custom_visuals.py --check     # verify only
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

DEFAULT_ASSETS = REPO / "samples" / "visual-gallery-assets"
DEFAULT_PBIVIZ = DEFAULT_ASSETS / "PBIVIZ"
DEFAULT_MANIFEST = DEFAULT_ASSETS / "manifest.csv"
DEFAULT_REPORT = (
    REPO / "samples" / "pbip-visual-gallery" / "VisualGallery.Report"
)


def fail(msg: str) -> None:
    print(f"[FAIL] {msg}")
    FAILURES.append(msg)


PASSES: list[str] = []
FAILURES: list[str] = []


def ok(msg: str) -> None:
    PASSES.append(msg)
    print(f"[PASS] {msg}")


def load_manifest(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        fail(f"manifest not found: {path}")
        return []
    with path.open(newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    ok(f"manifest loaded: {len(rows)} visual(s) from {path.name}")
    return rows


def normalise_version(version: str | None) -> str:
    """Compare versions by value, not by component count.

    The marketplace and the manifest pad versions to four components, but
    several Microsoft packages declare three: ForceGraph ships `2.0.2` where
    the manifest and the filename say `2.0.2.0`. Those are the same version, so
    trailing zero components are dropped before comparing. A genuine bump such
    as 2.0.3 vs 2.0.2.0 still differs.
    """
    if not version:
        return ""
    parts = [p for p in version.strip().split(".") if p != ""]
    while len(parts) > 1 and parts[-1] == "0":
        parts.pop()
    return ".".join(parts)


def visual_guid_from_package(zip_path: Path) -> tuple[str | None, str | None, str | None]:
    """Return (guid, version, displayName) from a .pbiviz's package.json."""
    try:
        with zipfile.ZipFile(zip_path) as zf:
            with zf.open("package.json") as fh:
                pkg = json.loads(fh.read().decode("utf-8-sig"))
    except (zipfile.BadZipFile, KeyError, json.JSONDecodeError) as exc:
        return None, None, f"{type(exc).__name__}: {exc}"
    visual = pkg.get("visual") or {}
    return visual.get("guid"), visual.get("version"), visual.get("displayName")


def extract(zip_path: Path, dest_root: Path) -> Path | None:
    """Unpack one .pbiviz into dest_root/<guid>/. Returns the package folder."""
    guid, _version, _name = visual_guid_from_package(zip_path)
    if guid is None:
        fail(f"could not read a visual guid from {zip_path.name}")
        return None
    target = dest_root / guid
    target.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(zip_path) as zf:
            for member in zf.namelist():
                # Refuse path traversal from a package before extracting.
                resolved = (target / member).resolve()
                if not str(resolved).startswith(str(target.resolve())):
                    fail(f"{zip_path.name}: refusing unsafe member path {member!r}")
                    return None
            zf.extractall(target)
    except zipfile.BadZipFile as exc:
        fail(f"{zip_path.name}: not a valid zip ({exc})")
        return None
    return target


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--assets", type=Path, default=DEFAULT_PBIVIZ,
                    help="folder of .pbiviz packages (default: samples/visual-gallery-assets/PBIVIZ)")
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST,
                    help="manifest.csv to cross-check GUIDs and versions against")
    ap.add_argument("--report", type=Path, default=DEFAULT_REPORT,
                    help="the .Report folder to register packages into")
    ap.add_argument("--check", action="store_true",
                    help="verify registration and GUID agreement without writing")
    args = ap.parse_args(argv)

    print(f"[INFO] packages: {args.assets}")
    print(f"[INFO] report:   {args.report}")

    rows = load_manifest(args.manifest)
    if not rows:
        print()
        print(f"[FAIL] {len(FAILURES)} check(s) failed, {len(PASSES)} passed.")
        return 1

    custom_visuals_dir = args.report / "CustomVisuals"
    report_json = args.report / "definition" / "report.json"

    # ── Cross-check every package against the manifest ────────────────────────
    guids: list[str] = []
    for row in rows:
        name = row["Visual"]
        manifest_guid = (row.get("VisualGuid") or "").strip()
        manifest_version = (row.get("Version") or "").strip()
        pbiviz_name = (row.get("PBIVIZ") or "").strip()

        if not manifest_guid:
            fail(f"{name}: manifest has no VisualGuid")
            continue

        package = args.assets / pbiviz_name
        if not package.is_file():
            fail(f"{name}: package missing: {package.name}")
            continue

        pkg_guid, pkg_version, pkg_display = visual_guid_from_package(package)
        if pkg_guid != manifest_guid:
            fail(f"{name}: package guid {pkg_guid!r} != manifest VisualGuid {manifest_guid!r}")
            continue
        if normalise_version(pkg_version) != normalise_version(manifest_version):
            fail(f"{name}: package version {pkg_version!r} != manifest Version {manifest_version!r}")
            continue

        guids.append(manifest_guid)

        target = custom_visuals_dir / manifest_guid
        if args.check:
            if (target / "package.json").is_file():
                ok(f"{name}: registered at {target.name}")
            else:
                fail(f"{name}: not registered (run without --check)")
        else:
            extract(package, custom_visuals_dir)
            if (target / "package.json").is_file():
                ok(f"{name}: {manifest_guid} v{manifest_version} ({pkg_display})")
            else:
                fail(f"{name}: extract did not produce package.json")

    # ── Register the GUID list in report.json ────────────────────────────────
    if report_json.is_file():
        doc = json.loads(report_json.read_text(encoding="utf-8"))
        current = list(doc.get("publicCustomVisuals") or [])
        wanted = sorted(set(guids))

        if args.check:
            if sorted(set(current)) == wanted:
                ok(f"report.json publicCustomVisuals matches all {len(wanted)} package(s)")
            else:
                missing = sorted(set(wanted) - set(current))
                extra = sorted(set(current) - set(wanted))
                fail(f"report.json publicCustomVisuals out of sync; missing={missing} unexpected={extra}")
        else:
            doc["publicCustomVisuals"] = wanted
            report_json.write_text(
                json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
                newline="\n",
            )
            ok(f"report.json publicCustomVisuals set to {len(wanted)} GUID(s)")
    else:
        fail(f"report.json not found: {report_json}")

    print()
    if FAILURES:
        print(f"[FAIL] {len(FAILURES)} check(s) failed, {len(PASSES)} passed.")
        return 1
    print(f"[PASS] All {len(PASSES)} check(s) passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))