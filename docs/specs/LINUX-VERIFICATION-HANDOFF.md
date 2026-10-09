# Linux Verification Results — Handoff for the Windows Agent

**Purpose:** one self-contained document with the completed Linux evidence and the exact
outstanding Windows work. Written 2026-10-08.

**Read this if:** you are picking up the DuckDB capability on Windows and need to know what is
already proven, what is not, and what to run next. Everything here is either measured on Linux or
explicitly flagged as a Windows-only open item.

**Supersedes:** `duckdb-pending-linux-verification.md` (gitignored, local, and now stale — it still
lists items A/B/C as open). That file was a to-do list for the Linux run; this is the record of
what the run found. It can be deleted.

---

## 1. Status at a glance

| # | Item | Status | Where the detail lives |
|---|---|---|---|
| A | LTS pin (`1.4.5`) smoke test | **Done, affirmative** | §3 below · `SPEC-02` §5 |
| B | Linux source-tier matrix | **Done — all 5 tiers pass** | §4 below · `SPEC-02` §5 |
| C | MCP server launch, no credentials | **Done, with a spec defect found** | §5 below · `SPEC-02` §6a |
| D | `install.duckdb.org` on Windows **without `winget`** | **OPEN — needs a machine with no DuckDB and no winget** | §6 below |
| E | Confirm the hardened MCP recipe on Windows | **Done — all 5 behaviours confirmed** | §7 below |

**Bottom line:** the cross-platform claim is now established by evidence on both platforms. The
temporary CI matrix job that was supposed to produce this evidence **was never created** — nothing
needs withdrawing. See §8.

---

## 2. Environment the Linux evidence came from

| Property | Value |
|---|---|
| OS | Debian 13, `x86_64`, kernel `7.0.9-1~bpo13+1` |
| Shell | GNU bash `5.2.37(1)` |
| Host DuckDB CLI | `v1.5.5` (Variegata, `d8cdaa33fd`) |
| Pinned LTS CLI | `v1.4.5` (Andium, `f31be57c18`), installed clean-room into an isolated `HOME` |
| MCP server | `mcp-server-motherduck` `1.1.0`, resolving `duckdb==1.5.6` |

Fixtures were written fresh on Linux with `printf` / Python — **not** transported from Windows.
That matters; see the CRLF trap in §4.

---

## 3. Item A — the LTS pin is proven

The previous concern was that `SPEC-01` D7 pins the CLI to the LTS line (`1.4.5`) while the dev
machine had `1.5.6` installed via `winget`, so no result transferred to the pinned version.

**It does.** Verified:

```bash
curl -sSL https://install.duckdb.org -o ins.sh
DUCKDB_VERSION=1.4.5 sh ins.sh          # isolated HOME, host CLI untouched
# -> Successfully installed DuckDB 1.4.5 ...
$HOME/.duckdb/cli/1.4.5/duckdb --version
# -> v1.4.5 (Andium) f31be57c18        # exactly the pin, not a 1.5.x
```

Assumption **A10 is resolved**. PR 2 still needs a smoke check at whatever constant it ships, but the
documented install path itself is confirmed working on Linux.

---

## 4. Item B — source-tier matrix: all five tiers pass

Same fixtures, both DuckDB versions:

| Tier | Check | `1.5.5` | LTS `1.4.5` |
|---|---|---|---|
| CLI | `duckdb --version`, `select 1` | Pass | Pass |
| 1 | `read_csv_auto` over local CSV | Pass — 2 rows, sum 200.5 | Pass — 2 rows, sum 200.5 |
| 1 | `read_parquet` over locally written Parquet | Pass — round-trip | Pass — round-trip |
| 2 | `read_json_auto` over local NDJSON | Pass | Pass — **no extension fetch** |
| 2 | `attach … (type sqlite)` on local `.db` | Pass | Pass |
| 2 | `read_xlsx` over local `.xlsx` | Pass | Pass |

### Finding B1 — the extension network caveat is real, and measurable

`excel` and `sqlite` were **absent** from `~/.duckdb/extensions/v1.5.5/linux_amd64/` before the run.
Both auto-downloaded on first use. The cost is measurable:

- cold `read_xlsx`: **1.089s**
- identical warm read: **0.107s** (10x)

