#!/usr/bin/env python3
"""
validate_m_expressions.py — Structural validator for M expression bodies embedded in TMDL.

A TMDL `expression` body is stored as an opaque literal string, so the TMDL parser never
compiles the M. A syntactically invalid M body therefore survives a TMDL folder import and
every schema-level validator, then blocks the project in Power BI Desktop:

    Syntax error in expression 'fnCalendar'. Token Identifier expected.
    Microsoft.Mashup.Host.Document

This script covers what the TMDL parser does not: file encoding hygiene, delimiter balance
with correct string and comment tracking, the shape of the terminating `in` expression, bare
relative `File.Contents` paths in partition sources (which do not resolve against the PBIP
root), and calls to M module members that do not exist (GAP-12).

GAP-12 is the DAX/Excel-to-M contamination class. `MAX()`/`MIN()` are DAX and Excel
idioms, not M ones: the `Number` module has neither `Max` nor `Min`, so the body imports
cleanly and only fails at refresh, when Desktop reports

    1 query is blocked by the following error:
    The import Number.Max matches no module reference.

Nothing upstream can see this. The TMDL parser stores `expression` bodies as opaque
strings, the JSON schema treats them as strings, and a M evaluator is required to reject
them - so the error surfaces only on a machine that can refresh. The member denylist below
was checked against the Microsoft Learn M reference on 2026-03-25.

Run from the repo root:  python3 scripts/validate_m_expressions.py
Target specific models: python3 scripts/validate_m_expressions.py path/to/Model.SemanticModel

Exits 0 when every expression is valid, 2 otherwise.
"""

import re
import sys
from pathlib import Path

EXIT_OK, EXIT_FAIL = 0, 2
PAIRS = {"(": ")", "[": "]", "{": "}"}

# GAP-12: module members that do not exist in Power Query M. Each entry is
# (replacement, why-it-happens). Keep this list to members confirmed absent from the
# official reference - a false positive here costs more than a missed detection, because
# this is a denylist, not an allowlist, and a wrong entry blocks correct M.
#   https://learn.microsoft.com/en-us/powerquery-m/number-functions
#   https://learn.microsoft.com/en-us/powerquery-m/text-functions
PHANTOM_MEMBERS = {
    "Number": {
        "Max": "List.Max({a, b})", "Min": "List.Min({a, b})",
        "Sum": "List.Sum(list)", "Average": "List.Average(list)",
        "Count": "List.Count(list)", "Concat": "List.Combine(lists)",
        "Floor": "Number.RoundDown(x)", "Ceiling": "Number.RoundUp(x)",
        "Rank": "Table.Sort(...)[Index]",
        "IsBlank": "x = null", "IsInfinity": "Double.IsInfinity(x)",
    },
    "Text": {
        "Len": "Text.Length(x)", "Left": "Text.Start(x, n)", "Right": "Text.End(x, n)",
        "Concat": "Text.Combine(list, sep)", "Find": "Text.PositionOf(x, sub)",
        "Pad": "Text.PadStart(x, n, c) / Text.PadEnd(x, n, c)",
        "IsBlank": "x = null", "IsEmpty": "x = \"\"",
    },
}


def extract_expressions(text):
    """Return [(name, body_lines)] for each `expression <name> =` block."""
    exprs, current, body = [], None, []

    for line in text.splitlines():
        if line.startswith("expression ") and line.rstrip().endswith("="):
            if current is not None:
                exprs.append((current, body))
            current = line[len("expression "):].rstrip()[:-1].strip()
            body = []
        elif current is not None:
            # A new top-level declaration (no leading indent) ends the body.
            if line and not line[0].isspace():
                exprs.append((current, body))
                current, body = None, []
            else:
                body.append(line)

    if current is not None:
        exprs.append((current, body))
    return exprs


def check_delimiters(name, body):
    """Walk the M body tracking string/comment state; return a list of errors."""
    errors = []
    stack, i, n = [], 0, len(body)
    line_no = 1
    in_str = in_line_comment = in_block_comment = False

    while i < n:
        ch = body[i]
        nxt = body[i + 1] if i + 1 < n else ""

        if ch == "\n":
            line_no += 1
            in_line_comment = False
            i += 1
            continue

        if in_line_comment:
            i += 1
            continue

        if in_block_comment:
            if ch == "*" and nxt == "/":
                in_block_comment = False
                i += 2
                continue
            i += 1
            continue

        if in_str:
            if ch == '"':
                if nxt == '"':  # escaped quote inside a verbatim string
                    i += 2
                    continue
                in_str = False
            i += 1
            continue

        if ch == "/" and nxt == "/":
            in_line_comment = True
            i += 2
            continue
        if ch == "/" and nxt == "*":
            in_block_comment = True
            i += 2
            continue
        if ch == '"':
            in_str = True
            i += 1
            continue
        if ch in PAIRS:
            stack.append((ch, line_no))
            i += 1
            continue
        if ch in PAIRS.values():
            if not stack:
                errors.append(f"{name}: line {line_no}: unmatched closing '{ch}'")
            else:
                open_ch, open_line = stack.pop()
                if PAIRS[open_ch] != ch:
                    errors.append(
                        f"{name}: line {line_no}: '{ch}' closes '{open_ch}' "
                        f"opened at line {open_line}"
                    )
            i += 1
            continue
        i += 1

    if in_str:
        errors.append(f"{name}: unterminated string literal at end of body")
    if in_block_comment:
        errors.append(f"{name}: unterminated /* */ comment at end of body")
    for open_ch, open_line in stack:
        errors.append(f"{name}: unclosed '{open_ch}' opened at line {open_line}")

    return errors


