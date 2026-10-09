# Getting Started with powerbi-dev-template

This guide walks you through cloning the template, configuring your environment, and running your first agent-assisted Power BI development session.

---

## 1. Prerequisites

Install these tools before starting:

| Tool | Min version | Install |
|------|------------|---------|
| **Python** | 3.10 | <https://python.org> or OS package manager |
| **Node.js** | 22 | <https://nodejs.org> |
| **uv** | latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| **git** | 2.30 | OS package manager |
| **Power BI Desktop** | latest | Windows only — for local data refresh and desktop visual rendering |

> **Node.js 22**: the devcontainer pins Node 22. Node 20 also runs `powerbi-modeling-mcp`; 22 is the floor required by the [Skills CLI](https://github.com/vercel-labs/skills) used for the optional upstream DuckDB skill in §8c.

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

Start with the browsable reference:
[`templates/visuals-gallery/index.html`](../templates/visuals-gallery/index.html).
It lists all 84 native, excluded and custom visuals with the data roles each
takes and the substitution rule that should stop you reaching for it. Single
self-contained file — open it, no server or build needed.

For the full inventory of Desktop-native visuals, local PBIR/CLI support, known
gaps and slicer options, see the
[Power BI visual coverage matrix](POWER_BI_VISUAL_COVERAGE.md). Open
[`samples/pbip-visual-gallery/VisualGallery.pbip`](../samples/pbip-visual-gallery/VisualGallery.pbip)
for runnable examples: 36 pages covering every supported native visual type plus
all 26 Microsoft custom visuals.

The gallery reference works on a fresh clone with nothing installed. The sample
**report** needs the `.pbiviz` payloads, which are publisher binaries and are not
committed — download and verify them, then register them:

```bash
python3 scripts/fetch_gallery_assets.py    # download + SHA-256 verify, no binaries in git
python3 scripts/extract_custom_visuals.py  # install into VisualGallery.Report/CustomVisuals/
python3 scripts/verify_gallery_coverage.py # assert coverage against the allowlist
python3 scripts/verify_html_gallery.py     # assert the reference page matches its sources
```

`fetch_gallery_assets.py` rewrites the manifest's GitHub URLs to raw, commit-pinned
downloads and checks every file against the SHA-256 recorded in the manifest, so a
clone at a given manifest revision always gets the same bytes. Add `--check` to
verify what is already on disk without downloading.

## Designing a report in HTML first

Copy `templates/html-prototype/dashboard-template.html` to mock a canvas layout
before writing any PBIR. It enforces an allowlist of visual and slicer types
generated from the CLI catalog and the custom-visual manifest, so a prototype
cannot offer a visual the report cannot actually render. See
[`templates/html-prototype/README.md`](../templates/html-prototype/README.md).
Regenerate the allowlist after adding a visual:

```bash
python3 scripts/generate_visual_allowlist.py
```

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
| Claude Code (project only) | `.mcp.json` in repo root — preferred, keeps config in the repo |
| OpenCode | `opencode.json` in repo root |

Then remove the `_comment` and `_locations` keys from the copied file.

---

## 8a. Optional: DuckDB for local data analysis

DuckDB gives an agent a fast SQL engine over local files — no database server, no cloud account, no sign-in. It is **entirely optional** and nothing else in this template depends on it. Skip this section if you do not need it.

[`setup.sh`](../setup.sh) section 7a offers the CLI and prints the registration snippet; this section is the reference version.

### What it can read

| Tier | Sources | Cost |
|------|---------|------|
| Built in | CSV, TSV, Parquet | Nothing to install |
| Official extension | JSON / NDJSON, `.xlsx` / `.xlsm`, local SQLite files | Downloaded on first use (see below) |

Not supported, so you are not left guessing:

- **`.xls`** (the legacy format). Only `.xlsx` and newer.
- **XML.** Deferred, and it needs a community extension — third-party code, so it is not promised here.
- **Remote or cloud sources** of any kind — no PostgreSQL, MySQL, BigQuery, S3, or Fabric warehouse. Local files only.

### Two things that will bite you

**Extensions download on first use.** `excel`, `sqlite`, and `json` are fetched the first time you touch them, so the first query is noticeably slower than later ones — measured at ~10x on a cold cache. In an offline environment, preload them while connected. Note that JSON behaves differently by version: on the pinned LTS line it is linked into the binary and needs no download at all, on other versions it is a loadable extension. Don't promise offline JSON support without checking your version.

**Trailing whitespace breaks CSV detection.** A CSV ending in a stray `\r\n` fails with *"It was not possible to automatically detect the CSV parsing dialect"* — and the error blames delimiters and quoting, neither of which is the problem. It fails even when you pass the correct delimiter explicitly. This reproduces on Linux and Windows alike. If you generate files from PowerShell, `Set-Content` appends exactly such a newline; write fixtures with `printf` or Python instead.

### Registering the MCP server

The CLI is for you, in a shell. For an **agent** to call DuckDB, your harness also has to load an MCP server. Those are three separate steps — installing the binary, registering the server, then enabling it — and completing the first does nothing for the other two.

Add this as a sibling of `powerbi-modeling-mcp` in your harness MCP config:

```json
"duckdb-local": {
  "type": "stdio",
  "command": "uvx",
  "args": [
    "mcp-server-motherduck",
    "--db-path", ":memory:",
    "--read-write",
    "--query-timeout", "30"
  ]
}
```

**Read this before you paste it:**

- **`--read-write` is required, not optional.** An in-memory DuckDB database cannot be read-only — upstream refuses to start without the flag. Remove it and the server will not start.
- **The database is throwaway.** It is created when the server starts, holds nothing that predates the session, and is discarded when the server exits. That is the point: for exploratory profiling there is no state worth keeping, so throwing it away avoids any cleanup burden.
- **The filesystem is not throwaway.** That same flag permits `COPY … TO` and `EXPORT DATABASE`, which write real files that persist after the server exits. Point this at data you are happy to have written. **If you need a read-only *database*, use a DuckDB file path instead** — DDL and DML are rejected, so the `.duckdb` file cannot be modified, at the cost of a file you have to clean up yourself:
  ```json
  "args": ["mcp-server-motherduck", "--db-path", "/absolute/path/to/analysis.duckdb", "--query-timeout", "30"]
  ```
  **This is not a filesystem sandbox.** Read-only protects the *database*, not the disk: `COPY … TO` still writes files in that mode (verified 2026-10-08). Both options can write files; the file path only removes the ability to change the database itself.
- **Keep your source files read-only-in-practice.** Both configs can write files. To stop that, add `--init-sql` with an **allow-list**, in this exact order — verified 2026-10-08:
  ```json
  "args": ["mcp-server-motherduck", "--db-path", ":memory:", "--read-write", "--query-timeout", "30",
           "--init-sql", "SET allowed_paths=['/abs/path/to/source.csv']; SET allowed_directories=['/abs/path/to/scratch']; SET enable_external_access=false;"]
  ```
  Your listed sources stay readable, `COPY … TO` against a source is **blocked**, and writes are confined to the scratch directory. **Order matters:** the allow-list must come *before* `enable_external_access=false`, or startup fails. Set `enable_external_access=false` on its own and you also lose every file *read*, including extension auto-install.
  Verified on **both** Linux and Windows (2026-10-08): allowed read succeeds, overwrite is refused with a permission error, out-of-list reads are refused, the source file is byte-identical afterwards, and the reverse order fails as described. Windows paths need forward slashes (`C:/data/source.csv`), not backslashes.
- **No MotherDuck account, token, or sign-in is involved.**
- **Results are bounded** to 1024 rows / 50,000 characters, and `--query-timeout` stops a runaway query. Upstream leaves the timeout disabled by default, which is why the value above is explicit.

Then restart your harness and enable the server. Nothing here is registered automatically, and `setup.sh` never writes to your harness configuration.

### What this does not do

DuckDB is a source-side SQL engine. It does **not** execute DAX, does not reproduce VertiPaq behaviour, and does not establish semantic parity with your model. A SQL result over a source file diverges from a model result whenever Power Query transforms the data, a measure applies filter context, a relationship changes grain, or RLS filters rows — and **matching numbers prove consistency, not equivalent definitions.** Comparing DuckDB against Power BI needs the grain, filters, source snapshot, and calendar context to be aligned explicitly first.

### If you would rather not install anything

[`scripts/inspect_data_source.py`](../scripts/inspect_data_source.py) profiles Excel, CSV, and TSV using only the standard library plus `openpyxl`. It samples the first 1,000 rows, so its statistics are sample-based, and its key/role suggestions are heuristics — but it needs no database engine and no network:

```bash
python3 scripts/inspect_data_source.py path/to/source.xlsx --markdown
```

It does not read Parquet or JSON, and CSV type inference is effectively untyped, since every value arrives as a string. DuckDB is the step up when you need those, or need full-file statistics rather than a sample.

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

> **A note on `etl`**: it also uses DuckDB, but against **lakehouse** data — a different job from the local, offline analysis in §8a. The two are unrelated and neither replaces the other; there is no need to install `etl` for §8a.

```bash
# Claude Code
claude plugin marketplace add data-goblin/power-bi-agentic-development
claude plugin install tabular-editor@power-bi-agentic-development

# Copilot CLI (reads the same marketplace.json manifest)
copilot plugin marketplace add data-goblin/power-bi-agentic-development
copilot plugin install tabular-editor@power-bi-agentic-development
```

Then browse with `claude plugin list` / `copilot plugin list`, or `/plugin` inside a session.

---

## 8c. Optional: upstream DuckDB SQL skill

`motherduckdb/agent-skills` (MIT) publishes a DuckDB SQL reference skill. It is **not** installed by this template and it is **not** needed for §8a — that section documents the query surface directly. Install it only if you want agent-side SQL syntax guidance across your other projects.

> **Only one of its 22 skills is usable locally.** Every other skill in the collection assumes a MotherDuck account, connection, or cloud workspace, which is out of scope here. We name the exception explicitly so you do not install the catalog and expect the rest to work:
>
> | Skill | Local? |
> |---|---|
> | `motherduck-duckdb-sql` | **Yes** — DuckDB SQL syntax. The only one. |
> | `motherduck-query`, `motherduck-explore` | No — both declare *"Prerequisites: An established MotherDuck connection"* |
> | `motherduck-cli` | No — this is the MotherDuck CLI, a different product from DuckDB's own CLI, and its workflows assume authentication |
> | The other 18 | No — MotherDuck product features (Dives, Flights, shares, Guides, DuckLake, REST API, pricing, migrations) or they depend on the skills above |

One caveat on the one that qualifies: it is DuckDB-generic in substance but MotherDuck-framed in instruction, and some of its guidance points at MotherDuck docs that do not apply here. Read it as a DuckDB syntax reference, not as MotherDuck documentation.

```bash
# OpenCode — note --global, see the note below
npx -y skills add motherduckdb/agent-skills \
  --agent opencode --skill motherduck-duckdb-sql --yes --global

# Claude Code
npx -y skills add motherduckdb/agent-skills \
  --agent claude-code --skill motherduck-duckdb-sql --yes --global

# GitHub Copilot
npx -y skills add motherduckdb/agent-skills \
  --agent github-copilot --skill motherduck-duckdb-sql --yes --global

# On Windows, add --copy if symlinks are unavailable
```

**Use `--global`, deliberately.** For OpenCode and GitHub Copilot, the Skills CLI installs *project-scoped* skills into `.agents/skills/` — which in this repo is the **canonical first-party skill directory** holding the three skills from §8b. A project-scoped install would write third-party content into that tree, where every harness reading `.agents/skills/` would pick it up. The upstream skill is a general DuckDB reference rather than a property of this template, so global is both safer here and more useful.

Other notes:

- **Requires Node.js 22+.** The devcontainer already pins 22; see §1.
- **Update and verify:** `npx -y skills update -g`, then `npx -y skills list -g`.
- **Telemetry:** the Skills CLI collects anonymous install data. Set `DISABLE_TELEMETRY=1` or `DO_NOT_TRACK=1` to opt out.
- **Manual install:** copy the whole skill directory, not only `SKILL.md`, from a checkout of the repo — `cp -R skills/motherduck-duckdb-sql ~/.agents/skills/`.
- **Hooks are not supported in OpenCode.** `motherduck-duckdb-sql` uses none, so this does not affect it.

> **A word of caution**: the marketplace's own README warns against installing everything — *"Each skill competes for the agent's attention and context window."* Add a plugin when you need it. Note also that these are released on a weekly cadence and versions 26.26–26.38 were a deliberate breaking transition, so pin **26.25 or earlier** if you depend on the older skill structure.

> **Licensing**: the marketplace is GPL-3.0 and licensed for free community use, but you may not incorporate its skills into your own products or tools without keeping attribution and a link to the upstream project. Installing via the plugin path is fine; copying skill text into this repo obliges you to retain that attribution.

---

## 9. Helper Scripts & Prototyping Templates

- **Profile Data Sources**:
  ```bash
  python3 scripts/inspect_data_source.py path/to/source.xlsx --markdown
  ```
  Profiles sheets, column types, null %, and automatically recommends Dimension vs Fact table roles and candidate primary/foreign keys. Handles Excel (`.xlsx`), CSV and TSV with no database engine and no network — statistics are over a 1,000-row sample and the key/role suggestions are heuristics. For Parquet, JSON, or full-file statistics, see the optional DuckDB section §8a.
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
