#!/usr/bin/env python3
"""
test_inspect_delimiter.py — Regression test for scripts/inspect_data_source.py.

The script advertises .tsv support but historically routed .tsv through the same
comma-delimited csv.reader as .csv, so a tab-separated file parsed as one column.
Every downstream statistic — null %, unique %, key/date heuristics, model-role
suggestion — was therefore wrong for .tsv input.

This test pins the delimiter wiring at the routing layer: given a file with a
known extension and a known field separator, the profile must report the
expected column count and column names.

Run:  python3 scripts/test_inspect_delimiter.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from inspect_data_source import inspect_csv  # noqa: E402

# (extension, delimiter, filename)
# .txt is intentionally comma-delimited: the script has never sniffed .txt, and
# this test exists to keep it that way rather than to introduce sniffing.
CASES = [
    (".csv", ",", "orders.csv"),
    (".tsv", "\t", "orders.tsv"),
    (".txt", ",", "notes.txt"),
]

# Header + 3 rows. 4 fields, distinct per column so unique % stays 100% and the
# null-rate assertions below are unambiguous.
HEADER = "order_id\tregion\tamount\torder_date"
ROWS = [
    "1001\tEMEA\t120.50\t2026-01-15",
    "1002\tAMER\t80.00\t2026-01-16",
    "1003\tAPAC\t240.75\t2026-01-17",
]


def build_fixture(delimiter: str) -> str:
    lines = [HEADER, *ROWS]
    return "\n".join(line.replace("\t", delimiter) for line in lines) + "\n"


def check_case(extension: str, delimiter: str, filename: str) -> list[str]:
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / filename
        path.write_text(build_fixture(delimiter), encoding="utf-8")

        profiles = inspect_csv(path, max_sample_rows=1000, delimiter=delimiter)

        if len(profiles) != 1:
            failures.append(f"{filename}: expected 1 profile, got {len(profiles)}")
            return failures

        profile = profiles[0]
        expected_cols = ["order_id", "region", "amount", "order_date"]

        actual_cols = [c["name"] for c in profile["columns"]]
        if actual_cols != expected_cols:
            failures.append(
                f"{filename}: columns {actual_cols!r} != expected {expected_cols!r}"
            )

        if profile["col_count"] != len(expected_cols):
            failures.append(
                f"{filename}: col_count {profile['col_count']} != {len(expected_cols)}"
            )

        # Every field is populated, so a wrong delimiter shows up as a null spike
        # as well as a column-count collapse.
        for col in profile["columns"]:
            if col["null_pct"] != 0.0:
                failures.append(
                    f"{filename}: column {col['name']!r} has null_pct "
                    f"{col['null_pct']}, expected 0.0"
                )
    return failures


def main() -> int:
    all_failures: list[str] = []
    for extension, delimiter, filename in CASES:
        failures = check_case(extension, delimiter, filename)
        status = "ok " if not failures else "FAIL"
        print(f"[{status}] {filename}  delimiter={delimiter!r}")
        for failure in failures:
            print(f"         {failure}")
        all_failures.extend(failures)

    print()
    if all_failures:
        print(f"[FAIL] {len(all_failures)} delimiter assertion(s) failed.")
        return 1

    print(f"[PASS] delimiter routing correct for all {len(CASES)} cases.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())