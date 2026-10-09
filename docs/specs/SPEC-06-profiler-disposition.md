# SPEC-06 — Disposition of `scripts/inspect_data_source.py`

**Status:** Draft · **Depends on:** `SPEC-01`

---

## 1. Decision

**`scripts/inspect_data_source.py` is unchanged in the MVP** (`SPEC-01` D3). It is documented as the **zero-dependency fallback** for profiling when DuckDB is not installed or not appropriate.

Consolidation behind a DuckDB backend is **deferred** to a future spec, gated on fixture-based parity evidence. The plan document's instruction — "do not simply delete it" — is adopted in full.

---

## 2. Current behaviour (verified by reading the source)

`scripts/inspect_data_source.py`, 225 lines, stdlib + `openpyxl` only.

| Aspect | Current behaviour |
|---|---|
| CLI | Positional `file`, `--markdown`, `--output/-o`, `--samples` (default `1000`) |
| Formats | `.xlsx` / `.xlsm` / `.xltx` via `openpyxl` (L205); `.csv` / `.tsv` / `.txt` via stdlib `csv` (L207) |
| Delimiter | `.tsv` → tab; `.csv` / `.txt` → comma. Selected at the routing layer (§3) |
| Not supported | `.xls`, `.parquet`, `.json` — exits 1 with "Unsupported file format" (L209–211) |
| Output | Console text (L110) or Markdown (L152). **No JSON output mode.** `-o` only writes when `--markdown` is also given (L219) |
| Sampling | First `N` rows per sheet/table; default 1000 (L82, L104) |
| Type inference | `type(v).__name__` over sampled values, joined to a string (L31). Every CSV value is `str`, so CSV types are effectively untyped |
| PK heuristic | `distinct == len(vals)` and no nulls (L35) |
| Key heuristic | Column name contains `key`/`id`/`code`/`number`, or is a candidate PK (L38) |
| Date heuristic | Column name contains `date`/`time`/`day`/`month`/`year`, or inferred type contains `date` (L37) |
| Role heuristic | PK present and `< 100000` rows → `DIMENSION`; ≥2 keys or ≥10,000 rows → `FACT`; else `LOOKUP` (L124–129, duplicated L163–168) |
| Exit codes | 0 success; 1 file not found (L202), missing `openpyxl` (L66), unsupported extension (L211) |
| Tests | `scripts/test_inspect_delimiter.py` (added with the §3 fix, wired into CI). Nothing else — no golden-output coverage of the renderers |
| Dependencies | `openpyxl` only, loaded lazily and degrades with a clear message (L62–66) |

**No dependency manifest exists anywhere in this repository** — no `requirements.txt`, `pyproject.toml`, or lockfile. `openpyxl` is an undeclared runtime dependency of this script today.

---

## 3. Observed defect — `.tsv` is advertised but not parsed

**This is a pre-existing bug, found while reading the source for this spec. It is not introduced by the DuckDB work.**

- L206 accepts `.tsv` and routes it to `inspect_csv`.
- L98 constructs `csv.reader(f)` with the **default comma delimiter**.
- L210 advertises `.tsv` in the error message.

A tab-separated file is therefore parsed with a comma delimiter, yielding **one column per row instead of one column per field**. Column names, null percentages, uniqueness, and every downstream key/date/role heuristic are wrong for `.tsv` input.

**Disposition: FIXED — shipped first, in its own PR** (`SPEC-01` D9; Q3 resolved 2026-10-07).

Rationale for sequencing it first rather than last: it is a small, self-contained correctness fix that is completely independent of the DuckDB work, and `SPEC-02` §2 lists TSV as a **Tier 1** source. Shipping it first means the documented TSV story is correct from the outset.

**The fix:**
- `inspect_csv` gained a `delimiter` parameter defaulting to `","`.
- The `main` routing layer selects `"\t"` for `.tsv` and `","` otherwise. `.txt` deliberately stays comma-delimited — the script has never sniffed, and this fix does not introduce sniffing.

**The regression test:** `scripts/test_inspect_delimiter.py`, following the standalone-runner convention of `scripts/test_pbir_discovery.py`. It asserts, for `.csv` / `.tsv` / `.txt`, that a known fixture yields the expected column names, the expected column count, and zero nulls. Wired into `.github/workflows/validate.yml`.

**Verified before/after** on a three-column fixture:
- Before: `Columns: 1`, single column named `order_id\tregion\tamount`.
- After: `Columns: 3`, each column with correct name, 0% nulls, 100% unique.

**Still deferred:** everything in §5. Consolidation behind a DuckDB backend remains out of scope; this fix only removes a defect from the existing script's own advertised behaviour.

---

## 4. Why it is not consolidated now

| Reason | Detail |
|---|---|
| **No parity evidence** | Any replacement must reproduce this output on fixtures. No fixtures exist (see §5). Building them is the actual cost of consolidation. |
| **No tests to break** | The script has zero tests, so "no regression" is unverifiable today. A rewrite would remove the only artifact users depend on with no safety net. |
| **Different strengths** | The script needs no DuckDB and no network. DuckDB needs an extension download for Excel. For a quick CSV glance, stdlib is genuinely sufficient. |
| **The fallback has value** | Offline environments, users who decline the optional install, and CI (which will not install DuckDB per `SPEC-01` D6) all still need this script. |
| **Scope discipline** | `SPEC-01` D1 limits the MVP to docs and setup. A rewrite is a different programme. |

---

## 5. Prerequisites for any future consolidation

1. **Purpose-built fixtures** under a committed test path — the repo has none today (only `samples/pbip-calendar-baseline/` and `samples/pbip-visual-gallery/`, which serve the validators, not this script).
2. **A golden-output test** capturing current behaviour, including console and Markdown renderings.
3. **A `--format json` output mode**, so downstream comparison does not scrape rendered text. This is the single most valuable preparatory change and is deliberately **not** in the MVP.
4. **Heuristic labelling.** Role and key suggestions stay explicitly labelled as heuristics in any output, per `SPEC-01` §6.5.
5. **Sampling honesty.** Statistics computed over 1,000 rows must never be presented as exact. This applies to both implementations.
6. **Exit-code and message parity**, or a documented breaking change.

---

## 6. Documentation requirements

1. Present the script as the **default, zero-dependency** profiling path — not as deprecated.
2. Note the formats it does and does not handle (`.xls`, `.parquet`, `.json` unsupported).
3. Note that CSV type inference is effectively untyped because all values arrive as strings.
4. State the 1,000-row default sampling and that statistics are sample-based.
5. State that key and role suggestions are heuristics.
6. Give the DuckDB path as the option for Parquet/JSON/`.xlsx` and for full-file rather than sampled statistics — per `SPEC-02`.
7. `.tsv` support is now genuine (§3) and may be advertised.
8. Note the undeclared `openpyxl` dependency for Excel profiling.

---

## 7. Assumptions

| ID | Assumption | Risk if wrong |
|---|---|---|
| A18 | Existing users rely on this script's output shape. | Low — but it is the reason the golden-output test is a prerequisite. |
| A19 | The sampling heuristics are adequate for first-pass profiling in most cases. | Medium. Documented as sample-based under `SPEC-01` §6.5. |
| A20 | ~~The `.tsv` defect has not caused downstream harm.~~ | **Resolved:** the defect is fixed (§3) and the fix is covered by a regression test. Any output already generated from `.tsv` input should be regenerated. |