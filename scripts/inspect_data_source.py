#!/usr/bin/env python3
"""
inspect_data_source.py — Profile tabular data sources (Excel, CSV) for Power BI modeling.
Identifies tables, columns, data types, nulls, candidate primary/foreign keys,
and recommends star-schema dimension vs fact classifications.

Usage:
    python3 scripts/inspect_data_source.py path/to/data.xlsx
    python3 scripts/inspect_data_source.py path/to/data.csv --markdown
"""

import argparse
import csv
import os
import sys
from pathlib import Path


def profile_rows(sheet_name: str, headers: list, rows: list, total_rows_est: int = None):
    num_cols = len(headers)
    num_samples = len(rows)

    col_stats = []
    for col_idx, col_name in enumerate(headers):
        vals = [r[col_idx] for r in rows if col_idx < len(r)]
        non_nulls = [v for v in vals if v is not None and v != ""]
        null_count = len(vals) - len(non_nulls)
        distinct_count = len(set(non_nulls))

        # Infer simple type
        types = set(type(v).__name__ for v in non_nulls)
        sample_val = non_nulls[0] if non_nulls else None

        # Check candidate PK / FK / Date
        is_candidate_pk = (distinct_count == len(vals) and null_count == 0 and len(vals) > 0)
        col_lower = str(col_name).lower()
        is_date = any(k in col_lower for k in ["date", "time", "day", "month", "year"]) or any("date" in t.lower() for t in types)
        is_key = any(k in col_lower for k in ["key", "id", "code", "number"]) or is_candidate_pk

        col_stats.append({
            "name": col_name,
            "sample_val": sample_val,
            "types": ", ".join(sorted(types)) if types else "empty",
            "null_pct": (null_count / len(vals) * 100) if vals else 0.0,
            "unique_pct": (distinct_count / len(non_nulls) * 100) if non_nulls else 0.0,
            "is_pk": is_candidate_pk,
            "is_key": is_key,
            "is_date": is_date,
        })

    return {
        "name": sheet_name,
        "sample_rows": num_samples,
        "total_rows_est": total_rows_est or num_samples,
        "col_count": num_cols,
        "columns": col_stats,
    }


def inspect_excel(filepath: Path, max_sample_rows: int = 1000):
    try:
        import openpyxl
    except ImportError:
        print("[ERROR] openpyxl is required to profile Excel files.")
        print("        Install with: pip install openpyxl   OR   uv pip install openpyxl")
        sys.exit(1)

    print(f"[INFO] Loading Excel workbook: {filepath} (read-only mode)...")
    wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
    profiles = []

    for name in wb.sheetnames:
        ws = wb[name]
        row_iter = ws.iter_rows(values_only=True)
        headers = None
        rows = []
        for r in row_iter:
            if headers is None:
                headers = [str(c) if c is not None else f"Col_{i}" for i, c in enumerate(r)]
                continue
            rows.append(r)
            if len(rows) >= max_sample_rows:
                break

        if headers:
            # Estimate total rows if possible
            total_est = ws.max_row - 1 if ws.max_row else len(rows)
            profiles.append(profile_rows(name, headers, rows, total_est))

    wb.close()
    return profiles


