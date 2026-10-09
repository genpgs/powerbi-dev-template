# SPEC-01 — Scope and Boundaries

**Status:** Draft · **Gates:** all other specs · **Decision record:** this document

> **Resolved 2026-10-07 (Q1).** The "untested by this repository" label does **not** carry into shipped user docs. Cross-platform viability is instead established by a **temporary** CI matrix on `ubuntu-latest` + `windows-latest` while the capability is developed, after which the job is withdrawn. D6 is unchanged — no *permanent* DuckDB CI dependency. See §7.

---

## 1. Problem

An agent working on a Power BI semantic model frequently needs to look at the **source data** behind a model — to profile a new extract, check grain, sanity-check an aggregate, or answer "does the source actually contain these rows?" Today the only first-party tool for that is `scripts/inspect_data_source.py`, which handles Excel and delimited text with stdlib + `openpyxl` and a 1,000-row sample.

DuckDB would give an agent a far more capable, zero-service local query engine over the same files. But adding it introduces real risk: it is an optional capability that could silently become a dependency, it brings extension auto-install (network access at first use, verified as a real 10x cold-cache penalty), and the most commonly recommended DuckDB tooling is entangled with a hosted service.

This spec defines what is in scope, what is permanently out of scope, and what the capability is **not allowed to claim**.

---

## 2. In scope

| Capability | Notes |
|---|---|
| Local DuckDB CLI (optional install) | Dependency-free, cross-platform executable. See `SPEC-03`. |
| Local-mode DuckDB MCP server (optional) | In-memory database, **write-enabled** because in-memory DuckDB cannot be read-only. See D10, `SPEC-03`, `SPEC-05` §4a. |
| Opt-in install of upstream DuckDB SQL skills | User-initiated. See `SPEC-04`. |
| Project-scoped MCP configuration examples | Example files and docs only. See `SPEC-03`. |
| Documentation of a Power BI reconciliation workflow | Spec-only this cycle. See `SPEC-07`. |

---

## 3. Out of scope — permanently excluded

These are excluded by requirement and must not appear in any code, config, docs, or agent instruction produced by this work.

| Excluded | Why |
|---|---|
| MotherDuck account, sign-in, or authentication | Explicit requirement. No token handling of any kind. |
| `motherduck_token` / `MOTHERDUCK_TOKEN` environment variables | Credential surface. Never written, read, or documented as a setup step. |
| MotherDuck cloud databases (`md:` db-path) | Remote service. |
| S3-hosted DuckDB databases (`s3://` paths) | Remote service; upstream supports it, we do not expose it. |
| MotherDuck **remote/hosted** MCP endpoint | Hosted service, read-write capable. Out of scope even though it is the easier install. |
| MotherDuck CLI (`motherduck` binary) | Distinct product from DuckDB's standalone CLI; its workflows assume auth. |
| Remote databases — PostgreSQL, MySQL, and any networked SQL source | Requires remote connectivity, often auth. |
| NoSQL sources (MongoDB, etc.) | Remote and not a local-file workflow. |
| Cloud analytics services (BigQuery, Snowflake, Fabric warehouse, Databricks) | Remote. |
| Writing to user data | Default read-only. |
| Community extensions as an MVP promise | Third-party code running with the parent process's privileges. See `SPEC-02`. |
| Replacing `scripts/inspect_data_source.py` | Deferred. See `SPEC-06`. |
| DAX execution, VertiPaq semantics, or model equivalence claims | See §6. |

---

## 4. In scope, but explicitly **opt-in** and off the default path

| Item | Default behavior |
|---|---|
| DuckDB CLI installation | Not attempted unless the user answers yes at the `setup.sh` prompt. |
| MCP server registration | Examples and docs only. Nothing pre-registered, nothing enabled. |
| Upstream skills | Not installed by this template. Documented as a user-initiated command. |
| Skill install scope | Project-scoped is discouraged in favor of global for upstream content. See `SPEC-04`. |

