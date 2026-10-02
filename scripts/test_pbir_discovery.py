#!/usr/bin/env python3
"""
test_pbir_discovery.py — Differential test for scripts/pbir_discovery.py.

The gitignore matcher in pbir_discovery is a deliberate reimplementation, so
the only trustworthy test is against git itself. For a corpus of paths, compare
`is_ignored()` to `git check-ignore` and fail on any disagreement.

Run:  python3 scripts/test_pbir_discovery.py
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pbir_discovery import is_ignored, load_patterns  # noqa: E402

REPO = Path(__file__).resolve().parent.parent

# Paths chosen to exercise anchoring, dir-only, **/.pbi/, negation-free rules,
# bare patterns, and things that must NOT be ignored.
CORPUS = [
    "README.md",
    "scripts/pbir_discovery.py",
    "samples/pbip-visual-gallery/VisualGallery.Report",
    "samples/pbip-calendar-baseline/CalendarBaseline.Report",
    "samples/visual-gallery-assets/manifest.csv",
    "samples/visual-gallery-assets/PBIVIZ/WordCloud1447959067750.2.3.4.0.pbiviz",
    "samples/visual-gallery-assets/PBIP/Sankey Chart.Report",
    "samples/visual-gallery-assets/PBIP/Chiclet Slicer.Report/definition/report.json",
    "artifacts/screenshots/Overview.png",
    ".claude/skills/playwright-cli/SKILL.md",
    ".vscode/settings.json",
    ".env",
    "data/sales.csv",
    "samples/pbip-visual-gallery/VisualGallery.Report/CustomVisuals/WordCloud1447959067750/package.json",
    "samples/pbip-visual-gallery/VisualGallery.SemanticModel/.pbi/editorSettings.json",
    "samples/pbip-visual-gallery/VisualGallery.SemanticModel/.pbi/cache.abf",
    "samples/pbip-visual-gallery/VisualGallery.SemanticModel/diagramLayout.json",
    "samples/pbip-visual-gallery/VisualGallery.SemanticModel/semanticModelDiagramLayout.json",
    "samples/pbip-visual-gallery/foo.pbiviz",
    "docs/POWER_BI_VISUAL_COVERAGE.md",
]


def git_says_ignored(paths: list[str]) -> set[str]:
    """Ask git which paths are ignored. One batched call.

    Uses bytes on stdin deliberately: in text mode Python translates `\\n` to
    `\\r\\n` on Windows, git reads the trailing `\\r` as part of each path, and
    then quotes its output — which would make every path look unmatched.
    """
    proc = subprocess.run(
        ["git", "check-ignore", "--stdin"],
        input=("\n".join(paths) + "\n").encode("utf-8"),
        capture_output=True,
        cwd=REPO,
    )
    if proc.returncode not in (0, 1):
        raise SystemExit(f"git check-ignore failed: {proc.stderr.decode().strip()}")
    out = set()
    for line in proc.stdout.decode("utf-8").splitlines():
        line = line.strip()
        if line.startswith('"') and line.endswith('"'):
            line = line[1:-1]
        if line:
            out.add(line)
    return out


def main() -> int:
    patterns = load_patterns(REPO / ".gitignore")
    if not patterns:
        print("[FAIL] no patterns loaded from .gitignore")
        return 1

    expected = git_says_ignored(CORPUS)
    mismatches: list[str] = []

    for path in CORPUS:
        mine = is_ignored(path, patterns)
        theirs = path in expected
        mark = "ok " if mine == theirs else "DIFF"
        if mine != theirs:
            mismatches.append(path)
        print(f"[{mark}] {path}  matcher={mine} git={theirs}")

    print()
    if mismatches:
        print(f"[FAIL] {len(mismatches)} disagreement(s) with git: {mismatches}")
        return 1
    print(f"[PASS] matcher agrees with git check-ignore on all {len(CORPUS)} paths.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())