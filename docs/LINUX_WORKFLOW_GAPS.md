# Power BI Template — Linux Workflow Gaps & Pull Request Log

> **Context**: This document logs all workflow breakages, Linux-specific limitations, and recommended pull requests discovered while testing [`genpgs/powerbi-dev-template`](https://github.com/genpgs/powerbi-dev-template) on a headless Linux environment using the Microsoft AdventureWorks Sales sample dataset.

---

## 1. Executive Summary

The `powerbi-dev-template` repository aims to provide a **"Linux-first, agent-agnostic GitHub Template for AI-assisted Power BI development"**. 

During real-world end-to-end testing on Linux (Ubuntu / x86_64, Python 3.13, Node.js 20), we created a full project (`AdventureWorksSales.pbip` containing `AdventureWorksSales.SemanticModel` and `AdventureWorksSales.Report`), built an interactive HTML prototype (`report-prototype.html`), authored 6 TMDL tables, 11 DAX measures, 5 relationships, and 11 PBIR visuals across 2 report pages.

We identified **6 concrete breakages / gaps** that affect developers and automated agent harnesses running on Linux:

| Gap ID | Component | Severity | Description | Status & Fix |
|---|---|---|---|---|
| **GAP-01** | `powerbi-modeling-mcp` | **Blocker** | MCP server blocks all execution until human user accepts EULA (`accept_eula`). In headless agent runs, this causes immediate failure unless documented and automated. | **Documented & Fixed**: Add `accept_eula` docs & `PBI_MODELING_MCP_ACCEPT_EULA=true` flag. |
| **GAP-02** | `setup.sh` / `pbir-cli` | **Critical** | `pbir-cli` on PyPI **only publishes wheels for Windows and macOS ARM64** (`macosx_11_0_arm64`, `win_amd64`). There is no Linux wheel and no source distribution (`sdist`). `setup.sh` fails on Linux. | **Fixed in Repo**: Added Python PBIR validator fallback; patched `setup.sh` to guard platform. |
| **GAP-03** | Baseline TMDL Sample | **Critical** | `CalendarBaseline.SemanticModel/definition/expressions.tmdl` contains standalone C-style `//` comments at root level. Official Microsoft TMDL parsers fail with `InvalidLineType: Unexpected line type: Other!`. | **Fixed in Repo**: Removed top-level `//` comments in `expressions.tmdl` (TMDL allows `///` for descriptions or comments only inside indented M blocks). |
| **GAP-04** | `scripts/validate_repo.py` | **Medium** | Fails with `[FAIL] .env file found` if `.env` exists on disk (`check(not Path(".env").exists())`), directly contradicting `setup.sh` which copies `.env.example` -> `.env`. | **Fixed in Repo**: Changed check to verify `.env` is not tracked in git (`git ls-files .env`). |
| **GAP-05** | Validation Scope | **Medium** | `validate_repo.py`, `validate_date_table.py`, and `validate_pbir.sh` hardcode `samples/pbip-calendar-baseline/` instead of validating any `.pbip` project in the workspace. | **Fixed in Repo**: Scans all `*.pbip` projects across the repo dynamically. |
| **GAP-06** | Headless Linux Lifecycle | **Architecture** | Linux cannot execute Power BI Desktop GUI or refresh local M partitions into VertiPaq memory offline. | **Documented**: Clarified the code-first authoring vs rendering/refresh boundary. |

---

## 2. Detailed Technical Breakdown

### GAP-01: `powerbi-modeling-mcp` EULA Consent Requirement

- **Symptom**: Calling any tool on `powerbi-modeling-mcp` (e.g. `connection_operations`) returns:
  ```json
  {
    "message": "The Power BI Authoring MCP EULA must be accepted before using this tool. Review https://go.microsoft.com/fwlink/?LinkId=2381247, then call the accept_eula tool, pass --accept-eula (or --accepteula), or set PBI_MODELING_MCP_ACCEPT_EULA=true.",
    "operation": "connection_operations"
  }
  ```
- **Root Cause**: Microsoft's Power BI Authoring MCP requires legal EULA acknowledgement before tools become available. The MCP server checks an in-memory flag or environment variable.
- **Impact**: Autonomous agents or CI/CD pipelines fail at step 1 because `accept_eula` cannot be called speculatively without user approval.
- **Recommended Template PR**:
  1. In `mcp/mcp.json.example`, add the environment variable option:
     ```json
     "env": {
       "PBI_MODELING_MCP_ACCEPT_EULA": "true"
     }
     ```
  2. In `docs/GETTING_STARTED.md`, add a dedicated "EULA Acceptance" note explaining how to accept it via the CLI flag or MCP environment variable.

---

### GAP-02: `pbir-cli` Missing Linux Wheels on PyPI

- **Symptom**: Running `setup.sh` (or `uv tool install pbir-cli`) on Linux fails:
  ```
  error: No solution found when resolving dependencies
    cause: Because all of:
               pbir-cli<=0.9.21
               pbir-cli>=0.9.23
            have no wheels with a matching platform tag (e.g., manylinux_2_41_x86_64)
  hint: Wheels are available for `pbir-cli` (v0.9.32) on the following platforms: `macosx_11_0_arm64`, `win_amd64`
  ```
  And attempting to build from source (`--no-binary :all:`) fails with:
  ```
  error: Because all versions of pbir-cli have no source distribution and you require pbir-cli, we can conclude that your requirements are unsatisfiable.
  ```
- **Root Cause**: Upstream `pbir-cli` (closed-source binary distribution on PyPI) only distributes wheels for Windows AMD64 and macOS ARM64. It does not provide Linux x86_64 wheels or source distributions.
- **Impact**: Any Linux developer running `setup.sh` sees an installation error, and `validate_pbir.sh` unconditionally skips validation with `[SKIP] powerbi-report-author not installed`.
- **Recommended Template PR**:
  1. Patch `setup.sh` to check `uname -s` and inform Linux users without failing.
  2. Provide `scripts/validate_pbir_schema.py` (a pure Python JSON schema and structural validator for `*.Report/definition/` files) so Linux users and Linux GitHub Actions runners can validate PBIR syntax.
  3. Update `scripts/validate_pbir.sh` to fall back to `python3 scripts/validate_pbir_schema.py` when `powerbi-report-author` is not in `$PATH`.

---

### GAP-03: Invalid Comments in `expressions.tmdl`

- **Symptom**: When connecting `powerbi-modeling-mcp` to `CalendarBaseline.SemanticModel` or importing via Microsoft Tabular Model Definition Language (TMDL) parser:
  ```
  Failed to import TMDL folder: TMDL Format Error:
  	Parsing error type - InvalidLineType
  	Detailed error - Unexpected line type: Other!
  	Document - './expressions'
  	Line Number - 1
  	Line - '// expressions.tmdl — named M expressions for CalendarBaseline'
  ```
- **Root Cause**: In TMDL syntax specification:
  - Top-level declarations must be keywords like `database`, `model`, `table`, `column`, `measure`, `partition`, `expression`, or descriptions starting with `///`.
  - Double slash `//` comments are **only valid inside indented M code blocks** (e.g. under `source = let ...`).
  - Standalone `//` comments at column 0 in `expressions.tmdl` are invalid TMDL syntax and reject the entire model.
- **Impact**: The template's default sample (`CalendarBaseline`) cannot be loaded by `powerbi-modeling-mcp` or Tabular Editor!
- **Recommended Template PR**:
  Remove lines 1-4 from `samples/pbip-calendar-baseline/CalendarBaseline.SemanticModel/definition/expressions.tmdl` or prefix descriptions with `///`.

---

### GAP-04: `validate_repo.py` Incompatible with Local `.env`

- **Symptom**:
  1. Step 3 of `docs/GETTING_STARTED.md` instructs the user to configure `.env`.
  2. `setup.sh` automatically creates `.env` by running `cp .env.example .env`.
  3. Step 4 runs `python3 scripts/validate_repo.py`.
  4. Script fails with:
     ```
     [FAIL] .env file found — it must not be committed (add to .gitignore)
     ```
- **Root Cause**: `validate_repo.py` used `check(not Path(".env").exists())`. This checks whether the file exists on the developer's local filesystem, not whether it is tracked or committed in Git.
- **Impact**: Following the template's official Getting Started walkthrough immediately fails repo validation.
- **Recommended Template PR**:
  Check Git tracking instead of disk existence using `git ls-files --error-unmatch .env`.

---

### GAP-05: Validation Scripts Hardcode `samples/` Directory

- **Symptom**:
  - `scripts/validate_repo.py` only scanned `samples/*.pbip`.
  - `scripts/validate_date_table.py` only checked `samples/pbip-calendar-baseline/`.
  - `scripts/validate_pbir.sh` only checked `samples/`.
  When a developer creates their actual project (e.g. `AdventureWorksSales.pbip` at the repo root or in `src/`), the validation scripts completely ignore it.
- **Root Cause**: Hardcoded path `Path("samples")` instead of searching the repository.
- **Recommended Template PR**:
  Update all validation scripts to search `Path(".").rglob("*.pbip")` (excluding `.git`), or accept an optional path argument.

---

### GAP-06: Headless Linux Development Model & Boundaries

- **Reality of Power BI on Linux**:
  - **What works 100% natively on Linux**:
    - Full TMDL authoring (tables, columns, data categories, DAX measures, partitions, relationships).
    - Full PBIR authoring (report definitions, canvas pages, visual containers, layout grids, formatting).
    - Power Query M code writing and fiscal calendar generation (`fnCalendarWeekBased.m`).
    - Offline semantic model inspection & validation via `powerbi-modeling-mcp` (in memory).
    - Interactive HTML dashboard prototyping (Generative UI) to validate layouts, colors, and metrics before code generation.
    - Automated repo and schema validation in Python / Bash.
  - **What requires Windows + Power BI Desktop or Fabric Service**:
    - Executing local Power Query M queries against local files (`Excel.Workbook(File.Contents(...))`) to populate VertiPaq column data in cache.
    - Native visual rendering / screenshot capture via Power BI Desktop engine.
    - Direct `.pbip` desktop GUI interactivity.
- **Recommended Template PR**:
  Add an architecture section to `README.md` and `docs/GETTING_STARTED.md` clarifying this distinction so developers understand that Linux is the **code-first authoring, scripting, and CI/CD plane**, while Desktop/Fabric is the **data refresh and rendering plane**.

---

## 3. Pull Request Package Ready for Submission

We have prepared the exact code patches:

### PR 1: `fix(tmdl): remove invalid root-level comments from expressions.tmdl`
- **Files**: `samples/pbip-calendar-baseline/CalendarBaseline.SemanticModel/definition/expressions.tmdl`
- **Diff**:
  ```diff
  - // expressions.tmdl — named M expressions for CalendarBaseline
  - // Both fnCalendar (month-aligned) and fnCalendarWeekBased (week-anchored) are
  - // declared here so either can be referenced from the Calendar partition.
  - // Switch the Calendar partition source to the function that matches your pattern.
  - 
   expression fnCalendar =
  ```

### PR 2: `fix(validation): fix .env git-tracking check and support root PBIP projects`
- **Files**: `scripts/validate_repo.py`
- **Diff**:
  ```diff
  - check(
  -     not Path(".env").exists(),
  -     "[PASS] .env not committed",
  -     "[FAIL] .env file found — it must not be committed (add to .gitignore)",
  - )
  + import subprocess
  + is_tracked = subprocess.run(["git", "ls-files", "--error-unmatch", ".env"], capture_output=True).returncode == 0
  + check(
  +     not is_tracked,
  +     "[PASS] .env not committed or tracked in git",
  +     "[FAIL] .env file is tracked by git — remove it: git rm --cached .env",
  + )

  - for pbip in Path("samples").rglob("*.pbip"):
  + for pbip in Path(".").rglob("*.pbip"):
  +     if ".git" in str(pbip):
  +         continue
  ```

### PR 3: `feat(pbir): add Python PBIR schema validator fallback for Linux`
- **Files**: `scripts/validate_pbir_schema.py` (new), `scripts/validate_pbir.sh` (updated), `setup.sh` (updated)
- **Feature**: Provides cross-platform JSON validation of `report.json`, `pages.json`, `page.json`, and `visual.json` containers when `pbir-cli` is unavailable.

### PR 4: `docs(mcp): document accept_eula requirement and headless env variable`
- **Files**: `mcp/mcp.json.example`, `docs/GETTING_STARTED.md`
- **Feature**: Documents `PBI_MODELING_MCP_ACCEPT_EULA=true` and `accept_eula` tool usage.