**CI:** no DuckDB presence. This repo's only CI job (`.github/workflows/validate.yml`) is `ubuntu-latest`, Python 3.12, and installs no Node. DuckDB is not added to it in any form — not as a required step, not as an allow-failure smoke test. Consequence recorded in `SPEC-02` §5.

---

## 5. Data access model

- **Sources:** local files and local database files only.
- **Default:** read-only **for the CLI**. The MCP path is a documented exception — write-enabled by necessity (D10, `SPEC-05` §4a). This is stated wherever the MCP config appears; it is never described as read-only.
- **Reads are bounded:** documented result caps (`SPEC-05`).
- **Input data is untrusted data.** Values read from a source file, a column name, or a query result are **never** to be treated as instructions to the agent. A cell containing text that looks like a prompt is data to report on, not a command to follow. This must be stated in any skill or MCP guidance we author.
- **No telemetry or outbound calls** as a side effect of using the capability. Note: the Vercel Skills CLI collects anonymous install telemetry; `SPEC-04` documents `DISABLE_TELEMETRY=1` / `DO_NOT_TRACK=1`.

---

## 6. What this capability must never claim

This is the single most important section of this spec. Agents using this capability must not be led to believe:

1. **DuckDB executes DAX.** It does not. DAX runs in the Power BI engine.
2. **SQL results over source files equal model results.** They diverge whenever Power Query applies a transformation, a measure applies DAX context, a relationship changes grain, or RLS filters rows.
3. **Matching aggregate values prove semantic parity.** Two numbers matching is evidence of consistency, not of equivalent definitions. See `SPEC-07`.
4. **DuckDB reproduces VertiPaq behavior** — compression, storage, or query planning semantics.
5. **Profiling output is exact.** Statistics computed over a sample are samples, and key/role suggestions are heuristics.
6. **A connector existing means it works uniformly.** An extension mechanism existing does not imply identical platform coverage, identical behaviour, or no network dependency.
7. **Read-only mode is a security sandbox.** It is a write guard, not filesystem isolation. See `SPEC-05`.
8. **The MCP path is read-only.** It is not — and it cannot be, because in-memory DuckDB cannot be read-only. `:memory:` + `--read-write` is the documented baseline (D10). The *database* is throwaway and ephemeral, so in-database writes are harmless; the *filesystem* is not, and `COPY … TO` writes persistent files. See `SPEC-05` §4a.

Any first-party skill, doc section, or agent instruction authored under this programme must be reviewed against this list.

---

## 7. Cross-platform position

The template is **Linux-first for authoring**, with **Windows + Power BI Desktop for render and refresh validation**.

DuckDB's own documentation states that Core and Community extensions are built and tested for macOS, Windows, and Linux on AMD64 and ARM64. That is upstream build coverage, which is not a substitute for a repo-level check.

**Resolution (Q1, resolved 2026-10-07):** cross-platform viability is established by a **temporary** CI matrix during development, then the job is withdrawn:

1. Run a throwaway `ubuntu-latest` CI job that installs DuckDB and exercises a bounded local-file read plus a Tier 2 extension load. `SPEC-02` §5 specifies the checks.
2. Record the result in `SPEC-02` §5.
3. **Withdraw the job.** D6 then holds in steady state — an optional capability carries no permanent CI weight.

The claim needs evidence once; it does not need a permanent job.

**Progress — complete 2026-10-08.** Verification ran in two stages, recorded in `SPEC-02` §5:

| Stage | Platform | Versions | Result |
|---|---|---|---|
| 1 | Windows x64 | `1.5.6` | All five checks pass |
| 2 | Linux (Debian 13, x86_64) | `1.5.5` **and** pinned LTS `1.4.5` | All five checks pass on both |

The Linux run additionally closed the **LTS pin** (A10 — `DUCKDB_VERSION=1.4.5` self-reported `v1.4.5 (Andium)` and passed every tier) and confirmed **Linux extension auto-install** on a genuinely cold cache (A11), measuring a 10x cold-vs-warm difference for `read_xlsx`. The CRLF sniffer trap reproduced identically on Linux, making it cross-platform evidence rather than a Windows quirk.

