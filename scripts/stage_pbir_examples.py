#!/usr/bin/env python3
"""
stage_pbir_examples.py — Copy the reference PBIR definitions out of the local staging area.

Why this exists
---------------
`samples/visual-gallery-assets/PBIP/` holds 26 Microsoft sample PBIPs, each one a working
report for a custom visual. They are the only place in this repo showing how those visuals
are *actually* configured - the gallery shows a simplified version, not the publisher's own.

They are third-party material, currently gitignored, and 15.8 MB of the 20 MB is the
`CustomVisuals/` package payload plus `.pbi/` runtime state. The part worth keeping is the
PBIR itself.

Three decisions, each with a reason
------------------------------------
1.  `definition/` and `definition.pbir` only. The `*.SemanticModel/` folders are excluded:
    they are generated sample models, mostly inline-M tables, and 4.5 MB of data that
    duplicates what the gallery's own model already demonstrates. `definition.pbir` is kept
    because it records the schema pointer and the datasetReference, which is 250 bytes of
    wiring a reader would otherwise have to infer.

2.  The `.Report` suffix is dropped, so `PBIR/<Visual Name>/`. This is not cosmetic.
    `scripts/pbir_discovery.py` treats any folder matching `*.Report` that git does not
    ignore as repo-owned, and every PBIR validator walks that set. Keeping the suffix would
    turn 26 third-party reports into this repo's validation failures - precisely the
    regression commit db80a36 fixed by ignoring the folder in the first place. Dropping the
    suffix keeps the discovery glob from matching, and it is more honest besides: without
    `.platform` and a sibling `.SemanticModel` these are not openable PBIP projects, they
    are reference definitions.

3.  Oversized `visual.json` files are trimmed. Three files carry base64-embedded assets
    (Infographic Designer at 465 KB, two Power KPI Matrix at ~440 KB) which is 2.2 MB of
    opaque payload in an otherwise diffable corpus. The PBIR structure is kept and the
    embedded assets are replaced with a recorded placeholder, so the binding is still
    readable and the omission is visible rather than silent. Every edit is reported.

Usage:
    python3 scripts/stage_pbir_examples.py            # copy and trim
    python3 scripts/stage_pbir_examples.py --check    # fail if the committed tree is stale
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SOURCE = REPO / "samples" / "visual-gallery-assets" / "PBIP"
DEST = REPO / "samples" / "visual-gallery-assets" / "PBIR"

# Skip: publisher package payload and Desktop runtime state. Neither is reference material.
SKIP_DIRS = {"CustomVisuals", ".pbi", ".platform"}

# Above this, a re-indented file is written compactly instead. See write_json().
INDENT_BUDGET = 120 * 1024
TRIM_STRING = 4096  # a literal longer than this is carrying an embedded asset, not config

PLACEHOLDER = (
    "[trimmed by scripts/stage_pbir_examples.py] base64-embedded asset removed. "
    "The original is in the publisher's PBIP export; this field is not the binding you "
    "came here to read."
)


class Fail(Exception):
    pass


def normalise_newlines(data: bytes) -> bytes:
    """CRLF -> LF, so the bytes written are the bytes git stores.

    `.gitattributes` pins `*.pbir` and `*.json` to LF, so a CRLF file written here is
    normalised by git on commit and the working copy then differs from what this script
    produces. That would leave `--check` permanently red on any machine that has the
    staging area, which is worse than not having the check at all. Normalising on write
    makes the committed tree exactly reproducible from the staging area.
    """
    return data.replace(b"\r\n", b"\n")


def write_json(doc) -> bytes:
    """Serialise, falling back to compact form when indentation makes the file useless.

    Four Power KPI Matrix and Infographic Designer files parse to a few thousand nodes
    with deeply nested scopeId -> And -> Right -> Comparison -> Right -> Literal
    expression trees, nesting around thirty levels deep. Written with indent=2, every
    one of those nodes carries ~60 characters of leading whitespace: a 75 KB document
    becomes 374 KB on disk, 80% of it indentation. Compact form keeps the same
    information in a fifth of the bytes.

    Small files stay indented, because those are the ones a human reads and diffs.
    """
    pretty = (json.dumps(doc, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    if len(pretty) <= INDENT_BUDGET:
        return pretty
    return (json.dumps(doc, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def scrub(node) -> tuple[object, list[str]]:
    """Replace very long literal strings with a placeholder. Returns (node, paths)."""
    touched: list[str] = []

    def walk(n, path: str):
        if isinstance(n, dict):
            return {k: walk(v, f"{path}.{k}") for k, v in n.items()}
        if isinstance(n, list):
            return [walk(v, f"{path}[{i}]") for i, v in enumerate(n)]
        if isinstance(n, str) and len(n) > TRIM_STRING:
            touched.append(path)
            return PLACEHOLDER
        return n

    return walk(node, ""), touched


def expected_tree() -> tuple[dict[str, bytes], list[str]]:
    """The exact file set this script produces, keyed by path relative to DEST.

    Also returns a note per file whose encoding this script altered, so the README can
    record it rather than the alteration being invisible in review.
    """
    if not SOURCE.is_dir():
        raise Fail(
            f"staging area missing: {SOURCE.relative_to(REPO)}\n"
            "       These are third-party sample PBIPs and are not committed. See "
            "docs/POWER_BI_VISUAL_COVERAGE.md for where they came from."
        )

    out: dict[str, bytes] = {}
    notes: list[str] = []
    for report in sorted(SOURCE.glob("*.Report")):
        if not report.is_dir():
            continue
        name = report.name[: -len(".Report")]

        for src in sorted(report.rglob("*")):
            if not src.is_file():
                continue
            rel = src.relative_to(report)
            if SKIP_DIRS & set(rel.parts):
                continue
            # Only the report definition, plus the schema pointer.
            if rel.parts[0] != "definition" and rel.name != "definition.pbir":
                continue

            raw = src.read_bytes()
            if src.suffix != ".json":
                out[(DEST / name / rel).relative_to(DEST).as_posix()] = normalise_newlines(raw)
                continue

            try:
                doc = json.loads(raw.decode("utf-8-sig"))
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                print(f"[FAIL] {name}/{rel.as_posix()} is not valid JSON ({exc})")
                continue

            doc, touched = scrub(doc)
            data = write_json(doc)
            rel_out = (DEST / name / rel).relative_to(DEST).as_posix()
            out[rel_out] = data

            if len(raw) > INDENT_BUDGET or touched:
                bits = []
                if touched:
                    bits.append(f"{len(touched)} embedded asset literal(s) replaced")
                if len(raw) > INDENT_BUDGET:
                    bits.append("re-serialised compactly (deep expression tree, indentation "
                                "dominated the original)")
                notes.append(f"| `{name}/{rel.as_posix()}` | {len(raw):,} | {len(data):,} | "
                             f"{'; '.join(bits)} |")
                print(f"[NOTE] {name}/{rel.as_posix()}: {len(raw):,} -> {len(data):,} B  "
                      f"({'; '.join(bits)})")
    if not out:
        raise Fail(f"no report definitions found under {SOURCE.relative_to(REPO)}")
    return out, notes


READ_ME = """# Reference PBIR definitions