So A11 is confirmed, and the §2 offline caveat is a practical concern, not a formality. **An offline
Windows runner would fail here where a cached one succeeds** — relevant to item D below.

### Finding B2 — JSON's offline behaviour differs by version

On a cold `1.4.5` cache, `read_json_auto` succeeded **with no download**: `json` is linked into the
`1.4.5` binary rather than shipped as a loadable extension. On `1.5.5` it *was* a loadable extension.
Docs must describe JSON's offline story as version-dependent, not promise it.

### Finding B3 — the CSV sniffer trap reproduces identically on Linux

A fixture ending `\n\r\n` fails with "It was not possible to automatically detect the CSV parsing
dialect" — enumerating delimiter and quote candidates, **even with `delim=','` passed explicitly**,
which failed identically. Byte-level check confirmed the clean fixture ended in a single `\n`.

This is now **cross-platform evidence, not a Windows quirk**. Practical rules:
- Write fixtures with `printf` or Python. Never a shell redirection that appends CRLF.
- If you hit this on either platform, suspect a trailing CRLF before you suspect delimiters.

---

## 5. Item C — MCP server: works, but the documented baseline was broken

**Launched with no MotherDuck credential of any kind**, driven end-to-end over stdio with a raw
JSON-RPC handshake.

### Finding C1 — the `:memory:` baseline did not start

`SPEC-05` §4 and acceptance criterion 3.13 documented this as the local baseline:

```bash
uvx mcp-server-motherduck --db-path :memory: --query-timeout 30
```

On `1.1.0` this **exits non-zero**, asking for `--read-write`. The only way to start it is to pass
that flag — which inverts the read-only contract the spec treats as load-bearing.

Root cause: in-memory DuckDB **cannot** be read-only. Upstream concedes "In-memory databases are
always writable (DuckDB limitation)". `:memory:` and read-only are mutually exclusive **by design**.

**Now corrected throughout:** the baseline is `:memory:` + `--read-write`, documented honestly as
write-enabled (`SPEC-05` §4a). Criterion 3.13 was also a flawed test — it could pass against a
broken config, since the command failed before any credential question arose. It is now a
**positive** assertion (server reaches "Waiting for client connection").

### Finding C2 — tool surface and argument name

| Fact | Value |
|---|---|
| Tools advertised | `execute_query`, `list_databases`, `list_tables`, `list_columns` |
| `switch_database_connection` | Not advertised (correct — `--allow-switch-databases` not set) |
| SQL argument | **`sql`**, *not* `query` — passing `query` fails pydantic validation |
| `--query-timeout` default | **`-1`, i.e. disabled** — so the finite value in our config is load-bearing |

Note this is the **inverse** of older upstream examples. All `SPEC-05` §4 flags still exist in
`1.1.0`; the breakage was behavioural, not a rename.

### Finding C3 — version facts in the specs were already stale

| Claim | Was | Actually (2026-10-08) |
|---|---|---|
| `mcp-server-motherduck` current | `1.0.8` | **`1.1.0`** |
| Its pinned `duckdb` | `duckdb==1.5.5` | **`duckdb==1.5.6`** |

The skew moved on **both** surfaces at once. This is why every flag stays explicit rather than
relying on defaults.

---

## 6. Item D — OPEN: `install.duckdb.org` on Windows without `winget`

**Why it's open:** the Windows evidence in `SPEC-02` §5 was gathered with DuckDB `1.5.6` **already
installed via `winget`**. So the documented install path has never been exercised on Windows — which
is precisely the path `setup.sh` §7a will now use for users who do not have DuckDB.

**What to run.** On a Windows box **without** DuckDB preinstalled, and **without** `winget` (e.g. a
plain VM or a machine where winget is unavailable):

```powershell
# In a normal shell, per docs/GETTING_STARTED.md / setup.sh 7a
curl https://install.duckdb.org | DUCKDB_VERSION=1.4.5 bash
duckdb --version          # MUST report 1.4.5 (Andium) — if it reports 1.5.x, STOP
```

**The acceptance bar is the version string.** `SPEC-02` §6 is explicit that a silently-wrong pin is
worse than no pin: if you get `1.5.x` back, something ignored `DUCKDB_VERSION` and that is the
finding.

**Record:**

