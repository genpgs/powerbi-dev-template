# SPEC-08 — Acceptance Criteria and Gates

**Status:** Draft · **Depends on:** all

---

## 1. Phase 0 gate (specs)

Implementation PRs do not open until `SPEC-01` and `SPEC-03` are signed off. The remaining six may be reviewed in parallel and revised without blocking each other.

| # | Criterion | How verified |
|---|---|---|
| 0.1 | All eight specs exist under `docs/specs/` with a README index | Files present and linked |
| 0.2 | Every spec separates verified facts from assumptions | Assumption tables present |
| 0.3 | No spec requires MotherDuck authentication | Review against `SPEC-01` §3 |
| 0.4 | Every cross-spec claim is consistent (no contradictions on scope, subset, or version policy) | Cross-read |
| 0.5 | Cross-platform verification approach is specified (`SPEC-01` §7) — temporary matrix, then withdrawn | Text present |
| 0.6 | `SPEC-04` records the corrected single-skill subset with its evidence | Text present |
| 0.7 | `SPEC-06` records the `.tsv` defect and its fix | Text present |
| 0.8 | Open questions in each spec are answered or consciously deferred | Reviewer sign-off |

### Resolved 2026-10-07

### Resolved 2026-10-08 (Linux verification)

| Question | Resolution |
|---|---|
| Q4 — what is the documented MCP baseline, given `:memory:` will not start read-only? | **`:memory:` + `--read-write`.** Reviewer decision. See `SPEC-02` §6a decision table and `SPEC-05` §4a. Consequence: the documented path is write-enabled against the filesystem, stated as such. |
| Q5 — where does the temp file live? | **Moot.** No file in the baseline. The file-path alternative remains documented as the fallback. |
| Q1 — untested-cross-platform label in user docs? | **No.** Temporary CI matrix establishes the claim, then the job is withdrawn. `SPEC-01` §7. |
| Q2 — LTS or current for the DuckDB pin? | **LTS.** `mcp-server-motherduck` pins its own `duckdb` in its `uvx` venv, so nothing requires a match. The resulting CLI/MCP version skew is documented — `SPEC-02` §6. |
| Q3 — when to fix the `.tsv` defect? | **First, in its own PR** (D9). Done; see §1b. |

---

## 1b. PR 0 — TSV delimiter fix (SHIPPED FIRST)

`SPEC-01` D9. Independent of the DuckDB work; landed ahead of it so the documented TSV story is correct from the outset.

| # | Criterion | How verified | Status |
|---|---|---|---|
| 0.1 | `inspect_csv` accepts an explicit `delimiter`, defaulting to `","` | Code inspection | Met |
| 0.2 | Routing layer selects `"\t"` for `.tsv`, `","` for `.csv` / `.txt` | Code inspection | Met |
| 0.3 | `.txt` remains comma-delimited — no delimiter sniffing introduced | Test case present | Met |
| 0.4 | `scripts/test_inspect_delimiter.py` asserts column names, column count, and zero nulls for all three extensions | `python3 scripts/test_inspect_delimiter.py` → 3/3 PASS | Met |
| 0.5 | Test wired into `.github/workflows/validate.yml` | Workflow inspection | Met |
| 0.6 | Test follows the standalone-runner convention of `test_pbir_discovery.py` (no pytest dependency) | Code inspection | Met |
| 0.7 | Before/after verified on a real `.tsv` fixture | Before: `Columns: 1`. After: `Columns: 3`, correct names, 0% nulls | Met |
| 0.8 | Full validation suite still passes | §9 | Met |
| 0.9 | `CHANGELOG.md` records the fix | Text check | Met |
| 0.10 | The fix is **not** bundled with any DuckDB change | `git diff --stat` per commit | Met |

---

## 2. PR 1 — Devcontainer Node 20 → 22

| # | Criterion | How verified |
|---|---|---|
| 1.1 | `.devcontainer/devcontainer.json` node feature version is `"22"` | File inspection |
| 1.2 | Devcontainer builds and `node -v` reports 22.x | `devcontainer` rebuild |
| 1.3 | `npx -y skills --version` resolves inside the container | Command run |
| 1.4 | `docs/GETTING_STARTED.md:13` no longer claims Node 18 | Text check |
| 1.5 | `README.md` prerequisites no longer claim Node 18 | Text check |
| 1.6 | `mcp/mcp.json.example` `_notes` reflects Node 22 | Text check |
| 1.7 | Existing validators still pass | Full validation suite |
| 1.8 | `pbir-cli` and `powerbi-modeling-mcp` still launch under Node 22 | Smoke check — assumption A4 verified, not assumed |

