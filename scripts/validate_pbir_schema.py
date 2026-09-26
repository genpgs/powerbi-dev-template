#!/usr/bin/env python3
"""
validate_pbir_schema.py — Cross-platform PBIR validator for Linux/macOS/Windows.
Validates report.json, pages.json, page.json, and visual.json structures and schemas.
"""
import json
import sys
from pathlib import Path

errors = []
passes = []

def check(condition: bool, pass_msg: str, fail_msg: str) -> bool:
    if condition:
        passes.append(pass_msg)
    else:
        errors.append(fail_msg)
    return condition

# Find all .Report folders
report_dirs = list(Path(".").rglob("*.Report"))
if not report_dirs:
    print("[WARN] No .Report directories found.")
    sys.exit(0)

for r_dir in report_dirs:
    if ".git" in str(r_dir):
        continue
    print(f"\n[INFO] Validating PBIR Report: {r_dir}")
    def_dir = r_dir / "definition"
    
    # 1. definition.pbir
    pbir_file = r_dir / "definition.pbir"
    if check(pbir_file.exists(), f"[PASS] {pbir_file} exists", f"[FAIL] Missing {pbir_file}"):
        try:
            pbir_json = json.loads(pbir_file.read_text(encoding="utf-8"))
            check("version" in pbir_json, f"[PASS] {pbir_file} has version", f"[FAIL] {pbir_file} missing version")
            check("datasetReference" in pbir_json, f"[PASS] {pbir_file} has datasetReference", f"[FAIL] {pbir_file} missing datasetReference")
        except json.JSONDecodeError as e:
            errors.append(f"[FAIL] Invalid JSON in {pbir_file}: {e}")

    # 2. version.json
    v_file = def_dir / "version.json"
    check(v_file.exists(), f"[PASS] {v_file} exists", f"[FAIL] Missing {v_file}")

    # 3. report.json
    rep_file = def_dir / "report.json"
    check(rep_file.exists(), f"[PASS] {rep_file} exists", f"[FAIL] Missing {rep_file}")

    # 4. pages.json
    pages_meta = def_dir / "pages" / "pages.json"
    if check(pages_meta.exists(), f"[PASS] {pages_meta} exists", f"[FAIL] Missing {pages_meta}"):
        try:
            pm = json.loads(pages_meta.read_text(encoding="utf-8"))
            order = pm.get("pageOrder", [])
            check(len(order) > 0, f"[PASS] pages.json lists {len(order)} page(s)", f"[FAIL] pages.json pageOrder is empty")
            for page_name in order:
                page_json = def_dir / "pages" / page_name / "page.json"
                if check(page_json.exists(), f"[PASS] Page definition exists: {page_name}", f"[FAIL] Missing page definition: {page_json}"):
                    pj = json.loads(page_json.read_text(encoding="utf-8"))
                    check("name" in pj and "displayName" in pj, f"[PASS] {page_name} metadata valid", f"[FAIL] {page_name} missing name/displayName")
                    check(pj.get("width") == 1280 and pj.get("height") == 720, f"[PASS] {page_name} standard 16:9 canvas (1280x720)", f"[WARN] Non-standard canvas size: {pj.get('width')}x{pj.get('height')}")

                # Check visuals
                visuals_dir = def_dir / "pages" / page_name / "visuals"
                if visuals_dir.is_dir():
                    v_files = list(visuals_dir.rglob("visual.json"))
                    check(len(v_files) > 0, f"[PASS] Page '{page_name}' contains {len(v_files)} visual(s)", f"[WARN] Page '{page_name}' has 0 visuals")
                    for vf in v_files:
                        vj = json.loads(vf.read_text(encoding="utf-8"))
                        check("position" in vj, f"[PASS] Visual {vf.parent.name} has position", f"[FAIL] Visual {vf} missing position")
                        check("visual" in vj and "visualType" in vj["visual"], f"[PASS] Visual {vf.parent.name} has visualType '{vj.get('visual',{}).get('visualType')}'", f"[FAIL] Visual {vf} missing visualType")
        except json.JSONDecodeError as e:
            errors.append(f"[FAIL] Invalid JSON in pages metadata: {e}")

print("\n" + "─"*50)
if errors:
    for e in errors:
        print(e)
    print(f"\n[FAIL] PBIR Validation failed with {len(errors)} error(s).")
    sys.exit(1)
else:
    print(f"[PASS] All {len(passes)} PBIR checks passed across all reports.")
    sys.exit(0)
