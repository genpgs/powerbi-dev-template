#!/usr/bin/env python3
"""
reduce_model.py — Produce a reduced copy of a TMDL semantic model, for bisecting
a Desktop load failure.

A PBIP that Power BI Desktop refuses to open reports only
"M Engine error: ... Token Identifier expected", with no file or line. To find
which object is at fault you have to remove objects until the project opens, then
put them back. This builds those reduced copies.

Keeps only the named tables, and drops any relationship whose endpoints are not
both kept, so the result is a loadable model rather than a dangling reference.
The PBI_QueryOrder annotation is filtered to match, since a stale list there is
its own kind of confusing.

Usage:
    python3 scripts/reduce_model.py SRC_DIR DST_DIR TableA,TableB,...
"""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path


def filter_model_tmdl(text: str, keep: set[str]) -> str:
    """Keep only `ref table` lines for tables in the keep set."""
    out = []
    for line in text.split("\n"):
        m = re.match(r"^\s*ref table (\S+)\s*$", line)
        if m and m.group(1).strip("'") not in keep:
            continue
        out.append(line)
    text = "\n".join(out)

    # Rewrite the PBI_QueryOrder annotation to list only surviving objects.
    def _qorder(match: re.Match) -> str:
        items = [i.strip().strip('"') for i in match.group(1).split(",")]
        items = [i for i in items if i in keep or not i[0].isupper()]
        return "annotation PBI_QueryOrder = [" + ", ".join(f'"{i}"' for i in items) + "]"

    return re.sub(r'annotation PBI_QueryOrder = \[([^\]]*)\]', _qorder, text)


def filter_relationships(text: str, keep: set[str]) -> str:
    """Drop whole relationship blocks whose from/to tables are not both kept."""
    blocks = re.split(r"\n(?=relationship )", "\n" + text.strip())
    kept = []
    for b in blocks:
        b = b.strip("\n")
        if not b.strip():
            continue
        tables = re.findall(r"^\s*(?:fromColumn|toColumn):\s*(\S+?)\.(\S+)\s*$", b, re.M)
        names = {t[0].strip("'") for t in tables}
        if names and names <= keep:
            kept.append(b)
    return "\n\n".join(kept) + ("\n" if kept else "")


def reduce(src: Path, dst: Path, keep) -> set[str]:
    """Write a reduced copy of a model definition folder. Returns the kept names."""
    keep = {t.strip() for t in keep if t.strip()}
    if dst.exists():
        shutil.rmtree(dst)
    tables_dir = dst / "tables"
    tables_dir.mkdir(parents=True)

    for name in ("database.tmdl", "expressions.tmdl"):
        shutil.copy2(src / name, dst / name)

    (dst / "model.tmdl").write_text(
        filter_model_tmdl((src / "model.tmdl").read_text(encoding="utf-8"), keep),
        encoding="utf-8", newline="\n",
    )

    rel = src / "relationships.tmdl"
    if rel.is_file():
        (dst / "relationships.tmdl").write_text(
            filter_relationships(rel.read_text(encoding="utf-8"), keep),
            encoding="utf-8", newline="\n",
        )

    copied = set()
    for tmdl in sorted((src / "tables").glob("*.tmdl")):
        if tmdl.stem not in keep:
            continue
        shutil.copy2(tmdl, tables_dir / tmdl.name)
        copied.add(tmdl.stem)
    return copied


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 2
    src = Path(argv[0])
    dst = Path(argv[1])
    keep = {t.strip() for t in argv[2].split(",") if t.strip()}
    copied = reduce(src, dst, keep)
    missing = keep - copied
    print(f"[INFO] kept: {', '.join(sorted(copied))}")
    if missing:
        print(f"[WARN] requested but absent: {', '.join(sorted(missing))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))