---

## 3. PR 2 — Optional installer (SHIPPED)

| # | Criterion | How verified | Status |
|---|---|---|---|
| 2.1 | Prompt follows the existing `setup.sh` opt-in pattern; declining prints working manual commands and continues | Extracted §7a, ran with stdin closed | Met |
| 2.2 | Script exits 0 with DuckDB absent | `bash -n` clean; skip paths exit 0 | Met |
| 2.3 | Re-running is idempotent — no reinstall, no duplicate config | Existing `duckdb` is detected and reported, never replaced | Met |
| 2.3a | A **matching** version is reported distinctly from a mismatched one | Two runs with `DUCKDB_VERSION` at, then off, the installed version | Met — both branches verified |
| 2.4 | An existing `duckdb` on PATH is detected and reported, not reinstalled | Ran against installed `v1.5.6` | Met |
| 2.5 | Version is a pinned constant on the **LTS** line, user-editable, documented | `DUCKDB_VERSION="1.4.5"` at `setup.sh:25`, in a labelled config block | Met |
| 2.5a | The constant carries its rationale inline, not just a bare assignment | Comment block explains why pinning *is* the point | Met |
| 2.5b | Docs state the CLI/MCP DuckDB version skew | `setup.sh` §7c note; `SPEC-02` §6 | Met |
| 2.6 | `DUCKDB_SKIP_INSTALL=1` bypasses the network step | Verified | Met |
| 2.6a | Non-interactive stdin never prompts and never installs unasked | Verified — CI safety | Met |
| 2.7 | Every network step warns and never aborts the script | Install failure falls through to a printed manual command | Met |
| 2.8 | Linux and Windows path handling reviewed | `install.duckdb.org` path plus `$HOME/.local/bin` and `$HOME/.duckdb/bin` on PATH | Met |
| 2.9 | **MCP registration snippet is printed**, as a sibling of `powerbi-modeling-mcp`, and never written to any config | Verified — printed in §7c; grep confirms no harness config is touched | Met |
| 2.9a | The printed snippet states `--read-write` is **required**, not decorative | `setup.sh` §7c note | Met |
| 2.9b | The printed snippet warns that the flag also permits **filesystem** writes, and gives the file-path alternative for a read-only **database** | `setup.sh` §7c note | Met — **corrected 2026-10-08**, see L3 |
| 2.9c | The printed snippet states no MotherDuck account/token/sign-in is needed | `setup.sh` §7c note | Met |
| 2.9d | Install → register → enable is explained as three distinct steps | `setup.sh` §7c preamble | Met |
| 2.10 | No MotherDuck token, `md:` path, or S3 path appears in script or output | Grep over `setup.sh` — none found | Met |
| 2.11 | The MotherDuck CLI is not installed | Code review | Met |
| 2.12 | The devcontainer does not install DuckDB unasked | `.devcontainer/setup.sh` unchanged; non-interactive + skip guards make it unreachable there | Met |
| 2.13 | `scripts/inspect_data_source.py` remains the documented zero-dependency fallback | Stated in the §7a banner | Met |

**Verification note:** `setup.sh` cannot complete on this Windows host because the `WindowsApps` `python3` stub exits non-zero at §1. §7a was therefore extracted by line range and exercised directly under Git-for-Windows bash. The logic tested is the logic that ships. A full end-to-end run still needs a Linux or WSL environment.

---

## 4. PR 3 — MCP example + docs (SHIPPED)

