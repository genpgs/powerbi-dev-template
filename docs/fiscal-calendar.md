# Fiscal Calendar Reference

This document explains the fiscal calendar patterns supported by this template, the Power Query M functions that implement them, and how to configure the sample PBIP.

---

## Calendar Patterns

### `standard` — Month-aligned

The simplest option. Fiscal periods follow calendar months. The fiscal year starts on the 1st of a configured month (e.g., April 1 for a UK/ANZ financial year).

**Function**: `fnCalendar(StartDate, EndDate, FiscalYearStartMonth, FiscalYearLabelMode, Culture)`

**When to use**: any business that doesn't need week-level standardisation.

**Example** — April fiscal year, labelled by ending year (FY2026 = Apr 2025–Mar 2026):
```m
fnCalendar(#date(2020,1,1), #date(2026,12,31), 4, "endingYear", "en-US")
```

---

### `445` — 4-4-5 weeks per quarter

The most common retail/CPG fiscal structure. Each quarter has three periods of 4, 4, and 5 weeks. Every quarter is exactly 13 weeks (91 days). The fiscal year has 52 weeks (364 days), with a 53rd week every ~5–6 years.

```
Q1: P1(4w) + P2(4w) + P3(5w) = 13 weeks
Q2: P4(4w) + P5(4w) + P6(5w) = 13 weeks
Q3: P7(4w) + P8(4w) + P9(5w) = 13 weeks
Q4: P10(4w) + P11(4w) + P12(5w) = 13 weeks
Total: 52 weeks (364 days) per year
```

**Used by**: Target, Walmart, Home Depot, many US retailers.

---

### `454` — 4-5-4 weeks per quarter

Variant where the middle period in each quarter has 5 weeks.

```
Q1: P1(4w) + P2(5w) + P3(4w) = 13 weeks
```

**Used by**: Some European and ANZ retailers.

---

### `544` — 5-4-4 weeks per quarter

Variant where the first period in each quarter has 5 weeks.

```
Q1: P1(5w) + P2(4w) + P3(4w) = 13 weeks
```

---

### `13period` — 13 × 4-week periods

The year is divided into 13 equal periods of 4 weeks each (52 weeks total). There are no quarters — each period is standalone. The `FiscalQuarter` column shows `P01`–`P13`.

**Used by**: hospitality, healthcare, period-based retail.

```
P01(4w) + P02(4w) + … + P13(4w) = 52 weeks
```

---

## Week Anchoring

For all week-based patterns (`445`, `454`, `544`, `13period`), the fiscal year does **not** start on a fixed calendar date. Instead it starts on the nearest **WeekStartDay** on or before the nominal `FiscalYearStartDate`.

**Example**:
- `FiscalYearStartDate = 2025-02-01`, `WeekStartDay = "Saturday"`
- 2025-02-01 is already a Saturday → FY1 starts exactly 2025-02-01
- FY2 starts 2026-02-07 (nearest Saturday to 2026-02-01)

**WeekStartDay options**: `Saturday` (US retail default), `Sunday`, `Monday` (UK/EU retail default)

---

## 53-Week Years

A fiscal year normally has 52 weeks (364 days). Approximately every 5–6 years the nominal anchor drifts enough that the fiscal year has **53 weeks**. The 53rd week is appended to the last period of the year.

When this happens:
- `FiscalWeekNumber` runs 1–53 instead of 1–52
- `FiscalPeriodNumber` stays 1–12 (or 1–13 for `13period`); the 53rd week is clamped into the last period
- All DAX measures using `FiscalWeekNumber` continue to work correctly

---

## M Functions

### `fnCalendarWeekBased`

```m
fnCalendarWeekBased(
    FiscalYearStartDate as date,    // nominal start of fiscal year 1
    NumberOfYears as number,        // how many fiscal years to generate
    optional WeekPattern,           // "445" | "454" | "544" | "13period"
    optional WeekStartDay,          // "Saturday" | "Sunday" | "Monday"
    optional Culture                // "en-US", "en-GB", etc.
) as table
```

**Output columns**: `DateKey`, `Date`, `CalendarYear`, `CalendarMonthNumber`, `CalendarMonth`, `DayOfWeek`, `FiscalYear`, `FiscalYearLabel`, `FiscalYearStartDate`, `FiscalWeekNumber`, `FiscalPeriodNumber`, `FiscalPeriodLabel`, `FiscalQuarterNumber`, `FiscalQuarter`, `FiscalWeekOfPeriod`

### `fnCalendar`

```m
fnCalendar(
    StartDate as nullable date,
    EndDate as nullable date,
    optional FiscalYearStartMonth,  // 1-12
    optional FiscalYearLabelMode,   // "endingYear" | "startingYear"
    optional Culture
) as table
```

**Output columns**: `DateKey`, `Date`, `Year`, `MonthNumber`, `Month`, `YearMonth`, `YearMonthSort`, `FiscalYearStartDate`, `FiscalYearEndDate`, `FiscalYear`, `FiscalYearLabel`, `FiscalMonthNumber`, `FiscalQuarterNumber`, `FiscalQuarter`

---

## DAX Considerations

> ⚠️ Standard time intelligence functions (`TOTALYTD`, `DATESYTD`, `DATESQTD`, `DATESINPERIOD` with MONTH/QUARTER/YEAR) assume **calendar months**. They produce incorrect results with week-based fiscal calendars.

Use these patterns instead for week-based calendars:

```dax
-- Fiscal Year-to-Date (week-based)
Total Amount FYTD =
VAR CurrentFY = MAX(Calendar[FiscalYear])
VAR CurrentWk = MAX(Calendar[FiscalWeekNumber])
RETURN
CALCULATE(
    [Total Amount],
    Calendar[FiscalYear] = CurrentFY,
    Calendar[FiscalWeekNumber] <= CurrentWk
)

-- Period-to-Date
Total Amount PTD =
VAR CurrentFY = MAX(Calendar[FiscalYear])
VAR CurrentPd = MAX(Calendar[FiscalPeriodNumber])
VAR CurrentWk = MAX(Calendar[FiscalWeekNumber])
VAR PdStart   = MINX(FILTER(ALL(Calendar), Calendar[FiscalYear] = CurrentFY && Calendar[FiscalPeriodNumber] = CurrentPd), Calendar[FiscalWeekNumber])
RETURN
CALCULATE(
    [Total Amount],
    Calendar[FiscalYear] = CurrentFY,
    Calendar[FiscalPeriodNumber] = CurrentPd,
    Calendar[FiscalWeekNumber] <= CurrentWk
)

-- Same period last year (week-based)
Total Amount PY =
VAR CurrentFY  = MAX(Calendar[FiscalYear])
VAR CurrentWks = VALUES(Calendar[FiscalWeekNumber])
RETURN
CALCULATE(
    [Total Amount],
    Calendar[FiscalYear] = CurrentFY - 1,
    Calendar[FiscalWeekNumber] IN CurrentWks
)
```

---

## Changing the Pattern

1. Edit `config/fiscal-calendar.json` — change `"pattern"`, `"fiscalYearStartDate"`, `"weekStartDay"`
2. Edit the Calendar partition in `CalendarBaseline.SemanticModel/definition/tables/Calendar.tmdl` — update the M variables at the top of the partition source
3. Run validation: `python3 scripts/validate_date_table.py`
4. Open in Power BI Desktop, refresh, run `dax/queries/validate-calendar.dax`
