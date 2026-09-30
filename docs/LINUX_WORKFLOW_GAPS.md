# Power BI Template — Workflow Gaps Register

> **This is a living register, not a pull-request log.** Every row is a gap that was hit in
> real use, with its current status. When a gap is fixed, the row stays and the status
> changes — do not delete rows. New gaps get the next `GAP-nn` number and are added here.
>
> Gaps 01–06 were found while building the template's Linux support. Gaps 07–12 were found
> later, while building a downstream project (`PBI-Adventureworks`) on top of this template —
> they are the reason `scripts/validate_m_expressions.py` exists. Gaps 13–18 were found in the
> same project, restyling the PBIR report to match a design prototype, and are the reason
> `scripts/validate_report.py` exists.

**Scope of the original exercise**: a headless Linux environment (Ubuntu x86_64, Python 3.13,
Node.js 20) authoring a full PBIP project — 6 TMDL tables, 11 DAX measures, 5 relationships,
11 PBIR visuals across 2 pages — with no Power BI Desktop available.

**Second exercise (gaps 13–18)**: the same headless environment restyling that project's report
to match an HTML design prototype — custom theme, 5 KPI cards, 2 added visuals, 2 pages
re-flowed to a 1280×720 canvas. No Power BI Desktop available, which is what made gaps 15, 17,
and 18 visible in the first place.

---

## 1. Register