| # | Criterion | How verified | Status |
|---|---|---|---|
| 3.1 | `mcp/mcp.json.example` gains a **sibling** `duckdb-local` entry; `powerbi-modeling-mcp` untouched | Diff inspection | Met |
| 3.2 | Config sets `--db-path :memory:` **and `--read-write`**, omits `--allow-switch-databases` | JSON parse | Met |
| 3.3 | A finite `--query-timeout` is set | JSON parse — upstream default `-1` | Met |
| 3.4 | Every flag is explicit — no reliance on upstream defaults | JSON parse | Met |
| 3.4a | Docs state the MCP path is **write-enabled against the filesystem**, and `:memory:` protects the database, not the filesystem | `GETTING_STARTED.md` §8a; `mcp.json.example` notes | Met |
| 3.4b | Docs warn that removing `--read-write` breaks the config | §8a and `_notes` | Met |
| 3.4c | Docs record that `execute_query` takes `sql`, not `query` | `_notes` | Met |
| 3.4d | Docs present the **throwaway** framing, with the filesystem limit stated separately | §8a bullets 2 and 3 | Met |
| 3.4e | Docs give the **file-path alternative** for a read-only **database** | §8a, `mcp.json.example` `_notes` | Met — **corrected 2026-10-08**, see L3 |
| 3.4f | Docs mention `--init-sql` as the available hardening lever | §8a, `_notes` | Met |
| 3.5 | `opencode.json` `_locations` row added | JSON parse — 6 locations now | Met |
| 3.5a | Claude **project** scope (`.mcp.json`) added, since `.claude/` is gitignored here | `_locations` | Met |
| 3.6 | Docs cover OpenCode, Claude, and Copilot registration | §8a + §8 | Met |
| 3.7 | Server ships `enabled: false` | JSON parse | Met |
| 3.8 | Copilot's `.vscode/mcp.json` documented as a **manual copy** — `.gitignore:13` ignores `.vscode/` | `CHANGELOG` records it; `_locations` marks the path | Met |
| 3.9 | Install → register → enable presented as three distinct steps | §8a "Three separate steps"; `_notes` | Met |
| 3.10 | Write-enabled reality stated wherever the config appears | §8a, `_notes`, `setup.sh` §7c | Met |
| 3.11 | Docs state setup never writes global harness configuration | §8a closing line | Met |
| 3.12 | §8b distinguishes the first-party path from the external `etl` plugin | §8b note: lakehouse vs local-offline, unrelated | Met |
| 3.13 | Each documented config **actually starts the server** | Linux verified 2026-10-08 — see 3.13a |
| 3.13a | **Positive assertion:** server reaches "Waiting for client connection", no credential present or requested | Verified on Linux with a raw JSON-RPC stdio handshake | Met |
| 3.13b | Read-only enforcement demonstrated where read-only is claimed | Verified on the file path: `CREATE TABLE` rejected | Met |
| 3.13c | Tool list matches docs (`execute_query`, `list_databases`, `list_tables`, `list_columns`) | `tools/list` — no `switch_database_connection` | Met |
| 3.14 | Every documented command is one the cited harness supports | Command review | Met |
| 3.15 | All relative doc links resolve | Verified — 0 missing across `GETTING_STARTED.md`, `README.md`, `CHANGELOG.md`, all specs | Met |
| 3.16 | Docs state what DuckDB does **not** do — no DAX, no VertiPaq parity, matching ≠ equivalent | §8a "What this does not do" | Met |

---

## 5. PR 4 — Upstream skill docs (SHIPPED)

| # | Criterion | How verified | Status |
|---|---|---|---|
| 5.1 | Only `motherduck-duckdb-sql` is documented | §8c | Met |
| 5.2 | Excluded skills are listed with reasons | §8c table — `motherduck-query` / `motherduck-explore` (declared MotherDuck prerequisite), `motherduck-cli` (different product), the other 18 (MotherDuck product features or dependents) | Met |
| 5.3 | `--global` is recommended, with the `.agents/skills/` collision as the stated reason | §8c "Use `--global`, deliberately" | Met |
| 5.4 | `--copy` is included in the Windows variant | §8c | Met |
| 5.5 | Node ≥ 22 requirement is stated, cross-referenced to §1 | §8c + §1 note | Met |
| 5.6 | Update and verify commands are present | §8c | Met |
| 5.7 | Telemetry suppression is mentioned | §8c — `DISABLE_TELEMETRY=1` / `DO_NOT_TRACK=1` | Met |
| 5.8 | Docs state the template does not install these skills | §8c opening | Met |
| 5.9 | No MotherDuck-only skill appears in any documented command | Grep — only `motherduck-duckdb-sql` | Met |
| 5.10 | The `.agents/skills/` tree is **unchanged** | `git diff --stat` — empty | Met |
| 5.11 | The MotherDuck framing caveat is stated | §8c closing caveat | Met |
| 5.12 | Hooks-not-supported-in-OpenCode limit recorded | §8c | Met |
| 5.13 | Docs state the skill is **not required** for §8a | §8c opening | Met |

---

## 6. PR 5 — Validation, changelog, cross-references (SHIPPED)

