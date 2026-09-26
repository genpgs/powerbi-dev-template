// fnFiscalCalendarConfig.m
// Configuration template for fiscal calendar parameters.
// Paste your config/fiscal-calendar.json values here.
// Return a record that calling queries can destructure.
//
// Usage in a Calendar partition:
//   let
//       cfg      = fnFiscalCalendarConfig(),
//       Calendar = fnCalendarWeekBased(cfg[FiscalStartDate], cfg[NumberOfYears],
//                                      cfg[Pattern], cfg[WeekStartDay], cfg[Culture])
//   in Calendar

() as record =>
let
    // ── Edit these values to match config/fiscal-calendar.json ───────────────
    Pattern         = "445",              // 445 | 454 | 544 | 13period | standard
    FiscalStartDate = #date(2025, 2, 1),  // nominal fiscal year 1 start date
    WeekStartDay    = "Saturday",         // Saturday | Sunday | Monday
    NumberOfYears   = 5,                  // how many fiscal years to generate
    // For standard (month-aligned) calendar only:
    FiscalStartMonth = 2,                 // 1=Jan, 2=Feb, … 4=Apr, etc.
    FiscalYearLabelMode = "endingYear",   // endingYear | startingYear
    Culture         = "en-US"
in
    [
        Pattern             = Pattern,
        FiscalStartDate     = FiscalStartDate,
        WeekStartDay        = WeekStartDay,
        NumberOfYears       = NumberOfYears,
        FiscalStartMonth    = FiscalStartMonth,
        FiscalYearLabelMode = FiscalYearLabelMode,
        Culture             = Culture
    ]
