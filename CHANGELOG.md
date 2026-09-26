# Changelog

All notable changes to this template are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- Cross-platform pure-Python PBIR schema validator: `scripts/validate_pbir_schema.py`
- PBIR report & PBIP project generator: `scripts/scaffold_pbir.py` (CLI for creating multi-page PBIR folders with visual scaffolds)
- Tabular data profiling utility: `scripts/inspect_data_source.py` (for Excel/CSV source inspection and Star Schema role suggestions)
- Reusable interactive HTML report prototype harness: `templates/html-prototype/dashboard-template.html`
- Comprehensive Linux workflow limitations and pull request log: `docs/LINUX_WORKFLOW_GAPS.md`
- Pre-commit hook integration for PBIR schema validation

### Fixed
- Fixed TMDL syntax error in `samples/pbip-calendar-baseline/CalendarBaseline.SemanticModel/definition/expressions.tmdl` by removing invalid root-level `//` comments
- Fixed `.env` false-positive failure in `scripts/validate_repo.py` by checking git tracking status instead of disk existence
- Fixed hardcoded path assumptions in `scripts/validate_repo.py` and `scripts/validate_pbir.sh` to dynamically detect all `.pbip` and `.Report` folders
- Fixed `setup.sh` failure on Linux by guarding `pbir-cli` installation and pointing to the Python validator fallback
- Documented `PBI_MODELING_MCP_ACCEPT_EULA` and Microsoft EULA requirements in `mcp/mcp.json.example` and `docs/GETTING_STARTED.md`

### Added
- Antigravity agent skills: `powerbi-report-cli`, `semantic-model-authoring`, `fabriciq`
- GitHub Copilot thin bridge stubs in `.github/agents/`
- Claude Code bridge `CLAUDE.md`
- Power Query M functions: `fnCalendar` (month-aligned) and `fnCalendarWeekBased` (4-4-5 / 4-5-4 / 5-4-4 / 13-period)
- `config/fiscal-calendar.json` — documents chosen calendar pattern
- Sample PBIP: `CalendarBaseline` with 4-4-5 week-based calendar
- Validation scripts: `validate_repo.py`, `validate_date_table.py`, `validate_pbir.sh`
- Pre-commit hook in `hooks/pre-commit`
- GitHub Actions CI workflow: `validate.yml` (ubuntu-latest)
- Dev Container: `.devcontainer/devcontainer.json` for Codespaces / VS Code Remote
- MCP config stub: `mcp/mcp.json.example`
- Onboarding: `README.md`, `docs/GETTING_STARTED.md`, `docs/fiscal-calendar.md`
- `CHANGELOG.md`, `.gitignore`, `.env.example`, `setup.sh`