| # | Criterion | How verified | Status |
|---|---|---|---|
| 6.1 | `validate_repo.py` lists are touched **only if** repo-owned files were added outside `mcp/` and existing files | Diff inspection — added `inspect_data_source.py` and `test_inspect_delimiter.py` | Met |
| 6.1a | The profiler was previously shipped but **unregistered**, so deleting it would have passed validation. Now required | `validate_repo.py` `REQUIRED_FILES` | Met |
| 6.2 | `CHANGELOG.md` records every user-visible change | Text check | Met |
| 6.3 | Changelog states optional/local-only and no MotherDuck auth | Text check | Met |
| 6.4 | **No rows added to the first-party skill tables** — no first-party DuckDB skill exists | `git diff --stat CLAUDE.md .github/instructions/powerbi-development.instructions.md` — **empty** | Met |
| 6.5 | Local DuckDB scratch docs stay gitignored | `git check-ignore` — both ignored | Met |
| 6.6 | `docs/specs/*.md` are tracked | Not ignored; present in `git status` | Met |
| 6.7 | Full validation suite passes | See §9 — **300 checks**, all green | Met |
| 6.8 | No MotherDuck credential material in any shipped file | Grep across the diff — none | Met |
| 6.9 | `README.md` gains an optional-capability bullet and the `docs/specs/` layout entry | Text check | Met |
| 6.10 | No permanent DuckDB CI dependency | `validate.yml` diff — one delimiter test added, no DuckDB step | Met |

---

## 7. Deferred scope (no PR this cycle)

Named so their absence is a decision, not an oversight.

| Item | Status | What would be required |
|---|---|---|
| DuckDB CI matrix job | **Not needed** — verification ran on the authoring host (`SPEC-01` §7). Withdrawal step was a no-op | Nothing to withdraw; `validate.yml` has no DuckDB step and D6 holds in steady state |
| Profiler consolidation | **Out** per D3 | `SPEC-06` §5 prerequisites: fixtures, golden-output test, `--format json`, heuristic labelling |
| Reconciliation comparer | **Out** per D1 | `SPEC-07` §6 constraints, plus provenance schema |
| Live-model bridge | **Out** | Route B tooling and access; outside this repo's control |
| SQLite connector promotion | **Deferred** | `SPEC-02` §4 evaluation gate |
| XML / `webbed` community extension | **Deferred** | `SPEC-02` §3 trust review, pinned version, documented approval |
| First-party DuckDB skill | **Out** per D1 | Observed workflow evidence (`SPEC-03` §6) |
| `.tsv` delimiter fix in `inspect_data_source.py` | **SHIPPED** — see §1b | Done as PR 0 per D9, with regression test in CI |
| Windows CI for existing validators | **Out** | CI is `ubuntu-latest` only today |

---

## 8. Global acceptance criteria

Apply to **every** PR. A PR failing any of these is not acceptable regardless of its own criteria passing.

| # | Criterion |
|---|---|
| G1 | **No MotherDuck authentication.** No token, `md:`, S3 path, MotherDuck CLI, or remote MCP endpoint anywhere in code, config, docs, or agent instructions. |
| G2 | **Nothing made required.** `setup.sh`, the devcontainer, CI, and every validation script still succeed with DuckDB entirely absent. |
| G3 | **No global config writes.** No script writes `~/.claude/`, `~/.copilot/`, or `~/.config/opencode/`. |
| G4 | **Local-only sources.** No remote database or cloud analytics service. |
| G5 | **No writes to persistent user data by default.** The MCP baseline is write-enabled against the filesystem by necessity (`SPEC-02` §6a) — this is a known, documented, accepted exception, not a silent one. |
| G6 | **Install/register/enable are never conflated.** |
| G7 | **Read-only is never presented as a security boundary, and the write-enabled baseline is never presented as read-only.** |
| G8 | **Claims match `SPEC-02`'s tiers.** No XML, no remote, no `.xls`. |
| G9 | **Cross-platform claims are limited to Linux and Windows**, and are backed by the temporary matrix result recorded in `SPEC-01` §7. macOS is never claimed. |
| G10 | **Bounded outputs.** Result caps honoured per `SPEC-05` §7. |
| G11 | **`setup.sh` stays non-fatal** for every optional step, matching existing convention. |
| G12 | **Docs are honest about statistics.** Sample-based statistics and heuristic key/role suggestions are never presented as exact. |
| G13 | **`CHANGELOG.md` updated** for user-visible changes. |

---

## 9. Verification commands

