# SPEC-07 — Power BI Reconciliation Boundaries

**Status:** Draft — **specification only, no implementation this cycle**
**Depends on:** `SPEC-01`, `SPEC-03`

---

## 1. Purpose and hard limit

An agent comparing DuckDB results over source files with Power BI results will find differences. **Most differences are correct** — they arise because the two sides are answering different questions.

This spec defines what may legitimately be compared, what makes two result sets comparable, and what a comparison can never prove. It is written now so the boundaries are agreed **before** any tooling is built, not after the first confusing mismatch.

**No implementation is proposed.** `SPEC-01` D1 limits the MVP to docs and setup. This document defines the boundary conditions a future helper must satisfy.

---

## 2. Two routes, both requiring explicit user-supplied artifacts

### Route A — Compare against an explicit export

The user produces a result set from Power BI (CSV/Parquet export, or a documented screenshot of a visual's underlying data), supplies the **query, grain, and filter context**, and the comparison runs DuckDB SQL over the same source snapshot.

- **Requires from the user:** the exported result set, the DAX/measure definition or visual definition, the filter context in effect, the source snapshot identity, and any Power Query transformations applied upstream.
- **Deterministic.** Reproducible and auditable.
- **Preferred** for routine reconciliation.

### Route B — Compare against a live model query

The agent obtains model-side results through **separate existing tooling** — the `powerbi-modeling-mcp` server (`mcp/mcp.json.example`), a connected Power BI Desktop instance, or another DAX-capable path.

- **Requires from the user:** a running/available model (Desktop local instance, or a Fabric workspace plus permissions), RLS identity if roles apply, and successful connection of that MCP server.
- **Gated by access.** Not provided by DuckDB, not guaranteed by this template, and unavailable offline.
- **Bounded results only.** Live query output must respect the same caps as `SPEC-05` §7.

**Neither route is self-sufficient.** DuckDB supplies source-side computation only. The Power BI side is always a user artifact or separately-tooled.

---

## 3. Alignment requirements

A comparison is meaningful only when **all** of the following are established and recorded:

| Dimension | Requirement |
|---|---|
| **Grain** | Identical row granularity. A daily aggregate compared to a monthly aggregate is meaningless. |
| **Filters** | The same filter set — slicers, date range, page/report filters, visual-level filters. Visual filter context is **not** inferable from an export and must be supplied. |
| **Source snapshot** | The same underlying data version. Power Query incremental refresh partitions are a common source of silent drift. |
| **Power Query transformations** | Any upstream transform — type coercion, trimming, splitting, deduplication, currency conversion — must be reproduced or explicitly excluded. |
| **Relationships** | Join direction, cardinality, and cross-filtering behaviour. An inner join in DuckDB may not match a bidirectional model relationship under row context. |
| **Time / fiscal calendar** | Which calendar, which `FiscalYear` / `FiscalWeekNumber` / `FiscalPeriodNumber` semantics, and whether week-based (445/454/544/13period) logic applies. See below. |
| **RLS identity** | If roles apply, which identity produced the Power BI result. |
| **Null vs blank vs 0** | Power BI's BLANK is not SQL `NULL`, and is not `0`. See §4. |
| **Numeric tolerance** | An explicit tolerance for floating-point comparison. Exact equality on floats is the wrong default. |
| **Measures** | Which measure definition was evaluated, and whether it depends on filter context that DuckDB cannot reproduce. |

**Week-based fiscal calendars deserve emphasis.** This template supports `standard`, `445`, `454`, `544`, and `13period` (`config/fiscal-calendar.json`, validated by `scripts/validate_date_table.py`). A naive `DATEPART` or calendar-month grouping in DuckDB will **not** reproduce a 4-4-5 fiscal period. Week-based fiscal logic must be reproduced explicitly against `FiscalYear` / `FiscalWeekNumber` / `FiscalPeriodNumber`, never approximated.

---

## 4. Systematic reasons results legitimately differ

These are **expected**, not defects. A comparison tool must classify them rather than report them as failures.

| Cause | Effect |
|---|---|
| **BLANK ≠ NULL ≠ 0** | An empty Power BI cell is BLANK, which aggregates as ignorable. SQL `NULL` and `0` behave differently in `SUM`, `COUNT`, and `AVERAGE`. |
| **DAX filter context** | Measures evaluate in a filter context determined by the visual and slicers. SQL has no equivalent implicit context. |
| **Relationships** | Model relationships filter in ways an explicit join does not reproduce, particularly bidirectionally and under RLS. |
| **Power Query transforms** | Applied before the model sees the data. Querying the raw file bypasses them entirely. |
| **Date/time semantics** | Fiscal periods, week boundaries, and time-intelligence functions (YTD, rolling, same-period-last-year) are model-side logic. |
| **Type coercion** | Power Query may have typed a text column as a number; the file still holds strings. |
| **Floating point** | Aggregate arithmetic order differs. Tolerance is mandatory, not optional. |
| **Incremental refresh** | Power BI may hold a refresh partition boundary that the source file does not reflect. |

---

## 5. What a comparison may never claim

1. **Matching aggregates prove semantic equivalence.** They prove consistency at one grain under one filter set. Definitions can still differ.
2. **DuckDB validates DAX.** It cannot evaluate DAX.
3. **A mismatch proves the model is wrong.** It may prove the source changed, the export is stale, the grain differs, or the comparison is misaligned.
4. **Silent filter inference.** Visual filter context must be supplied by the user. Guessing it produces confidently wrong comparisons.
5. **Autonomous model modification.** Reconciliation is read-and-report. Fixing the model is a separate, explicitly authorised action under `semantic-model-authoring`.

---

## 6. Future-helper constraints (if ever built)

Any comparison tool must:

- Require **explicit user-supplied provenance** — query, grain, filters, snapshot, calendar — and refuse to proceed without it rather than inferring.
- Take **numeric tolerance as a required parameter**, with no exact-equality default on floats.
- **Classify** differences by the §4 causes where detectable, and label the rest "unexplained — requires investigation" rather than "Power BI is wrong".
- Be **read-only on both sides** and write only to user-designated paths.
- **Bound output** per `SPEC-05` §7.
- Emit a **provenance record** with every comparison: both queries, the tolerance, the grain, the calendar, the filter context, and the source snapshot identity.
- Treat result content as **untrusted data** per `SPEC-05` §6.

---

## 7. Documentation deliverable for the MVP

`SPEC-01` D1 permits docs but not tooling. So the MVP ships **prose only**, in `GETTING_STARTED.md`, stating:

1. The two routes and what each requires from the user.
2. The alignment checklist in §3, as a required input list.
3. The §4 divergence table, so users read differences as expected.
4. The §5 prohibitions.
5. An explicit note that Route B depends on separately available tooling and access, which this template does not provide.

**No comparer, no CLI flag, no script.** If a user asks for automated comparison, the answer in the MVP is the documented manual workflow plus the §3 checklist.

---

## 8. Assumptions

| ID | Assumption | Risk if wrong |
|---|---|---|
| A21 | Users can supply export artifacts and filter context when they want reconciliation. | Medium — this is the workflow's main friction, and the reason automated comparison keeps getting requested. |
| A22 | Live model access (Route B) is genuinely available to a minority of template users. | Medium. It depends on Desktop, Fabric, and permissions outside this repo's control. |
| A23 | The §4 divergence causes cover most real-world mismatches. | Medium — hence the "unexplained" classification requirement in §6. |