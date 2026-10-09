# powerbi-dev-template

[![Validate](https://github.com/genpgs/powerbi-dev-template/actions/workflows/validate.yml/badge.svg)](https://github.com/genpgs/powerbi-dev-template/actions/workflows/validate.yml)

**Linux-first, agent-agnostic GitHub Template** for AI-assisted Power BI (Standard workspace) development.

Ships with:
- 🗓️ **Fiscal calendar library** — month-aligned + week-based (4-4-5 / 4-5-4 / 5-4-4 / 13-period) Power Query M functions with configurable start date and week-start day
- 🤖 **Antigravity agent skills** — `powerbi-report-cli`, `semantic-model-authoring`, `fabriciq`
- 🔗 **Thin bridges** for GitHub Copilot (`.github/agents/`) and Claude Code (`CLAUDE.md`)
- ✅ **Validation** — Python scripts + pre-commit hook + GitHub Actions CI
- 📦 **Sample PBIP** — `CalendarBaseline` with 4-4-5 calendar, time-intelligence measures, FactSales stub
- 🐳 **Dev Container** — ready for GitHub Codespaces
- 🦆 **Optional local DuckDB** — opt-in CLI + MCP server for SQL over local CSV/Parquet/JSON/XLSX/SQLite. No cloud account; nothing else depends on it ([docs §8a](docs/GETTING_STARTED.md#8a-optional-duckdb-for-local-data-analysis))

---

## Quick Start (5 steps)

```bash
# 1. Clone your new repo (after clicking "Use this template" on GitHub)
git clone https://github.com/genpgs/<your-repo>.git && cd <your-repo>

# 2. Run setup (installs uv, pbir-cli, copies .env, optional pre-commit hook)
bash setup.sh

# 3. Edit .env with your workspace and fiscal calendar settings
#    Then update config/fiscal-calendar.json to match

# 4. Run validation
python3 scripts/validate_repo.py && python3 scripts/validate_date_table.py && python3 scripts/validate_m_expressions.py

# 5. Open the sample PBIP in Power BI Desktop (Windows) to render and refresh
#    samples/pbip-calendar-baseline/CalendarBaseline.pbip
```

→ Full walkthrough: **[docs/GETTING_STARTED.md](docs/GETTING_STARTED.md)**

---

## Fiscal Calendar Patterns

| Pattern | Weeks/quarter | Periods/year | Use case |
|---------|--------------|--------------|----------|
| `standard` | varies | 12 (months) | General business, month-aligned |
| `445` | 4+4+5 | 12 | US retail, CPG |
| `454` | 4+5+4 | 12 | Retail variant |
| `544` | 5+4+4 | 12 | Retail variant |
| `13period` | 4 | 13 | Hospitality, period-based reporting |

Set `pattern` in [`config/fiscal-calendar.json`](config/fiscal-calendar.json) and update the Calendar partition in the PBIP.

See **[docs/fiscal-calendar.md](docs/fiscal-calendar.md)** for full pattern docs and M function usage.

---

## Agent Harness Support

| Harness | Config location | Status |
|---------|----------------|--------|
| **Antigravity** | `.agents/skills/` | ✅ Canonical |
| **GitHub Copilot** | `.github/agents/` + `.github/instructions/` | ✅ Bridge stubs |
| **Claude Code** | `CLAUDE.md` | ✅ Bridge |

---

## Repo Layout

```
powerbi-dev-template/
├── .agents/skills/          # Antigravity skills (canonical)
│   ├── powerbi-report-cli/
│   ├── semantic-model-authoring/
│   └── fabriciq/
├── .github/agents/          # Copilot bridge stubs
├── .github/instructions/    # Copilot development instructions
├── .github/workflows/       # CI (validate.yml)
├── .devcontainer/           # Codespaces / VS Code Remote
├── CLAUDE.md                # Claude Code bridge
├── config/fiscal-calendar.json
├── power-query/
│   ├── fnCalendar.m         # Month-aligned calendar
│   ├── fnCalendarWeekBased.m# 4-4-5 / 454 / 544 / 13-period
│   └── fnFiscalCalendarConfig.m
├── samples/pbip-calendar-baseline/  # Working PBIP sample
├── samples/pbip-visual-gallery/      # 36-page, 190-visual PBIP reference report
├── samples/visual-gallery-assets/    # Asset manifest, visual catalog, images, icons
├── templates/html-prototype/         # Canvas mockup harness with an enforced allowlist
├── templates/visuals-gallery/        # Browsable visual reference (open index.html)
├── dax/queries/validate-calendar.dax
├── docs/specs/              # Specifications, incl. the optional DuckDB capability
├── scripts/                 # Validation scripts
├── hooks/pre-commit         # Git pre-commit hook
├── mcp/mcp.json.example     # powerbi-modeling-mcp config stub
├── docs/                    # GETTING_STARTED.md, fiscal-calendar.md
├── .env.example
└── setup.sh
```

---

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.10+ | <https://python.org> |
| Node.js | 22+ | <https://nodejs.org> |
| uv | latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| git | 2.30+ | package manager |
| Power BI Desktop | latest | Windows only — for rendering & publish |

---

## License

MIT