| Question | Note |
|---|---|
| Did the documented command work as written? | |
| Resulting `duckdb --version` | |
| Does the install land in the same location as the Linux path (`~/.duckdb/cli/<ver>/duckdb`)? | |
| Any difference in the hint text vs. the Linux installer? | |
| Did you need PowerShell-specific syntax instead of `curl … \| bash`? | |

**If the documented form fails on Windows**, that is a genuine portability defect in a doc users will
follow — capture the exact error and the working alternative. `setup.sh` §7a prints this command, so
a Windows-only failure would ship to every Windows user who runs setup.

**Also worth checking on Windows, same session:** extension auto-install behaviour on a **cold**
cache. Finding B1 showed this costs ~1s and requires network on Linux. Confirm Windows behaves
identically, since that is what justifies the offline caveat being platform-neutral.

---

## 7. Item E — DONE: hardening recipe confirmed on Windows

**Run 2026-10-08 on Windows x64, DuckDB `v1.5.6` (Variegata).** All five Linux behaviours reproduce exactly.

| Operation | Expected | Windows result |
|---|---|---|
| `read_csv_auto` on an allow-listed source | ALLOWED | **ALLOWED** — 2 rows, sum 200.5 |
| `COPY (…) TO` overwriting that source | BLOCKED | **BLOCKED** — `Permission Error: Cannot access file …` |
| `COPY (…) TO` into the allow-listed scratch dir | ALLOWED | **ALLOWED** |
| `read_csv_auto` outside the allow-list | BLOCKED | **BLOCKED** — `Permission Error` |
| `COPY (…) TO` to an arbitrary path | BLOCKED | **BLOCKED** — `Permission Error` |
| Source file checksum afterwards | unchanged | **unchanged** — `18aedc5f…` before and after |
| Reverse order (`enable_external_access` first) | fails at startup | **fails** — `Cannot change allowed_paths when enable_external_access is disabled` |

**Extension autoload confirmed blocked by the bare form** (the reason the recipe is an allow-list, not `enable_external_access=false` alone): with only that setting, `read_xlsx` fails with `Extension Autoloading Error: An error occurred while trying to automatically install the required extension 'excel'`.

### Two method notes for anyone re-running this

Both cost a wrong result on the first attempt, so they are recorded here rather than rediscovered:

1. **`--init-sql` is an `mcp-server-motherduck` flag, not a DuckDB CLI flag.** Testing the engine directly, use `duckdb -cmd "<settings>" -c "<sql>"`. Passing `--init-sql` to the CLI gives `Unknown Option Error: Unrecognized option '-init-sql'`, and — importantly — every query in that run fails for an unrelated reason, so a naive "source unchanged" check will **falsely report the source as safe**.
2. **`SET` does not carry across `duckdb -c` invocations.** Each invocation is a separate session. Putting the settings in a first invocation and the query in a second applies nothing, which again produces a false "INTACT". The settings and the query must be in the same invocation (or use `-init`).

Both mistakes initially reported the opposite of the truth. If a hardening test ever appears to pass, confirm it failed for the *intended* reason before believing it.

### Windows path note

Allow-list entries need **forward slashes** (`C:/data/source.csv`). Backslashes will not match. The shipped docs show POSIX-style absolute paths; Windows users substitute the drive form.

**Conclusion:** the `--init-sql` allow-list holds cross-platform. Item E is closed.

---

## 8. The CI matrix job never existed

`SPEC-01` §7 step 3 and the old runbook both say to withdraw a temporary `ubuntu-latest` matrix job
once the Linux evidence is recorded. **There is no such job.** `.github/workflows/validate.yml` has
exactly one job, `validate`, on `ubuntu-latest`, containing no DuckDB steps.

Consequences:
- **Nothing to withdraw.** The step is a no-op, not an oversight.
- Linux evidence was gathered on the authoring host, which is the stronger position — Linux is this
  template's primary authoring environment.
- D6 (an optional capability carries no permanent CI weight) already holds in steady state.

**Do not add a DuckDB CI job to "complete" this. It is not wanted.**

---

## 9. Two unrelated defects found and fixed (no action needed, FYI)

Both were pre-existing rather than DuckDB-related, but both were invisible to current validation.

### L1 — CRLF shell script slipped through everything

