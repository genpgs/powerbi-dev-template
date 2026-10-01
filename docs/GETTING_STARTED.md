# Getting Started with powerbi-dev-template

This guide walks you through cloning the template, configuring your environment, and running your first agent-assisted Power BI development session.

---

## 1. Prerequisites

Install these tools before starting:

| Tool | Min version | Install |
|------|------------|---------|
| **Python** | 3.10 | <https://python.org> or OS package manager |
| **Node.js** | 18 | <https://nodejs.org> |
| **uv** | latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| **git** | 2.30 | OS package manager |
| **Power BI Desktop** | latest | Windows only — for local data refresh and desktop visual rendering |

> **Linux users**: All authoring (TMDL model definition, PBIR report JSON, M functions, DAX measures, automated schema validation, and HTML dashboard prototyping) runs natively on Linux. You only need Windows + Power BI Desktop or Microsoft Fabric when executing local Power Query M data refreshes into VertiPaq memory or previewing the desktop GUI. See [`docs/LINUX_WORKFLOW_GAPS.md`](LINUX_WORKFLOW_GAPS.md) for full Linux findings.

---

## 2. Create your project from the template

1. Go to <https://github.com/genpgs/powerbi-dev-template>
2. Click the green **"Use this template"** button → **"Create a new repository"**
3. Name your repo (e.g., `my-pbi-project`) and choose visibility
4. Click **Create repository**

Then clone it:

```bash
git clone https://github.com/genpgs/my-pbi-project.git
cd my-pbi-project
```

> **Codespaces users**: Click **"Code" → "Create codespace"** — the Dev Container will auto-install everything.

---

## 3. Run setup.sh

```bash
bash setup.sh
```

The script:
- Installs **uv** (if not present)
- Checks / installs **pbir-cli** (on macOS and Windows; on Linux, it informs you that the built-in `scripts/validate_pbir_schema.py` is used automatically)
- Copies `.env.example` → `.env`
- Optionally installs the pre-commit validation hook

---

## 4. Configure .env

Edit `.env` with your workspace and fiscal calendar settings:

```dotenv
AZURE_TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
PBI_WORKSPACE_NAME=My Power BI Workspace
FISCAL_CALENDAR_PATTERN=445
FISCAL_YEAR_START_DATE=2025-02-01
FISCAL_WEEK_START_DAY=Saturday
FISCAL_NUMBER_OF_YEARS=5
```

> `.env` is gitignored — never commit it.

---

## 5. Configure the fiscal calendar

Edit [`config/fiscal-calendar.json`](../config/fiscal-calendar.json) to match your business:

```json
{
  "pattern": "445",
  "fiscalYearStartDate": "2025-02-01",
  "weekStartDay": "Saturday",
  "numberOfYears": 5
}
```

Then update the Calendar partition in the sample PBIP (`CalendarBaseline.SemanticModel/definition/tables/Calendar.tmdl`) to pass the same values to `fnCalendarWeekBased`.

See [`docs/fiscal-calendar.md`](fiscal-calendar.md) for full pattern documentation.

---

## 6. Run validation

From the repo root:

```bash
python3 scripts/validate_repo.py        # structure, JSON, git tracking, PBIP projects
python3 scripts/validate_date_table.py  # Calendar TMDL columns for your pattern
bash scripts/validate_pbir.sh           # PBIR JSON (uses pbir-cli or validate_pbir_schema.py)
python3 scripts/validate_m_expressions.py # M body structure, 'in' shape, partition file paths
```

All checks should show `[PASS]`.

---

## 7. Open the sample in Power BI Desktop (Windows)

1. Copy the repo to a Windows machine (or use a shared drive/WSL path)
2. Open `samples/pbip-calendar-baseline/CalendarBaseline.pbip`
3. Click **Refresh** — the Calendar partition calls `fnCalendarWeekBased` against FactSales dates
4. Open DAX Studio and run `dax/queries/validate-calendar.dax` — confirm `ValidationPassed = TRUE`
5. Browse `FiscalWeekNumber`, `FiscalPeriodLabel`, `FiscalQuarter` columns to spot-check

## Visual options and sample gallery

See the [Power BI visual coverage matrix](POWER_BI_VISUAL_COVERAGE.md) for the
Desktop-native visual inventory, local PBIR/CLI support, known gaps, slicer
options, and Microsoft-published custom visual verification status. Open
[`samples/pbip-visual-gallery/VisualGallery.pbip`](../samples/pbip-visual-gallery/VisualGallery.pbip)
for runnable examples of core chart, card, and slicer authoring patterns. The
gallery includes its own copy of the calendar-baseline sample model and can be
opened independently.

---

