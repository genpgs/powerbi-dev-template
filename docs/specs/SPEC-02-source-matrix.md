# SPEC-02 — Source and Format Support Matrix

**Status:** Draft · **Depends on:** `SPEC-01`

---

## 1. Purpose

Define exactly which local sources this capability may claim to handle, at what tier, and with what caveats. The plan document's central warning applies: **support is not one uniform tier.** CSV and XML are not peers. An extension existing is not the same as a format being a supported first-class path.

Every row below is a **claim the user-facing docs are permitted to make**. Anything not in this table is undocumented, and `SPEC-01` §3 applies.

---

## 2. Support tiers

### Tier 1 — Built-in readers, no extension

| Source | Reader | Notes |
|---|---|---|
| CSV | `read_csv` / `read_csv_auto` | Direct reader. Type sniffing and schema available. |
| TSV | `read_csv` with delimiter | Same reader. |
| Parquet | `read_parquet` | Direct reader. Native schema, no inference needed. |

These are the only sources we may present as working with no installation and no first-use network fetch.

### Tier 2 — Official extension, auto-loaded or installable

| Source | Extension | Tier | Notes |
|---|---|---|---|
| JSON / NDJSON | `json` | Official core | Shipped with most DuckDB distributions and auto-loaded on first use. |
| Excel `.xlsx` / `.xlsm` | `excel` | Official core | **Reads and writes `.xlsx`. Does not support legacy `.xls`.** |
| SQLite file | `sqlite` | Official core | Local file attach. Candidate, see §4. |

**Network caveat:** DuckDB's extension auto-install means a **first-use network download** for any extension not already cached in the environment. This is true even for "official core" extensions. Docs must state that offline environments need the extension pre-installed; this is a first-use cost, not a setup cost.

### Tier 3 — Deferred, requires trust review

| Source | Extension | Status |
|---|---|---|
| XML / HTML | `webbed` (community) | **Deferred.** Not an MVP promise. |

`webbed` is a **community** extension: third-party code running with the privileges of the DuckDB process. DuckDB's own security documentation states extensions carry the permissions of the parent process. Presenting XML as a supported format would overstate the position.

**Rule:** no Tier 3 source appears in the MVP docs. If it is later promoted, it requires an explicit trust review, a pinned version, and documented approval.

---

## 3. Explicitly unsupported

| Source | Reason |
|---|---|
| Legacy `.xls` | Not supported by the `excel` extension. Say so plainly — users will ask. |
| Remote PostgreSQL / MySQL / any networked SQL | Out of scope. Remote connectivity, frequently auth. |
| S3, GCS, Azure Blob | Remote. |
| Cloud warehouses (BigQuery, Snowflake, Fabric, Databricks) | Remote. |
| NoSQL sources | Remote, and not a local-file workflow. |
| MotherDuck (`md:`) | Out of scope by requirement. See `SPEC-01` §3. |

---

## 4. Local database files — evaluation only

A local SQLite file is the only database candidate worth evaluating. It is a local file, it needs no server, and it is a realistic shape for a source extract in this template's domain.

It is **Tier 2 pending evaluation**, not promised. Promoting it requires: a documented attach procedure, a read-only statement, a demonstrated round-trip against a fixture, and confirmation that the `sqlite` extension behaves identically on the supported platforms. `SPEC-08` §6 holds the gate.

---

## 5. Platform matrix and its honest status

Upstream states that **Core and Community extensions are built and tested for macOS, Windows, and Linux, on AMD64 and ARM64.**

**Per `SPEC-01` §7 (Q1, resolved), this claim is verified before the docs ship.** Verification has two stages; see the results table below.

### Verification results

**Stage 1 — Windows, verified 2026-10-07.** DuckDB CLI `v1.5.6` (Variegata), Windows x64, exercised directly against purpose-built fixtures:

| Tier | Check | Result |
|---|---|---|
| CLI | `duckdb --version`, `select 1` | **Pass** |
| 1 | `read_csv_auto` over a local CSV | **Pass** — 2 rows, sum 200.5 |
| 2 | `read_json_auto` over a local JSON array | **Pass** — extension auto-loaded |
| 2 | `attach … (type sqlite)` on a local `.db` | **Pass** |
| 2 | `read_xlsx` over a local `.xlsx` | **Pass** — extension auto-loaded |

Two findings from this stage, both worth carrying forward:

