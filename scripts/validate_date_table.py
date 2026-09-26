#!/usr/bin/env python3
"""
validate_date_table.py — Validate the Calendar TMDL against the configured fiscal pattern.
Run from the repo root: python3 scripts/validate_date_table.py

Reads config/fiscal-calendar.json to determine which pattern-specific columns to expect.
"""

import json
import sys
from pathlib import Path

# ── Load fiscal calendar config ───────────────────────────────────────────────
cfg_path = Path("config/fiscal-calendar.json")
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

# ── Locate TMDL files ─────────────────────────────────────────────────────────
sample_root = Path("samples/pbip-calendar-baseline")
c_path = next(sample_root.rglob("tables/Calendar.tmdl"), None)
m_path = next(sample_root.rglob("model.tmdl"), None)
e_path = next(sample_root.rglob("expressions.tmdl"), None)

if not all([c_path, m_path, e_path]):
    missing = [n for n, p in [("Calendar.tmdl", c_path), ("model.tmdl", m_path), ("expressions.tmdl", e_path)] if p is None]
    print(f"[FAIL] Missing TMDL files: {missing}")
    print("       Is the sample PBIP present in samples/pbip-calendar-baseline/?")
    sys.exit(1)

c_text = c_path.read_text(encoding="utf-8")
m_text = m_path.read_text(encoding="utf-8")
e_text = e_path.read_text(encoding="utf-8")

# ── Run checks ────────────────────────────────────────────────────────────────
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

# ── Print results ─────────────────────────────────────────────────────────────
all_pass = True
for name, result in checks.items():
    status = "[PASS]" if result else "[FAIL]"
    print(f"{status} {name}")
    if not result:
        all_pass = False

if all_pass:
    print(f"\n[PASS] All {len(checks)} Calendar TMDL checks passed.")
    sys.exit(0)
else:
    failed = sum(1 for v in checks.values() if not v)
    print(f"\n[FAIL] {failed}/{len(checks)} Calendar TMDL check(s) failed.")
    sys.exit(1)