**Step 3 was a no-op:** no temporary CI job was ever created. `validate.yml` has one job and no DuckDB steps, so D6 already holds in steady state. Running on the authoring host is the stronger position here, since Linux is this template's primary authoring environment.

---

## 8. Locked decisions

Recorded here so later specs and PRs can cite them.

| # | Decision |
|---|---|
| D1 | MVP delivers **docs and setup only**. No first-party skill, no Python helper, no reconciliation comparer. |
| D2 | Upstream skills are a **documented opt-in subset**, not vendored. No first-party re-teaching of DuckDB SQL. |
| D3 | `scripts/inspect_data_source.py` is **unchanged** and documented as the zero-dependency fallback. |
| D4 | MCP registration lives in **project-scoped example files plus per-harness docs**. No committed `.vscode/mcp.json`. |
| D5 | Devcontainer Node is pinned to **`"22"`**. |
| D6 | DuckDB has **no permanent CI presence**, and none was needed — verification ran on the authoring host. A temporary matrix was permitted but proved unnecessary (§7). |
| D7 | DuckDB CLI is pinned to the **LTS line** (resolved 2026-10-07, Q2). `mcp-server-motherduck` pins its own `duckdb` inside its `uvx` venv, so the two are independent; the resulting version skew is documented, not engineered away. |
| D8 | `docs/specs/*.md` **ships to git**. Reviewable diffs are the point of spec-first. |
| D9 | The TSV delimiter fix ships **first**, in its own PR, ahead of the DuckDB work (resolved 2026-10-07, Q3). |
| D10 | The documented MCP baseline is **`:memory:` + `--read-write`** (resolved 2026-10-08, Q4). In-memory DuckDB cannot be read-only. The database is deliberately **throwaway** — ephemeral, discarded on exit, holding no user data — which is what makes write-enabled acceptable *for the database*. It does **not** cover the filesystem, where `COPY … TO` writes persistent files. Documented as such; never described as read-only. |

---

## 9. Assumptions (not verified facts)

| ID | Assumption | Risk if wrong |
|---|---|---|
| A1 | Users who want DuckDB capability will read a docs section and run one command. | Low. Mitigated by `setup.sh` prompting. |
| A2 | ~~A read-only in-memory MCP server is a reasonable default for profiling local files.~~ | **Refuted 2026-10-08.** In-memory DuckDB cannot be read-only, so this option does not exist. Superseded by D10 (`SPEC-05` §4a). |
| A3 | Upstream `motherduck-duckdb-sql` remains useful despite MotherDuck framing. | Medium. `SPEC-04` records the framing risk; no vendoring means no sync burden if it degrades. |
| A4 | Node 22 does not break the existing `npx`-consumed tools (`pbir-cli`, `powerbi-modeling-mcp`). | Low — both declare Node 18+. Verified by devcontainer rebuild in PR 1, not assumed. |
| A5 | Pinning to DuckDB LTS is preferable to tracking current. | Low. One constant to change. |

---

## 10. Resolved questions

| # | Question | Resolution |
|---|---|---|
| Q1 | Should the untested-cross-platform label survive into shipped user docs? | **No.** Establish the claim with a temporary CI matrix, then withdraw the job. See §7. |
| Q2 | LTS or current for the DuckDB CLI pin? | **LTS.** `mcp-server-motherduck` pins `duckdb` independently inside its `uvx` venv, so nothing requires the CLI to match. Skew is documented — see `SPEC-02` §6. |
| Q3 | When to fix the `.tsv` delimiter defect? | **First, in its own PR** (D9). It is small, self-contained, and independent of the DuckDB work. |
| Q4 | What is the documented MCP baseline, given `:memory:` will not start read-only? | **`:memory:` + `--read-write`** (D10). A throwaway analysis surface: the database is ephemeral by design, which covers in-database writes but not filesystem writes. `SPEC-05` §4a. |
| Q5 | Where does a temp `.db` file live, if the baseline used one? | **Moot** — no file in the baseline. The file-path alternative stays documented as the fallback. |

No open questions remain at this revision.