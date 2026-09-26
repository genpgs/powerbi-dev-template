# Changelog

All notable changes to this template are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [0.1.0] — 2026-09-26

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