def inspect_csv(filepath: Path, max_sample_rows: int = 1000, delimiter: str = ","):
    profiles = []
    with open(filepath, "r", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.reader(f, delimiter=delimiter)
        headers = next(reader, None)
        if not headers:
            return profiles
        rows = []
        for r in reader:
            rows.append(r)
            if len(rows) >= max_sample_rows:
                break
        profiles.append(profile_rows(filepath.stem, headers, rows))
    return profiles


def render_console(profiles):
    print("=" * 80)
    print(" DATA SOURCE PROFILING REPORT")
    print("=" * 80)

    for p in profiles:
        print(f"\nTable / Sheet: {p['name']}")
        print(f"  Estimated Rows: {p['total_rows_est']:,} | Columns: {p['col_count']}")
        
        # Star schema role hint
        pks = [c["name"] for c in p["columns"] if c["is_pk"]]
        dates = [c["name"] for c in p["columns"] if c["is_date"]]
        keys = [c["name"] for c in p["columns"] if c["is_key"] and not c["is_pk"]]

        if pks and p['total_rows_est'] < 100000:
            role = f"DIMENSION (Primary Key: {', '.join(pks)})"
        elif len(keys) >= 2 or p['total_rows_est'] >= 10000:
            role = "FACT TABLE (Multiple foreign keys / high transaction volume)"
        else:
            role = "LOOKUP / AUXILIARY"

        print(f"  Recommended Role: {role}")
        if dates:
            print(f"  Date Dimension Candidates: {', '.join(dates)}")
        
        print("  Columns:")
        header_line = f"    {'Column Name':<30} {'Type':<12} {'Null %':<8} {'Unique %':<10} {'Flags'}"
        print(header_line)
        print("    " + "-" * (len(header_line) - 4))
        for c in p["columns"]:
            flags = []
            if c["is_pk"]:
                flags.append("PK")
            elif c["is_key"]:
                flags.append("FK/KEY")
            if c["is_date"]:
                flags.append("DATE")
            flag_str = ",".join(flags) if flags else "-"
            sample_val_str = str(c["sample_val"])[:15] if c["sample_val"] is not None else ""
            print(f"    {c['name']:<30} {c['types']:<12} {c['null_pct']:>6.1f}%  {c['unique_pct']:>8.1f}%   {flag_str:<8} (e.g. {sample_val_str})")


def render_markdown(profiles):
    lines = ["# Data Source Profiling Summary\n"]
    for p in profiles:
        lines.append(f"## Table: `{p['name']}`\n")
        lines.append(f"- **Estimated Rows**: {p['total_rows_est']:,}")
        lines.append(f"- **Column Count**: {p['col_count']}")
        
        pks = [c["name"] for c in p["columns"] if c["is_pk"]]
        dates = [c["name"] for c in p["columns"] if c["is_date"]]
        keys = [c["name"] for c in p["columns"] if c["is_key"] and not c["is_pk"]]

        if pks and p['total_rows_est'] < 100000:
            lines.append(f"- **Recommended Model Role**: `DIMENSION` (Primary Key: `{', '.join(pks)}`)")
        elif len(keys) >= 2 or p['total_rows_est'] >= 10000:
            lines.append(f"- **Recommended Model Role**: `FACT` (Keys: `{', '.join(keys)}`)")
        else:
            lines.append("- **Recommended Model Role**: `LOOKUP`")

        if dates:
            lines.append(f"- **Date Candidates (Join to Calendar)**: `{', '.join(dates)}`")

        lines.append("\n| Column Name | Inferred Type | Null % | Unique % | Classification |")
        lines.append("|---|---|---|---|---|")
        for c in p["columns"]:
            flags = []
            if c["is_pk"]:
                flags.append("`PK`")
            elif c["is_key"]:
                flags.append("`FK/KEY`")
            if c["is_date"]:
                flags.append("`DATE`")
            flag_str = ", ".join(flags) if flags else "-"
            lines.append(f"| `{c['name']}` | {c['types']} | {c['null_pct']:.1f}% | {c['unique_pct']:.1f}% | {flag_str} |")
        lines.append("\n---\n")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Profile Excel/CSV sources for Power BI semantic modeling.")
    parser.add_argument("file", help="Path to Excel (.xlsx) or CSV file.")
    parser.add_argument("--markdown", action="store_true", help="Output in GitHub Markdown format.")
    parser.add_argument("--output", "-o", help="Write output to specified file.")
    parser.add_argument("--samples", type=int, default=1000, help="Max sample rows per table (default: 1000).")

    args = parser.parse_args()
    filepath = Path(args.file)

    if not filepath.exists():
        print(f"[ERROR] File not found: {filepath}")
        sys.exit(1)

    ext = filepath.suffix.lower()
    if ext in [".xlsx", ".xlsm", ".xltx"]:
        profiles = inspect_excel(filepath, args.samples)
    elif ext in [".csv", ".tsv", ".txt"]:
        delimiter = "\t" if ext == ".tsv" else ","
        profiles = inspect_csv(filepath, args.samples, delimiter)
    else:
        print(f"[ERROR] Unsupported file format: {ext}. Supported: .xlsx, .csv, .tsv")
        sys.exit(1)

    if args.markdown:
        out = render_markdown(profiles)
    else:
        out = None
        render_console(profiles)

    if args.output and out:
        Path(args.output).write_text(out, encoding="utf-8")
        print(f"\n[OK] Profiling report written to {args.output}")


if __name__ == "__main__":
    main()