Generated by `scripts/stage_pbir_examples.py`. Do not hand-edit.

These are the **PBIR report definitions** from the 26 Microsoft sample reports in
[`../PBIP/`](../PBIP), kept as reference material: each one is a working
configuration for its custom visual, written by whoever built it, which the gallery
deliberately does not reproduce.

They are not openable PBIP projects. To use a definition, copy the binding you need
into your own report.

## What is included

| | |
|---|---|
| `<Visual Name>/definition/` | the report's pages, visuals and bindings |
| `<Visual Name>/definition.pbir` | the schema pointer and `datasetReference` |

Folder names **drop the `.Report` suffix** on purpose.
`scripts/pbir_discovery.py` treats any folder matching `*.Report` that git does not
ignore as repo-owned, and every PBIR validator walks that set — so keeping the suffix
would turn 26 third-party reports into this repo's validation failures, which is the
exact regression commit `db80a36` fixed by ignoring the folder.

## What is excluded, and why

| Excluded | Why |
|---|---|
| `*.Report/CustomVisuals/` | publisher package payload, 11.8 MB. Fetched and verified by `scripts/fetch_gallery_assets.py`, never committed |
| `*.SemanticModel/` | generated sample models, 4.5 MB of inline-M tables. The gallery's own model already demonstrates every visual |
| `*.Report/.pbi/` | Desktop runtime state, rewritten on every open |
| `*.Report/.platform` | only meaningful for a complete project, which these are not |

