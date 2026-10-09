# SPEC-03 — Tooling Surface Selection

**Status:** Draft · **Gates:** implementation PRs 2–4 · **Depends on:** `SPEC-01`

---

## 1. Purpose

Three candidate tooling surfaces exist. They are routinely conflated, and the conflation is the main documentation hazard in this work. This spec assigns each a distinct role, records what it is not, and fixes the language used to describe it.

---

## 2. The three-step distinction

This is the single most-repeated point in the plan document and the most likely source of user error. It must be stated in exactly these three steps, every time.

| Step | What it means | DuckDB example |
|---|---|---|
| **1. Install** | A binary or package exists on the machine. | `duckdb --version` returns. |
| **2. Register** | The agent harness is configured to launch that program as an MCP server. | An entry exists in `opencode.json` / `.mcp.json` / `.vscode/mcp.json`. |
| **3. Enable** | The harness actually loads it and exposes its tools to the model. | The user approves it; it is not disabled. |

**A successful install implies neither registration nor enablement.** A user with DuckDB correctly installed and no MCP entry has, from the agent's perspective, no DuckDB capability. Docs must never use "set up DuckDB" to mean steps 1–3 collectively.

---

## 3. Surface A — DuckDB CLI

**What it is:** a single dependency-free executable, precompiled for Windows, macOS, and Linux.

**Role:** shell-based analysis, scripted pipelines, CI-style automation, and agent work that benefits from an explicit result file rather than tool-call output.

**Why keep it separate from MCP:** CLI results redirect to a file and are therefore not injected into model context in bulk. That is a real safety property for large result sets, and it is the reason the upstream `motherduck-cli` skill recommends the CLI for exactly this reason class.

**What it is not:** not registered with any harness; not an MCP server; not required by any other surface here.

**Version policy:** pinned explicit constant, LTS default. See `SPEC-02` §6.

---

## 4. Surface B — Local-mode DuckDB MCP server

**What it is:** `motherduckdb/mcp-server-motherduck`, MIT-licensed, installable from PyPI, launched via `uvx`.

**Upstream defaults (verified):**

| Flag | Default | Our position |
|---|---|---|
| `--db-path` | `:memory:` | **Keep** — no file artifact. **But `:memory:` now requires `--read-write`** (verified 2026-10-08, `SPEC-02` §6a), so it cannot be paired with a read-only posture. |
| `--read-write` | `false` | **Set it, despite the default.** Required to start `:memory:`. Upstream states in-memory databases are always writable — a DuckDB limitation, not a misconfiguration. See `SPEC-05` §4a for the cost. |
| `--allow-switch-databases` | `false` | **Never set it.** It would expose `switch_database_connection`, enabling attachment of remote or MotherDuck paths — directly violating `SPEC-01` §3. This flag is now the *only* thing preventing remote attachment. |
| `--max-rows` | `1024` | **Keep**, and document. Re-confirmed in `1.1.0`. |
| `--max-chars` | `50000` | **Keep**, and document. Re-confirmed in `1.1.0`. |
| `--query-timeout` | `-1` (disabled) | **Set a finite value.** `-1` means an unbounded query can run. Re-confirmed as `-1` in `1.1.0`, so the finite value is load-bearing, not cosmetic. |
| `--init-sql` | none | **The only real security lever** now that `--read-write` is on. See `SPEC-05` §4a. |
| `--transport` | `stdio` | Keep. HTTP transport is for self-hosted server deployment, which is out of scope. |

All flags above were re-verified against upstream `1.1.0` on 2026-10-08: none has been removed or renamed. The breakage is behavioural, not a flag rename.

**Tool surface (upstream, `1.1.0`):** `execute_query`, `list_databases`, `list_tables`, `list_columns`. `switch_database_connection` is gated behind `--allow-switch-databases`, which we never set — so four tools, confirmed by `tools/list` on 2026-10-08.

**`execute_query` takes SQL in an `sql` argument, not `query`** (verified 2026-10-08). Passing `query` fails pydantic validation. This is the *inverse* of `mcp-server-motherduck`'s older documented examples, so an agent following them will fail.

**Excluded modes:** `--db-path md:` (MotherDuck), `--db-path s3://…`, `--motherduck-token`, `--motherduck-saas-mode`, `--motherduck-connection-parameters`, HTTP transport. None appear in our docs or configs.

