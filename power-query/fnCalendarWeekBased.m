// fnCalendarWeekBased.m
// Week-anchored fiscal calendar for Power BI (Standard workspace, Import mode).
// Supports 4-4-5, 4-5-4, 5-4-4, and 13-period (13 × 4-week) fiscal structures.
//
// HOW WEEK ANCHORING WORKS
// ─────────────────────────
// The fiscal year does NOT start on an exact calendar date. Instead it starts on
// the nearest WeekStartDay that falls ON OR BEFORE the nominal FiscalYearStartDate.
// Example: FiscalYearStartDate = 2025-02-01, WeekStartDay = "Saturday"
//   → 2025-02-01 is already a Saturday → FY1 starts 2025-02-01 exactly.
// Example: FiscalYearStartDate = 2025-02-03, WeekStartDay = "Saturday"
//   → nearest Saturday on or before Feb 3 is Feb 1 → FY1 starts 2025-02-01.
//
// 53-WEEK YEARS
// ─────────────
// A fiscal year has 52 weeks (364 days) by default. When the calendar would
// otherwise drift more than half a week from the nominal anchor, a 53rd week is
// inserted at the end of the year (appended to the last period). This occurs
// approximately every 5–6 years.
//
// PATTERN REFERENCE
// ─────────────────
//   445      : Q1=(4+4+5), Q2=(4+4+5), Q3=(4+4+5), Q4=(4+4+5) = 12 periods
//   454      : Q1=(4+5+4), Q2=(4+5+4), Q3=(4+5+4), Q4=(4+5+4) = 12 periods
//   544      : Q1=(5+4+4), Q2=(5+4+4), Q3=(5+4+4), Q4=(5+4+4) = 12 periods
//   13period : 13 equal 4-week periods per year. FiscalQuarter shows "P01"–"P13".
//
// OUTPUT COLUMNS
// ─────────────────────────────────────────────────────────────────────────────
//   DateKey              INT    YYYYMMDD
//   Date                 DATE
//   CalendarYear         INT    Gregorian year
//   CalendarMonthNumber  INT    1-12
//   CalendarMonth        TEXT   "January" etc.
//   DayOfWeek            TEXT   "Monday" etc.
//   FiscalYear           INT    fiscal year number (1 = first FY generated)
//   FiscalYearLabel      TEXT   "FY1", "FY2", …
//   FiscalWeekNumber     INT    week within fiscal year (1–52 or 1–53)
//   FiscalPeriodNumber   INT    period within fiscal year (1–12 or 1–13)
//   FiscalPeriodLabel    TEXT   "P01"–"P12" (or "P01"–"P13")
//   FiscalQuarterNumber  INT    1–4 (or 1–13 for 13period)
//   FiscalQuarter        TEXT   "Q1"–"Q4" (or "P01"–"P13" for 13period)
//   FiscalWeekOfPeriod   INT    week number within the current period (1–4 or 1–5)
//   FiscalYearStartDate  DATE   first day of the fiscal year this row belongs to
//
// USAGE EXAMPLES
// ─────────────────────────────────────────────────────────────────────────────
//   // 4-4-5, Saturday-anchored, 5 fiscal years from Feb 2025
//   fnCalendarWeekBased(#date(2025,2,1), 5, "445", "Saturday", "en-US")
//
//   // 13-period, Sunday-anchored, 3 fiscal years from Feb 2024
//   fnCalendarWeekBased(#date(2024,2,1), 3, "13period", "Sunday", null)
//
// PARAMETERS
// ─────────────────────────────────────────────────────────────────────────────
//   FiscalYearStartDate : date   — nominal start of fiscal year 1
//   NumberOfYears       : number — how many fiscal years to generate (≥ 1)
//   WeekPattern         : text   — "445" | "454" | "544" | "13period" (optional, default "445")
//   WeekStartDay        : text   — "Saturday" | "Sunday" | "Monday"   (optional, default "Saturday")
//   Culture             : text   — locale for month/day names          (optional, default "en-US")