def strip_literals(line):
    """Blank out quoted string contents so comment/terminator scans ignore them."""
    out, i, in_str, n = [], 0, False, len(line)
    while i < n:
        ch = line[i]
        if in_str:
            if ch == '"':
                if i + 1 < n and line[i + 1] == '"':
                    i += 2
                    continue
                in_str = False
            i += 1
            continue
        if ch == '"':
            in_str = True
            out.append(" ")
            i += 1
            continue
        if ch == "/" and i + 1 < n and line[i + 1] == "/":
            break
        out.append(ch)
        i += 1
    return "".join(out)


def check_body_shape(name, body):
    """Catch the TMDL/M gotcha: a ';' on the terminating `in` expression.

    M has no ';' statement terminator, so a trailing ';' makes the parser start a fresh
    expression and demand a token identifier at the next position. The offending `;` sits
    on whichever line carries the `in` value, which is not always the line starting with
    `in`, so the check inspects the last meaningful line of the body.
    """
    errors = []
    # A line is meaningful when it has content that is not purely a comment.
    meaningful = [ln for ln in body if ln.strip() and strip_literals(ln).strip()]

    if not any(re.match(r"^\s*in\b", ln) for ln in meaningful):
        errors.append(f"{name}: body has no terminating 'in' expression")
        return errors

    last = meaningful[-1]
    last_idx = body.index(last)
    if strip_literals(last).rstrip().endswith(";"):
        errors.append(
            f"{name}: line {last_idx + 1}: trailing ';' on the terminating 'in' expression - "
            f"M does not use ';' as a statement terminator, so the parser then demands a "
            f"token identifier at the next position"
        )

    return errors


def check_file_paths(tables_dir):
    """Flag bare relative File.Contents paths in partition sources.

    File.Contents resolves a relative path against the M engine's working directory, not
    against the PBIP root, so File.Contents("data/x.xlsx") fails on refresh no matter where
    the project folder lives. The path must be built from a parameter, e.g.
    BasePath & "data/x.xlsx".

    Only a string literal in first-argument position is matched, so the correct
    `File.Contents(BasePath & "data/x.xlsx")` form never matches here and needs no exemption.
    """
    errors = []
    if not tables_dir.is_dir():
        return errors

    literal = re.compile(r"""File\.Contents\(\s*["']([^"']+)["']""", re.IGNORECASE)
    absolute = re.compile(r"^[A-Za-z]:[\\/]|^\\\\|^/")

    for table_file in sorted(tables_dir.glob("*.tmdl")):
        lines = table_file.read_text(encoding="utf-8").splitlines()
        for line_no, line in enumerate(lines, 1):
            code = line.split("//", 1)[0]
            for path in literal.findall(code):
                if absolute.match(path):
                    continue  # absolute path - resolves on its own
                errors.append(
                    f"{table_file.name}: line {line_no}: File.Contents(\"{path}\") uses a bare "
                    f"relative path, which does not resolve against the PBIP root; build it "
                    f"from a parameter, e.g. BasePath & \"{path}\" (GAP-08)"
                )
    return errors


def check_phantom_members(label, lines):
    """Flag `Module.Member` calls where Member does not exist in M (GAP-12).

    Scans line by line with string literals and `//` comments stripped, so a member name
    appearing in prose or inside a quoted string is not reported.
    """
    errors = []
    for line_no, line in enumerate(lines, 1):
        code = strip_literals(line)
        for module, members in PHANTOM_MEMBERS.items():
            for member, fix in members.items():
                if re.search(rf"\b{module}\.{member}\b", code):
                    errors.append(
                        f"{label}: line {line_no}: '{module}.{member}' matches no module "
                        f"reference - it is a DAX/Excel name, not an M one. Use {fix} (GAP-12)"
                    )
    return errors


def resolve_tmdl(target):
    """Accept a .pbip file, a *.SemanticModel folder, or a definition folder."""
    if target.is_file():
        target = target.parent
    if target.name == "definition" and (target.parent / "expressions.tmdl").is_file():
        return target / "expressions.tmdl"
    for candidate in (target / "definition" / "expressions.tmdl", target / "expressions.tmdl"):
        if candidate.is_file():
            return candidate
    # A PBIP root: the model sits in a sibling *.SemanticModel folder.
    if target.is_dir():
        for candidate in sorted(target.glob("*.SemanticModel/definition/expressions.tmdl")):
            return candidate
    return None


