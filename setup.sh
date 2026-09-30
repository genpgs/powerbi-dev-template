#!/usr/bin/env bash
# setup.sh — Interactive post-clone setup for powerbi-dev-template.
# Run from the repo root: bash setup.sh
set -euo pipefail

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
if [ -d .git ]; then
    read -rp "Install pre-commit validation hook? [Y/n] " ans
    if [[ "${ans:-Y}" =~ ^[Yy]$ ]]; then
        cp hooks/pre-commit .git/hooks/pre-commit
        chmod +x .git/hooks/pre-commit
        echo "[OK] Pre-commit hook installed — will run validate_repo.py + validate_date_table.py on staged PBIP/TMDL changes."
    else
        echo "[SKIP] Pre-commit hook not installed. Run manually: cp hooks/pre-commit .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit"
    fi
else
    echo "[SKIP] Not a git repo — skipping pre-commit hook installation. Run 'git init' first."
fi

# ── 7. MCP config reminder ────────────────────────────────────────────────────
echo ""
echo "━━ MCP Configuration ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Copy mcp/mcp.json.example to your harness config:"
echo "    Antigravity : ~/.config/antigravity/mcp.json"
echo "    VS Code     : .vscode/mcp.json"
echo "    Claude Code : ~/.claude/mcp.json"
echo ""

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
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
