#!/usr/bin/env python3
"""
validate_date_table.py — Validate the Calendar TMDL against the configured fiscal pattern.

Run from the repo root:   python3 scripts/validate_date_table.py
Validate a specific model: python3 scripts/validate_date_table.py path/to/Model.SemanticModel
                          python3 scripts/validate_date_table.py path/to/Project.pbip

With no arguments every *.SemanticModel folder in the repo is checked, so the script is
useful in a downstream project whose calendar is not the template's sample.

Reads config/fiscal-calendar.json to determine which pattern-specific columns to expect.
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _rel(p: Path) -> str:
    """Repo-relative path when possible, absolute otherwise."""
    try:
        return str(p.relative_to(REPO_ROOT))
    except ValueError:
        return str(p)

# ── Resolve targets ──────────────────────────────────────────────────────────
def resolve_models(raw_targets):
    """Expand paths to semantic-model folders that contain a Calendar table."""
    if raw_targets:
        roots = []
        for raw in raw_targets:
            p = Path(raw).resolve()
            if p.is_file() and p.suffix.lower() == ".pbip":
                p = p.parent
            roots.append(p)
    else:
        roots = sorted(
            p for p in REPO_ROOT.rglob("*.SemanticModel")
            if ".git" not in p.parts and p.is_dir()
        )

    models = []
    for root in roots:
        for found in sorted(root.rglob("Calendar.tmdl")):
            if found.parent.name != "tables":
                continue
            # <model>/definition/tables/Calendar.tmdl -> parents[2]; <model>/tables/... -> parents[1]
            model_root = found.parents[2] if found.parents[1].name == "definition" else found.parents[1]
            models.append(model_root)
    # De-duplicate while preserving order.
    seen, unique = set(), []
    for m in models:
        if m not in seen:
            seen.add(m)
            unique.append(m)
    return unique


# ── Load fiscal calendar config ───────────────────────────────────────────────
cfg_path = REPO_ROOT / "config" / "fiscal-calendar.json"
pattern = "445"  # default

if cfg_path.exists():
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        pattern = cfg.get("pattern", "445")
    except json.JSONDecodeError as e:
        print(f"[FAIL] Cannot parse config/fiscal-calendar.json: {e}")
        sys.exit(1)
else:
    print("[WARN] config/fiscal-calendar.json not found — assuming pattern=445")

week_based = pattern in ("445", "454", "544", "13period")
print(f"[INFO] Validating for pattern: {pattern} ({'week-based' if week_based else 'month-aligned'})")

models = resolve_models(sys.argv[1:])
if not models:
    print("[FAIL] No semantic model with a tables/Calendar.tmdl was found.")
    print("       Pass a path, or check that the model has a Calendar table.")
    sys.exit(1)
print(f"[INFO] Found {len(models)} semantic model(s) with a Calendar table.")

overall_pass = True
for model_root in models:
    c_path = model_root / "definition" / "tables" / "Calendar.tmdl"
    if not c_path.is_file():
        c_path = model_root / "tables" / "Calendar.tmdl"
    m_path = model_root / "definition" / "model.tmdl"
    e_path = model_root / "definition" / "expressions.tmdl"
    if not m_path.is_file():
        m_path = model_root / "model.tmdl"
    if not e_path.is_file():
        e_path = model_root / "expressions.tmdl"

    missing = [n for n, p in [("Calendar.tmdl", c_path), ("model.tmdl", m_path),
                              ("expressions.tmdl", e_path)] if not p.is_file()]
    if missing:
        print(f"\n[FAIL] {_rel(model_root)}")
        print(f"       Missing TMDL files: {missing}")
        overall_pass = False
        continue

    print(f"\n[INFO] Model: {_rel(model_root)}")

    c_text = c_path.read_text(encoding="utf-8")
    m_text = m_path.read_text(encoding="utf-8")
    e_text = e_path.read_text(encoding="utf-8")

    # ── Run checks ────────────────────────────────────────────────────────────
    checks: dict[str, bool] = {
        "Auto date/time disabled":      "__PBI_TimeIntelligenceEnabled = 0" in m_text,
        "Calendar marked as Time table":"dataCategory: Time" in c_text,
        "Date column with isKey":       "column Date" in c_text and "isKey" in c_text,
        "List.Dates in partition":      "List.Dates" in e_text,
        "fnCalendar declared":          "expression fnCalendar" in e_text or "fnCalendar" in e_text,
    }

    if week_based:
        checks.update({
            "fnCalendarWeekBased declared":     "fnCalendarWeekBased" in e_text,
            "FiscalWeekNumber column":          "FiscalWeekNumber" in c_text,
            "FiscalPeriodNumber column":        "FiscalPeriodNumber" in c_text,
            "FiscalPeriodLabel column":         "FiscalPeriodLabel" in c_text,
            "FiscalQuarterNumber column":       "FiscalQuarterNumber" in c_text,
            "FiscalQuarter column":             "FiscalQuarter" in c_text,
            "FiscalWeekOfPeriod column":        "FiscalWeekOfPeriod" in c_text,
            "FiscalYear column":                "column FiscalYear" in c_text,
            "FiscalYearLabel column":           "FiscalYearLabel" in c_text,
            "CalendarYear column":              "CalendarYear" in c_text,
        })
    else:
        # Month-aligned (standard) pattern
        checks.update({
            "FiscalYearStartDate column":  "FiscalYearStartDate" in c_text,
            "FiscalMonthNumber column":    "FiscalMonthNumber" in c_text,
            "FiscalQuarterNumber column":  "FiscalQuarterNumber" in c_text,
            "FiscalYear column":           "column FiscalYear" in c_text,
        })

    for name, result in checks.items():
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {name}")
        if not result:
            overall_pass = False

print()
if overall_pass:
    print(f"[PASS] All Calendar TMDL checks passed across {len(models)} model(s).")
    sys.exit(0)
else:
    print("[FAIL] Calendar TMDL check(s) failed.")
    sys.exit(1)
