# Changelog

All notable changes to this template are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- HTML visual gallery: `templates/visuals-gallery/index.html`, a single self-contained file listing all 84 native, excluded and custom visuals with the data roles each takes and the substitution rule that should stop you reaching for it. Filter by origin, family, authorability or thumbnail tier; searchable; opens straight off disk with no server and no network
- `samples/visual-gallery-assets/content.json` - the authored use-when / not-for prose, kept out of the markup so it can be reviewed in a diff and survives regeneration
- `scripts/build_visual_catalog.py` and `visual-catalog.json` - one derived file carrying identity, version, roles, thumbnail tier and demo page for every visual, merging the manifest, the `.pbiviz` capabilities, the allowlist, the icon lock and the gallery PBIR
- `scripts/vendor_native_icons.py` and `samples/visual-gallery-assets/icons/` - a chart-type glyph per native `visualType` from Tabler Icons (MIT), vendored verbatim from a pinned commit with a per-file SHA-256 lock and generated attribution. Desktop screenshots are Windows-only and DPI-dependent; Learn documentation images are Microsoft's content licensed for internal use, not redistribution
- `scripts/schematics.py` - ten labelled CSS/SVG diagrams for the visual types no glyph can honestly represent, such as the 100% stacked variants where equal column height is the defining property
- `scripts/fetch_gallery_assets.py` - downloads the `.pbiviz` packages and images from the manifest, rewriting GitHub `blob/` URLs to commit-pinned raw URLs and verifying every file against its SHA-256. PBIX is opt-in
- `scripts/verify_html_gallery.py` - 17 assertions over the gallery: allowlist parity in both directions, GUID agreement with `report.json`, roles provenanced to a package, thumbnail resolution, schematic and collision coverage, and that the HTML is self-contained and well-formed
- `samples/visual-gallery-assets/EXCEPTIONS.md` - the 28 visuals whose thumbnail is a stand-in, as a review list rather than a silent gap
- `samples/visual-gallery-assets/manifest.csv` is now tracked, so the fetch contract survives a clone
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
- `generate_visual_allowlist.py` emitted `roles: []` for all 26 custom visuals on any machine that had not run the fetcher, with no error - the mockup drawer's role list simply emptied. Roles now fall back to `visual-catalog.json`, and the fallback announces itself on stderr
- `build_visual_catalog.py` reported its own committed output as stale on a machine without the `.pbiviz` packages, because the roles read as empty. Roles are now carried forward from the previous catalog, so the build is byte-identical with or without the packages and `--check` is usable in CI
- `.gitignore` named a non-existent `scripts/extract_custom_visuals.ps1`; the script is `.py`
- The `.gitignore` rules re-including the gallery contracts were inert. Git does not descend into an excluded directory, so the negations only work if the parent stays visible - the folder's *contents* are now excluded rather than the folder itself
- `.gitattributes` marked every `*.csv` binary, which would have stored `manifest.csv` as an opaque blob with no diffs and no merge. It is text, and `*.pbiviz` is now pinned binary so a deliberate `git add -f` cannot corrupt a package
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
