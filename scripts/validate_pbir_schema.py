#!/usr/bin/env python3
"""
validate_pbir_schema.py — Cross-platform PBIR validator for Linux/macOS/Windows.
Validates report.json, pages.json, page.json, and visual.json structures and schemas.

Run from anywhere; the scan is anchored to the repo root so results do not depend on cwd.
Only repo-owned reports are checked: a `.Report` folder that `.gitignore` excludes is
skipped, so third-party sample projects in local staging folders are not our problem.
Errors block (exit 1); warnings are advisory and never block (exit 0).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pbir_discovery  # noqa: E402

# The report separator below is a non-ASCII box-drawing char, which crashes on a cp1252
# console. Reconfigure stdout so the same output works on Windows, Linux and macOS.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

errors = []
passes = []
warns = []

REPO_ROOT = Path(__file__).resolve().parent.parent

# Desktop-canonical PBIR shape. See docs/LINUX_WORKFLOW_GAPS.md GAP-09.
VERSION_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json"
VERSION_VALUE = "2.0.0"
# GAP-10: Desktop writes one .platform per item folder (Report AND SemanticModel).
PLATFORM_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json"
PAGES_META_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json"
PAGE_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json"

def check(condition: bool, pass_msg: str, fail_msg: str) -> bool:
    if condition:
        passes.append(pass_msg)
    else:
        errors.append(fail_msg)
    return condition

def warn(condition: bool, pass_msg: str, warn_msg: str) -> bool:
    if condition:
        passes.append(pass_msg)
    else:
        warns.append(f"[WARN] {warn_msg}")
    return condition

# Find all repo-owned .Report folders
report_dirs = pbir_discovery.report_dirs(REPO_ROOT)
if not report_dirs:
    print("[WARN] No .Report directories found.")
    sys.exit(0)

for r_dir in report_dirs:
    rel = r_dir.relative_to(REPO_ROOT)
    print(f"\n[INFO] Validating PBIR Report: {rel}")
    def_dir = r_dir / "definition"
    
    # 0. .platform — Desktop writes one per item folder. Its absence is a
    #    PBIR_PLATFORM_MISSING error in the Fabric CLI and shows up as an unidentified
    #    item in the Power BI Project view, so it is a hard error, not a warning.
    plat = r_dir / ".platform"
    if check(plat.exists(), f"[PASS] .platform exists", f"[FAIL] Missing {plat} (GAP-10)"):
        try:
            pj = json.loads(plat.read_text(encoding="utf-8"))
            check(pj.get("$schema") == PLATFORM_SCHEMA,
                  f"[PASS] .platform $schema matches Desktop canonical",
                  f"[FAIL] .platform $schema is {pj.get('$schema')!r}; expected {PLATFORM_SCHEMA!r} (GAP-10)")
            meta = pj.get("metadata", {})
            check(meta.get("type") == "Report",
                  f"[PASS] .platform metadata.type is 'Report'",
                  f"[FAIL] .platform metadata.type is {meta.get('type')!r}; expected 'Report' (GAP-10)")
            check(meta.get("displayName") == r_dir.name[:-len(".Report")],
                  f"[PASS] .platform displayName matches folder ('{meta.get('displayName')}')",
                  f"[FAIL] .platform displayName is {meta.get('displayName')!r}; folder is {r_dir.name[:-len('.Report')]!r} (GAP-10)")
            cfg = pj.get("config", {})
            check(bool(cfg.get("logicalId")),
                  f"[PASS] .platform config.logicalId present",
                  f"[FAIL] .platform config.logicalId missing (GAP-10)")
        except json.JSONDecodeError as e:
            errors.append(f"[FAIL] Invalid JSON in {plat}: {e}")

    # 1. definition.pbir
    pbir_file = r_dir / "definition.pbir"
    if check(pbir_file.exists(), f"[PASS] definition.pbir exists", f"[FAIL] Missing {pbir_file}"):
        try:
            pbir_json = json.loads(pbir_file.read_text(encoding="utf-8"))
            check("version" in pbir_json, f"[PASS] definition.pbir has version", f"[FAIL] {pbir_file} missing version")
            check("$schema" in pbir_json, f"[PASS] definition.pbir has $schema", f"[FAIL] {pbir_file} missing $schema (Desktop writes it; tools that strip it can still open but round-trip badly)")
            check("datasetReference" in pbir_json, f"[PASS] definition.pbir has datasetReference", f"[FAIL] {pbir_file} missing datasetReference")
        except json.JSONDecodeError as e:
            errors.append(f"[FAIL] Invalid JSON in {pbir_file}: {e}")

    # 2. version.json — Desktop writes a $schema/version pair; a hand-rolled file often omits both.
    v_file = def_dir / "version.json"
    if check(v_file.exists(), f"[PASS] version.json exists", f"[FAIL] Missing {v_file}"):
        try:
            vj = json.loads(v_file.read_text(encoding="utf-8"))
            check(vj.get("$schema") == VERSION_SCHEMA,
                  f"[PASS] version.json $schema matches Desktop canonical",
                  f"[FAIL] version.json $schema is {vj.get('$schema')!r}; expected {VERSION_SCHEMA!r} (GAP-09)")
            check(vj.get("version") == VERSION_VALUE,
                  f"[PASS] version.json version == {VERSION_VALUE}",
                  f"[FAIL] version.json version is {vj.get('version')!r}; expected {VERSION_VALUE!r} (GAP-09)")
        except json.JSONDecodeError as e:
            errors.append(f"[FAIL] Invalid JSON in {v_file}: {e}")

    # 3. report.json — Desktop-canonical shape (see GAP-09).
    #    themeCollection is an object with a `baseTheme` entry, and resourcePackages is a
    #    FLAT list of {name, type, items[]} — not a list of {"resourcePackage": {...}}
    #    wrappers. Some hand-written generators emit the wrapped form; Desktop still opens
    #    it but the theme silently fails to apply, so it is worth flagging.
    rep_file = def_dir / "report.json"
    if check(rep_file.exists(), f"[PASS] report.json exists", f"[FAIL] Missing {rep_file}"):
        try:
            rj = json.loads(rep_file.read_text(encoding="utf-8"))
            check("$schema" in rj, f"[PASS] report.json has $schema",
                  f"[FAIL] {rep_file} missing $schema (GAP-09)")
            check("layoutOptimization" not in rj, f"[PASS] report.json omits layoutOptimization (Desktop-canonical)",
                  f"[FAIL] {rep_file} sets layoutOptimization; Desktop drops it on save (GAP-09)")

            themes = rj.get("themeCollection")
            if check(isinstance(themes, dict) and "baseTheme" in themes,
                     f"[PASS] report.json themeCollection.baseTheme present",
                     f"[FAIL] {rep_file} themeCollection must be an object with a 'baseTheme' entry, got {type(themes).__name__} (GAP-09)"):
                check(bool(themes["baseTheme"].get("name")),
                      f"[PASS] baseTheme is named '{themes['baseTheme'].get('name')}'",
                      f"[FAIL] baseTheme in {rep_file} has no name")

            for i, pkg in enumerate(rj.get("resourcePackages", [])):
                if "resourcePackage" in pkg and not {"name", "type"} & set(pkg):
                    errors.append(
                        f"[FAIL] {rep_file} resourcePackages[{i}] uses the wrapped "
                        f"{{'resourcePackage': {{...}}}} form; Desktop writes a flat "
                        f"{{'name', 'type', 'items'}} entry (GAP-09)"
                    )
                else:
                    check("name" in pkg and "type" in pkg,
                          f"[PASS] resourcePackages[{i}] is a flat entry ('{pkg.get('name')}')",
                          f"[FAIL] {rep_file} resourcePackages[{i}] missing name/type (GAP-09)")
        except json.JSONDecodeError as e:
            errors.append(f"[FAIL] Invalid JSON in {rep_file}: {e}")

    # 4. pages.json
    pages_meta = def_dir / "pages" / "pages.json"
    if check(pages_meta.exists(), f"[PASS] pages.json exists", f"[FAIL] Missing {pages_meta}"):
        try:
            pm = json.loads(pages_meta.read_text(encoding="utf-8"))
            check(pm.get("$schema") == PAGES_META_SCHEMA,
                  f"[PASS] pages.json $schema matches Desktop canonical",
                  f"[FAIL] pages.json $schema is {pm.get('$schema')!r}; expected {PAGES_META_SCHEMA!r}. Fabric rejects PBIR definition JSON without $schema (GAP-10)")
            order = pm.get("pageOrder", [])
            check(len(order) > 0, f"[PASS] pages.json lists {len(order)} page(s)", f"[FAIL] pages.json pageOrder is empty")
            for page_name in order:
                page_json = def_dir / "pages" / page_name / "page.json"
                if check(page_json.exists(), f"[PASS] Page definition exists: {page_name}", f"[FAIL] Missing page definition: {page_json}"):
                    pj = json.loads(page_json.read_text(encoding="utf-8"))
                    check(pj.get("$schema") == PAGE_SCHEMA,
                          f"[PASS] {page_name}/page.json $schema matches Desktop canonical",
                          f"[FAIL] {page_name}/page.json $schema is {pj.get('$schema')!r}; expected {PAGE_SCHEMA!r} (GAP-10)")
                    check("name" in pj and "displayName" in pj, f"[PASS] {page_name} metadata valid", f"[FAIL] {page_name} missing name/displayName")
                    check("displayOption" in pj,
                          f"[PASS] {page_name} has displayOption ('{pj.get('displayOption')}')",
                          f"[FAIL] {page_name}/page.json missing displayOption — the page 2.1.0 schema requires it and Fabric rejects the file (GAP-10)")
                    warn(pj.get("width") == 1280 and pj.get("height") == 720, f"[PASS] {page_name} standard 16:9 canvas (1280x720)", f"{page_name} non-standard canvas size: {pj.get('width')}x{pj.get('height')}")

                # Check visuals
                visuals_dir = def_dir / "pages" / page_name / "visuals"
                if visuals_dir.is_dir():
                    v_files = list(visuals_dir.rglob("visual.json"))
                    warn(len(v_files) > 0, f"[PASS] Page '{page_name}' contains {len(v_files)} visual(s)", f"Page '{page_name}' has 0 visuals")
                    for vf in v_files:
                        vj = json.loads(vf.read_text(encoding="utf-8"))
                        check("position" in vj, f"[PASS] Visual {vf.parent.name} has position", f"[FAIL] Visual {vf} missing position")
                        check("visual" in vj and "visualType" in vj["visual"], f"[PASS] Visual {vf.parent.name} has visualType '{vj.get('visual',{}).get('visualType')}'", f"[FAIL] Visual {vf} missing visualType")
        except json.JSONDecodeError as e:
            errors.append(f"[FAIL] Invalid JSON in pages metadata: {e}")

print("\n" + "─"*50)
for w in warns:
    print(w)
if warns:
    print(f"[INFO] {len(warns)} warning(s) — advisory only, not blocking.")
if errors:
    for e in errors:
        print(e)
    print(f"\n[FAIL] PBIR Validation failed with {len(errors)} error(s).")
    sys.exit(1)
else:
    print(f"[PASS] All {len(passes)} PBIR checks passed across all reports.")
    sys.exit(0)
