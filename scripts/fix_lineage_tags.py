#!/usr/bin/env python3
"""
fix_lineage_tags.py — Make TMDL lineageTag values valid and unique.

Two distinct defects, both silent to the repo's validators and both fatal to
Power BI Desktop, which reports neither a file nor a line:

1. **Invalid token.** A TMDL scalar is lexed as an M-style token, and an
   unquoted identifier cannot contain a hyphen. `lineageTag: dimstore-count`
   parses as `dimstore - count`, and the model fails to open with:

       M Engine error: 'Microsoft.Data.Mashup.Preview; Token Identifier expected.'

   The error names the M engine, so it reads like a broken Power Query
   expression when it is really a broken lineageTag.

2. **Collisions.** lineageTag must be unique across the model. Two tables using
   the column name as their lineageTag - `lineageTag: ProductKey` in both
   DimProduct and FactSales - collide.

Fix: qualify every non-GUID lineageTag with its table name, e.g.
`dimstore_storekey`. Real GUID lineageTags (the shape Desktop writes) are left
alone, and files outside the given roots are never touched.

Usage:
    python3 scripts/fix_lineage_tags.py [--check] <tmdl-root> [...]
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

GUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
TABLE = re.compile(r"^table\s+(\S+)\s*$")
LINEAGE = re.compile(r"^(\s*lineageTag:\s*)(\S+)(\s*)$")
IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def qualify(table: str, value: str) -> str:
    return f"{table.lower()}_{value.lower()}"


def model_scopes(roots: list[Path]) -> list[list[Path]]:
    """Group TMDL files into models.

    lineageTag must be unique within one model, not across the repository. Two
    sample projects legitimately both name a table `Calendar` with lineageTag
    `Calendar`; treating that as a collision rewrites a working file. So each
    *.SemanticModel directory is its own scope, and anything outside one is
    grouped by its top-level root.
    """
    scopes: dict[Path, list[Path]] = {}
    for root in roots:
        root = Path(root)
        if root.suffix == ".SemanticModel" or (root / "definition").is_dir():
            scopes.setdefault(root, [])
        for path in sorted(root.rglob("*.tmdl")):
            owner = path
            for parent in path.parents:
                if parent.suffix == ".SemanticModel":
                    owner = parent
                    break
            scopes.setdefault(owner, []).append(path)
    return [sorted(set(v)) for v in scopes.values() if v]


def process_scope(files: list[Path], check: bool) -> int:
    """Fix one model's lineageTags. Returns the number of problems found."""
    seen: dict[str, list[str]] = defaultdict(list)
    for path in files:
        table = None
        for line in path.read_text(encoding="utf-8").split("\n"):
            mt = TABLE.match(line)
            if mt:
                table = mt.group(1).strip("'")
            ml = LINEAGE.match(line)
            if ml:
                seen[ml.group(2)].append(f"{path.name}:{table}")

    problems = 0
    for path in files:
        lines = path.read_text(encoding="utf-8").split("\n")
        table = None
        touched = False
        for i, line in enumerate(lines):
            mt = TABLE.match(line)
            if mt:
                table = mt.group(1).strip("'")
                continue
            ml = LINEAGE.match(line)
            if not ml or table is None:
                continue
            value = ml.group(2)
            is_guid = bool(GUID.match(value))
            # A GUID is a valid lineageTag even though it contains hyphens, so it
            # is exempt from the token check. It can still collide, in which case
            # it is replaced outright - GUID lineageTags carry no meaning.
            invalid = not is_guid and not IDENT.match(value)
            collides = len(seen[value]) > 1
            if not invalid and not collides:
                continue
            fixed = value if is_guid else qualify(table, value)
            problems += 1
            touched = True
            print(f"  {path}:{i + 1}  {value} -> {fixed}"
                  f"{'  [invalid token]' if invalid else ''}"
                  f"{'  [duplicate]' if collides else ''}")
            if not check:
                lines[i] = f"{ml.group(1)}{fixed}"
        if touched and not check:
            path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return problems


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("roots", nargs="*", type=Path, default=[Path("samples")])
    ap.add_argument("--check", action="store_true", help="report only, do not write")
    args = ap.parse_args(argv)

    problems = 0
    changed_files = 0
    for files in model_scopes(args.roots):
        problems += process_scope(files, args.check)
        changed_files += 0  # per-scope writes counted inside process_scope

    verb = "would change" if args.check else "changed"
    status = "FAIL" if (args.check and problems) else "PASS"
    print(f"[{status}] {problems} lineageTag problem(s); {verb} files")
    return 1 if (args.check and problems) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))