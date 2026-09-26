#!/usr/bin/env bash
# .devcontainer/setup.sh — post-create setup for the Dev Container.
# Installs uv, pbir-cli, and warms up the powerbi-modeling-mcp npm cache.
set -euo pipefail

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Power BI Dev — Dev Container Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 1. Install uv (fast Python package manager)
if ! command -v uv &>/dev/null; then
    echo "==> Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
    echo "uv installed: $(uv --version)"
else
    echo "==> uv already present: $(uv --version)"
fi

# Ensure uv is on PATH for remainder of script
export PATH="$HOME/.local/bin:$PATH"

# 2. Install pbir-cli
echo "==> Installing pbir-cli..."
uv tool install pbir-cli 2>/dev/null || uv tool upgrade pbir-cli
echo "pbir-cli: $(powerbi-report-author --version 2>/dev/null || echo 'installed')"

# 3. Warm up powerbi-modeling-mcp npx cache (best-effort)
echo "==> Warming up powerbi-modeling-mcp cache..."
npx -y @microsoft/powerbi-modeling-mcp@latest --version 2>/dev/null || true

# 4. Copy .env if not present
if [ ! -f .env ] && [ -f .env.example ]; then
    cp .env.example .env
    echo "==> Created .env from .env.example — edit it with your credentials."
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Setup complete!"
echo "  Next: edit .env, then open a PBIP in Power BI Desktop."
echo "  See docs/GETTING_STARTED.md for the full walkthrough."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