| Gap ID | Component | Severity | Description | Status |
|---|---|---|---|---|
| **GAP-01** | `powerbi-modeling-mcp` | Blocker | MCP server blocks all execution until a human accepts the EULA. In headless agent runs this fails immediately. | **Fixed** — `PBI_MODELING_MCP_ACCEPT_EULA: "true"` in `mcp/mcp.json.example`; §8 of `GETTING_STARTED.md` documents it. |
| **GAP-02** | `setup.sh` / `pbir-cli` | Critical | `pbir-cli` ships wheels for Windows AMD64 and macOS ARM64 only — no Linux wheel, no sdist. `setup.sh` fails on Linux. | **Fixed** — `setup.sh` guards on `uname -s`; `scripts/validate_pbir_schema.py` is the cross-platform fallback, wired into `validate_pbir.sh` and CI. |
| **GAP-03** | Baseline TMDL sample | Critical | Root-level `//` comments in `expressions.tmdl` are invalid TMDL; parsers reject with `InvalidLineType: Unexpected line type: Other!`. | **Fixed** — top-level comments removed; `///` descriptions used instead. |
| **GAP-04** | `scripts/validate_repo.py` | Medium | `validate_repo.py` failed if `.env` *existed on disk*, contradicting `setup.sh` which creates it from `.env.example`. | **Fixed** — the check now tests git tracking (`git ls-files`), not filesystem presence. |
| **GAP-05** | Validation scope | Medium | `validate_date_table.py` hardcoded `samples/pbip-calendar-baseline/` instead of validating whatever model you are working on. | **Fixed** — now scans every `*.SemanticModel` with a `Calendar` table; accepts an explicit `.pbip` / model path argument. |
| **GAP-06** | Headless lifecycle | Architecture | Linux cannot run the Desktop GUI or refresh local M partitions into VertiPaq. | **Documented** — Linux is the code-first authoring / scripting / CI plane; Desktop or Fabric is the refresh and rendering plane. |
| **GAP-07** | M bodies in `expressions.tmdl` | Critical | TMDL stores `expression` bodies as opaque strings, so invalid M passes TMDL import *and* every schema validator, then blocks the project in Desktop. | **Fixed** — `scripts/validate_m_expressions.py` added and wired into pre-commit, CI, and all agent instruction files. |
| **GAP-08** | `File.Contents` in partitions | Critical | `File.Contents("data/X.xlsx")` resolves against the M engine's working directory, not the PBIP root, so refresh fails wherever the project lives. | **Fixed** — use a `BasePath` parameter and concatenate; enforced by `validate_m_expressions.py`. |
| **GAP-09** | Hand-authored PBIP JSON | Medium | Desktop silently drops unrecognised properties (e.g. `layoutOptimization`) on save, so a generator cannot assume its output survives a round-trip. | **Fixed** — generator and sample emit Desktop-canonical JSON; `validate_pbir_schema.py` enforces the shape. |
| **GAP-10** | Missing `.platform` / `$schema` in PBIR JSON | Critical | A hand-built `.Report` folder opens in Desktop but is rejected by the Fabric tooling, and `$schema`-less definition JSON cannot be schema-validated at all. | **Fixed** — `.platform` added to the sample and emitted by `scaffold_pbir.py`; `validate_pbir_schema.py` enforces `.platform` and every `$schema` key. |
| **GAP-11** | `<Name>.pbip` manifest | Critical | A `semanticModel` entry in `artifacts` makes Desktop refuse to open the project outright — a hard stop, unlike the other gaps. Unvalidated because `validate_repo.py` only checked that the `.Report` / `.SemanticModel` folders *existed*, never parsing the manifest. | **Fixed** — `validate_repo.py` §5 parses every `.pbip` and enforces the `ArtifactShortcutContainer` schema; `scaffold_pbir.py` emits a valid manifest. |
| **GAP-12** | M bodies / `.m` reference files | Critical | DAX/Excel names used as M module members (`Number.Max`, `Number.Min`, `Text.Len`, …). The member does not exist, so the body imports cleanly and only fails on refresh: `The import Number.Max matches no module reference`. | **Fixed** — `validate_m_expressions.py` scans expressions, tables, and loose `*.m` files against a denylist of members confirmed absent from the official M reference. |
| **GAP-13** | npm global install | Critical | `npm install -g` fails with `EACCES` on any non-root Linux account, because npm's default prefix is `/usr/local` and `/usr/local/lib/node_modules` does not exist. This blocks installing `powerbi-report-author`, the only tool that can author PBIR correctly. | **Fixed** — install with `npm install -g --prefix "$HOME/.local"`; documented in §8. |
| **GAP-14** | PBIR canvas layout | Critical | Visual overlap, negative positions, and out-of-bounds placement pass every schema and shape validator. A report can be fully valid JSON, correct against the PBIR schema, and still render unusably. | **Fixed** — `scripts/validate_report.py` added, wired into pre-commit and CI (§15). |
| **GAP-15** | Validator offline behaviour | High | When the PBIR JSON schemas cannot be fetched, the validator reports `succeededWithWarnings` and **skips schema validation entirely** for the affected files. The result reads like success. | **Fixed** — `validate_pbir.sh` now captures tool output and exits non-zero if `PBIR_SCHEMA_UNREACHABLE` appears, even when the tool itself exited 0; the warning names every skipped file (§10). |
| **GAP-16** | PBIR + theme property names | High | Formatting property names and value encodings cannot be guessed. Theme JSON uses plain values, PBIR uses `expr` wrappers, and several names differ from the intuitive guess (`fontColor` is `labelColor`, `lineCapStyle` is `lineStyle`, sort `direction` is `Ascending` not `Asc`). | **Workaround** — always look the value up via `powerbi-report-author formatting describe-object` / `catalog describe` before writing JSON; see §11. |
| **GAP-17** | `cardVisual` clipping | High | Nothing validates that a card is tall enough for its content. The callout value and label can be clipped at render time while the visual passes every validator. | **Partially automated** — `validate_report.py` now computes minimum card height from explicitly-set font sizes, padding, border, and accent bar, and warns when `position.height` is too small (§12). Theme-inherited values are not visible at static analysis time, so a green check is necessary but not sufficient. |
| **GAP-18** | Rendered-output verification | Architecture | The authoring loop requires a reload + screenshot to confirm a change rendered correctly, but `powerbi-desktop` needs Power BI Desktop, which is Windows-only. On Linux the loop cannot complete. | **Open** — extends GAP-06. Validate on Linux, then confirm visually on a Windows machine before merging (§13). |

---

## 2. GAP-07 — invalid M in `expressions.tmdl` passes every structural validator

**Symptom.** The project imports cleanly through the TMDL folder importer and through
`validate_repo.py`, `validate_date_table.py` and `validate_pbir_schema.py`, but Desktop
refuses to open it:

```
Syntax error in expression 'fnCalendar'. Token Identifier expected.
Microsoft.Mashup.Host.Document
```

**Root cause.** A TMDL `expression <name> =` block stores its M body as an **opaque literal
string**. The TMDL parser never compiles the M, so a syntactically invalid body is invisible
to TMDL-level tooling. The Mashup host is the first component that actually parses it, and
that only happens when Desktop opens the project.

The concrete defect was a trailing `;` on the `in` expression. M has no `;` statement
terminator, so the parser treated it as the start of a new expression and demanded a token
identifier at the next position. The reported start position is the line *after* the
offending line, which is why the error appears to point at innocent whitespace.

**Detection subtlety worth knowing.** The obvious check — "does a line both start with `in`
and end with `;`?" — does **not** catch this, because `in` and the terminator are usually on
*separate* lines:

```m
let
    // ...
in
    Result;      // <- the semicolon is on the line AFTER `in`
```

`validate_m_expressions.py` therefore checks the **last meaningful line** of the body rather
than scanning for `in ` … `;` on one line, and blanks out string-literal contents first so a
`;` inside a string literal is not a false positive.

