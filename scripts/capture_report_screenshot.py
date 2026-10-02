#!/usr/bin/env python3
"""capture_report_screenshot.py - Render-verify a PBIR page via the Desktop Bridge.

Windows-only. Completes the authoring loop's last step (edit -> validate ->
reload -> screenshot) described in docs/LINUX_WORKFLOW_GAPS.md GAP-18. Linux and
CI can validate a report but cannot confirm it *renders* correctly; this script
is the Windows-side verification that closes that half.

Requires:
  - Power BI Desktop with the target .pbip open
  - node + `npm i -g @microsoft/powerbi-desktop-bridge-cli`

The bridge talks to Desktop's local API. Recent Desktop builds expose it
without a preview-feature toggle; if it is unreachable this script prints the
remedy rather than failing silently.

Usage:
  python3 scripts/capture_report_screenshot.py                       # all pages
  python3 scripts/capture_report_screenshot.py Overview              # one page
  python3 scripts/capture_report_screenshot.py --reload              # pick up on-disk edits first
  python3 scripts/capture_report_screenshot.py --region 0,0,1280,720  # canvas only
  python3 scripts/capture_report_screenshot.py --out artifacts/shots
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

BRIDGE_CLI = "powerbi-desktop"
UNREACHABLE_HINT = (
    "Power BI Desktop's local API is not reachable.\n"
    "  1. Open the target .pbip in Power BI Desktop\n"
    "  2. Check File > Options and settings > Options > Preview features for\n"
    "     'Enable external tool access to Power BI Desktop through secure local APIs'\n"
    "  3. Restart Desktop with the report open\n"
    "If that toggle is not present, your Desktop build predates the GA bridge; update Desktop."
)


def fail(msg, code=1):
    print(f"[ERROR] {msg}", file=sys.stderr)
    sys.exit(code)


def resolve_cli():
    """Return an argv[0] that subprocess can actually exec.

    On Windows the npm shim is a bare `powerbi-desktop.ps1` (PowerShell), which
    CreateProcess cannot run. Sibling `.cmd`/`.exe` shims can, so prefer those.
    """
    found = shutil.which(BRIDGE_CLI)
    if not found:
        return None
    if sys.platform != "win32" or not found.lower().endswith(".ps1"):
        return found
    base = found[: -len(".ps1")]
    for ext in (".cmd", ".exe"):
        if os.path.exists(base + ext):
            return base + ext
    return None


def run(args):
    """Run the bridge CLI and return (exit_code, parsed_json_or_None, raw)."""
    exe = resolve_cli()
    if exe is None:
        fail(f"Could not resolve '{BRIDGE_CLI}' on PATH.")
    try:
        proc = subprocess.run(
            [exe] + args,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        fail("Timed out talking to Power BI Desktop after 120s.")
    except OSError as exc:
        fail(f"Could not run '{BRIDGE_CLI}': {exc}")

    raw = (proc.stdout or "") + (proc.stderr or "")
    # The .cmd shim may print a banner before the JSON payload. Take the first
    # top-level object that decodes cleanly rather than the last, so a nested
    # object later in the payload cannot win.
    payload = None
    decoder = json.JSONDecoder()
    for start, ch in enumerate(raw):
        if ch != "{":
            continue
        try:
            payload, _ = decoder.raw_decode(raw[start:])
        except json.JSONDecodeError:
            continue
        break
    return proc.returncode, payload, raw.strip()


def require_bridge():
    if not shutil.which(BRIDGE_CLI):
        fail(
            f"'{BRIDGE_CLI}' not found on PATH.\n"
            f"       Install: npm install -g @microsoft/powerbi-desktop-bridge-cli"
        )
    if sys.platform != "win32":
        fail(
            f"Desktop Bridge is Windows-only (detected {sys.platform}).\n"
            f"       Run this on a Windows machine with Power BI Desktop open.\n"
            f"       On Linux, see docs/LINUX_WORKFLOW_GAPS.md GAP-18."
        )


def main():
    ap = argparse.ArgumentParser(
        description="Capture a PBIR page screenshot from a running Power BI Desktop instance."
    )
    ap.add_argument("page", nargs="?", help="Page ID from PBIR (default: every page).")
    ap.add_argument("--reload", action="store_true",
                    help="Reload the on-disk report into the canvas before capturing.")
    ap.add_argument("--region", help="Canvas-only crop as x,y,width,height in PBIR units.")
    ap.add_argument("--scale", default="1.0", help="Capture scale 1.0-3.0 (default 1.0).")
    ap.add_argument("--out", default="artifacts/screenshots",
                    help="Output directory (default: artifacts/screenshots).")
    ap.add_argument("--settle", type=float, default=15.0,
                    help="Seconds to wait after selecting a page before capturing. "
                         "Custom visuals that lay out asynchronously - the "
                         "force-directed graph especially - render a partial, "
                         "clipped canvas if captured immediately, which reads as "
                         "a broken visual. Default 15s.")
    args = ap.parse_args()

    require_bridge()

    code, status, raw = run(["status"])
    if status is None:
        print(raw, file=sys.stderr)
        fail(f"Could not parse '{BRIDGE_CLI} status' output.")
    if status.get("status") != "ready" or not status.get("instances"):
        print(UNREACHABLE_HINT, file=sys.stderr)
        fail(f"Desktop Bridge not ready (status={status.get('status')!r}).")

    instance = status["instances"][0]
    if instance.get("hasUnsavedChanges"):
        print("[WARN] Desktop reports unsaved changes; the capture reflects the "
              "in-memory report, not what is on disk. Save or reopen first.")
    if not args.reload and instance.get("currentFilePath"):
        print(f"[INFO] Open file: {instance['currentFilePath']}")

    pages = [p["id"] for p in instance.get("pages", [])]
    if not pages:
        fail("Desktop reported no PBIR pages. Is a .pbip (not .pbix) open?")
    if args.page and args.page not in pages:
        fail(f"Page {args.page!r} not found. Available: {', '.join(pages)}")

    targets = [args.page] if args.page else pages

    if args.reload:
        rc, payload, raw = run(["reload"])
        if rc != 0 or not (payload or {}).get("status") == "ok":
            print(raw, file=sys.stderr)
            fail("Reload failed; canvas may not reflect on-disk edits.")
        print("[OK] Canvas reloaded from disk.")

    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    written = []
    for page in targets:
        cmd = ["screenshot", page, "--output", str(outdir / f"{page}.png")]
        if args.scale != "1.0":
            cmd += ["--scale", args.scale]
        if args.settle > 0:
            # The bridge selects the page and captures in one call, so there is no
            # way to select, wait, then capture. Instead take a throwaway pass to
            # make the page current, let the visual finish laying out, then
            # capture over it. Force-directed layout in particular renders a
            # clipped, half-positioned canvas if captured on the first pass.
            run(cmd)
            time.sleep(args.settle)
        rc, payload, raw = run(cmd)
        if rc != 0 or not payload or payload.get("status") != "ok":
            print(raw, file=sys.stderr)
            fail(f"Screenshot failed for page {page!r}.")
        written.append(payload.get("outputPath", str(outdir / f"{page}.png")))
        print(f"[OK] {page} -> {payload.get('outputPath')}")

    print(f"\n[INFO] Captured {len(written)} page(s). Review each image before "
          f"calling the report done - see GAP-18.")

    if args.region:
        print("[NOTE] --region is recorded for reference but this script uses the "
              "full-canvas capture. For cropped captures use the bridge's "
              "report.snapshot.capture/v2 region parameter directly.")


if __name__ == "__main__":
    main()