```bash
# Validation suite (all four, per CLAUDE.md)
python3 scripts/validate_repo.py
python3 scripts/validate_date_table.py
bash scripts/validate_pbir.sh
python3 scripts/validate_m_expressions.py

# Profiler regression (PR 0)
python3 scripts/test_inspect_delimiter.py

# Installer behaviour
bash setup.sh                                    # decline -> [SKIP] path, exit 0
DUCKDB_SKIP_INSTALL=1 bash setup.sh              # network step bypassed
bash setup.sh                                    # accept -> then re-run to confirm idempotency

# Devcontainer
# devcontainer rebuild, then:
node -v                                           # expect 22.x
npx -y skills --version                           # must resolve

# DuckDB paths, local only — no credential of any kind.
# Assert POSITIVELY: the server must reach "Waiting for client connection".
# A non-zero exit is a FAILURE, not a pass.
uvx mcp-server-motherduck --db-path :memory: --read-write --query-timeout 30
# :memory: REQUIRES --read-write (verified 2026-10-08) - omitting it exits with
# "In-memory databases require the --read-write flag."
duckdb --version                                     # must report the pinned LTS line
duckdb -c "select 1"                                 # CLI smoke

# LTS pin check (open item A, proven 2026-10-08 - re-verify at PR 2's constant)
curl https://install.duckdb.org | DUCKDB_VERSION=1.4.5 bash
duckdb --version                                     # must report 1.4.5, not 1.5.x

# No-MotherDuck grep across the change set
git diff --name-only | xargs grep -n -i -E 'motherduck_token|MOTHERDUCK_TOKEN|--db-path +md:|s3://|motherduck connect'
```

---

## 10. Status

All reviewer questions are resolved (see the tables under §1). **PRs 0–5 are complete.** No open questions remain.

**Completed:**
- PR 0 — TSV delimiter fix + regression test + CI wiring + CHANGELOG (§1b)
- PR 1 — devcontainer Node `22`, and the Node 18 → 22 corrections in `docs/GETTING_STARTED.md`, `README.md`, and `mcp/mcp.json.example` (§2)
- PR 2 — `setup.sh` §7a (CLI install, pinned LTS constant) and §7c (printed MCP snippet) (§3)
- PR 3 — `mcp/mcp.json.example` `duckdb-local` entry + `docs/GETTING_STARTED.md` §8a (§4)
- PR 4 — `docs/GETTING_STARTED.md` §8c, upstream skill opt-in (§5)
- PR 5 — `validate_repo.py`, `CHANGELOG.md`, `README.md`, cross-references (§6)
- **Cross-platform verification, both stages** (`SPEC-02` §5). Windows on `1.5.6`; Linux on `1.5.5` **and** pinned LTS `1.4.5`. All five source tiers pass on every version tested. A10 (LTS pin) and A11 (Linux extension auto-install) closed.
- **MCP server verified end-to-end** on Linux against upstream `1.1.0`, with no MotherDuck credential. Found and fixed a broken baseline (§6a) and a test-design flaw (criterion 3.13).

### Carried into each PR, and how it landed

| Carried item | Landed as |
|---|---|
| Smoke-test the LTS constant that actually ships (2.5b) | Constant is `1.4.5`; §7a verifies the installed version and reports a mismatch distinctly |
| Don't reuse §5 results for other versions | `setup.sh` compares `duckdb --version` against the pin rather than assuming |
| Record the CLI/MCP version skew (`SPEC-02` §6) | `setup.sh` §7c note, `mcp.json.example` `_notes`, §8a |
| Write-enabled baseline stated everywhere (`SPEC-05` §4a) | §8a, `mcp.json.example` `_notes`, `setup.sh` §7c — with the throwaway/filesystem split |
| Upstream versions move independently | §8c notes only `motherduck-duckdb-sql` is local-usable; §8a cites `1.1.0` verification |

### Final Linux verification pass — run 2026-10-08 (Debian 13, x86_64, GNU bash 5.2.37)

This closes deferred items 1 and 2 from the previous revision. Item 3 is Windows-only and stays open.

**1. Full `setup.sh` run on Linux — completes end-to-end with piped input; cannot run unattended (L2).**

| Check | Result |
|---|---|
| `bash -n setup.sh` | **Pass** — parses |
| `bash setup.sh` with piped input (`printf 'n\nn\n' \|`) | **Pass** — exit 0, completes all sections through "Setup complete!" |
| `DUCKDB_SKIP_INSTALL=1 bash setup.sh` | **Pass** — `[SKIP]` branch taken, DuckDB prompt bypassed |
| `python3 scripts/validate_repo.py` | **Pass** — all 300 checks |
| `bash -n .devcontainer/setup.sh` | **Fail in the working tree** — see finding L1 |
| `bash setup.sh </dev/null` (no stdin) | **Fail, exit 1** — see finding L2 |