**Rule of thumb.** If Desktop reports an M syntax error but the TMDL import succeeds, the
defect is inside the M body — not in the TMDL structure. Diff the expression against a
Desktop-generated reference rather than re-checking TMDL indentation.

---

## 3. GAP-08 — `File.Contents` relative paths do not resolve against the PBIP root

**Symptom.** A partition authored as:

```m
Source = Excel.Workbook(File.Contents("data/AdventureWorks Sales.xlsx"), null, true)
```

opens in Desktop but fails on refresh, because the import path effectively started at
`data/` rather than at the project root.

**Root cause.** `File.Contents` resolves a relative path against the **M engine's current
working directory**, not against the `.pbip` root. In Desktop that directory is managed
internally, so a path that looks project-relative is not.

**Fix.** Declare a Power Query **parameter** holding the folder path and concatenate. In
TMDL this is a named expression in `expressions.tmdl`:

```tmdl
expression BasePath = "E:\01-Projects\MyProject\" meta [IsParameterQuery=true, Type="Any"]
    lineageTag: f4622c3a-d94b-4a8f-b485-aba488849cac
```

and each partition reads:

```m
Source = Excel.Workbook(File.Contents(BasePath & "data/AdventureWorks Sales.xlsx"), null, true)
```

**Portable variant.** The `IsParameterQuery=true` marker is what makes Desktop show `BasePath`
as an editable parameter in the Queries pane, so the value can be repointed per machine
without editing TMDL. For a repo meant to be cloned across machines, author the parameter
with an empty or placeholder value and let each developer set it once — a hardcoded absolute
path will not survive a move, and it is a non-issue for the Linux-authors /
Windows-refreshes split (GAP-06) as long as the refresh machine sets it.

**Note.** `Calendar.tmdl` needs no `BasePath`; its partition is generated by
`fnCalendarWeekBased` and reads no file.

**Enforcement.** `validate_m_expressions.py` scans every partition's `source =` block and fails
on a bare relative `File.Contents` literal. It matches only a string literal in
first-argument position, so the correct `File.Contents(BasePath & "data/x.xlsx")` form needs
no exemption. Absolute paths and occurrences inside `//` comments are ignored.

---

## 4. GAP-09 — Desktop silently normalises and drops unrecognised JSON properties

**Symptom.** A hand-authored `report.json` opens fine, but after one open-and-save a property
is simply gone. A root-level `"layoutOptimization": "Canvas"` was **removed** on save, and
Desktop wrote out `"settings"` in its place.

**Root cause.** Desktop rewrites PBIR definition files to its own canonical form on save.
Properties it does not recognise for the current schema version are discarded without warning,
and defaults it considers implicit are written out explicitly.

**Convention: treat a Desktop-saved project as canonical.** When a generator emits PBIR,
emit the properties Desktop itself would emit, and verify by round-tripping once through
Desktop. Do not hand-add speculative root-level properties — a property Desktop drops was
never being honoured anyway.

**Expected Desktop writes, not defects.** Desktop also bumps schema versions it owns
(`visualContainer` `2.9.0` → `2.12.0`, `pagesMetadata` `1.0.0` → `1.1.0`), pins
`activePageName` to the page last viewed, and adds partition annotations
(`PBI_NavigationStepName`, `PBI_ResultType = Table`).

---

## 5. GAP-10 — a hand-built `.Report` folder is missing `.platform` and `$schema`

**Symptom.** A PBIP project assembled by hand or by an agent opens in Power BI Desktop without
complaint, but the Fabric tooling rejects it, reporting three errors:

```
PBIR_PLATFORM_MISSING      Missing: <report>/.platform
PBIR_JSON_FILE_NO_SCHEMA   pages.json has no "$schema" and cannot be schema-validated
                           page.json  has no "$schema" and cannot be schema-validated
```

and after those are fixed, a fourth:

```
PBIR_SCHEMA_VALIDATION_ERROR   / must have required property 'displayOption'
```

**Root cause.** There are two different notions of "valid" here, and only the looser one
applies while authoring. Power BI Desktop is tolerant: it will open a `.Report` folder that
lacks `.platform`, and it will open definition JSON with no `$schema` key. The Fabric
toolchain is **not** tolerant — `.platform` is the file that identifies an item folder to the
git-integration layer, and `$schema` is what makes a definition file schema-validatable at
all. So a project can be "working in Desktop" and simultaneously not deployable.

`displayOption` is a third case: it is required by the `page/2.1.0` schema, but Desktop
supplies a default and never complains about its absence.

