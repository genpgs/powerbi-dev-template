# Reference Resources

Agents must consult relevant references before nontrivial DAX, time-intelligence, M, or TMDL work. Record references used in your response.

## DAX

- Function reference: <https://dax.guide/>
- Pattern library: <https://www.daxpatterns.com/patterns/>
- Microsoft DAX docs: <https://learn.microsoft.com/dax/>
- DAX UDF packages (daxlib): <https://github.com/daxlib/daxlib/tree/main/packages>

> ⚠️ Standard time intelligence functions (`TOTALYTD`, `DATESYTD`, `DATESQTD`, etc.) assume calendar months. For week-based fiscal calendars (4-4-5, 13-period) use `FiscalYear` and `FiscalPeriodNumber` / `FiscalWeekNumber` columns directly. Do not use `DATESYTD` with these patterns.

## Power Query M

- M function reference: <https://powerquery.how/>
- Microsoft M docs: <https://learn.microsoft.com/powerquery-m/>
- 4-4-5 calendar pattern reference: <https://gorilla.bi/power-query/445-calendar/>

## PBIP / TMDL

- PBIP overview: <https://learn.microsoft.com/power-bi/developer/projects/projects-overview>
- TMDL overview: <https://learn.microsoft.com/analysis-services/tmdl/tmdl-overview>

## Prefer Microsoft Learn for authoritative support and compatibility information.

When using daxlib: inspect package source, version, license, and dependencies before importing. Import only required functions. Never copy a pattern blindly without understanding it.

If sources conflict, explain the conflict and prefer current Microsoft product documentation.