The full run is therefore sound on Linux *when given input*. It does **not** run unattended, which is finding L2.

**2. The shipped MCP config, launched exactly as documented — Pass, with the §4a write behaviour confirmed.**

Driven through a raw JSON-RPC stdio handshake using the literal `command` array from `mcp/mcp.json.example`:

```
uvx mcp-server-motherduck --db-path :memory: --read-write --query-timeout 30
```

| Assertion | Result |
|---|---|
| Server starts, no MotherDuck credential present or requested | **Pass** — zero token/credential/sign-in/account references in stderr |
| `initialize` handshake completes | **Pass** — `serverInfo` reports `mcp-server-motherduck` `1.1.0` |
| Query over a local CSV | **Pass** — `{"success": true, "rows": [[2, 200.5]]}`, identical to the CLI result for the same fixture |
| Write behaviour matches `SPEC-05` §4a | **Confirmed** — `CREATE TABLE zz (a int)` **succeeded** on `:memory:` |

That last row is the important one: it is the positive proof that `SPEC-05` §4a's characterisation is accurate. `:memory:` with `--read-write` is genuinely write-enabled, so §4a's "must not be described as read-only anywhere" is not a conservative hedge — it is a measured fact. The read-only path remains available via a file `--db-path`, where `CREATE TABLE` is rejected (3.13b).

**Finding L1 — `.devcontainer/setup.sh` has CRLF in the working tree and fails to parse on Linux. Not a shipped defect.**

`bash -n .devcontainer/setup.sh` fails with `line 49: syntax error: unexpected end of file`. Cause is **CRLF line terminators** on all 48 lines, not the script's content: `sed 's/\r$//'` produces a file that parses cleanly, and the committed blob has zero CR bytes. This is working-tree pollution, not a commit:

| Evidence | Reading |
|---|---|
| `git show HEAD:.devcontainer/setup.sh \| grep -c $'\r'` | `0` — committed blob is LF |
| `git archive HEAD` → fresh copy, `bash -n` | **Pass** — a fresh clone is fine |
| `git ls-files --eol` | `i/lf w/crlf attr/text eol=lf` — index LF, working tree CRLF |
| `git diff --quiet` | clean — `.gitattributes` `*.sh text eol=lf` normalises CRLF away on add |
| `scripts/validate_pbir.sh`, `setup.sh` | both `w/lf`, both parse — blast radius is one file |

**Why this still matters, and why validation did not catch it.** `.devcontainer/devcontainer.json` runs `postCreateCommand: bash .devcontainer/setup.sh`, so a devcontainer build on a host with this working-tree state would fail at post-create. It escaped `scripts/validate_repo.py` (300/300 pass) because that validator checks structure and JSON, not shell parseability, and it escaped `git status` because `eol=lf` normalisation makes the CRLF invisible to diff. A contributor whose editor writes CRLF can therefore reproduce this at any time, and nothing in the current validation surface would notice.

Two follow-ups, neither blocking and neither a change to shipped behaviour:

- **Recommended:** add a `bash -n` check over the repo's shell scripts to `scripts/validate_repo.py` (or as a CI step alongside `test_inspect_delimiter.py`). Cheap, and it closes a class of defect that is currently silent.
- **Housekeeping on this host only:** `git checkout -- .devcontainer/setup.sh` restores the LF form. Not committed, so there is nothing to push.

Note this is a *different* root cause from the CSV sniffer trap in `SPEC-02` §5. That one is malformed file *content*; this one is malformed file *encoding* of an otherwise correct script. Both are silent-failure modes that only a deliberate check surfaces.

**Finding L2 — `setup.sh` cannot run unattended. Pre-existing, not introduced by the DuckDB work.**

`bash setup.sh </dev/null` exits **1**, stopping at the pre-commit hook prompt. `bash -x` shows it reaching line 91:

```
+ '[' -d .git ']'
+ read -rp 'Install pre-commit validation hook? [Y/n] ' ans
   → exit 1
```

Under `set -euo pipefail` (line 4), a `read` with no input available fails, and the script aborts. The DuckDB prompt added in PR 2 is **correctly guarded** — `elif [ ! -t 0 ]` at line 130 skips it in non-interactive shells and prints the manual command instead. The older pre-commit prompt at line 91 has **no such guard**, so the two prompts in the same script behave differently, and the unguarded one runs first.

| Input | Result |
|---|---|
| `bash setup.sh </dev/null` | **exit 1** at the pre-commit prompt |
| `DUCKDB_SKIP_INSTALL=1 bash setup.sh </dev/null` | **exit 1** at the same prompt — the DuckDB guard does not help |
| `printf 'n\nn\n' \| bash setup.sh` | **exit 0** |
| `printf 'n\n' \| bash setup.sh` | completes |

