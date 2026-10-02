#!/usr/bin/env bash
# validate_pbir.sh — Validate all .Report folders with powerbi-report-author CLI or Python fallback.
# Run from the repo root: bash scripts/validate_pbir.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Discover repo-owned .Report folders.
#
# Only reports this repo owns may be validated. samples/visual-gallery-assets/ is a
# gitignored local staging folder holding 26 third-party Microsoft sample PBIPs; a bare
# `find` walks into those and reports failures we neither introduced nor can fix.
# scripts/pbir_discovery.py applies .gitignore and is the single source of truth
# (validate_report.py and validate_pbir_schema.py use it too). It needs python3, which
# the fallback branch below already requires; if python3 is missing, fall back to find
# with the staging folder excluded explicitly.
if command -v python3 &>/dev/null; then
    REPORT_DIRS=()
    # One absolute path per line; pbir_discovery.py never prints blank lines.
    while IFS= read -r report_dir; do
        REPORT_DIRS+=("$report_dir")
    done < <(python3 "$SCRIPT_DIR/pbir_discovery.py")

    if [ ${#REPORT_DIRS[@]} -eq 0 ]; then
        echo "[SKIP] No repo-owned .Report folders found."
        exit 0
    fi
else
    echo "[WARN] python3 not found; falling back to find with an explicit staging exclusion."
    REPORT_DIRS=()
    while IFS= read -r -d '' report_dir; do
        REPORT_DIRS+=("$report_dir")
    done < <(find "$REPO_ROOT" -type d -name "*.Report" -not -path "*/.*" -not -path "*/samples/visual-gallery-assets/*" -print0 2>/dev/null)

    if [ ${#REPORT_DIRS[@]} -eq 0 ]; then
        echo "[SKIP] No .Report folders found."
        exit 0
    fi
fi

if command -v powerbi-report-author &>/dev/null; then
    echo "[INFO] Using powerbi-report-author CLI..."
    FAIL=0
    FOUND=0

    for report_dir in "${REPORT_DIRS[@]}"; do
        FOUND=$((FOUND + 1))
        echo "Validating: $report_dir"
        # Capture output so we can detect PBIR_SCHEMA_UNREACHABLE (GAP-15).
        # The tool exits 0 even when it skipped schema validation entirely because
        # schemas could not be fetched over HTTPS. Inspecting the text is the only
        # reliable signal — a silent "pass" here is a false negative.
        if out=$(powerbi-report-author validate "$report_dir" 2>&1); then
            printf '%s\n' "$out"
            if printf '%s\n' "$out" | grep -q "PBIR_SCHEMA_UNREACHABLE"; then
                echo "[FAIL] $report_dir: schema validation was skipped (PBIR_SCHEMA_UNREACHABLE)." \
                     "Re-run on a machine with network access to validate against the full schemas (GAP-15)."
                FAIL=1
            else
                echo "[PASS] $report_dir"
            fi
        else
            printf '%s\n' "$out"
            echo "[FAIL] $report_dir"
            FAIL=1
        fi
    done

    if [ "$FAIL" -eq 1 ]; then
        echo "[FAIL] One or more PBIR validations failed."
        exit 1
    fi

    echo "[PASS] All $FOUND PBIR validation(s) passed via powerbi-report-author."
else
    echo "[INFO] powerbi-report-author CLI not found (e.g. on Linux without win/macos wheels)."
    echo "[INFO] Falling back to cross-platform pure-Python PBIR schema validator..."
    python3 "$SCRIPT_DIR/validate_pbir_schema.py"
fi