`.devcontainer/setup.sh` had CRLF line endings **in the working tree** and failed `bash -n` with a
misleading `line 49: syntax error: unexpected end of file`. It escaped `git status` because
`.gitattributes` `*.sh text eol=lf` normalises CRLF away, and escaped all 300 validation checks
because they covered structure and JSON, not shell parsing. A devcontainer build would fail at
`postCreateCommand`.

The **committed blob was LF**, so this was host pollution, not a shipped defect.

Fixed: file restored to LF; `validate_repo.py` now enforces LF + `bash -n` across all three shell
scripts (300 → **306** checks), plus a CI step. Proven by reintroducing CRLF and confirming the check
fails naming both the cause and the parse error.

> **Relevant to you:** if a shell script fails `bash -n` on Windows but the committed file looks
> fine, suspect your editor is writing CRLF. `git checkout --` may **not** fix it, because git
> considers the normalised file up to date — you may need to delete and re-checkout.

### L2 — `setup.sh` could not run unattended

The pre-commit prompt used a bare `read`, which fails under `set -euo pipefail` when stdin is
closed or piped, so `bash setup.sh </dev/null` exited 1 partway through. The DuckDB prompt added in
PR 2 was correctly guarded; the older prompt was not, and ran first.

Fixed with the same `[ ! -t 0 ]` guard. Unattended runs now exit 0; interactive prompting unchanged.

---

## 10. Documentation corrections you should know about

These are **already applied**, but they change documented behaviour, so check whether you have local
copies that need re-syncing.

| Change | Reason |
|---|---|
| MCP baseline is `:memory:` + `--read-write`, described as write-enabled | C1 — the old baseline did not start |
| Criterion 3.13 is now a positive assertion | Old version could pass against a broken config |
| The **file path is no longer described as "genuine read-only"** | Read-only blocks DDL/DML on the *database*; `COPY … TO` still writes files. `access_mode='READ_ONLY'` does not close this either |
| The hardening recipe is now documented as an **allow-list**, not bare `enable_external_access=false` | Bare form also blocks every file *read*, including extension auto-install, making it useless for profiling |
| `A10`, `A11` verified; `A18` verified affirmative; `A12`/`A2`/`A11(SPEC-03)` refuted | See §3, §4, §5 |

---

## 11. Suggested order of work

1. ~~**Item E** — hardening recipe on Windows.~~ **Done 2026-10-08**, §7.
2. **Item D** — the last open evidence gap. Run the LTS install on a Windows box with **no** DuckDB and **no** winget; record the version string. Needs a suitable machine — see §12 Q2.
3. Record D in `SPEC-02` §5/§6 and close the §1 row.
4. **Delete this file and `duckdb-pending-linux-verification.md`** once D is recorded.

---

## 12. Open questions for the reviewer

1. **Nothing is committed.** The whole working tree is uncommitted, and it is now larger — the L1/L2 fixes, the hardening documentation, and the `bash -n` validator change all landed after the last commit point. Worth committing before more parallel work piles up.
2. **Item D needs a specific machine.** The documented `install.duckdb.org` path has never run on Windows, because this box already had DuckDB via winget. Reproducing it requires a Windows environment with **no DuckDB installed and no winget available** — a plain VM, or a user account where winget is disabled. Is one available? If not, the honest outcome is to record it as untested rather than infer it from the Linux result.
3. **Windows extension autoload on a cold cache** is still unconfirmed here. Finding B1 measured it on Linux only. It is a caveat in shipped docs, so confirming it on Windows would close the loop — low priority, since the docs already describe it as version- and platform-dependent.
4. **`motherduck-duckdb-sql` installs `--global` deliberately** — so third-party skill content does not land in `.agents/skills/`, which is this repo's canonical first-party skill directory. This is the counterintuitive choice and is justified in `GETTING_STARTED` §8c, but is worth an explicit sanity check.
5. **Validator false-failure fixed.** The `bash -n` check added for L1 initially reported three `FAIL`s on this Windows host, because `bash` on PATH is the WSL shim (`C:\Windows\system32\bash.exe`) and cannot translate a repo on another drive. That is an environment limitation, not a script defect. `validate_repo.py` now distinguishes the two and prints `[SKIP]` with the reason when the shell cannot run, leaving the LF check — which needs no shell — as the load-bearing half. Worth a look, since a validator that cries wolf gets ignored.