## 7b. Two things that will bite you

Both of these pass every schema-level check and still fail on open or refresh. They are
enforced by `scripts/validate_m_expressions.py` and `scripts/validate_pbir_schema.py`, but
it is worth knowing the cause.

### 7b.1 Partition paths must be built from a parameter (GAP-08)

`File.Contents` resolves a relative path against the M engine's working directory, **not**
against the PBIP root. So this looks right and fails on refresh wherever the project lives:

```m
Source = Excel.Workbook(File.Contents("data/sales.xlsx"), null, true)
```

Declare a path parameter and concatenate instead:

```m
expression BasePath = "/home/me/projects/Adventureworks/" meta [IsParameterQuery=true, Type="Any"]

// in the partition
Source = Excel.Workbook(File.Contents(BasePath & "data/sales.xlsx"), null, true)
```

`BasePath` is a normal M parameter: it belongs in `expressions.tmdl` with the
`IsParameterQuery=true` metadata, and you pass the value at refresh time. The validator
only flags a string literal in first-argument position, so the correct form needs no
exemption.

### 7b.2 No `;` on the terminating `in` expression (GAP-07)

M has no `;` statement terminator. A trailing semicolon makes the parser start a fresh
expression and demand a token identifier:

```
Syntax error in expression 'fnCalendar'. Token Identifier expected.
```

The offending `;` sits on whichever line carries the `in` value, which is often the line
*after* `in`, so it is easy to miss by eye:

```m
let
    // ...
in
    Result;      // <- this semicolon is the whole bug
```

### 7b.3 Generated state is not source

Desktop rewrites these on every open and save, so committing them produces diff noise and
merge conflicts rather than meaning. They are all covered by `.gitignore`:

| Path | What it is |
|------|-----------|
| `**/.pbi/` | Per-user Desktop runtime state: settings, caches, editor layout |
| `diagramLayout.json`, `semanticModelDiagramLayout.json` | Diagram auto-layout, rewritten on save |
| `.vscode/`, `.idea/` | IDE folders Desktop may create next to the PBIP |

---

## 7c. Write PBIP files the way Desktop does

`scripts/validate_pbir_schema.py` enforces the Desktop-canonical shape, because a
hand-written file that is *nearly* right opens fine and then fails to render a theme or
gets rewritten on first save. The key points:

| File | Canonical form |
|------|----------------|
| `<Name>.pbip` | Has `$schema` (`.../fabric/pbip/pbipProperties/1.0.0/schema.json`); `artifacts` lists the **report only** — a `semanticModel` entry makes Desktop refuse to open the project (GAP-11); `settings.enableAutoRecovery: true` |
| `definition.pbir` | Has `$schema` (`.../fabric/item/report/definitionProperties/2.0.0/schema.json`); `datasetReference.byPath` |
| `definition/version.json` | Has `$schema` (`.../versionMetadata/1.0.0/schema.json`) and `version: "2.0.0"` |
| `definition/report.json` | `themeCollection` is an **object** with a `baseTheme` entry; `resourcePackages` is a **flat** list of `{name, type, items}`; **no** `layoutOptimization` |
| `definition.pbism` | `version: "4.2"`, `settings: {}` |
| `definition/database.tmdl` | Bare `database` keyword plus `compatibilityLevel` (Desktop drops the model name) |
| `<Item>.platform` | **One per item folder** — both `.Report` and `.SemanticModel`. Has `metadata.type`, `metadata.displayName` and a stable `config.logicalId` UUID. Missing it is `PBIR_PLATFORM_MISSING` in the Fabric toolchain. |
| `pages/pages.json` | Has `$schema` (`.../pagesMetadata/1.1.0/schema.json`) |
| `pages/<Name>/page.json` | Has `$schema` (`.../page/2.1.0/schema.json`) **and** `displayOption` (e.g. `FitToPage`), which the schema requires |

The `resourcePackages` shape is the easiest to get wrong: some generators emit a wrapped
`{"resourcePackage": {...}}` form. Desktop tolerates it but the theme silently fails to
apply.

**Desktop's tolerance is not correctness.** A `.Report` folder missing `.platform`, or
definition JSON missing `$schema`, opens in Desktop without complaint and is still rejected
by the Fabric toolchain — so "it opens" is not evidence that it is right. Where
`pbir-cli` is available, `scripts/validate_pbir.sh` validates against the real JSON Schemas
and will catch constraints `validate_pbir_schema.py` does not implement. Run both when unsure.
See `docs/LINUX_WORKFLOW_GAPS.md` GAP-10.

**The one hard stop.** A `semanticModel` entry in the `.pbip` manifest is the only defect here
that Desktop will not open at all:

```
Property 'semanticModel' has not been defined and the schema does not allow
additional properties.  Path 'artifacts[1].semanticModel'
```

The manifest's `artifacts` array describes what the shortcut *launches* — the report. The
semantic model is already wired up by `definition.pbir` → `datasetReference.byPath`, so
listing it is both invalid and redundant. A correct manifest is:

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
  "version": "1.0",
  "artifacts": [ { "report": { "path": "MyReport.Report" } } ],
  "settings": { "enableAutoRecovery": true }
}
```

`scripts/validate_repo.py` checks this for every `*.pbip` it finds — note that it validates
whatever project is in front of you, so a downstream copy that has drifted from this template
is still caught. See `docs/LINUX_WORKFLOW_GAPS.md` GAP-11.

**Errors that only appear on refresh.** Some M problems survive every import and every
validator, because nothing outside a running M engine resolves a symbol. The classic case is
a DAX or Excel function name used as an M module member — the project opens, the report
renders, and refresh reports:

```
1 query is blocked by the following error:
The import Number.Max matches no module reference.
```

`MAX()` and `MIN()` are DAX and Excel calls. In M, aggregation is in `List`, and the `Number`
module has no `Max` or `Min`:

| Written | Correct in M |
|---|---|
| `Number.Max(a, b)` | `List.Max({a, b})` |
| `Number.Min(a, b)` | `List.Min({a, b})` |
| `Number.Sum(list)` | `List.Sum(list)` |
| `Number.Average(list)` | `List.Average(list)` |
| `Number.Count(list)` | `List.Count(list)` |
| `Text.Len(x)` | `Text.Length(x)` |
| `Number.IsBlank(x)` | `x = null` |

Two habits prevent this. When porting a calculation from DAX, re-derive the function against
the [M reference](https://learn.microsoft.com/en-us/powerquery-m/) rather than transliterating
the name. And remember Desktop stops at the *first* bad expression, so a file with three
defects reports one — expect the next to appear after you fix this one.

`scripts/validate_m_expressions.py` scans `expressions.tmdl`, every `tables/*.tmdl`, and the
`power-query/*.m` reference files against a denylist of members confirmed absent from the
official reference. It is a denylist, so it cannot be exhaustive — **a refresh is still the
only complete check.** A green M validator is necessary, not sufficient. See
`docs/LINUX_WORKFLOW_GAPS.md` GAP-12.

---

## 8. Configure the MCP server & EULA

The `powerbi-modeling-mcp` MCP server enables Tier 1 semantic model authoring (live model edits, measure creation, etc.).

> **Important (EULA Acceptance)**: Microsoft's MCP requires legal terms acknowledgement before tools execute. In headless or agent environments, set `"PBI_MODELING_MCP_ACCEPT_EULA": "true"` in your MCP environment configuration, or pass `--accept-eula` when invoking the server. Review the terms at <https://go.microsoft.com/fwlink/?LinkId=2381247>.

Copy `mcp/mcp.json.example` to the correct location for your harness:

| Harness | Location |
|---------|----------|
| Antigravity (global) | `~/.config/antigravity/mcp.json` |
| Antigravity (per repo) | `.antigravity/mcp.json` in repo root |
| VS Code / GitHub Copilot | `.vscode/mcp.json` in repo root |
| Claude Code | `~/.claude/mcp.json` |

Then remove the `_comment` and `_locations` keys from the copied file.

---

## 8b. Optional agent skills & plugins (marketplace)

The three skills in `.agents/skills/` are **canonical and ship with this repo** — they need no installation:

| Skill | Covers |
|-------|--------|
| `powerbi-report-cli` | Report planning, design canon, authoring, publish |
| `semantic-model-authoring` | TMDL, DAX, measures, modeling, deploy |
| `fabriciq` | Natural-language data Q&A over an existing report |

> `fabriciq` has no equivalent in the community marketplace, so dropping the repo copy loses that capability entirely.

### Adding optional extra coverage

The [`data-goblin/power-bi-agentic-development`](https://github.com/data-goblin/power-bi-agentic-development) marketplace publishes additional plugins. Install them if you need something the repo skills don't cover:

| Plugin | Adds |
|--------|------|
| `tabular-editor` | BPA rules, C# scripting, `te` / `te2` CLI automation |
| `pbi-desktop` | Connect to and query a live Power BI Desktop model |
| `paginated-reports` | RDL authoring, validation, PDF/Excel render |
| `custom-visuals` | Deneb, Python, R, SVG, and `.pbiviz` visuals |
| `fabric-cli` / `fabric-admin` | Remote Fabric ops; tenant settings audits |
| `etl` | Spark, Livy, and DuckDB against lakehouse data |

```bash
# Claude Code
claude plugin marketplace add data-goblin/power-bi-agentic-development
claude plugin install tabular-editor@power-bi-agentic-development

# Copilot CLI (reads the same marketplace.json manifest)
copilot plugin marketplace add data-goblin/power-bi-agentic-development
copilot plugin install tabular-editor@power-bi-agentic-development
```

Then browse with `claude plugin list` / `copilot plugin list`, or `/plugin` inside a session.

> **A word of caution**: the marketplace's own README warns against installing everything — *"Each skill competes for the agent's attention and context window."* Add a plugin when you need it. Note also that these are released on a weekly cadence and versions 26.26–26.38 were a deliberate breaking transition, so pin **26.25 or earlier** if you depend on the older skill structure.

> **Licensing**: the marketplace is GPL-3.0 and licensed for free community use, but you may not incorporate its skills into your own products or tools without keeping attribution and a link to the upstream project. Installing via the plugin path is fine; copying skill text into this repo obliges you to retain that attribution.

---

## 9. Helper Scripts & Prototyping Templates

- **Profile Data Sources**:
  ```bash
  python3 scripts/inspect_data_source.py path/to/source.xlsx --markdown
  ```
  Profiles sheets, column types, null %, and automatically recommends Dimension vs Fact table roles and candidate primary/foreign keys.
- **Scaffold PBIR Reports & PBIP Projects**:
  ```bash
  python3 scripts/scaffold_pbir.py SalesReport --pages "Executive Overview" "Product Breakdown" --template executive
  ```
  Generates a complete, compliant `.Report` folder (`definition.pbir`, `pages.json`, `page.json`, and visual layout placeholders) plus the `.pbip` manifest.
- **Interactive HTML Dashboard Prototype**:
  Copy `templates/html-prototype/dashboard-template.html` to rapidly mockup canvas layouts, test KPI metrics, and inspect exact PBIR visual position coordinates before writing TMDL/PBIR.
- **Rendered-output verification (Windows only)**:
  ```bash
  python3 scripts/capture_report_screenshot.py --reload
  ```
  Captures a PNG of every page from a running Power BI Desktop instance into `artifacts/screenshots/`. Use `--reload` to pull on-disk edits into the canvas first, or pass a page ID (`Overview`) to capture just one. This is the step that completes the authoring loop: validation cannot catch a visual that renders wrong while passing every check (see [GAP-18](LINUX_WORKFLOW_GAPS.md#13-gap-18--the-authoring-loop-cannot-be-completed-on-linux)). Requires `npm i -g @microsoft/powerbi-desktop-bridge-cli` and the target `.pbip` open in Desktop. On Linux it exits with a pointer to GAP-18 — describe report work there as *validate-clean, visually unverified*.

---

## 10. Start your first agent session

Open your agent harness (Antigravity, GitHub Copilot, Claude Code) in the repo directory and try these example prompts:

### Semantic model authoring
```
Load .agents/skills/semantic-model-authoring/SKILL.md.
Inspect the CalendarBaseline semantic model and list all measures.
```

### Report planning
```
Load .agents/skills/powerbi-report-cli/SKILL.md.
Plan a Sales Performance report using the CalendarBaseline semantic model.
```

### DAX review
```
Load .agents/skills/semantic-model-authoring/SKILL.md.
Review the 'Total Amount FYTD' measure in Calendar.tmdl for correctness
with a 4-4-5 week-based fiscal calendar.
```

### Switch fiscal pattern
```
Load .agents/skills/semantic-model-authoring/SKILL.md.
Update the Calendar partition to use the 13-period pattern
(13 × 4-week periods, Sunday-anchored, starting 2025-01-05).
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `powerbi-report-author: command not found` (macOS/Win) | Run `uv tool install pbir-cli` and ensure `~/.local/bin` is on `PATH`. On Linux, `scripts/validate_pbir.sh` automatically falls back to `scripts/validate_pbir_schema.py`. |
| MCP tool fails with `EULA must be accepted` | Add `"PBI_MODELING_MCP_ACCEPT_EULA": "true"` to your MCP `env` block, or invoke the `accept_eula` tool. |
| `npx: command not found` | Install Node.js 18+ |
| Calendar refresh fails in Desktop | Check that `FactSales[OrderDate]` has valid dates; the partition derives its range from fact data |
| `ValidationPassed = FALSE` in DAX | Check `NoNullWeeks`/`NoNullPeriods` — a null week usually means the date falls outside the generated fiscal years; increase `NumberOfYears` |
| MCP not connecting | Check that `powerbi-modeling-mcp` is in your harness MCP config and that Node.js is on PATH |