**Convention: build to the strict reading, then relax.** Treat the Fabric-toolchain rules as
the specification and Desktop's tolerance as a debugging hazard — a file that Desktop accepts
is not evidence that the file is correct. This is the same conclusion as GAP-09, reached from
the opposite direction: GAP-09 says *do not* hand-add properties Desktop does not recognise,
GAP-10 says *do* include the ones the schema requires even when Desktop will not ask.

**Why `.platform` needs a stable `logicalId`.** The `config.logicalId` is the item's identity
across renames and moves; it is not decorative. Generate it once with `uuid.uuid4()` and
leave it alone afterwards. Desktop rewrites `.platform` metadata on rename, but the
`logicalId` is preserved.

---

## 6. GAP-11 — a `semanticModel` entry in the `.pbip` manifest blocks the project from opening

**Symptom.** Double-clicking the `.pbip` fails immediately. Desktop reports:

```
Property 'semanticModel' has not been defined and the schema does not allow
additional properties.  Path 'artifacts[1].semanticModel'

Required properties are missing from object: report.  Path 'artifacts[1]'
```

**Root cause.** The PBIP 1.0.0 schema types the manifest as `ArtifactShortcutContainer`, which
sets `additionalProperties: false` and declares exactly one property, `report`, as required.
A `semanticModel` sibling is therefore not merely unknown — it is prohibited. This is the
only gap in this register whose symptom is a **hard failure to open**, with no tolerance
from any tool. The manifest that a well-meaning agent produces (`{"report": ...},
{"semanticModel": ...}`) mirrors the *thin* report-plus-model shape, but the schema has
never accepted it.

The `semanticModel` entry is also unnecessary. The report reaches the model through
`definition.pbir` → `datasetReference.byPath`, so the folder layout already links them. The
`artifacts` array describes what the shortcut *launches*, and that is the report.

**Why this shipped undetected.** `validate_repo.py` §5 checked that `<Name>.SemanticModel/` and
`<Name>.Report/` existed, and that four files inside them were present. It never opened the
`.pbip`. Folder structure is necessary but not sufficient — and here the folders were perfect
while the manifest that indexes them was invalid. The fix parses every `*.pbip` and enforces
`$schema`, `version == "1.0"`, a non-empty `artifacts` array, the per-artifact
`additionalProperties` restriction, and that `report.path` resolves to a real folder.

