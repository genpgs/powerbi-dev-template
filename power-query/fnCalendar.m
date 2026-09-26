// fnCalendar.m
// Month-aligned fiscal calendar for Power BI (Standard workspace, Import mode).
// Supports any fiscal year start month (1-12) and configurable year-label mode.
//
// Usage:
//   fnCalendar(#date(2020,1,1), #date(2026,12,31), 4, "endingYear", "en-US")
//   — generates a calendar from Jan 2020 to Mar 2027, fiscal year starting April,
//     labelled by the year in which the fiscal year ends (FY2021 = Apr 2020–Mar 2021).
//
// Parameters:
//   StartDate           : date  — first date of data range
//   EndDate             : date  — last date of data range
//   FiscalYearStartMonth: number (1-12, optional, default 1)
//   FiscalYearLabelMode : text ("endingYear" | "startingYear", optional, default "endingYear")
//   Culture             : text (optional, default "en-US")

(
    StartDate as nullable date,
    EndDate as nullable date,
    optional FiscalYearStartMonth as nullable number,
    optional FiscalYearLabelMode as nullable text,
    optional Culture as nullable text
) as table =>
let
    // ── Parameter validation ────────────────────────────────────────────────
    FiscalStartMonth  = if FiscalYearStartMonth = null then 1
                        else Number.RoundDown(FiscalYearStartMonth),
    ValidFiscalMonth  = if FiscalStartMonth >= 1 and FiscalStartMonth <= 12
                        then FiscalStartMonth
                        else error "FiscalYearStartMonth must be between 1 and 12.",
    LabelMode         = if FiscalYearLabelMode = null or FiscalYearLabelMode = ""
                        then "endingYear"
                        else FiscalYearLabelMode,
    CalendarCulture   = if Culture = null or Text.Trim(Culture) = ""
                        then "en-US" else Culture,
    CheckedStart      = if StartDate = null
                        then error "StartDate cannot be null." else Date.From(StartDate),
    CheckedEnd        = if EndDate = null
                        then error "EndDate cannot be null." else Date.From(EndDate),
    RangeCheck        = if CheckedEnd < CheckedStart
                        then error "EndDate must be on or after StartDate." else null,

    // ── Date range: expand to full fiscal years ──────────────────────────────
    FYStart = (d as date) as date =>
        if Date.Month(d) >= ValidFiscalMonth
        then #date(Date.Year(d), ValidFiscalMonth, 1)
        else #date(Date.Year(d) - 1, ValidFiscalMonth, 1),
    RangeStart  = FYStart(CheckedStart),
    RangeEnd    = Date.AddDays(Date.AddYears(FYStart(CheckedEnd), 1), -1),
    Dates       = List.Dates(RangeStart, Duration.Days(RangeEnd - RangeStart) + 1, #duration(1,0,0,0)),

    // ── Build table ─────────────────────────────────────────────────────────
    T   = Table.TransformColumnTypes(
              Table.FromList(Dates, Splitter.SplitByNothing(), {"Date"}),
              {{"Date", type date}}),

    // Gregorian columns
    DK  = Table.AddColumn(T,  "DateKey",        each Date.Year([Date])*10000+Date.Month([Date])*100+Date.Day([Date]), Int64.Type),
    Y   = Table.AddColumn(DK, "Year",           each Date.Year([Date]),  Int64.Type),
    MN  = Table.AddColumn(Y,  "MonthNumber",    each Date.Month([Date]), Int64.Type),
    M   = Table.AddColumn(MN, "Month",          each Date.MonthName([Date], CalendarCulture), type text),
    YM  = Table.AddColumn(M,  "YearMonth",      each Date.ToText([Date], "yyyy-MM", CalendarCulture), type text),
    YMS = Table.AddColumn(YM, "YearMonthSort",  each [Year]*100+[MonthNumber], Int64.Type),

    // Fiscal columns
    FYS = Table.AddColumn(YMS, "FiscalYearStartDate", each FYStart([Date]),                             type date),
    FYE = Table.AddColumn(FYS, "FiscalYearEndDate",   each Date.AddDays(Date.AddYears([FiscalYearStartDate],1),-1), type date),
    FYN = Table.AddColumn(FYE, "_FiscalYearEndingYear", each Date.Year([FiscalYearEndDate]),            Int64.Type),
    FY  = Table.AddColumn(FYN, "FiscalYear",
              each if LabelMode = "startingYear"
                   then Date.Year([FiscalYearStartDate])
                   else [_FiscalYearEndingYear], Int64.Type),
    FYL = Table.AddColumn(FY,  "FiscalYearLabel",    each "FY" & Text.From([FiscalYear]),              type text),
    FM  = Table.AddColumn(FYL, "FiscalMonthNumber",  each Number.Mod([MonthNumber]-ValidFiscalMonth,12)+1, Int64.Type),
    FQN = Table.AddColumn(FM,  "FiscalQuarterNumber",each Number.RoundUp([FiscalMonthNumber]/3),       Int64.Type),
    FQ  = Table.AddColumn(FQN, "FiscalQuarter",      each "FQ" & Text.From([FiscalQuarterNumber]),     type text),

    // Remove internal helper column
    Result = if RangeCheck = null
             then Table.RemoveColumns(FQ, {"_FiscalYearEndingYear"})
             else error "Invalid date range."
in
    Result