(
    FiscalYearStartDate as date,
    NumberOfYears as number,
    optional WeekPattern as nullable text,
    optional WeekStartDay as nullable text,
    optional Culture as nullable text
) as table =>
let
    // ── Parameter defaults & validation ──────────────────────────────────────
    Pattern   = if WeekPattern  = null or WeekPattern  = "" then "445"       else WeekPattern,
    StartDay  = if WeekStartDay = null or WeekStartDay = "" then "Saturday"  else WeekStartDay,
    Culture_  = if Culture      = null or Culture      = "" then "en-US"     else Culture,
    NYears    = if NumberOfYears < 1 then error "NumberOfYears must be >= 1." else Number.RoundDown(NumberOfYears),

    // Validate pattern
    ValidPatterns = {"445", "454", "544", "13period"},
    _PatternCheck = if List.Contains(ValidPatterns, Pattern) then null
                    else error "WeekPattern must be one of: 445, 454, 544, 13period.",

    // Validate WeekStartDay → map to Power Query Day enum offset (0=Sunday)
    DayOffsetMap = [Saturday = 6, Sunday = 0, Monday = 1],
    DayOffset    = if Record.HasFields(DayOffsetMap, StartDay)
                   then Record.Field(DayOffsetMap, StartDay)
                   else error "WeekStartDay must be Saturday, Sunday, or Monday.",

    // ── Week-period pattern definitions ──────────────────────────────────────
    // For 4-4-5 family: list of 3 numbers = weeks in period 1, 2, 3 within each quarter
    // Repeated 4× across the year → 12 periods total
    // For 13period: 13 periods of 4 weeks each, no quarterly grouping
    PeriodPattern_3 = if Pattern = "445" then {4, 4, 5}
                      else if Pattern = "454" then {4, 5, 4}
                      else if Pattern = "544" then {5, 4, 4}
                      else {4},   // 13period sentinel — not used in quarter calc
    Is13Period    = (Pattern = "13period"),
    WeeksPerQtr   = if Is13Period then 4 else List.Sum(PeriodPattern_3),  // 13 or 13
    PeriodsPerYr  = if Is13Period then 13 else 12,
    BaseWeeksPerFY = 52,  // 53-week years handled below

    // ── Anchor FY1 start to nearest WeekStartDay on/before nominal date ──────
    NominalStart  = FiscalYearStartDate,
    NominalDOW    = Date.DayOfWeek(NominalStart, Day.Sunday),  // 0=Sun,1=Mon,...,6=Sat
    AnchorOffset  = Number.Mod(NominalDOW - DayOffset + 7, 7),
    ActualFY1Start = Date.AddDays(NominalStart, -AnchorOffset),

    // ── Compute the actual start date of each fiscal year ────────────────────
    // A FY has 52 weeks. A 53-week year occurs when the next FY's anchor would
    // otherwise land ≥ 364 days from the nominal cycle (i.e. the "nearest weekday"
    // to the next nominal date is 53 weeks away from the current FY start).
    FYStartDates = List.Generate(
        () => [fy = 1, startD = ActualFY1Start],
        each [fy] <= NYears,
        each
            let
                // Nominal start for the NEXT fiscal year
                nextNominal    = Date.AddYears(NominalStart, [fy]),
                nextNomDOW     = Date.DayOfWeek(nextNominal, Day.Sunday),
                nextAnchorOff  = Number.Mod(nextNomDOW - DayOffset + 7, 7),
                nextActual     = Date.AddDays(nextNominal, -nextAnchorOff),
                weeksInThisFY  = Number.RoundDown(Duration.Days(nextActual - [startD]) / 7)
            in
            [fy = [fy] + 1, startD = nextActual, _weeks = weeksInThisFY],
        each [startD]
    ),
    FYStartList = FYStartDates,   // list of date values, one per FY

    // ── Build list of all dates in the calendar ───────────────────────────────
    // Total days = from FY1 start to end of last FY
    // We need the end date of the last FY.
    // Re-compute next anchor after the last FY to get last FY end date.
    LastFYStart   = List.Last(FYStartList),
    AfterNominal  = Date.AddYears(NominalStart, NYears),
    AfterDOW      = Date.DayOfWeek(AfterNominal, Day.Sunday),
    AfterOffset   = Number.Mod(AfterDOW - DayOffset + 7, 7),
    AfterActual   = Date.AddDays(AfterNominal, -AfterOffset),
    TotalDays     = Duration.Days(AfterActual - ActualFY1Start),

    Dates  = List.Dates(ActualFY1Start, TotalDays, #duration(1, 0, 0, 0)),
    T      = Table.TransformColumnTypes(
                 Table.FromList(Dates, Splitter.SplitByNothing(), {"Date"}),
                 {{"Date", type date}}),

    // ── Day index (0-based from FY1 start) ───────────────────────────────────
    DI = Table.AddColumn(T, "_DayIdx",
             each Duration.Days([Date] - ActualFY1Start), Int64.Type),

    // ── Fiscal Year (1-based) ─────────────────────────────────────────────────
    // For each date, count how many FY start dates are <= Date
    FY_Col = Table.AddColumn(DI, "FiscalYear",
                 each List.Count(List.Select(FYStartList, (s) => s <= [Date])),
                 Int64.Type),
    FYLabel = Table.AddColumn(FY_Col, "FiscalYearLabel",
                  each "FY" & Text.From([FiscalYear]), type text),

    // ── Fiscal year start date for this row ───────────────────────────────────
    FYStartForRow = Table.AddColumn(FYLabel, "FiscalYearStartDate",
                        each FYStartList{[FiscalYear] - 1}, type date),

    // ── Week within fiscal year (1-based) ────────────────────────────────────
    WInFY = Table.AddColumn(FYStartForRow, "FiscalWeekNumber",
                each Number.RoundDown(Duration.Days([Date] - [FiscalYearStartDate]) / 7) + 1,
                Int64.Type),

    // ── Period within fiscal year ─────────────────────────────────────────────
    PeriodCol = Table.AddColumn(WInFY, "FiscalPeriodNumber",
        each
            let w = [FiscalWeekNumber]
            in if Is13Period then
                // 13 periods × 4 weeks; any 53rd week belongs to period 13
                Number.Min(Number.RoundDown((w - 1) / 4) + 1, 13)
               else
                let
                    wInQtr      = Number.Mod(w - 1, WeeksPerQtr) + 1,
                    cum1        = PeriodPattern_3{0},
                    cum2        = cum1 + PeriodPattern_3{1},
                    periodInQtr = if wInQtr <= cum1 then 1
                                  else if wInQtr <= cum2 then 2
                                  else 3,
                    qtrIdx      = Number.RoundDown((w - 1) / WeeksPerQtr),
                    period      = qtrIdx * 3 + periodInQtr
                in Number.Min(period, PeriodsPerYr)  // clamp 53rd-week overshoot
        , Int64.Type),

    PeriodLabel = Table.AddColumn(PeriodCol, "FiscalPeriodLabel",
                      each "P" & Text.PadStart(Text.From([FiscalPeriodNumber]), 2, "0"),
                      type text),

    // ── Quarter ───────────────────────────────────────────────────────────────
    QtrNum = Table.AddColumn(PeriodLabel, "FiscalQuarterNumber",
                 each if Is13Period
                      then [FiscalPeriodNumber]   // each period IS a "quarter"
                      else Number.RoundUp([FiscalPeriodNumber] / 3),
                 Int64.Type),
    QtrLabel = Table.AddColumn(QtrNum, "FiscalQuarter",
                   each if Is13Period
                        then "P" & Text.PadStart(Text.From([FiscalPeriodNumber]), 2, "0")
                        else "Q" & Text.From([FiscalQuarterNumber]),
                   type text),

    // ── Week within period ────────────────────────────────────────────────────
    WkOfPeriod = Table.AddColumn(QtrLabel, "FiscalWeekOfPeriod",
        each
            let w = [FiscalWeekNumber]
            in if Is13Period then
                Number.Mod(w - 1, 4) + 1
               else
                let
                    wInQtr    = Number.Mod(w - 1, WeeksPerQtr) + 1,
                    cum1      = PeriodPattern_3{0},
                    cum2      = cum1 + PeriodPattern_3{1},
                    wInPeriod = if wInQtr <= cum1 then wInQtr
                                else if wInQtr <= cum2 then wInQtr - cum1
                                else wInQtr - cum2
                in wInPeriod
        , Int64.Type),

    // ── Gregorian reference columns ───────────────────────────────────────────
    DateKey_  = Table.AddColumn(WkOfPeriod, "DateKey",
                    each Date.Year([Date])*10000 + Date.Month([Date])*100 + Date.Day([Date]),
                    Int64.Type),
    CalYr     = Table.AddColumn(DateKey_,  "CalendarYear",        each Date.Year([Date]),               Int64.Type),
    CalMoNum  = Table.AddColumn(CalYr,     "CalendarMonthNumber", each Date.Month([Date]),              Int64.Type),
    CalMo     = Table.AddColumn(CalMoNum,  "CalendarMonth",       each Date.MonthName([Date], Culture_), type text),
    DayOfWk   = Table.AddColumn(CalMo,     "DayOfWeek",           each Date.DayOfWeekName([Date], Culture_), type text),

    // ── Remove internal helper columns & reorder ──────────────────────────────
    Cleaned = Table.RemoveColumns(DayOfWk, {"_DayIdx"}),
    Result  = Table.ReorderColumns(Cleaned, {
                  "DateKey", "Date",
                  "CalendarYear", "CalendarMonthNumber", "CalendarMonth", "DayOfWeek",
                  "FiscalYear", "FiscalYearLabel", "FiscalYearStartDate",
                  "FiscalWeekNumber", "FiscalPeriodNumber", "FiscalPeriodLabel",
                  "FiscalQuarterNumber", "FiscalQuarter", "FiscalWeekOfPeriod"
              })
in
    if _PatternCheck = null then Result else error "pattern check failed"