1. **Extension auto-install did not visibly block.** `json`, `excel`, and `sqlite` loaded without an explicit `INSTALL` step. It is still a network operation on a cold cache, so the §2 caveat stands.
2. **The CSV sniffer is strict about a trailing malformed line.** A fixture written by PowerShell `Set-Content` ended `\n\r\n` (a stray CRLF appended after the final newline) and `read_csv_auto` **failed outright** with "It was not possible to automatically detect the CSV parsing dialect" — even with `delim=','` supplied explicitly. The same content with clean LF endings read correctly.

   Finding 2 is a genuine usability trap: the failure message points at delimiters and quoting, neither of which is wrong. Any docs sample that shows a CSV read should use LF line endings, and the troubleshooting note should name trailing whitespace as a cause.

**Stage 2 — Linux, verified 2026-10-08.** Run directly on the authoring host (Debian 13, `x86_64`, kernel 7.0.9) rather than through a temporary CI matrix — see "CI note" below. Two DuckDB versions were exercised against the *same* fixtures: the host CLI `v1.5.5` (Variegata, `/home/dev/.local/bin/duckdb`) and a clean-room install of the pinned LTS `v1.4.5` (Andium).

| Tier | Check | Result (`1.5.5`) | Result (LTS `1.4.5`) |
|---|---|---|---|
| CLI | `duckdb --version`, `select 1` | **Pass** | **Pass** |
| 1 | `read_csv_auto` over a local CSV | **Pass** — 2 rows, sum 200.5 | **Pass** — 2 rows, sum 200.5 |
| 1 | `read_parquet` over a locally written Parquet file | **Pass** — round-trip write + read | **Pass** — round-trip write + read |
| 2 | `read_json_auto` over local NDJSON | **Pass** — extension already cached | **Pass** — **no extension fetch needed** |
| 2 | `attach … (type sqlite)` on a local `.db` | **Pass** — extension auto-fetched | **Pass** — extension auto-fetched |
| 2 | `read_xlsx` over a local `.xlsx` | **Pass** — extension auto-fetched | **Pass** — extension auto-fetched |

Three findings from this stage, all of which change or sharpen what the specs currently claim:

1. **The §2 network caveat is confirmed, and it was observed on a genuinely cold cache.** `excel` and `sqlite` were absent from `~/.duckdb/extensions/v1.5.5/linux_amd64/` before the run. Both loaded automatically on first use, downloading `excel.duckdb_extension` and `sqlite_scanner.duckdb_extension` into the cache. The effect is measurable: the cold `read_xlsx` took **1.089s**, the identical warm read took **0.107s** — a 10x difference attributable solely to the first-use fetch. A11 is therefore **resolved in the affirmative**: Linux behaves as Windows did. An offline Linux runner would fail here where a cached one succeeds, so the offline caveat is real and not theoretical.

2. **JSON is the one Tier 2 source that needed no fetch on a cold cache — on LTS.** The `1.4.5` install had an empty extension cache, and `read_json_auto` succeeded without downloading anything: `json` is linked into the `1.4.5` CLI binary rather than shipped as a loadable extension. This refines §2's row for JSON. The general caveat still stands for `excel` and `sqlite` on both versions, and it stands for JSON on `1.5.5`, where `json` *was* present as a loadable extension. Docs should describe JSON's offline behaviour as version-dependent rather than promising it.

3. **The CRLF sniffer trap reproduces identically on Linux, with the same misleading message.** A fixture ending `\n\r\n` fails `read_csv_auto` with "It was not possible to automatically detect the CSV parsing dialect", enumerating delimiter and quote candidates — **even with `delim=','` passed explicitly**, which failed with the same error. The byte-level `od -c` check confirmed the clean fixture ended in a single `\n` and read correctly. This is now cross-platform evidence, not a Windows quirk, and the troubleshooting note in §5's stage-1 finding 2 should be written as platform-independent. Fixtures must be written with `printf` or Python, never a shell redirection that appends CRLF.

**LTS pin (A10) — now proven.** Open item A asked whether the documented `curl https://install.duckdb.org | DUCKDB_VERSION=1.4.5 bash` path actually yields the pinned version. It does. Installed into an isolated `HOME` to avoid disturbing the host CLI, it reported exactly `v1.4.5 (Andium) f31be57c18`, and it passed all five source-tier checks above. **The stage-1 Windows results were obtained on `1.5.6` and do not transfer; these LTS results do.** A10 is resolved, and PR 2 no longer needs to carry this as an open risk — it still needs its own smoke check at the version constant it actually ships.

