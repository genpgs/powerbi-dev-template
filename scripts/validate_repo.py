#!/usr/bin/env python3
"""
validate_repo.py — Validate Power BI repo structure, JSON syntax, and required files.
Run from the repo root: python3 scripts/validate_repo.py

Only repo-owned files are checked. Anything `.gitignore` excludes is skipped, so a
local staging folder (e.g. samples/visual-gallery-assets/, which holds third-party
PBIP/PBIX/PBIVIZ material) is never reported as a repo defect. See
scripts/pbir_discovery.py.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pbir_discovery  # noqa: E402

owned = pbir_discovery.ownership_filter(Path("."))

# ── Required files ────────────────────────────────────────────────────────────
REQUIRED_FILES = [
    ".gitignore",
    ".env.example",
    "README.md",
    "CHANGELOG.md",
    "config/fiscal-calendar.json",
    "power-query/fnCalendar.m",
    "power-query/fnCalendarWeekBased.m",
    "power-query/fnFiscalCalendarConfig.m",
    "scripts/validate_repo.py",
    "scripts/validate_date_table.py",
    "scripts/validate_pbir.sh",
    "scripts/validate_pbir_schema.py",
    "scripts/validate_m_expressions.py",
    "scripts/validate_report.py",
    "scripts/inspect_data_source.py",
    "scripts/scaffold_pbir.py",
    "scripts/test_inspect_delimiter.py",
    "hooks/pre-commit",
    "mcp/mcp.json.example",
    "dax/queries/validate-calendar.dax",
    "docs/GETTING_STARTED.md",
    "docs/fiscal-calendar.md",
    ".devcontainer/devcontainer.json",
    ".github/workflows/validate.yml",
]

REQUIRED_SKILL_FILES = [
    ".agents/skills/powerbi-report-cli/SKILL.md",
    ".agents/skills/semantic-model-authoring/SKILL.md",
    ".agents/skills/fabriciq/SKILL.md",
    ".agents/common/COMMON-CORE.md",
    ".agents/common/COMMON-CLI.md",
]

errors = []
passes = []


def check(condition: bool, pass_msg: str, fail_msg: str) -> bool:
    if condition:
        passes.append(pass_msg)
    else:
        errors.append(fail_msg)
    return condition


# ── 1. Required files exist ───────────────────────────────────────────────────
for f in REQUIRED_FILES + REQUIRED_SKILL_FILES:
    check(
        Path(f).exists(),
        f"[PASS] Found: {f}",
        f"[FAIL] Missing required file: {f}",
    )

# ── 2. JSON syntax ────────────────────────────────────────────────────────────
for p in Path(".").rglob("*.json"):
    if not owned(p):
        continue
    try:
        json.loads(p.read_text(encoding="utf-8"))
        passes.append(f"[PASS] Valid JSON: {p}")
    except json.JSONDecodeError as e:
        errors.append(f"[FAIL] Invalid JSON in {p}: {e}")

# ── 3. .env not committed ─────────────────────────────────────────────────────
import subprocess
is_tracked = subprocess.run(["git", "ls-files", "--error-unmatch", ".env"], capture_output=True).returncode == 0
check(
    not is_tracked,
    "[PASS] .env not committed or tracked in git",
    "[FAIL] .env file is tracked by git — remove it: git rm --cached .env",
)

# ── 4. No binary .pbix files ──────────────────────────────────────────────────
pbix_files = [str(p) for p in Path(".").rglob("*.pbix") if owned(p)]
check(
    len(pbix_files) == 0,
    "[PASS] No .pbix binary files",
    f"[FAIL] Binary .pbix file(s) found (use PBIP instead): {pbix_files}",
)

# ── 5. PBIP folder structure ──────────────────────────────────────────────────
# The PBIP 1.0.0 schema (ArtifactShortcutContainer) sets additionalProperties=false
# and requires exactly one property, "report". A "semanticModel" entry — which older
# templates and most hand-written examples still emit — is rejected outright by Desktop:
#   Property 'semanticModel' has not been defined and the schema does not allow
#   additional properties. Path 'artifacts[1].semanticModel'
# The semantic model is reached through the report's definition.pbir datasetReference
# instead, so listing it in the manifest is both invalid and unnecessary. See GAP-11.
PBIP_SCHEMA_PREFIX = "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/"

for pbip in Path(".").rglob("*.pbip"):
    if not owned(pbip):
        continue
    base = pbip.stem
    parent = pbip.parent
    sm = parent / f"{base}.SemanticModel"
    rpt = parent / f"{base}.Report"
    check(sm.is_dir(), f"[PASS] SemanticModel folder: {sm}", f"[FAIL] Missing: {sm}")
    check(rpt.is_dir(), f"[PASS] Report folder: {rpt}", f"[FAIL] Missing: {rpt}")
    for req in [
        sm / "definition.pbism",
        sm / "definition" / "model.tmdl",
        sm / "definition" / "expressions.tmdl",
        rpt / "definition.pbir",
    ]:
        check(req.exists(), f"[PASS] Found: {req}", f"[FAIL] Missing: {req}")

    # Parse the manifest itself. Folder presence alone says nothing about whether the
    # shortcut will load — a schema-invalid artifacts array fails at open time.
    try:
        doc = json.loads(pbip.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        check(False, "", f"[FAIL] Invalid JSON in {pbip}: {e}")
        continue

    check(
        str(doc.get("$schema", "")).startswith(PBIP_SCHEMA_PREFIX),
        f"[PASS] {pbip.name} declares $schema",
        f"[FAIL] {pbip} missing a valid $schema (expected {PBIP_SCHEMA_PREFIX}1.x.y/schema.json) — required by the PBIP schema (GAP-11)",
    )
    check(doc.get("version") == "1.0", f"[PASS] {pbip.name} version == 1.0",
          f"[FAIL] {pbip} version is {doc.get('version')!r}; expected '1.0' (GAP-11)")

    artifacts = doc.get("artifacts")
    if not check(isinstance(artifacts, list) and artifacts, f"[PASS] {pbip.name} has a non-empty artifacts array",
                 f"[FAIL] {pbip} 'artifacts' must be a non-empty array (GAP-11)"):
        continue

    for idx, artifact in enumerate(artifacts):
        where = f"artifacts[{idx}] of {pbip}"
        if not check(isinstance(artifact, dict), f"[PASS] {where} is an object", f"[FAIL] {where} is not an object (GAP-11)"):
            continue
        extra = set(artifact) - {"report"}
        if extra:
            offender = sorted(extra)[0]
            check(
                False,
                "",
                f"[FAIL] {where} has {sorted(extra)} — the PBIP schema allows only 'report'. "
                f"Desktop refuses to open the project: 'Property {offender!r} has not been defined "
                f"and the schema does not allow additional properties'. The semantic model is reached "
                f"via definition.pbir -> datasetReference, so remove this entry (GAP-11)",
            )
        else:
            check(True, f"[PASS] {where} has no disallowed properties", "")
        if "report" in artifact:
            rpath = artifact["report"].get("path")
            check(
                bool(rpath) and (parent / rpath).is_dir(),
                f"[PASS] {where}.report.path resolves ('{rpath}')",
                f"[FAIL] {where}.report.path is {rpath!r} and does not resolve to a folder (GAP-11)",
            )

# ── 6. fiscal-calendar.json valid pattern ────────────────────────────────────
cfg_path = Path("config/fiscal-calendar.json")
if cfg_path.exists():
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    valid_patterns = {"standard", "445", "454", "544", "13period"}
    pattern = cfg.get("pattern", "")
    check(
        pattern in valid_patterns,
        f"[PASS] fiscal-calendar.json pattern '{pattern}' is valid",
        f"[FAIL] fiscal-calendar.json pattern '{pattern}' invalid. Must be one of: {valid_patterns}",
    )

# ── 7. Shell scripts are LF-terminated and parse ─────────────────────────────
# Added 2026-10-08 after a real incident: .devcontainer/setup.sh had CRLF line
# endings in the working tree, which `bash -n` rejects with a misleading
# "unexpected end of file". Two things let it hide: (1) this validator only
# checked structure and JSON, and (2) `.gitattributes` `*.sh text eol=lf`
# normalises CRLF away, so `git status` reported the file clean. A contributor
# whose editor writes CRLF can reproduce this at any time.
#
# Both halves matter: the parse check catches the breakage, the line-ending
# check catches the cause and names it. See SPEC-08 §10 finding L1.
SHELL_SCRIPTS = [
    "setup.sh",
    ".devcontainer/setup.sh",
    "scripts/validate_pbir.sh",
]

for rel in SHELL_SCRIPTS:
    p = Path(rel)
    if not p.exists():
        continue

    raw = p.read_bytes()
    crlf_count = raw.count(b"\r\n")
    check(
        crlf_count == 0,
        f"[PASS] {rel} uses LF line endings",
        f"[FAIL] {rel} has {crlf_count} CRLF line ending(s). Shell scripts must be LF: "
        f"CRLF breaks `bash -n` and can mask as a syntax error. Fix with "
        f"`git checkout -- {rel}` (safe: the committed blob is LF), and check your "
        f"editor is not writing CRLF.",
    )

    # Only attempt a parse if a shell is actually available. Run via the caller's
    # shell so this works on Linux and in CI without extra deps.
    #
    # Windows note: `bash` on PATH may be the WSL shim (C:\Windows\system32\bash.exe),
    # which cannot reach a repo on another drive and exits non-zero with a
    # "Failed to translate" message. That is an ENVIRONMENT failure, not a script
    # defect, so it must not be reported as one — a validator that cries wolf on a
    # host limitation trains people to ignore it. The LF check above is the
    # load-bearing half and needs no shell at all.
    import shutil
    import subprocess

    if shutil.which("bash") is None:
        print(f"[SKIP] {rel} not parsed: no bash on PATH (LF check above still applies)")
        continue

    try:
        proc = subprocess.run(
            ["bash", "-n", rel],
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        print(f"[SKIP] {rel} not parsed: could not invoke bash ({exc})")
        continue

    stderr = (proc.stderr or "").strip()
    stdout = (proc.stdout or "").strip()

    if proc.returncode == 0:
        check(True, f"[PASS] {rel} parses (bash -n)", "")
        continue

    # Distinguish "this script is broken" from "this shell cannot run here".
    # A genuine parse failure names the script and a line: "<path>: line N: ...".
    combined = "\n".join(x for x in (stderr, stdout) if x)
    environment_failure = any(
        marker in combined
        for marker in (
            "Failed to translate",   # WSL shim, cross-drive path
            "not recognized as an internal",  # cmd.exe fallback
            "command not found",
        )
    )
    if environment_failure:
        print(f"[SKIP] {rel} not parsed: bash on PATH cannot run here — {combined.splitlines()[0]}")
        continue

    detail = (combined or f"exit {proc.returncode}").splitlines()
    detail = detail[0] if detail else f"exit {proc.returncode}"
    check(
        False,
        "",
        f"[FAIL] {rel} does not parse: {detail}",
    )

# ── Summary ───────────────────────────────────────────────────────────────────
for msg in passes:
    print(msg)
for msg in errors:
    print(msg)

if errors:
    print(f"\n[FAIL] {len(errors)} check(s) failed, {len(passes)} passed.")
    sys.exit(1)
else:
    print(f"\n[PASS] All {len(passes)} repo validation checks passed.")
    sys.exit(0)