**Known gaps, documented honestly:**

1. Upstream's own README states that **read-only mode alone is not sufficient** — it still allows local filesystem access and changing DuckDB settings. Our config narrows the surface; it does not eliminate it. See `SPEC-05`.
2. **The documented default is write-enabled.** `:memory:` cannot be read-only (`SPEC-02` §6a), so `--read-write` is mandatory and filesystem writes via SQL are possible. This is the single largest reduction in enforced safety in the programme, taken deliberately. See `SPEC-05` §4a.

**Verified end-to-end 2026-10-08:** the server was driven over stdio with a raw JSON-RPC handshake against a local `.db` file, reaching "Waiting for client connection" in read-only mode with **no MotherDuck credential present or requested**. A `select` returned `{"success": true, "rows": [[2, 200.5]], "rowCount": 1}`, matching the CLI on the same fixture. Read-only was **enforced, not merely advertised** — `CREATE TABLE` was rejected with "attached in read-only mode!".

---

## 5. Surface C — Upstream agent skills

**What it is:** `motherduckdb/agent-skills`, MIT-licensed, 22 skills, installable via the Vercel Skills CLI (`npx -y skills add …`, requires Node ≥ 22.20), Claude Code / GitHub Copilot CLI plugins, or manual directory copy.

**Role:** optional, user-installed DuckDB SQL reference. Explicitly **not** a first-party dependency and **not** vendored. See `SPEC-04` for the installation spec and the local-usable subset.

**What it is not:** not configured by this template; not a connection; upstream states plainly that installing skills does not configure a connection or MCP server.

---

## 6. Selection decision

| Surface | In MVP? | Form |
|---|---|---|
| DuckDB CLI | Yes | Optional install via `setup.sh` prompt. |
| Local DuckDB MCP server | Yes | Example config + per-harness registration docs. Never auto-enabled. |
| Upstream skills | Yes, opt-in | Documented user-initiated install. |
| MotherDuck CLI | **No** | Different product; auth-dependent. |
| MotherDuck remote MCP | **No** | Hosted service. |
| First-party DuckDB skill | **No** | `SPEC-01` D1. Deferred to a future spec. |

**Why no first-party skill in the MVP.** A first-party skill would need to teach DuckDB SQL — duplicating upstream — or route between CLI and MCP, which is a few lines of guidance in `GETTING_STARTED.md`. Writing one now would front-run the evidence that consolidation actually helps, which is what `SPEC-06` and `SPEC-07` exist to gather. Revisit once a real workflow has been observed.

---

## 7. Relationship to existing surfaces

| Existing | Interaction |
|---|---|
| `mcp/mcp.json.example` (`powerbi-modeling-mcp`) | DuckDB is added as a **sibling key**. The existing entry is untouched. The file's `_locations` map gains an `opencode.json` row. |
| `.agents/skills/` (first-party canonical) | Untouched in the MVP. See `SPEC-04` §5 for the install-collision risk. |
| `docs/GETTING_STARTED.md:353` (`etl` plugin: Spark/Livy/lakehouse, mentions DuckDB) | **Stays external and stays separate.** Add one clarifying row so users do not mistake it for the first-party local path. Do not attempt consolidation. |
| `scripts/inspect_data_source.py` | Unchanged. Documented as the zero-dependency fallback. See `SPEC-06`. |
| `scripts/validate_repo.py` | Touched **only if** implementation adds repo-owned files outside `mcp/` and existing files. See `SPEC-08` §4. |

---

## 8. Assumptions

| ID | Assumption | Risk if wrong |
|---|---|---|
| A9 | `uvx` is a reasonable launch mechanism, given `setup.sh` already installs `uv`. | Low — verified in both setup scripts. |
| A10 | A finite `--query-timeout` default is tolerable for profiling. | Low — a generous default is configurable. |
| A11 | `mcp-server-motherduck` continues to default to `:memory:` and read-only. | **Refuted 2026-10-08.** Upstream is at `1.1.0` and refuses to start `:memory:` without `--read-write`. The version facts in this table must be re-checked per release, not trusted from this document. The mitigation — pinning every flag explicitly — remains correct and is why the breakage was found by inspection rather than silently inherited. |