**CI note — there is no matrix job to withdraw.** `SPEC-01` §7 step 3 and the runbook both describe withdrawing a temporary `ubuntu-latest` matrix job after evidence is recorded. **No such job exists.** `.github/workflows/validate.yml` has exactly one job, `validate`, on `ubuntu-latest`, and it contains no DuckDB steps at all. The Linux evidence was therefore gathered on the authoring host, which is the stronger position for this template since Linux is its primary authoring environment. Nothing needs removing; the withdrawal step is simply a no-op, and D6 (an optional capability carries no permanent CI weight) already holds in steady state.

| Platform | Role in this template | DuckDB status |
|---|---|---|
| Windows | Power BI Desktop render/refresh validation; most end users | **Verified** — stage 1 (`1.5.6`), all five checks pass |
| Linux | Primary authoring environment; CI runner | **Verified** — stage 2 (2026-10-08), all five checks pass on both `1.5.5` and pinned LTS `1.4.5` |
| macOS | Not a stated target | Upstream build coverage only. Not a repo target, so not tested — docs must not claim macOS support. |

A secondary, non-guaranteed caveat: upstream documents extension build coverage, not uniform availability across **every Python/runtime/tooling combination**. The `mcp-server-motherduck` package pins a specific `duckdb` version, so the MCP path and a standalone CLI install can be on different DuckDB versions. Docs should not imply they are interchangeable.

---

## 6. Version pinning, and a live discrepancy

**Verified at time of writing (2026-10):**

- DuckDB install page lists `1.5.6` as current, `1.4.5` as LTS, `2.0.0-dev` as preview.
- The DuckDB CLI documentation page states the latest stable CLI is `1.5.5`.
- `mcp-server-motherduck` `1.0.8` is the current PyPI release and pins `duckdb==1.5.5`.

**The two upstream pages disagree by one patch release.** Minor, but instructive: version numbers here move fast, and hard-coding a "latest" into docs guarantees staleness.

### Resolved: LTS pin, and the resulting version skew

Per `SPEC-01` D7 (Q2, resolved 2026-10-07): the CLI is pinned to the **LTS line**, with an explicit version constant rather than `latest` or `current`.

**Checked before deciding:** does the MCP server or any skill require a specific DuckDB version? No. `mcp-server-motherduck` pins `duckdb==1.5.5` **inside its own `uvx`-managed virtual environment**, entirely separate from any CLI installed on the host. The two are independent, so nothing forces the CLI to match, and **LTS is sufficient**.

**The consequence, which must be documented rather than hidden:** a user with the LTS CLI (1.4.5) and the MCP server (1.5.5) has **two DuckDB engine versions on one machine**. They can produce different results for the same query where behaviour changed between versions.

**Note from verification:** the CLI present on the development machine is `v1.5.6`, not the LTS line — it was already installed via `winget`. This is precisely the state `SPEC-02` §6 is written for, and it means **the LTS pin is not yet proven to install correctly**; the stage-1 results in §5 were obtained on 1.5.6. When the installer is built, its LTS path needs its own smoke check rather than inheriting these results.

Docs must therefore state that:
- The CLI and the MCP server may run different DuckDB versions.
- Results should not be compared across the two surfaces without noting the versions.
- `duckdb --version` and the MCP server's own version report are the authoritative record for a given surface.

**Alternative considered and rejected:** pinning the CLI to `1.5.5` to match the MCP server would remove the skew, but it ties a template's CLI install to another project's release cadence and would need revisiting on every MCP server patch. The skew is cheaper to document than to couple.

### Update, 2026-10-08: both upstream version claims above are now stale

Verified on Linux by inspecting the `uvx`-resolved environment:

| Claim in §6 | Was | **Actually** (2026-10-08) |
|---|---|---|
| `mcp-server-motherduck` current PyPI release | `1.0.8` | **`1.1.0`** |
| Its pinned `duckdb` | `duckdb==1.5.5` | **`duckdb==1.5.6`** |

The server also self-reports its version and mode at startup: `MotherDuck MCP Server v1.1.0 … Database mode: read-only … Query result limits: 1024 rows, 50,000 characters`.

This strengthens §6's existing argument rather than weakening it: the skew is not hypothetical, it has already moved, and it moved on **both** surfaces at once. The `1.5.5` CLI pin considered and rejected above would have tracked the MCP server exactly once already. It also means `SPEC-05` §4's warning about upstream changing defaults between `v0.x` and `v1.0` is not a historical caution — it is the normal release cadence of an actively developed `1.x` package. Every flag in the documented config must stay explicit, and the version facts in this section must be re-checked rather than trusted from this document.

