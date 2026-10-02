# Changelog

All notable changes to this template are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- Visual gallery sample: `samples/pbip-visual-gallery/` rebuilt as a 36-page, 190-visual PBIP covering every supported native visual type plus the 26 Microsoft-published custom visuals in the manifest
- Generated shared model for the gallery: 13 tables of inline-M data (star schema plus one table per custom-visual data requirement), deterministic via a new `fnSeed` helper
- `scripts/build_gallery_report.mjs` — declarative page plan that emits the gallery's PBIR deterministically, so `queryRef` cannot drift from its field reference and a re-run gives an empty diff
- `scripts/extract_custom_visuals.py` — unzips the local `.pbiviz` packages into `CustomVisuals/<guid>/`, writes `report.json -> publicCustomVisuals`, and cross-checks every package against `manifest.csv`
- `scripts/generate_visual_allowlist.py` — generates the allowed visual and slicer contract from `catalog list` and the custom-visual manifest, with a recorded reason for each excluded type
- `scripts/verify_gallery_coverage.py` — asserts the gallery covers the allowlist and that `publicCustomVisuals` matches the GUIDs actually used
- `scripts/pbir_discovery.py` and `scripts/test_pbir_discovery.py` — one gitignore-aware source of truth for "which folders are ours", plus a differential test against `git check-ignore`
- Visual coverage matrix: `docs/POWER_BI_VISUAL_COVERAGE.md`
- Gallery base theme: `VisualGallery.Report/StaticResources/SharedResources/BaseThemes/GalleryBase.json`
- `templates/html-prototype/README.md` documenting the prototype's allowlist contract

### Fixed
- Validators walked into gitignored local staging folders. `validate_report.py` and `validate_repo.py` already reported failures for third-party sample PBIPs that are not this repo's; all five validators now share `scripts/pbir_discovery.py`
- `Calendar.tmdl` in the gallery anchored its fiscal year with `List.Max({YearsBack - 1, 0})`, which can only move forward. Facts older than `FiscalYearStartDate` fell outside the generated calendar and bound to nothing
- `VisualGallery.Report/definition/report.json` named base theme `CY24SU10` and registered `BaseThemes/CY24SU10.json`, but no such file existed, so the theme silently failed to apply
- `dashboard-template.html` specified a 1280x720 canvas, contradicting the 1920x1080 greenfield default the gallery is built at
- `generate_visual_allowlist.py` resolves the report-author CLI's npm shim explicitly on Windows, where `CreateProcess` cannot exec the bare name

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
