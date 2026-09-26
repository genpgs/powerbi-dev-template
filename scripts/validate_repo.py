#!/usr/bin/env python3
"""
validate_repo.py — Validate Power BI repo structure, JSON syntax, and required files.
Run from the repo root: python3 scripts/validate_repo.py
"""

import json
import sys
from pathlib import Path

# ── Required files ────────────────────────────────────────────────────────────
REQUIRED_FILES = [
    ".gitignore",
    ".env.example",
    "README.md",
    "CHANGELOG.md",
    "config/fiscal-calendar.json",
    "power-query/fnCalendar.m",
    "power-query/fnCalendarWeekBased.m",
    "power-query/fnFiscalCalendarConfig.m",
    "scripts/validate_repo.py",
    "scripts/validate_date_table.py",
    "scripts/validate_pbir.sh",
    "hooks/pre-commit",
    "mcp/mcp.json.example",
    "dax/queries/validate-calendar.dax",
    "docs/GETTING_STARTED.md",
    "docs/fiscal-calendar.md",
    ".devcontainer/devcontainer.json",
    ".github/workflows/validate.yml",
]

REQUIRED_SKILL_FILES = [
    ".agents/skills/powerbi-report-cli/SKILL.md",
    ".agents/skills/semantic-model-authoring/SKILL.md",
    ".agents/skills/fabriciq/SKILL.md",
    ".agents/common/COMMON-CORE.md",
    ".agents/common/COMMON-CLI.md",
]

errors = []
passes = []


def check(condition: bool, pass_msg: str, fail_msg: str) -> bool:
    if condition:
        passes.append(pass_msg)
    else:
        errors.append(fail_msg)
    return condition


# ── 1. Required files exist ───────────────────────────────────────────────────
for f in REQUIRED_FILES + REQUIRED_SKILL_FILES:
    check(
        Path(f).exists(),
        f"[PASS] Found: {f}",
        f"[FAIL] Missing required file: {f}",
    )

# ── 2. JSON syntax ────────────────────────────────────────────────────────────
for p in Path(".").rglob("*.json"):
    if any(skip in str(p) for skip in ["node_modules", ".git", "__pycache__"]):
        continue
    try:
        json.loads(p.read_text(encoding="utf-8"))
        passes.append(f"[PASS] Valid JSON: {p}")
    except json.JSONDecodeError as e:
        errors.append(f"[FAIL] Invalid JSON in {p}: {e}")

# ── 3. .env not committed ─────────────────────────────────────────────────────
check(
    not Path(".env").exists(),
    "[PASS] .env not committed",
    "[FAIL] .env file found — it must not be committed (add to .gitignore)",
)

# ── 4. No binary .pbix files ──────────────────────────────────────────────────
pbix_files = [str(p) for p in Path(".").rglob("*.pbix") if ".git" not in str(p)]
check(
    len(pbix_files) == 0,
    "[PASS] No .pbix binary files",
    f"[FAIL] Binary .pbix file(s) found (use PBIP instead): {pbix_files}",
)

# ── 5. PBIP folder structure ──────────────────────────────────────────────────
for pbip in Path("samples").rglob("*.pbip"):
    base = pbip.stem
    parent = pbip.parent
    sm = parent / f"{base}.SemanticModel"
    rpt = parent / f"{base}.Report"
    check(sm.is_dir(), f"[PASS] SemanticModel folder: {sm}", f"[FAIL] Missing: {sm}")
    check(rpt.is_dir(), f"[PASS] Report folder: {rpt}", f"[FAIL] Missing: {rpt}")
    for req in [
        sm / "definition.pbism",
        sm / "definition" / "model.tmdl",
        sm / "definition" / "expressions.tmdl",
        rpt / "definition.pbir",
    ]:
        check(req.exists(), f"[PASS] Found: {req}", f"[FAIL] Missing: {req}")

# ── 6. fiscal-calendar.json valid pattern ────────────────────────────────────
cfg_path = Path("config/fiscal-calendar.json")
if cfg_path.exists():
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    valid_patterns = {"standard", "445", "454", "544", "13period"}
    pattern = cfg.get("pattern", "")
    check(
        pattern in valid_patterns,
        f"[PASS] fiscal-calendar.json pattern '{pattern}' is valid",
        f"[FAIL] fiscal-calendar.json pattern '{pattern}' invalid. Must be one of: {valid_patterns}",
    )

# ── Summary ───────────────────────────────────────────────────────────────────
for msg in passes:
    print(msg)
for msg in errors:
    print(msg)

if errors:
    print(f"\n[FAIL] {len(errors)} check(s) failed, {len(passes)} passed.")
    sys.exit(1)
else:
    print(f"\n[PASS] All {len(passes)} repo validation checks passed.")
    sys.exit(0)