### §6a — the documented `:memory:` baseline does not start (verified 2026-10-08)

`SPEC-05` §4 and acceptance criterion 3.13 document this as the local MCP baseline:

```
uvx mcp-server-motherduck --db-path :memory: --query-timeout 30
```

**This command exits non-zero on `mcp-server-motherduck` `1.1.0`**, with no MotherDuck credential present and none requested:

```
Error: In-memory databases require the --read-write flag.
Options:
  - Add --read-write to allow writes (data won't persist anyway)
  - Use --db-path with a file path for read-only access to a DuckDB file
  - Use --db-path md: with a MotherDuck token for cloud database access
```

**The fix was rejected at the time and later reconsidered.** The original reasoning was that `--read-write` inverts the read-only contract `SPEC-05` §4 treated as load-bearing. An in-memory database cannot be read-only — upstream's own help text concedes "In-memory databases are always writable (DuckDB limitation)" — so `:memory:` and read-only are **mutually exclusive by design, not by misconfiguration**.

On review (2026-10-08, Q4) the reviewer accepted `--read-write` rather than abandoning the `:memory:` surface, trading enforced read-only for a documented write-enabled path with no disk artifact. The cost is recorded in `SPEC-05` §4a and the decision table below.

**Verified working alternative:** a **local DuckDB file path** starts cleanly with no credential of any kind, and was driven end-to-end over stdio with a raw JSON-RPC handshake:

```
uvx mcp-server-motherduck --db-path <path>.db --query-timeout 30
→ MotherDuck MCP Server v1.1.0 … Database mode: read-only … Waiting for client connection
```

- `tools/list` advertises four tools: `execute_query`, `list_databases`, `list_tables`, `list_columns`.
- **`execute_query` takes its SQL in an `sql` argument, not `query`.** Passing `query` fails pydantic validation (`Missing required argument [type=missing_argument … 'sql']` plus `Unexpected keyword argument … 'query'`). Note this is the *inverse* of `mcp-server-motherduck`'s older documented examples.
- `execute_query` with `sql: "select count(*) n, sum(amount) total from t"` returned `{"success": true, "rows": [[2, 200.5]], "rowCount": 1}` — matching the CLI result for the same fixture exactly.
- Read-only is **enforced, not merely advertised**: `CREATE TABLE zz (a int)` returned `Cannot execute statement of type "CREATE" on database "mcp" which is attached in read-only mode!`.

**Consequences for the specs — now resolved, recorded here so the reasoning survives:**

1. `SPEC-05` §4's baseline encoded an invocation that **does not start**. Corrected in place; `SPEC-05` §4a states the cost.
2. The baseline points at `:memory:` **with `--read-write`** rather than a file path. See the decision table below.
3. A temp-file path was considered and **not adopted**, so no lifecycle decision is needed. The file-path mode stays documented as the fallback.
4. `SPEC-02` §2's framing of the MCP surface no longer promises `:memory:` implies read-only.
5. The credential check is now made **positively** — assert the server reaches "Waiting for client connection", not that it exited. See `SPEC-08` 3.13a. As originally worded the criterion was satisfiable by a command that died for an unrelated reason first, and would have passed against this broken config.
6. The `execute_query` `sql`-vs-`query` finding is carried into `SPEC-03` §4 and `SPEC-05` §8 as a documentation requirement.

### Decision: `:memory:` + `--read-write` (reviewer, 2026-10-08)

**Chosen:** keep `:memory:` as the documented baseline and set `--read-write`. No file path in the baseline.

Rationale and the alternatives considered:

| Option | Verdict |
|---|---|
| **`:memory:` + `--read-write`** | **Chosen.** The database is throwaway — created on start, discarded on exit, holding no user data — so in-database writes cannot damage anything. No disk artifact, no lifecycle to manage. The filesystem is the real exposure; `--init-sql` is the mitigation. `SPEC-05` §4a. |
| Local `.db` file, OS temp dir | Verified working and genuinely read-only, but writes a **durable** artifact needing create/reuse/delete/cleanup-on-crash handling. Against an ephemeral scratch surface, a file with a lifecycle is the larger ongoing risk. Remains the documented fallback for anyone needing true read-only. |
| Local `.db` file, repo-local | Rejected — would need a new `.gitignore` rule and risks committing a binary. |
| Both, file as default | Rejected as unnecessary complexity for an optional capability. |
| Drop MCP from the MVP | Rejected — the surface is verified working and useful. |