**Desktop-canonical manifest:**

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
  "version": "1.0",
  "artifacts": [ { "report": { "path": "MyReport.Report" } } ],
  "settings": { "enableAutoRecovery": true }
}
```

A fresh downstream copy of this template can drift out of sync with the template's sample,
so validate a *copied* project, not just the template: the failure is a property of the file
in front of you, not of the repo it came from.

---

## 7. GAP-12 — DAX/Excel function names used as M module members

**Symptom.** The project opens, and the report renders. On refresh one query is blocked:

```
Load
1 query is blocked by the following error:
A Calendar
The import Number.Max matches no module reference.
```

Desktop stops at the *first* bad expression, so a file with three defects reports one. Fix
the one shown and reopen — the next appears.

**Root cause.** `MAX()` and `MIN()` are DAX and Excel function calls. In M they are *module
members*, and the `Number` module has no `Max` and no `Min`. Confirmed against the official
reference: the `Number` module is `IsEven`/`IsNaN`/`IsOdd`, the `*From`/`ToText`
conversions, the rounding family, `Abs`/`Mod`/`Power`/`Sign`/`Sqrt`, `Random`, the
trigonometric functions, and the bitwise functions. Aggregation lives in `List`:

| Written | Correct in M |
|---|---|
| `Number.Max(a, b)` | `List.Max({a, b})` |
| `Number.Min(a, b)` | `List.Min({a, b})` |
| `Number.Sum(list)` | `List.Sum(list)` |
| `Number.Average(list)` | `List.Average(list)` |
| `Number.Count(list)` | `List.Count(list)` |
| `Text.Len(x)` | `Text.Length(x)` |
| `Text.Left(x, n)` / `Text.Right(x, n)` | `Text.Start(x, n)` / `Text.End(x, n)` |
| `Text.Concat(list, sep)` | `Text.Combine(list, sep)` |
| `Number.IsBlank(x)` | `x = null` |
| `Number.Floor(x)` / `Number.Ceiling(x)` | `Number.RoundDown(x)` / `Number.RoundUp(x)` |

`List.Max` is a single-argument aggregate over a list, so a two-argument clamp becomes a
two-element list literal: `Number.Max(YearsBack - 1, 0)` → `List.Max({YearsBack - 1, 0})`.
The braces are not optional decoration — `List.Max(a, b)` is a syntax error, and it fails
*later* than the original bug, after a refresh has already been scheduled.

**Why this shipped undetected.** This is the same blind spot as GAP-07, one level deeper. GAP-07
is M that cannot be *parsed*; GAP-12 is M that parses perfectly and cannot be *resolved*.
A TMDL `expression` body is an opaque string to the TMDL parser, an opaque string to the
JSON schema, and an opaque string to `validate_pbir_schema.py` and `validate_date_table.py`.
Rejecting it requires resolving a symbol against the M standard library — i.e. actually
evaluating the expression. That is exactly what a headless CI box cannot do, which is why
the same defect reaches a Windows developer who *can* refresh.

So this class cannot be fully closed by the validator. `validate_m_expressions.py` carries a
curated denylist of members confirmed absent from the Microsoft Learn reference, which
catches the common cases at review time, but it is a denylist and cannot be exhaustive.
**A refresh is still the only complete check** — treat a green M validator as necessary, not
sufficient.

**Scope.** The check covers `expressions.tmdl` bodies, every `tables/*.tmdl` partition, and
the standalone `power-query/*.m` reference files, because the TMDL bodies are generated from
those and the defect otherwise gets copied between them. Fixing only the file Desktop
complains about leaves the reference copy broken for the next generation.

## 8. GAP-13 — `npm install -g` fails on a non-root Linux account

**Symptom.** Installing the PBIR authoring CLI fails immediately:

```
npm ERR! permissions of the file and its containing directories, or try running
npm ERR! the command again as root/Administrator.
```

and the binary is absent afterwards:

```
powerbi-report-author: command not found
```

**Root cause.** npm's default global prefix is `/usr/local`, so a global install writes to
`/usr/local/lib/node_modules`. On a stock image that directory does not even exist, and a
non-root user cannot create it. `sudo npm install -g` appears to work and is the wrong fix: it
installs a root-owned binary that later self-update attempts cannot replace, so the tool breaks
again on the first update.

**Fix.** Install into a user-owned prefix and make sure it is on `PATH`:

```bash
npm install -g --prefix "$HOME/.local" @microsoft/powerbi-report-authoring-cli@latest
export PATH="$HOME/.local/bin:$PATH"
powerbi-report-author --version
```

The same applies to any other global npm package on Linux. Note that GAP-02's `pbir-cli` guard
in `setup.sh` is a *different* problem — that is a missing Linux wheel, not a permissions
problem, and the `uname -s` guard does not help here.

---

## 9. GAP-14 — canvas layout defects pass every validator

**Symptom.** Two visuals sit on top of each other and the page is unusable, but every check is
green:

```
powerbi-report-author validate AdventureWorksSales.Report
  result=succeededWithWarnings errors=0 warnings=1
  PBIR_LAYOUT_NEGATIVE_X: 0
```

The overlap was real: a channel chart at `x=536, width=300` (right edge 836) and a newly added
column chart at `x=852` — the numbers look fine in isolation and only collide once you add them
together. Neither file had a syntax error, an unknown property, or a schema violation.

**Root cause.** PBIR validation is *declarative*: it checks each `visual.json` against a schema
for that file's type, and confirms that referenced columns and measures exist. Layout is a
*relational* property of the page — a statement about the interaction between files that no
per-file schema can express. `position` is four numbers, each individually in range, while the
pair is contradictory.

This is the same structural blind spot as GAP-09 and GAP-12 one level up: those are properties
Desktop normalises away and that M cannot resolve, and this is a property no single file owns.
It is also the failure mode most likely to be produced here, because an agent or generator
positions visuals from arithmetic and cannot see the result.

**Why it is worse here than for a human author.** A person dragging a visual sees it land on top
of another one immediately. A script does not, and neither does an LLM writing `position` blocks.
So the class of defect that is *easiest* for a human to catch is the one a code-first workflow
produces most often.

**Fix.** `scripts/validate_report.py` reads every `position` block per page and reports:

| Check | Catches |
|---|---|
| Negative `x` or `y` | Off-canvas placement, including the `PBIR_LAYOUT_NEGATIVE_X` case the CLI flags |
| Right/bottom edge past the page `width`/`height` | A visual pushed off the right or bottom of the canvas |
| Pairwise overlap | Two visuals occupying the same rectangle |

Overlap is only reported when the two visuals carry the **same** `z` value (or both default to 0),
so deliberate stacking across different `z` layers (a shape behind a label) is not flagged as an error.

**What it still cannot catch.** It is a geometry check, not a rendering check. It cannot see
text that overflows its container, a chart whose plot area collapses to nothing, or two visuals
that are technically adjacent but visually cramped. Those need a screenshot — which is GAP-18,
and the reason this gap cannot be closed completely on Linux.

---

## 10. GAP-15 — the validator reports success while skipping schema validation

**Symptom.** A validation run comes back green on a report that contains schema violations:

```
result=succeededWithWarnings errors=0 warnings=1
  PBIR_SCHEMA_UNREACHABLE: 1
```

The single warning is not cosmetic. The underlying message is:

```
JSON Schema ".../visualContainer/2.12.0/schema.json" could not be fetched;
schema validation skipped for: .../catbar.../visual.json, .../chan.../visual.json,
.../slicer.../visual.json, .../trend.../visual.json, .../subcat.../visual.json
```

**Root cause.** The validator fetches the published schemas over HTTPS. On a sandboxed or
offline agent box the fetch fails, and rather than fail closed it falls back to the checks it can
perform locally. That is the right trade-off for a CI gate — a network outage should not block
commits — but it means `errors=0` no longer implies "schema-valid". Five files were validated
only for structure in the run that surfaced this gap.

**Fix.** Read `warnings=1` with `PBIR_SCHEMA_UNREACHABLE` as a **validation gap**, not a pass.
The warning names every skipped file, so the exposure is bounded and knowable. Re-run the
validator on a networked machine before treating the result as complete.

**Worth knowing.** This is the one case in this register where a green result is weaker than it
looks, and it is easy to miss because the summary line leads with `errors=0`.

---

## 11. GAP-16 — PBIR and theme property names cannot be guessed

**Symptom.** Formatting written from a reasonable guess is rejected, one property at a time:

```
Unknown theme property "legend.fontColor" for "lineChart"
Unknown property "customizeSpacing" in formatting object "spacing" for cardVisual
Unknown property "orientation" in formatting object "general" for barChart
```

and, in PBIR rather than theme:

```
/visual/query/sortDefinition/sort/0/direction must be equal to constant:   (wrote "Asc")
```

**Root cause.** Three separate traps compound here. Property names are not always the obvious
spelling — `fontColor` on an axis or legend is `labelColor`, `lineCapStyle` is `lineStyle`, and
`cardVisual`'s `border` (a visual-container object) has no `radius` at theme level. Encodings
differ by file: a theme writes plain JSON (`"show": true`, `"fontSize": 12`, `"#2563EB"`) while
a `visual.json` wraps every value in `{"expr": {"Literal": {"Value": "..."}}}`, and the literal
needs a type suffix — `20D`, `0L`, `'solid'`. And a property may simply not exist on the object
you are targeting, because `spacing` on `cardVisual` is a *visual-container* object and belongs
under `visualContainerObjects`, not `objects`.

**Fix.** Never write PBIR formatting from memory. Look it up first:

```bash
powerbi-report-author formatting list-objects <visualType>
powerbi-report-author formatting describe-object <visualType> <object>
powerbi-report-author formatting search <visualType> "<regex>"     # when the object is unknown
powerbi-report-author catalog describe <visualType>               # data roles
```

Then validate after each logical batch rather than at the end, so one bad guess does not cascade
into a rewrite of the whole file. Every one of the four errors above was caught in a single
validation cycle; none required guessing twice.

**Note the asymmetry.** This gap is only painful because the CLI exists (GAP-13). Without it the
only options are copying from a reference file or guessing — and guessing is what produced all
four errors.

---

## 12. GAP-17 — nothing validates that a card is tall enough for its content

**Symptom.** A `cardVisual` validates cleanly and renders with its callout value or label
clipped. No error, no warning, no obvious cause.

**Root cause.** Card height is a function of a cascade of eight values — VCO border width, VCO
padding, the title, two independent content-padding objects, the value font size, the vertical
spacing, and the label font size — and no validator in the toolchain evaluates that sum against
`position.height`. Worse, the label **always renders** even when `label.show: false`, so it must
be budgeted at ≥ 12pt regardless of what you set.

Worse still on this report specifically: the Fluent2 base theme in
`StaticResources/SharedResources/BaseThemes/` carries no `cardVisual` entry and no `textClasses`
at all, so there are no authoritative defaults to read and the runtime defaults are the only
source. A green validator says nothing about whether the result is legible.

**Fix.** Compute the requirement before sizing the card:

```
required_height = border*2 + padding_top + padding_bottom
                + (render(title_fs) + spaceBelowTitleArea) * title_visible
                + content_padding_top + content_padding_bottom
                + render(value_fs) + verticalSpacing + render(max(label_fs, 12))
                + accentBar_width
  where render(fs) = ceil(fs * 1.5)
```

Worked example for the five KPI cards on this report (value 20pt, label 9pt→12pt effective,
`paddingUniform` 8, VCO padding 6, `verticalSpacing` 2, accent bar 4, border 1, no title):

```
1*2 + 6+6 + 0 + 8+8 + ceil(20*1.5) + 2 + ceil(12*1.5) + 4 = 78  <=  95   OK
```

Set the padding and spacing values **explicitly** rather than inheriting them, so the arithmetic
above is actually knowable. A `required_height` that exceeds `position.height` means the value
clips; the fix is a smaller font or a taller card, never a shorter one.

---

## 13. GAP-18 — the authoring loop cannot be completed on Linux

**Symptom.** The documented authoring loop is edit → validate → reload → screenshot, and the
instructions are explicit that a change is not done until the screenshot has been reviewed. On
Linux the loop stops after validate:

```
powerbi-desktop: command not found
```

**Root cause.** `powerbi-desktop` is a bridge to a running Power BI Desktop instance, and Desktop
does not run on Linux. This is GAP-06 — headless lifecycle — applied to *verification* rather
than to *refresh*. GAP-06's documented position is that Linux is the code-first authoring plane
and Desktop is the rendering plane; the consequence for report work is that the plane boundary
falls in the middle of the loop, and the half that cannot run is the half that would catch a
clipping or overlap defect.

**Why it matters more than it looks.** Gaps 14, 16, and 17 are all defects that *render* wrong
while validating *clean*. Layout overlap is now automated (GAP-14), and property-name guessing is
now avoidable (GAP-16), but clipping (GAP-17) and any purely aesthetic mismatch are exactly the
class that only a screenshot catches. A green validator on Linux narrows the risk; it does not
close it.

**Status and the honest position.** Open, and it cannot be closed on Linux. The workable
sequence is:

1. Edit and validate on Linux — `powerbi-report-author validate` plus `validate_report.py`.
2. Open the `.pbip` in Power BI Desktop on a Windows machine and screenshot the affected page.
3. Only then merge.

Report work should be described as **validate-clean, visually unverified** until step 2 happens.
Claiming a report is finished on the strength of validation alone is the mistake this gap
rewards.

---

## 14. Desktop alignment reference (verified)

Derived by opening a project in Power BI Desktop and diffing against a Desktop-authored
reference project. The shipped sample `samples/pbip-calendar-baseline/` and the output of
`scripts/scaffold_pbir.py` both follow this table.

| File | Desktop-canonical form | Note |
|---|---|---|
| `<Name>.pbip` | `$schema` `.../fabric/pbip/pbipProperties/1.0.0/...` + `version: "1.0"` + `artifacts` (report only) + `settings.enableAutoRecovery: true` | Desktop **removes** the `semanticModel` artifact — `definition.pbir` already points at the model via `byPath`. A `semanticModel` entry blocks the project from opening (GAP-11). |
| `definition.pbir` | `$schema` `.../fabric/item/report/definitionProperties/2.0.0/...` + `version: "4.0"` + `datasetReference.byPath` | |
| `definition/version.json` | `$schema` `.../fabric/item/report/definition/versionMetadata/1.0.0/...` + `version: "2.0.0"` | Both keys are required for the canonical form. |
| `definition/report.json` | `report/3.3.0` + `themeCollection` (object with `baseTheme`) + `resourcePackages` (**flat** list) + `settings`; **no** `layoutOptimization` | `resourcePackages` is a flat `{name, type, items[]}` list. The wrapped `{"resourcePackage": {...}}` form is *not* canonical. |
| `definition.pbism` | `$schema` `.../fabric/item/semanticModel/definitionProperties/1.0.0/...` + `version: "4.2"` + `settings: {}` | |
| `<Item>.platform` | `gitIntegration/platformProperties/2.0.0` + `metadata.type` (`Report` / `SemanticModel`) + `metadata.displayName` + `config.version "2.0"` + `config.logicalId` (stable UUID) | **One per item folder**, i.e. both `.Report` and `.SemanticModel`. Absent → `PBIR_PLATFORM_MISSING` (GAP-10). |
| `definition/database.tmdl` | bare `database` + `compatibilityLevel` | Desktop **drops the model name**. |
| `definition/model.tmdl` | adds `sourceQueryCulture`, `dataAccessOptions`, `annotation PBI_QueryOrder`, `annotation PBI_ProTooling = ["DevMode"]` | Desktop-generated annotations. |
| `pages/pages.json` | `pagesMetadata/1.1.0` | `activePageName` reflects the last-viewed page. |
| `pages/<Name>/page.json` | `page/2.1.0` + `name` + `displayName` + **`displayOption`** (e.g. `FitToPage`) + `height` + `width` | `displayOption` is required by the schema; Desktop defaults it silently, the Fabric toolchain does not (GAP-10). |
| `visuals/*/visual.json` | `visualContainer/2.12.0`, with `active: true` on each `queryRole` selection | Cosmetic normalisation. |

A custom theme adds a second entry to `themeCollection` alongside `baseTheme`, plus a
`RegisteredResources` package in the flat `resourcePackages` list:

```json
"themeCollection": {
  "baseTheme":   { "name": "Fluent2-CY26SU08", "type": "SharedResources", "reportVersionAtImport": { ... } },
  "customTheme": { "name": "AdventureWorksClean-a7c3e91b.json", "type": "RegisteredResources", "reportVersionAtImport": { ... } }
}
```

Three details are load-bearing, and all three fail quietly rather than loudly:

| Rule | Consequence if wrong |
|---|---|
| `customTheme.name` **and** `resourcePackages[].items[].name` must both carry the `.json` extension and equal `items[].path` | The published report silently applies no theme — the resource mapping never matches the file. |
| `path` must be the **filename only**, with no directory prefix | Desktop silently ignores the theme. |
| The `"name"` **inside** the theme JSON must match those fields exactly | Validation failure, and Desktop may not load the theme at all. |

Desktop caches themes **by filename**, so editing a theme in place can leave stale state even
after a reload. Append a short random GUID suffix (`<Name>-<guid>.json`) and rotate it on every
content change, keeping the base name stable. This is the only reliable way to force a reload to
pick up theme edits.

Desktop ships built-in themes (e.g. `CY24SU10`) with **no** `BaseThemes/*.json` on disk, so
the `BaseThemes/...` path in `resourcePackages` is a reference, not a file that must exist.
`validate_pbir_schema.py` does not require the file.

---

## 15. Validation set

All five run in `hooks/pre-commit` and in `.github/workflows/validate.yml`:

| Script | Covers |
|---|---|
| `scripts/validate_repo.py` | Required files, JSON well-formedness, git tracking, PBIP project discovery, `.pbip` manifest schema (GAP-11) |
| `scripts/validate_date_table.py` | Calendar TMDL columns for the configured fiscal pattern |
| `scripts/validate_pbir.sh` | PBIR JSON via `pbir-cli`, falling back to `validate_pbir_schema.py` on Linux |
| `scripts/validate_m_expressions.py` | M body structure (GAP-07), bare relative `File.Contents` paths (GAP-08), non-existent M module members such as `Number.Max` (GAP-12) |
| `scripts/validate_report.py` | PBIR **canvas layout**: visual overlap, negative positions, out-of-bounds placement (GAP-14) |

`scripts/validate_report.py` exists because of GAP-14 and is the only check in this set that
looks at *geometry*. Every other script reads file contents or JSON structure; a page in which
two charts sit on top of each other is valid by all of them. It reports overlap as an error only
when the two visuals share the same `z` layer, so deliberate stacking across different `z` values is not flagged.

`powerbi-report-author validate` is a stronger check than anything in this table and should be
run alongside them when it is available (see GAP-13 for installing it). It is not in the pre-commit
set because it needs a network fetch and a Node global install, and this set is designed to run
anywhere. Read its result carefully — GAP-15 explains why a green run may still have skipped
schema validation entirely.

`scripts/validate_pbir_schema.py` additionally enforces the Desktop-canonical JSON shape
described in §4 (GAP-09) and the `.platform` / `$schema` / `displayOption` requirements
(GAP-10), and separates **blocking errors** from **non-blocking warnings** — canvas size and
empty pages are reported as warnings and never fail the run.

Note the split of responsibility: `validate_pbir_schema.py` validates the *contents* of a
report folder, while `validate_repo.py` §5 validates the `.pbip` manifest that points at it
(GAP-11). Neither implies the other, so a project needs both.

**Where the PBIP validator stops and `pbir-cli` starts.** `validate_pbir_schema.py` is the
cross-platform fallback and checks the *shape* Desktop and Fabric agree on. It is not a full
JSON-Schema validator, so it will not catch a schema constraint it does not explicitly
implement. When `pbir-cli` is available (`validate_pbir.sh`), it validates against the real
schemas and will report things the Python fallback cannot see. Run both when you are unsure.

---

## 16. Adding a gap

When you hit something not listed here:

1. Take the next `GAP-nn` number.
2. Add a row to §1 with severity, component, symptom, and status.
3. If a validator can catch it, add the check to the relevant script and reference the gap ID
   in the error message so the failure is self-explanatory.
4. If it cannot be automated, add it to `docs/GETTING_STARTED.md` and to the guardrails
   section of `.github/instructions/powerbi-development.instructions.md`.
