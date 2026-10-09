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
- `scripts/stage_pbir_examples.py` and `samples/visual-gallery-assets/PBIR/` - the report definitions from the 26 Microsoft sample reports, 452 files and 1.3 MB, as reference material showing how each custom visual is actually configured. The `CustomVisuals/` payload and `.SemanticModel/` folders are excluded, and the folder names drop the `.Report` suffix so `pbir_discovery.py` does not adopt 26 third-party reports as repo-owned
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
- `docs/specs/` - eight specifications for an optional local-only DuckDB agent capability (scope and boundaries, source/format matrix, tooling selection, upstream skill installation, safety model, profiler disposition, Power BI reconciliation boundaries, acceptance criteria)
- `scripts/test_inspect_delimiter.py` - regression test pinning CSV/TSV delimiter routing in `inspect_data_source.py`
- Optional DuckDB in `setup.sh` - new section 7a offers the DuckDB CLI pinned to an explicit LTS version constant (`DUCKDB_VERSION`, declared with its rationale at the top of the script). The pin is the point: DuckDB is here for robust structured-data analysis, which only holds if the engine version is a known quantity rather than a floating tag. Fully opt-in; `scripts/inspect_data_source.py` remains the zero-dependency profiler; skipped automatically on non-interactive shells and by `DUCKDB_SKIP_INSTALL=1`
- `setup.sh` section 7c - prints the DuckDB MCP registration snippet as a sibling of `powerbi-modeling-mcp` without ever writing a harness config. Records that installing the CLI, registering the server, and enabling it in a harness are three separate steps, that `:memory:` requires `--read-write`, that the flag also permits filesystem writes (with a DuckDB file path offered for a read-only *database*, not a read-only filesystem), and that no MotherDuck account or token is involved
- `docs/GETTING_STARTED.md` section 8a - reference documentation for the optional DuckDB capability: what each source format costs, the `.xls` and XML limitations, the first-use extension download and its measured cost, the trailing-whitespace CSV detection trap, the MCP registration snippet with its caveats, an explicit statement of what DuckDB does not do (no DAX, no VertiPaq parity, matching numbers do not prove equivalent definitions), and the zero-install `inspect_data_source.py` fallback
- `docs/GETTING_STARTED.md` section 8c - opt-in install of the single upstream DuckDB SQL skill that works without a MotherDuck account, with the other 21 listed and why each is excluded, and a recommendation to install `--global` so third-party skills stay out of the canonical `.agents/skills/` tree
- `mcp/mcp.json.example` - a `duckdb-local` server alongside `powerbi-modeling-mcp`, registered but `enabled: false`, plus project-scoped `.mcp.json` and `opencode.json` config locations. Local files only, no credentials, no remote or cloud sources
- `.vscode` and `.claude` are gitignored in this repo, so the Copilot and Claude project-scoped MCP locations are documented for manual copy rather than committed
- `scripts/validate_repo.py` now enforces LF line endings **and** `bash -n` parseability on `setup.sh`, `.devcontainer/setup.sh` and `scripts/validate_pbir.sh`, plus a CI step. CRLF in a shell script fails `bash -n` as a misleading "unexpected end of file", and `.gitattributes` `*.sh text eol=lf` normalises the damage away so `git status` shows nothing - a devcontainer build would fail at `postCreateCommand`. The parse check reports `[SKIP]` with the reason when the host's shell cannot run at all (for example the Windows WSL shim), so an environment limitation is never reported as a script defect

### Added
- `docs/specs/LINUX-VERIFICATION-HANDOFF.md` - single-file record of the Linux verification pass: completed items (LTS pin, five source tiers, MCP launch with no credentials), the findings, and the two Windows items still open. Supersedes the gitignored `duckdb-pending-linux-verification.md`, which had gone stale
- Documented DuckDB source-file protection for the optional MCP server, via a DuckDB allow-list: `allowed_paths` / `allowed_directories` set **before** `enable_external_access=false`. Verified on DuckDB `1.5.5`, LTS `1.4.5` and the engine bundled with `mcp-server-motherduck==1.1.0`. Allow-listed sources stay readable, `COPY … TO` against a source is blocked, and writes are confined to a designated scratch directory. Bare `enable_external_access=false` is not usable on its own - it also blocks every file read, including extension auto-install

### Fixed
- `setup.sh` could not run unattended: the pre-commit-hook prompt used a bare `read`, which fails under `set -euo pipefail` when stdin is closed or piped, so `bash setup.sh </dev/null` exited 1 partway through. It is now guarded with `[ ! -t 0 ]`, the same guard already used for the DuckDB prompt, and the "not a git repo" case is a separate branch so CI is not told to run `git init`. Interactive prompting is unchanged
- `scripts/validate_repo.py` did not check shell scripts, and `.gitattributes` `*.sh text eol=lf` normalises CRLF away, so a CRLF `.devcontainer/setup.sh` passed `git status` and all 300 checks while `bash -n` rejected it with a misleading "unexpected end of file" - and a devcontainer build would fail at `postCreateCommand`. Validation now enforces LF line endings and `bash -n` across `setup.sh`, `.devcontainer/setup.sh` and `scripts/validate_pbir.sh`, with a matching CI step. The parse check reports `[SKIP]` with the reason when the host's shell cannot run at all (for example the Windows WSL shim, which cannot reach a repo on another drive), so an environment limitation is never reported as a script defect
- Documentation overstated DuckDB MCP read-only guarantees. `--db-path` with a file path rejects DDL/DML but **not** `COPY … TO`, and `access_mode='READ_ONLY'` does not close that either, so both documented configs could write files; `SPEC-05` §4a contradicted its own §3 on this. Corrected in `SPEC-05` §4a, `docs/GETTING_STARTED.md` §8a, `setup.sh` §7c and `mcp/mcp.json.example`. Source-file protection is now documented as a DuckDB **allow-list** — `allowed_paths` / `allowed_directories` set **before** `enable_external_access=false`, which keeps sources readable while blocking `COPY … TO` against them; the order is mandatory or startup fails. Verified on Linux and Windows
- `scripts/inspect_data_source.py` advertised `.tsv` support but routed it through the comma-delimited reader, so a tab-separated file parsed as a single column and every statistic - null %, unique %, key and date flags, model-role suggestion - was wrong. The delimiter is now selected per extension; `.txt` stays comma-delimited
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

### Changed
- Devcontainer Node.js pinned `20` → `22`. Node 20 still runs `powerbi-modeling-mcp`, but 22 is the floor the Skills CLI requires for the optional upstream DuckDB skill. Prerequisites in `README.md` and `docs/GETTING_STARTED.md` corrected from Node 18 to 22 — they were stale against the devcontainer's 20 as well
- `scripts/validate_repo.py` now requires `scripts/inspect_data_source.py` and `scripts/test_inspect_delimiter.py`. The profiler was previously shipped but unregistered, so deleting it would have passed validation

### Added
- Cross-platform pure-Python PBIR schema validator: `scripts/validate_pbir_schema.py`
- PBIR report & PBIP project generator: `scripts/scaffold_pbir.py` (CLI for creating multi-page PBIR folders with visual scaffolds)
- Tabular data profiling utility: `scripts/inspect_data_source.py` (for Excel/CSV/TSV source inspection and Star Schema role suggestions)
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
