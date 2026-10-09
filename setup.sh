#!/usr/bin/env bash
# setup.sh — Interactive post-clone setup for powerbi-dev-template.
# Run from the repo root: bash setup.sh
set -euo pipefail

# ══ DuckDB configuration ═══════════════════════════════════════════════════════
#
# This pin is the point of the DuckDB option, not an incidental detail. DuckDB is
# here because it is a robust way to analyse structured data, and that only holds
# if the engine version is a known quantity: an unpinned or floating install can
# change dialect behaviour or extension availability between two people running
# the same query on the same machine layout.
#
# Pinned to the DuckDB LTS line. Deliberately NOT "latest" or "current" — those
# are floating tags, and a template that derived repos copy should produce the
# same engine for everyone.
#
# This is the single place to change it. Note that mcp-server-motherduck pins its
# own duckdb inside its own uvx environment and is therefore independent of this
# constant; the two are EXPECTED to differ. See docs/specs/SPEC-02-source-matrix.md §6.
#
# Verified 2026-10-08: DUCKDB_VERSION=1.4.5 installs and self-reports
# "v1.4.5 (Andium)", and passes CSV / Parquet / JSON / SQLite / XLSX on both
# Linux and Windows. Re-verify after changing this value.
DUCKDB_VERSION="1.4.5"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Power BI Dev Template — Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ── 1. Check Python ────────────────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    echo "[ERROR] Python 3 not found."
    echo "        Install from https://python.org or your OS package manager."
    exit 1
fi
PY_VERSION=$(python3 --version 2>&1)
echo "[OK] $PY_VERSION"

# ── 2. Install uv ─────────────────────────────────────────────────────────────
if ! command -v uv &>/dev/null; then
    echo "[Installing uv (fast Python tool manager)...]"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Add uv to PATH for this session
    export PATH="$HOME/.local/bin:$PATH"
    echo "[OK] uv $(uv --version)"
else
    export PATH="$HOME/.local/bin:$PATH"
    echo "[OK] uv $(uv --version)"
fi

# ── 3. Install pbir-cli ───────────────────────────────────────────────────────
echo "[Checking pbir-cli compatibility...]"
OS_TYPE="$(uname -s 2>/dev/null || echo "Unknown")"
if [ "$OS_TYPE" = "Linux" ]; then
    echo "[INFO] Running on Linux: upstream pbir-cli wheels currently support Windows and macOS only."
    echo "       This template includes a built-in cross-platform pure-Python schema validator:"
    echo "       -> scripts/validate_pbir_schema.py (used automatically by scripts/validate_pbir.sh)."
else
    echo "[Installing/upgrading pbir-cli...]"
    if uv tool install pbir-cli 2>/dev/null; then
        echo "[OK] pbir-cli installed"
    elif uv tool upgrade pbir-cli 2>/dev/null; then
        echo "[OK] pbir-cli upgraded"
    else
        echo "[WARN] Could not install pbir-cli — run manually: uv tool install pbir-cli"
    fi
fi

# ── 4. Check Node.js / npx ───────────────────────────────────────────────────
if ! command -v npx &>/dev/null; then
    echo "[WARN] Node.js / npx not found."
    echo "       Install Node.js 18+ from https://nodejs.org to use powerbi-modeling-mcp."
else
    echo "[OK] Node $(node --version) / npm $(npm --version)"
fi

# ── 5. Copy .env ──────────────────────────────────────────────────────────────
if [ ! -f .env ]; then
    cp .env.example .env
    echo "[OK] Created .env — edit it with your credentials and fiscal calendar settings."
else
    echo "[OK] .env already exists — skipping copy."
fi

# ── 6. Pre-commit hook ────────────────────────────────────────────────────────
echo ""
if [ ! -d .git ]; then
    echo "[SKIP] Not a git repo — skipping pre-commit hook installation. Run 'git init' first."
elif [ ! -t 0 ]; then
    # Non-interactive (CI, piped input). A bare `read` here would fail under
    # `set -e` and abort the whole script, so never prompt. Same guard as §7a.
    echo "[SKIP] Non-interactive shell — not prompting for the pre-commit hook."
    echo "       To install it: cp hooks/pre-commit .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit"
