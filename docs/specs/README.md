# Specification Index — Local DuckDB Agent Capability

This directory holds the specifications for adding **local-only DuckDB** as an optional agent capability in `powerbi-dev-template` and repositories derived from it.

These are **specifications, not documentation**. Nothing here is implemented. Each spec states what would be built, why, and how we would know it is correct. Implementation proceeds phase by phase, gated on review of the relevant specs (see `SPEC-08`).

---

## Source plan

Derived from `duckdb-Feature-Addition-plan.md` (local planning document, intentionally gitignored at `.gitignore:21`). That file established the problem, the boundaries, and a first feasibility pass. This directory converts it into reviewable specs with stable IDs so implementation PRs can reference specific decisions.

## Implementation status

| Phase | Scope | Status |
|---|---|---|
| Phase 0 | Eight specs authored | **Done** |
| PR 0 | `.tsv` delimiter fix in `inspect_data_source.py` + regression test | **Done** (`SPEC-01` D9) |
| PR 1 | Devcontainer Node 20 → 22, stale Node 18 claims corrected | **Done** |
| Cross-platform verification | Windows + Linux, all documented source tiers | **Done** — Windows `1.5.6`; Linux `1.5.5` **and** LTS `1.4.5`. All five tiers pass on every version. `SPEC-02` §5 |
| MCP server verification | End-to-end stdio handshake, no credential | **Done** on Linux and Windows. Found a broken baseline (`SPEC-02` §6a) and a test-design flaw (`SPEC-08` 3.13) |
| PR 2 | Optional DuckDB CLI + local MCP installer | **Done** — `setup.sh` §7a / §7c |
| PR 3 | MCP example config + per-harness docs | **Done** — `mcp/mcp.json.example`, `GETTING_STARTED.md` §8a |
| PR 4 | Upstream skill install + onboarding docs | **Done** — `GETTING_STARTED.md` §8c |
| PR 5 | Validation, changelog, cross-references | **Done** — `validate_repo.py`, `CHANGELOG.md`, `README.md` |

**Verification passes.** Linux 2026-10-08, then Windows 2026-10-08 (`SPEC-08` §10). Full `setup.sh` runs end-to-end unattended (exit 0) on both, the shipped MCP config launches and answers queries with no MotherDuck credential, and all three findings are closed:

- **L1 — fixed, and hardened against false failure.** `.devcontainer/setup.sh` restored to LF; `validate_repo.py` now enforces LF + `bash -n` across all shell scripts, with a matching CI step. Proven by reintroducing CRLF and confirming the check fails. The parse half now distinguishes a genuine syntax error from a shell that cannot run on the host (e.g. the Windows WSL shim) and reports `[SKIP]` for the latter, so the validator does not cry wolf.
- **L2 — fixed.** The pre-commit prompt is now guarded with `[ ! -t 0 ]`, reusing the pattern already used for the DuckDB prompt. Interactive behaviour unchanged. Confirmed exit 0 unattended on Windows.
- **L3 — resolved.** Source-file protection is available and documented: `allowed_paths` / `allowed_directories`, set **before** `enable_external_access=false`, keep sources readable while blocking `COPY … TO` against them. Verified on **both** platforms — Windows checksum byte-identical after a blocked overwrite.

Still open: Windows behaviour of `install.duckdb.org` without `winget`. It needs a Windows environment with no DuckDB and no winget, which the dev host is not. Record it as untested rather than inferring it from the Linux result. See [`LINUX-VERIFICATION-HANDOFF.md`](LINUX-VERIFICATION-HANDOFF.md) §6.

