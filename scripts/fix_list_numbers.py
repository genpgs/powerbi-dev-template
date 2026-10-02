#!/usr/bin/env python3
"""
fix_list_numbers.py — Rewrite `List.Numbers({a..b})` to a valid call.

Power Query M has no `a..b` range operator. `{1..n}` parses as a one-element list
containing a record, so `List.Numbers({1..60})` hands a list to a function whose
first parameter is a number. M reports the resulting overload failure as

    [Expression.Error] 1 arguments were passed to a function which expects
    between 2 and 3.

which names neither the function nor the table, and appears identically for every
partition that shares the mistake - all 13 in the gallery model.

The rewrite is arithmetically exact:

    List.Numbers({1..X})  ->  List.Numbers(1, X)
    List.Numbers({0..X})  ->  List.Numbers(0, X + 1)

`List.Numbers(from, count)` emits `count` values starting at `from`, so the first
form is unchanged and the second gains the extra element that `{0..X}` implied.

Usage:
    python3 scripts/fix_list_numbers.py [--check] <tmdl-root> [...]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

CALL = "List.Numbers("
RANGE = re.compile(r"^\{(0|1)\.\.(.+)\}$", re.S)
# Two more M mistakes that surface only at refresh, with no file or line:
#   - a lambda whose body starts with a bare `{` on the next line: M reads that
#     as a let block, so `Source = e{0}` becomes a variable reference and fails
#     with "The name 'Source' wasn't recognized".
#   - `Number.Pi`, which does not exist in M; it fails with "The name
#     'Number.Pi' wasn't recognized".
# `[ \t]*$` not `\s*$`: \s matches newlines, so \s*$ can swallow the line break
# and the pattern silently stops matching the shape it is meant to catch.
LAMBDA_BRACE = re.compile(r"=>[ \t]*\r?\n[ \t]*\{[ \t]*\r?$", re.M)
PI = re.compile(r"Number\.Pi\b")
TWO_PI = 6.28318530717959


def match_args(text: str, start: int) -> tuple[str, int]:
    """Given index of '(' return (inner text, index just past matching ')')."""
    depth = 0
    in_str = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
            if depth == 0:
                return text[start + 1:i], i + 1
    raise ValueError("unbalanced parentheses")


def fix(text: str, path: Path) -> tuple[str, int]:
    count = 0
    while True:
        at = text.find(CALL)
        if at < 0:
            break
        open_paren = at + len(CALL) - 1
        try:
            inner, end = match_args(text, open_paren)
        except ValueError:
            text = text[:at] + "\x00" + text[at + len(CALL):]
            continue
        m = RANGE.match(inner.strip())
        if not m:
            text = text[:at] + "\x00" + text[at + len(CALL):]
            continue
        lo, hi = m.group(1), m.group(2).strip()
        repl = f"List.Numbers({lo}, {hi})" if lo == "1" else f"List.Numbers(0, {hi} + 1)"
        count += 1
        print(f"  {path.name}: {CALL}{inner.strip()}) -> {repl}")
        text = text[:at] + repl + text[end:]
    return text.replace("\x00", CALL), count


def strip_comments(text: str) -> str:
    """Blank out comment lines, preserving line numbering.

    The checks below look for code constructs, and a line documenting the very
    construct being banned would otherwise trip them.
    """
    return "\n".join("" if line.lstrip().startswith("//") else line
                     for line in text.split("\n"))


def audit(path: Path, text: str) -> list[str]:
    """Report M constructs that parse or resolve wrongly. Never auto-rewrites."""
    code = strip_comments(text)
    out = []
    for m in LAMBDA_BRACE.finditer(code):
        line = code[:m.start()].count("\n") + 1
        out.append(f"{path.name}:{line}: bare '{{' after '=>' is read as a let block, "
                   f"not a record - use '[' ']'")
    for m in PI.finditer(code):
        line = code[:m.start()].count("\n") + 1
        out.append(f"{path.name}:{line}: M has no Number.Pi - use a literal (2*Pi = {TWO_PI})")
    return out


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("roots", nargs="*", type=Path, default=[Path("samples")])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)

    total = 0
    for root in args.roots:
        for path in sorted(Path(root).rglob("*.tmdl")):
            original = path.read_text(encoding="utf-8")
            updated, n = fix(original, path)
            if n:
                total += n
                if not args.check:
                    path.write_text(updated, encoding="utf-8", newline="\n")
            for problem in audit(path, original if not n else updated):
                print(f"  [ERROR] {problem}")
                total += 1

    status = "FAIL" if (args.check and total) else "PASS"
    verb = "would fix" if args.check else "fixed"
    print(f"[{status}] {total} List.Numbers range call(s) {verb}; "
          f"plus any [ERROR] lines above")
    return 1 if (args.check and total) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