else
    read -rp "Install pre-commit validation hook? [Y/n] " ans
    if [[ "${ans:-Y}" =~ ^[Yy]$ ]]; then
        cp hooks/pre-commit .git/hooks/pre-commit
        chmod +x .git/hooks/pre-commit
        echo "[OK] Pre-commit hook installed — will run validate_repo.py + validate_date_table.py on staged PBIP/TMDL changes."
    else
        echo "[SKIP] Pre-commit hook not installed. Run manually: cp hooks/pre-commit .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit"
    fi
fi

# ── 7. MCP config reminder ────────────────────────────────────────────────────
echo ""
echo "━━ MCP Configuration ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Copy mcp/mcp.json.example to your harness config:"
echo "    Antigravity : ~/.config/antigravity/mcp.json"
echo "    VS Code     : .vscode/mcp.json"
echo "    Claude Code : ~/.claude/mcp.json"
echo ""

# ── 7a. Optional DuckDB (local analysis engine) ────────────────────────────────
# Entirely optional. Skipped non-interactively in CI and by default in the
# devcontainer. Nothing downstream requires DuckDB: scripts/inspect_data_source.py
# remains the zero-dependency profiler. See docs/specs/SPEC-01-scope-and-boundaries.md.
echo ""
echo "━━ Optional: DuckDB (local analysis engine) ━━━━━━━━━━━━━"
echo "  DuckDB gives an agent a fast SQL engine over local CSV, Parquet,"
echo "  JSON, .xlsx and SQLite files, with no database server and no"
echo "  cloud account. Pinned to v${DUCKDB_VERSION} (LTS line)."
echo ""
echo "  It is optional. scripts/inspect_data_source.py still handles"
echo "  quick Excel/CSV profiling with no extra install."
echo ""

DUCKDB_ENV_HINT="  To skip this prompt entirely: DUCKDB_SKIP_INSTALL=1 bash setup.sh"

if [ "${DUCKDB_SKIP_INSTALL:-}" = "1" ]; then
    echo "[SKIP] DUCKDB_SKIP_INSTALL=1 — DuckDB install skipped.${DUCKDB_ENV_HINT}"
elif [ ! -t 0 ]; then
    # Non-interactive (CI, piped input). Never block, never install unasked.
    echo "[SKIP] Non-interactive shell — not prompting. To install DuckDB v${DUCKDB_VERSION}:"
    echo "         curl https://install.duckdb.org | DUCKDB_VERSION=${DUCKDB_VERSION} bash"
elif command -v duckdb &>/dev/null; then
    # Idempotency: an existing install is reported, never silently replaced.
    DUCKDB_HAVE="$(duckdb --version 2>/dev/null || echo 'unknown')"
    if printf '%s' "$DUCKDB_HAVE" | grep -q "v${DUCKDB_VERSION}"; then
        echo "[OK] DuckDB already installed and matches the pin: ${DUCKDB_HAVE}"
    else
        echo "[OK] DuckDB already installed: ${DUCKDB_HAVE}"
        echo "     (setup.sh pins v${DUCKDB_VERSION}. Leaving your existing install alone.)"
    fi
else
    read -rp "Install DuckDB v${DUCKDB_VERSION}? [y/N] " ans
    if [[ "${ans:-N}" =~ ^[Yy]$ ]]; then
        echo "[Installing DuckDB v${DUCKDB_VERSION}...]"
        if curl -LsSf https://install.duckdb.org | DUCKDB_VERSION="$DUCKDB_VERSION" bash; then
            export PATH="$HOME/.local/bin:$HOME/.duckdb/bin:$PATH"
            echo "[OK] DuckDB $(duckdb --version 2>/dev/null || echo "v${DUCKDB_VERSION} installed")"
        else
            echo "[WARN] DuckDB install failed. Run manually:"
            echo "       curl https://install.duckdb.org | DUCKDB_VERSION=${DUCKDB_VERSION} bash"
        fi
    else
        echo "[SKIP] DuckDB not installed. Install manually with:"
        echo "       curl https://install.duckdb.org | DUCKDB_VERSION=${DUCKDB_VERSION} bash"
    fi
fi

