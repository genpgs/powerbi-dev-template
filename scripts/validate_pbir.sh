#!/usr/bin/env bash
# validate_pbir.sh — Validate all .Report folders with the powerbi-report-author CLI.
# Run from the repo root: bash scripts/validate_pbir.sh
# Requires: uv tool install pbir-cli
set -euo pipefail

if ! command -v powerbi-report-author &>/dev/null; then
    echo "[SKIP] powerbi-report-author not installed."
    echo "       Install with: uv tool install pbir-cli"
    exit 0
fi

FAIL=0
FOUND=0

while IFS= read -r -d '' report_dir; do
    FOUND=$((FOUND + 1))
    echo "Validating: $report_dir"
    if powerbi-report-author validate "$report_dir"; then
        echo "[PASS] $report_dir"
    else
        echo "[FAIL] $report_dir"
        FAIL=1
    fi
done < <(find samples -type d -name "*.Report" -print0 2>/dev/null)

if [ "$FOUND" -eq 0 ]; then
    echo "[SKIP] No .Report folders found under samples/"
    exit 0
fi

if [ "$FAIL" -eq 1 ]; then
    echo "[FAIL] One or more PBIR validations failed."
    exit 1
fi

echo "[PASS] All $FOUND PBIR validation(s) passed."