**Scope.** This is **pre-existing** and unrelated to DuckDB: the unguarded prompt is present in the committed `HEAD` version (`git show HEAD:setup.sh`, line 70 there). It matters for CI and container use, where stdin is typically closed or empty. It does not affect an interactive developer running `bash setup.sh` in a terminal, which is the documented path, so it is not a regression and not a release blocker.

**Optional fix:** apply the same `[ ! -t 0 ]` guard already used at line 130 to the prompt at line 91. One-line pattern reuse, consistent with the file's existing convention. Left unapplied here because it is outside the scope of this verification pass and touches pre-existing behaviour.

**Methodological note.** An earlier run of this same command appeared to exit 0. That reading was wrong — the exit code was captured after a pipe into `tail`, so it reported `tail`'s status rather than `setup.sh`'s. Always check the script's own status unpiped (`bash setup.sh >/dev/null 2>&1; echo $?`), never `$?` after a pipeline. The table above uses unpiped exit codes.

**Finding L3 — A18 verified. The "no read-but-not-write switch" conclusion in the first draft of this finding was WRONG and has been corrected.**

The first pass tested only `enable_external_access=false` and `disabled_filesystems`, concluded that no read-but-not-write switch existed, and recorded that as A18. **That was an incomplete search and the conclusion was wrong.** DuckDB exposes `allowed_paths` and `allowed_directories`, which together with `enable_external_access=false` give exactly the requested property. Corrected below; the earlier wording is preserved in the audit note so the error is not silently erased.

**The working mechanism — an allow-list, in a required order:**

```sql
SET allowed_paths=['/abs/path/to/source.csv'];   -- 1. allow-list FIRST
SET allowed_directories=['/abs/path/to/scratch']; --    (may be several)
SET enable_external_access=false;                 -- 2. THEN deny everything else
```

`allowed_paths` / `allowed_directories` are documented as "ALWAYS allowed to be queried — even when `enable_external_access` is false". The ordering is **mandatory**, not stylistic: setting `allowed_directories` *after* `enable_external_access=false` fails with `Cannot change allowed_directories when enable_external_access is disabled`. Because `--init-sql` accepts a multi-statement string and executes it in order, this composes correctly into one flag.

Verified end-to-end through the real MCP server, pinned via `uvx --from mcp-server-motherduck==1.1.0`:

| Operation | Result |
|---|---|
| `read_csv_auto('/abs/path/source.csv')` (allow-listed exact file) | **ALLOWED** — reads work |
| `COPY (…) TO '/abs/path/source.csv'` (overwrite a source) | **BLOCKED** — `Permission Error` |
| `COPY (…) TO '/abs/path/scratch/out.csv'` (designated scratch) | **ALLOWED** |
| `COPY (…) TO '/anywhere/else.csv'` | **BLOCKED** |
| `read_json_auto` on a file outside the allow-list | **BLOCKED** |
| Source file byte-comparison after the run | **INTACT** |

This is precisely the property the capability needs: **source data (CSV, JSON, Parquet, `.xlsx`, SQLite) is readable and provably not amendable, while writes are confined to a user-designated scratch directory.** Confirmed present on DuckDB `1.5.5`, on LTS `1.4.5`, and in the `1.5.6` engine bundled with `mcp-server-motherduck==1.1.0`.

**Finding L3b — still true: bare read-only mode is not filesystem isolation.** Unchanged by the above, and independently verified: on a **file** `--db-path` with no `--read-write`, `CREATE TABLE` is rejected (`attached in read-only mode`) but `COPY (…) TO '/tmp/…'` **succeeds and writes a file**, because exporting is not governed by the read-only attachment flag. `access_mode='READ_ONLY'` does not help either — it cannot be changed at runtime ("must be set when opening or attaching"), cannot be set on `:memory:` at all ("Cannot launch in-memory database in read-only mode"), and on a file database still permits `COPY TO`.

So the accurate position is two-tier:

| Config | DB writes | Source files amendable | Writes outside allow-list | Reads local files |
|---|---|---|---|---|
| `:memory:` + `--read-write` | Yes (ephemeral) | **Yes** | **Yes** | Yes |
| File path (no `--read-write`) | Blocked | **Yes** | **Yes** | Yes |
| Either + `--init-sql` allow-list | Blocked or scratch-only | **No** | **No** | Yes (allow-listed only) |