def expand_targets(raw_targets):
    """Turn .pbip files into their parent folders so one entry covers the whole project."""
    expanded = []
    for raw in raw_targets:
        target = Path(raw)
        if target.is_file() and target.suffix.lower() == ".pbip":
            target = target.parent
        if target not in expanded:
            expanded.append(target)
    return expanded


def main(argv):
    if len(argv) > 1:
        targets = expand_targets(argv[1:])
    else:
        repo = Path(__file__).resolve().parent.parent
        targets = sorted(p for p in repo.rglob("expressions.tmdl") if ".git" not in p.parts)

    # The standalone power-query/*.m files are the reference copies the TMDL bodies are
    # generated from, so they carry the same defect class and are checked the same way.
    repo = Path(__file__).resolve().parent.parent
    loose_m = sorted(
        p for p in repo.rglob("*.m")
        if ".git" not in p.parts and "node_modules" not in p.parts
    )

    if not targets:
        print("[FAIL] No expressions.tmdl found")
        return EXIT_FAIL

    total_errors, checked, skipped = [], 0, 0

    for target in targets:
        tmdl = resolve_tmdl(target)
        if tmdl is None:
            print(f"[SKIP] No expressions.tmdl at {target}")
            skipped += 1
            continue

        print(f"[INFO] {tmdl}")
        raw = tmdl.read_bytes()
        if raw[:3] == b"\xef\xbb\xbf":
            total_errors.append(f"{tmdl}: UTF-8 BOM present - must be UTF-8 without BOM")
            print("[FAIL] UTF-8 BOM detected")
        # Mixed line endings break TMDL's block termination, which silently merges
        # the following property into the preceding multi-line M expression. The
        # result is an M-engine parse error naming neither file nor line.
        if b"\r\n" in raw and re.search(rb"(?<!\r)\n", raw):
            total_errors.append(f"{tmdl}: mixed CRLF and bare-LF line endings")
            print("[FAIL] Mixed line endings")
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            total_errors.append(f"{tmdl}: not valid UTF-8 ({exc})")
            print("[FAIL] Not valid UTF-8")
            continue

        exprs = extract_expressions(text)
        if not exprs:
            print("[WARN] No 'expression' blocks found")
            continue

        for name, body in exprs:
            checked += 1
            errs = check_delimiters(name, body) + check_body_shape(name, body)
            if errs:
                total_errors.extend(errs)
                print(f"[FAIL] {name}")
                for err in errs:
                    print(f"       {err}")
            else:
                print(f"[PASS] {name} - {len(body)} lines, delimiters balanced, 'in' well formed")

        tables_dir = tmdl.parent / "tables"
        if tables_dir.is_dir():
            path_errors = check_file_paths(tables_dir)
            table_count = len(list(tables_dir.glob("*.tmdl")))
            if path_errors:
                total_errors.extend(path_errors)
                print("[FAIL] partition file paths")
                for err in path_errors:
                    print(f"       {err}")
            else:
                print(f"[PASS] {table_count} table(s) - no bare relative File.Contents paths")

    # GAP-12 sweep. Deliberately runs outside the per-target loop: a phantom module member
    # anywhere in the model blocks the import, and the loose .m files are not reachable from
    # any expressions.tmdl.
    phantom_scanned = 0
    phantom_failures = 0
    phantom_sources = list(loose_m)
    for target in targets:
        resolved = resolve_tmdl(target)
        if resolved is not None:
            phantom_sources.append(resolved)
            phantom_sources.extend(sorted((resolved.parent / "tables").glob("*.tmdl")))

    seen = set()
    phantom_failures = 0
    for src in phantom_sources:
        key = src.resolve()
        if key in seen or not src.is_file():
            continue
        seen.add(key)
        try:
            phantom_errs = check_phantom_members(src.name, src.read_text(encoding="utf-8").splitlines())
        except UnicodeDecodeError:
            continue  # encoding is reported by the per-target path above
        phantom_scanned += 1
        if phantom_errs:
            phantom_failures += 1
            total_errors.extend(phantom_errs)
            print(f"[FAIL] {src.name} - non-existent M module member(s)")
            for err in phantom_errs:
                print(f"       {err}")

    if phantom_scanned and not phantom_failures:
        print(f"[PASS] {phantom_scanned} M file(s) - no non-existent M module members")

    print()
    if total_errors:
        print(f"[FAIL] {len(total_errors)} problem(s) across {checked} expression(s).")
        return EXIT_FAIL
    print(f"[PASS] All {checked} M expression(s) are structurally valid."
          + (f" ({skipped} target(s) skipped.)" if skipped else ""))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main(sys.argv))