**Decisions of note:**
- D7 — CLI pinned to the DuckDB **LTS** line. Proven working; `mcp-server-motherduck` pins its own version independently, and the resulting skew is documented.
- `:memory:` + `--read-write` is the documented MCP baseline, because in-memory DuckDB **cannot** be read-only. The path is therefore **write-enabled against the filesystem**, stated as such in `SPEC-05` §4a. No artifact may call it read-only.
- Source-file protection uses a DuckDB **allow-list**: `allowed_paths` / `allowed_directories` set **before** `enable_external_access=false`. Bare read-only blocks DDL/DML on the database but *not* `COPY … TO`; the allow-list is what makes sources non-amendable. Order is mandatory.
- The upstream DuckDB skill (`motherduck-duckdb-sql`) is documented in `docs/GETTING_STARTED.md` §8c and is **independent of the MCP server** — installing either does not install or register the other. Of the four upstream skills checked, it is the only one usable locally; `motherduck-query` and `motherduck-explore` declare a MotherDuck connection as a prerequisite, and `motherduck-cli` is the MotherDuck CLI, a different product that assumes authentication.

See `SPEC-08` for per-PR acceptance criteria and `SPEC-01` §8 for locked decisions D1–D9.

> **Cross-platform work in progress.** [`LINUX-VERIFICATION-HANDOFF.md`](LINUX-VERIFICATION-HANDOFF.md)
> is the single-file record for the Linux verification pass: what was proven, the findings, and the
> two Windows items still open. Start there if you are picking this up on Windows.

---

## Specs

| ID | Spec | Status |
|----|------|--------|
| `SPEC-01` | [Scope and boundaries](SPEC-01-scope-and-boundaries.md) | Reviewed · Q1/Q2/Q3 resolved |
| `SPEC-02` | [Source and format support matrix](SPEC-02-source-matrix.md) | Reviewed · cross-platform verified · §6a defect found |
| `SPEC-03` | [Tooling surface selection](SPEC-03-tooling-selection.md) | Reviewed · A11 refuted by upstream `1.1.0` |
| `SPEC-04` | [Upstream skill installation](SPEC-04-skill-installation.md) | Draft |
| `SPEC-05` | [Safety model](SPEC-05-safety-model.md) | Revised 2026-10-08 · baseline is now **write-enabled** |
| `SPEC-06` | [Disposition of `inspect_data_source.py`](SPEC-06-profiler-disposition.md) | Reviewed · TSV defect fixed (PR 0) |
| `SPEC-07` | [Power BI reconciliation boundaries](SPEC-07-reconciliation.md) | Draft — spec only |
| `SPEC-08` | [Acceptance criteria and gates](SPEC-08-acceptance-criteria.md) | Tracks per-PR status |

**Review order:** `SPEC-01` and `SPEC-03` gate everything else. The remaining specs can be reviewed in parallel once those two are settled.

---

## Ground rules

These apply to every spec in this directory.

1. **No MotherDuck authentication, ever.** No account, token, sign-in, `md:` database path, S3 connection, MotherDuck CLI workflow, or hosted MotherDuck MCP endpoint. Any change that needs one is a new spec, not an amendment.
2. **Local-only and read-only by default.** Local files and local database files only. No remote databases, no cloud analytics services.
3. **Optional, never required.** No spec may make DuckDB a prerequisite for `setup.sh`, the devcontainer, CI, or any validation script.
4. **Installing ≠ registering ≠ enabling.** These are three distinct steps and docs must never blur them.
5. **Local-only documentation.** Nothing writes global harness configuration (`~/.claude/`, `~/.copilot/`, `~/.config/opencode/`) on a user's behalf.
6. **Separate verified facts from assumptions.** Every claim is tagged. Unverified claims are written as risks, not findings.
7. **No silent data mutation.** Default read paths, bounded outputs, explicit consent for extension installs and writes.

---

## Relationship to existing repo capabilities

This capability is **additive**. It does not replace or modify:

- `scripts/inspect_data_source.py` — see `SPEC-06`
- `semantic-model-authoring` / `powerbi-report-cli` / `fabriciq` skills — model and report authoring stay with their existing owners
- `mcp/mcp.json.example` `powerbi-modeling-mcp` entry — see `SPEC-03`

The one interaction to be careful about is the external `etl` plugin (Spark / Livy / lakehouse, which also mentions DuckDB) documented at `docs/GETTING_STARTED.md:353`. `SPEC-03` records that it stays separate and undocumented as a first-party path.