Only the third row delivers the guarantee. It requires the user to supply `--init-sql`, which is why it is documented hardening rather than the default — the same conclusion §4a already reached, now with a mitigation that actually works.

**Also ruled out, so they are not re-tested later:** `SET disabled_filesystems='LocalFileSystem'` (blocks all local access, same dead end as bare `enable_external_access=false`); `SET secret_directory`; `SET lock_configuration=true` (neither affects write access). No setting provides read-but-not-write on a *directory prefix* — the granularity is per-path/prefix, so the allow-list is the mechanism, and confinement to a scratch directory is what substitutes for a write ban.

### Windows confirmation pass — run 2026-10-08

The L1/L2/L3 fixes left three Windows-side items. Two are now closed.

**L2 — unattended `setup.sh` on Windows: confirmed exit 0.**

| Check | Result |
|---|---|
| `bash setup.sh < /dev/null` | **exit 0** — 444 lines of output, reaches "Setup complete!" |
| `setup.sh` §7a reached | **Yes** — non-interactive branch, no prompt |
| `setup.sh` §7c reached | **Yes** — MCP snippet printed |
| `validate_repo.py` | **303 checks pass** |

**L3 / item E — the `--init-sql` allow-list holds on Windows.** DuckDB `v1.5.6` (Variegata), Windows x64, forward-slash paths:

| Operation | Result |
|---|---|
| Read an allow-listed source | **ALLOWED** — 2 rows, sum 200.5 |
| `COPY (…) TO` over that source | **BLOCKED** — `Permission Error: Cannot access file …` |
| `COPY (…) TO` into the scratch dir | **ALLOWED** |
| Read outside the allow-list | **BLOCKED** — `Permission Error` |
| `COPY (…) TO` to an arbitrary path | **BLOCKED** — `Permission Error` |
| Source checksum after | **unchanged** (`18aedc5f…` before and after) |
| Reverse order | **fails** — `Cannot change allowed_paths when enable_external_access is disabled` |

Also confirmed, and the reason the recipe is an allow-list rather than the bare setting: with only `enable_external_access=false`, `read_xlsx` fails with `Extension Autoloading Error … 'excel'`.

**Two method traps hit on the way, both of which first produced the *opposite* of the truth — recorded because a hardening test that appears to pass usually means it failed for the wrong reason:**

1. `--init-sql` is an `mcp-server-motherduck` flag, **not** a DuckDB CLI flag. The CLI gives `Unknown Option Error: Unrecognized option '-init-sql'`, so every query in the run fails — and a naive "source unchanged" check then reports the source **safe**.
2. `SET` does not survive across `duckdb -c` invocations; each is a separate session. Settings in one invocation and the query in another apply nothing, producing the same false `INTACT`.

The corrected form is `duckdb -cmd "<settings>" -c "<sql>"` — both in one invocation.

### L1 follow-up — validator false-failure, fixed

The `bash -n` check added for L1 initially reported three `FAIL`s on this Windows host:

```
[FAIL] setup.sh does not parse: wsl: Failed to translate 'E:\01-Projects\...'
```

Cause: `bash` on `PATH` here is the WSL shim (`C:\Windows\system32\bash.exe`), which cannot reach a repo on another drive. **That is an environment limitation, not a script defect**, and a validator that reports it as one trains people to ignore its output.

`validate_repo.py` now distinguishes the two: no `bash` on `PATH` → `[SKIP]` with the reason; a shell that cannot run here (WSL `Failed to translate`, `command not found`) → `[SKIP]` naming the cause; a genuine parse error (which names the script and a line) → `[FAIL]`. The LF check needs no shell and remains the load-bearing half.

Verified after the fix: **303 checks pass, 0 failures**, three `[SKIP]` lines with explanations. The LF check was separately proven to catch the real defect by injecting 81 CRLF line endings into `scripts/validate_pbir.sh` — it failed naming both the cause and the count — and the file was restored clean.

### Remaining

1. **Windows behaviour of `install.duckdb.org` on a machine without `winget`.** Still open — it needs a Windows environment with no DuckDB and no winget, which this host is not. Recommend recording it as untested rather than inferring it from the Linux result.
2. **Windows extension autoload on a cold cache.** Unconfirmed here; measured on Linux only (L3 note). The shipped docs already describe it as version- and platform-dependent, so this is a nice-to-have.
3. Everything else in this pass is closed: L1 fixed and guarded against false failure, L2 fixed and confirmed on Windows, L3 resolved with the allow-list now verified on both platforms.