**Why "throwaway" is the right instinct here, stated carefully:** for exploratory profiling there is no state worth preserving, so discarding it costs nothing and removes cleanup obligations entirely. That reasoning is sound for the database. It does **not** extend to the filesystem, where `COPY … TO` produces files that outlive the session. Both halves are recorded in `SPEC-05` §4a so the second is not lost behind the first.

Consequences, recorded so no later reader mistakes this for a read-only default:

1. `SPEC-05` §4 and `SPEC-05` §4a hold the corrected baseline and its cost.
2. `SPEC-08` criterion 3.13 is rewritten as a **positive** assertion (see below).
3. The credential check must assert the server **reaches** "Waiting for client connection", not merely that it exited. As originally written it passed against a broken config.
4. `SPEC-05` §5's blanket write prohibition is narrowed to filesystem writes specifically; in-memory writes are ephemeral.
5. `--allow-switch-databases` is now the **only** flag preventing remote or MotherDuck attachment, so it is more load-bearing than before.
6. Users who "tighten" the config by removing `--read-write` will break it — the docs must say so.

### Other MCP flags confirmed current (2026-10-08)

All flags in the `SPEC-05` §4 baseline still exist upstream in `1.1.0`, with the defaults the spec describes: `--max-rows` (1024), `--max-chars` (50000), `--query-timeout` (**`-1`**, i.e. disabled — the finite value is therefore load-bearing, not cosmetic), `--read-write` (off), `--allow-switch-databases` (off), `--ephemeral-connections`, `--home-dir`, `--init-sql`, `--motherduck-token`, `--motherduck-saas-mode`, `--motherduck-connection-parameters`. `--db-path` still defaults to `:memory:`. No documented flag has been removed or renamed; the breakage is behavioural (see §6a), not a flag rename.

**Requirements on that constant:**
- It lives in one place in `setup.sh` and is documented as user-editable.
- It is **not** a floating tag. If upstream removes a build, the failure must be obvious, not silent.
- Any PR changing it must reconcile it against `mcp-server-motherduck`'s pin, or state that the two intentionally differ.

---

## 7. Docs requirements derived from this spec

The user-facing source-support table must:

1. Present Tier 1 as requiring nothing; Tier 2 as requiring a first-use extension download.
2. State the `.xls` limitation explicitly.
3. Omit XML, or list it as deferred with the community-extension trust note.
4. Claim **Linux and Windows only** (verified per §5). Do not mention macOS.
5. Not use "DuckDB supports X" phrasing where X is Tier 2 or 3. Prefer "reads X via the `excel` extension, downloaded on first use."
6. Not imply remote or cloud sources are reachable.
7. State the CLI/MCP version skew from §6 so a user comparing results across surfaces knows to record versions.

---

## 8. Assumptions

| ID | Assumption | Risk if wrong |
|---|---|---|
| A6 | Tier 1 readers are sufficient for the MVP's profiling use case. | Low — if insufficient, that is a Phase 2 decision, not a redesign. |
| A7 | First-use extension download is acceptable in connected dev environments, and users in offline environments will read the caveat. | Medium. Docs must be explicit; offline users otherwise get a confusing runtime error. |
| A8 | The `1.5.6` / `1.5.5` page discrepancy is transient rather than a stale-docs problem. | Low. The pinned constant makes this non-breaking either way. |
| A9 | The CLI/MCP version skew (§6) does not materially change results for profiling-sized queries. | Low — profiling queries are simple aggregates. Documented so a discrepancy is diagnosable. |
| A10 | The LTS install path works as documented. | **Verified 2026-10-08.** `DUCKDB_VERSION=1.4.5` installs and self-reports `v1.4.5 (Andium)`, and passes all five source tiers (§5 stage 2). PR 2 still needs a smoke check at whatever constant it ships. |
| A11 | Extension auto-install succeeds on the Linux path as it did on Windows (§5 stage 1). | **Verified 2026-10-08.** Confirmed on a genuinely cold cache: `excel` and `sqlite` auto-downloaded, 10x cold-vs-warm timing difference. Now **Low** — the behaviour is cross-platform, though the offline caveat is concrete rather than theoretical. |
| A12 | The local MCP server's documented `:memory:` config actually starts without credentials. | **Refuted 2026-10-08** — see §6a. The documented baseline in `SPEC-05` §4 **exits with an error**; in-memory mode now requires `--read-write`, contradicting the read-only contract. |