# ── 7b. Optional agent plugin marketplace ─────────────────────────────────────
echo "━━ Optional: Power BI agent skills/plugins ━━━━━━━━━━━━━━━━━"
echo "  The 3 skills in .agents/skills/ are canonical and ship with this repo."
echo "  You do NOT need this section. These add extra coverage:"
echo "    tabular-editor (BPA rules, C# scripting, te/te2 CLI)"
echo "    pbi-desktop (connect to and query a live Desktop model)"
echo "    paginated-reports, custom-visuals, fabric-cli, fabric-admin, etl"
echo ""
echo "  Install with whichever harness you use:"
if command -v claude &>/dev/null; then
    echo "    [Claude Code found]"
    echo "      claude plugin marketplace add data-goblin/power-bi-agentic-development"
    echo "      claude plugin install tabular-editor@power-bi-agentic-development"
else
    echo "    Claude Code : claude plugin marketplace add data-goblin/power-bi-agentic-development"
fi
if command -v copilot &>/dev/null; then
    echo "    [Copilot CLI found]"
    echo "      copilot plugin marketplace add data-goblin/power-bi-agentic-development"
    echo "      copilot plugin install tabular-editor@power-bi-agentic-development"
else
    echo "    Copilot CLI : copilot plugin marketplace add data-goblin/power-bi-agentic-development"
fi
echo ""
echo "  Then list what's available:  claude plugin list  /  copilot plugin list"
echo "  Note: those plugins are GPL-3.0 and licensed for community use. If you copy"
echo "        skill text into THIS repo, keep the attribution link to the upstream."
echo ""

# ── 7c. Optional DuckDB MCP server (registration only, never enabled) ─────────
# Installing the CLI above does NOT give an agent DuckDB tools. The CLI is a shell
# tool; an MCP server is what an agent harness can call. Registering it is a
# separate, deliberate step that setup.sh prints but never performs — it never
# writes to a global harness config.
echo "━━ Optional: DuckDB MCP server (agent access) ━━━━━━━━━━━"
echo "  The DuckDB CLI above is for you, in a shell. To let an AGENT"
echo "  call DuckDB, your harness must also load an MCP server."
echo "  Those are three separate things: install the binary, register"
echo "  the server, then enable it in your harness."
echo ""
echo "  To register, add this as a sibling of powerbi-modeling-mcp in"
echo "  your harness MCP config (see mcp/mcp.json.example for locations):"
echo ""
echo "    \"duckdb-local\": {"
echo "      \"type\": \"stdio\","
echo "      \"command\": \"uvx\","
echo "      \"args\": [\"mcp-server-motherduck\","
echo "               \"--db-path\", \":memory:\","
echo "               \"--read-write\","
echo "               \"--query-timeout\", \"30\"]"
echo "    }"
echo ""
echo "  Notes before you paste that:"
echo "    - :memory: REQUIRES --read-write. Remove the flag and the"
echo "      server refuses to start. The database is throwaway and"
echo "      discarded on exit."
echo "    - That flag also permits filesystem writes via SQL. Point it"
echo "      at data you are happy to have written. A DuckDB file path"
echo "      gives you a read-only DATABASE (no DDL/DML), but it is NOT a"
echo "      filesystem sandbox: COPY ... TO still writes files in that"
echo "      mode. Both options can write files."
echo "    - No MotherDuck account, token or sign-in is needed anywhere."
echo "    - mcp-server-motherduck pins its own DuckDB version, which may"
echo "      differ from the CLI pin above. Both are fine; record which"
echo "      you used when comparing results."
echo ""
echo "  Then restart your harness and enable the server. Nothing above"
echo "  is registered automatically, and no global config is written."
echo ""

# ── 8. Quick validation ───────────────────────────────────────────────────────
echo "Running quick validation..."
python3 scripts/validate_repo.py && python3 scripts/validate_date_table.py || {
    echo ""
    echo "[WARN] Some validation checks failed — see output above."
    echo "       This is expected until you configure config/fiscal-calendar.json."
}

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Setup complete!"
echo ""
echo "  Next steps:"
echo "  1. Edit .env with your workspace + fiscal calendar settings"
echo "  2. Edit config/fiscal-calendar.json to match"
echo "  3. Open samples/pbip-calendar-baseline/CalendarBaseline.pbip in Power BI Desktop"
echo "  4. See docs/GETTING_STARTED.md for the full walkthrough"
echo "  5. Optional: install extra agent plugins (see section above)"
echo "  6. Optional: DuckDB CLI + MCP server (see sections 7a and 7c)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
