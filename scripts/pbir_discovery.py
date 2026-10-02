#!/usr/bin/env python3
"""
pbir_discovery.py — Shared discovery of PBIR `.Report` folders for validators.

Every PBIR validator in this repo (validate_report.py, validate_pbir_schema.py,
validate_pbir.sh) needs the same thing: "which .Report folders should I check?".
Answering it in one place avoids three scripts drifting apart.

Why this exists: validators must only inspect reports this repo owns. A bare
`rglob("*.Report")` also picks up third-party PBIP projects that happen to sit
inside a gitignored local staging folder. Those are reference material, not
ours — validating their layout produces failures we cannot fix and should not
be blocked by. `samples/visual-gallery-assets/` is the current example: 26
Microsoft sample PBIPs, all gitignored.

So: honour `.gitignore`. A `.Report` folder that git ignores is skipped.

The gitignore matcher below is deliberately minimal. It supports only the
constructs that actually appear in this repo's `.gitignore`:

  - blank lines and `#` comments
  - `!` negation
  - a trailing `/` meaning "directory and everything under it"
  - a leading `/` or an embedded `/` meaning "anchored to the ignore file's dir"
  - `*` (not crossing `/`), `?`, `**` (crossing `/`)

Patterns it cannot model correctly are ignored rather than guessed. Git itself
remains the authority: if you need an exact answer, use `git check-ignore`.

Usage:
    python3 scripts/pbir_discovery.py            # list repo-owned .Report dirs
    python3 scripts/pbir_discovery.py --explain  # list all, and why each is kept
"""
from __future__ import annotations

import re
import sys
from pathlib import Path


def _translate(pattern: str) -> tuple[re.Pattern[str], bool]:
    """Compile one gitignore pattern. Returns (regex, dir_only)."""
    dir_only = pattern.endswith("/")
    if dir_only:
        pattern = pattern.rstrip("/")

    anchored = "/" in pattern
    if pattern.startswith("/"):
        pattern = pattern.lstrip("/")
    elif not anchored:
        pattern = "**/" + pattern

    # Escape regex metacharacters, then re-introduce the glob wildcards.
    out: list[str] = []
    i = 0
    while i < len(pattern):
        ch = pattern[i]
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("/**", i) and i + 3 == len(pattern):
            out.append("(?:/.*)?")
            i += 3
        elif ch == "*":
            out.append("[^/]*")
            i += 1
        elif ch == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(ch))
            i += 1

    body = "".join(out)
    # `dir_only` patterns still have to match a path prefix, e.g.
    # `artifacts/` must exclude `artifacts/x/y.Report`.
    suffix = r"(?:/.*)?" if dir_only else r"(?:/.*)?"
    return re.compile(f"^{body}{suffix}$"), dir_only


def load_patterns(gitignore: Path) -> list[tuple[re.Pattern[str], bool, bool]]:
    """Return [(regex, negated, dir_only)] in file order."""
    if not gitignore.is_file():
        return []
    out: list[tuple[re.Pattern[str], bool, bool]] = []
    for raw in gitignore.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        negated = line.startswith("!")
        if negated:
            line = line[1:]
        line = line.strip()
        if not line:
            continue
        try:
            regex, dir_only = _translate(line)
        except re.error:
            continue
        out.append((regex, negated, dir_only))
    return out


def is_ignored(rel_posix: str, patterns) -> bool:
    """True when `rel_posix` (repo-relative, forward slashes) is git-ignored.

    Later patterns win, matching git's own precedence.
    """
    result = False
    for regex, negated, _dir_only in patterns:
        if regex.match(rel_posix):
            result = not negated
    return result


def report_dirs(root: Path) -> list[Path]:
    """Repo-owned `.Report` folders under `root`, sorted, gitignore respected."""
    return sorted(p for p, is_owned in all_report_dirs(root) if is_owned)


def all_report_dirs(root: Path) -> list[tuple[Path, bool]]:
    """Every `.Report` folder under `root` as (path, is_repo_owned). For --explain."""
    root = root.resolve()
    owned = ownership_filter(root)
    out: list[tuple[Path, bool]] = []
    for p in sorted(root.rglob("*.Report")):
        if not p.is_dir():
            continue
        out.append((p, owned(p)))
    return out


# Always-excluded regardless of .gitignore. node_modules and __pycache__ are
# already gitignored, but a validator should not silently depend on that.
ALWAYS_SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv"}


def ownership_filter(root: Path):
    """Return `owned(path) -> bool`: True when `path` belongs to this repo.

    Used by the validators that walk for arbitrary globs (*.json, *.pbix,
    *.pbip) and need the same rule as report_dirs: skip anything git ignores, so
    a gitignored local staging folder never turns into a validation failure.
    """
    root = root.resolve()
    patterns = load_patterns(root / ".gitignore")

    def owned(path: Path) -> bool:
        try:
            rel = path.resolve().relative_to(root)
        except ValueError:
            return False
        if any(part in ALWAYS_SKIP_DIRS for part in rel.parts):
            return False
        return not is_ignored(rel.as_posix(), patterns)

    return owned


def main(argv: list[str]) -> int:
    root = Path(__file__).resolve().parent.parent
    explain = "--explain" in argv

    if explain:
        entries = all_report_dirs(root)
        for path, owned in entries:
            tag = "owned  " if owned else "IGNORED"
            print(f"{tag}  {path.relative_to(root).as_posix()}")
        print(f"\n{len(entries)} discovered, {sum(1 for _, o in entries if o)} repo-owned.")
        return 0

    for path in report_dirs(root):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))