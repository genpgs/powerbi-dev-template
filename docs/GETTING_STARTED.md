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
```

All checks should show `[PASS]`.

---

## 7. Open the sample in Power BI Desktop (Windows)

1. Copy the repo to a Windows machine (or use a shared drive/WSL path)
2. Open `samples/pbip-calendar-baseline/CalendarBaseline.pbip`
3. Click **Refresh** — the Calendar partition calls `fnCalendarWeekBased` against FactSales dates
4. Open DAX Studio and run `dax/queries/validate-calendar.dax` — confirm `ValidationPassed = TRUE`
5. Browse `FiscalWeekNumber`, `FiscalPeriodLabel`, `FiscalQuarter` columns to spot-check

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