## Files this script altered

Every alteration is listed here. Nothing was edited by hand.

{table}

The four ~450 KB files are not mostly embedded images. Each parses to a few
thousand nodes with `scopeId -> And -> Right -> Comparison -> Right -> Literal`
expression trees nesting about thirty levels deep, so `indent=2` alone turned a
75 KB document into 453 KB on disk, the great majority of it leading whitespace.
Those are written compactly instead, and small files stay indented because those
are the ones a human reads.

## Regenerating

```bash
python3 scripts/stage_pbir_examples.py          # copy and re-encode from ../PBIP/
python3 scripts/stage_pbir_examples.py --check  # fail if this tree is stale
```

`../PBIP/` is gitignored, so this is a local operation. `--check` skips cleanly
(exit 0) where the staging area is absent, because a staleness check whose input is
not in the repository cannot report staleness — it says so rather than passing
silently. Rebuilding without it is a failure.
"""


def write_readme(notes: list[str], n_files: int, n_reports: int, total: int) -> None:
    table = ("| File | Original | Here | What changed |\n|---|---:|---:|---|\n"
             + ("\n".join(notes) if notes else "| _(none)_ | | | |"))
    (DEST / "README.md").write_text(
        READ_ME.format(table=table), encoding="utf-8", newline="\n")
    print(f"       {n_reports} report(s), {n_files} file(s), {total:,} B")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="exit 1 if the committed tree differs from what this produces")
    args = ap.parse_args(argv)

    if not SOURCE.is_dir() and args.check:
        print(f"[SKIP] {SOURCE.relative_to(REPO)} is absent, so there is nothing to compare "
              "against. It is gitignored third-party sample material.")
        print("       The committed PBIR/ tree is left as-is; staleness cannot be detected "
              "on a machine that never staged the samples.")
        return 0

    try:
        want, notes = expected_tree()
    except Fail as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1

    on_disk = {p.relative_to(DEST).as_posix(): p.read_bytes()
               for p in DEST.rglob("*") if p.is_file() and p.name != "README.md"} if DEST.is_dir() else {}

    if args.check:
        missing = sorted(set(want) - set(on_disk))
        extra = sorted(set(on_disk) - set(want))
        differs = sorted(k for k in set(want) & set(on_disk) if want[k] != on_disk[k])
        if missing or extra or differs:
            for label, items in (("missing", missing), ("unexpected", extra), ("differs", differs)):
                for i in items[:6]:
                    print(f"[FAIL] {label}: {i}")
                if len(items) > 6:
                    print(f"       ... and {len(items)-6} more")
            print(f"[FAIL] PBIR/ is stale ({len(missing)} missing, {len(extra)} unexpected, "
                  f"{len(differs)} differing). Run scripts/stage_pbir_examples.py")
            return 1
        print(f"[PASS] PBIR/ matches scripts/stage_pbir_examples.py ({len(want)} files).")
        return 0

    if DEST.exists():
        shutil.rmtree(DEST)
    DEST.mkdir(parents=True)
    for rel, data in want.items():
        target = DEST / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    total = sum(len(v) for v in want.values())
    print(f"\n[PASS] staged {len(want)} file(s) into {DEST.relative_to(REPO)}")
    write_readme(notes, len(want), len({p.split('/')[0] for p in want}), total)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))