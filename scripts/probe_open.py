#!/usr/bin/env python3
"""
probe_open.py — Does this PBIP open in Power BI Desktop?

Wraps the Desktop Bridge CLI with a hard timeout and a bounded poll, so a
bisection loop cannot hang on a modal error dialog. Power BI Desktop's
`open` waits on a dialog nobody is going to click, and the bridge then reports
"Host is not ready to accept operations" forever; a fixed sleep would either be
far too short or block indefinitely.

Exit codes:
    0  opened (the bridge reports a currentFilePath)
    1  did not open within the budget
    2  the CLI or the environment misbehaved

Usage:
    python3 scripts/probe_open.py <path-to-.pbip> [--budget-seconds 240]
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

DESKTOP_EXE = Path(r"C:\Program Files\Microsoft Power BI Desktop\bin\PBIDesktop.exe")


def kill_desktop() -> None:
    subprocess.run(["taskkill", "/F", "/IM", "PBIDesktop.exe"], capture_output=True)
    time.sleep(3)


def status() -> dict:
    exe = shutil.which("powerbi-desktop.cmd") or shutil.which("powerbi-desktop")
    cmd = [exe] if exe else [
        "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", r"C:\Users\Pranam\AppData\Roaming\npm\powerbi-desktop.ps1",
    ]
    job = subprocess.Popen(cmd + ["status"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        out, _ = job.communicate(timeout=40)
    except subprocess.TimeoutExpired:
        job.kill()
        return {"status": "timeout", "instances": []}
    try:
        return json.loads(out.decode("utf-8", "replace"))
    except json.JSONDecodeError:
        return {"status": "unparseable", "instances": [], "raw": out.decode("utf-8", "replace")[:400]}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pbip")
    ap.add_argument("--budget-seconds", type=int, default=240)
    ap.add_argument("--label", default="")
    args = ap.parse_args(argv)

    pbip = Path(args.pbip).resolve()
    if not pbip.is_file():
        print(f"[FAIL] no such file: {pbip}")
        return 2
    if not DESKTOP_EXE.is_file():
        print(f"[FAIL] Power BI Desktop not found at {DESKTOP_EXE}")
        return 2

    kill_desktop()
    subprocess.Popen([str(DESKTOP_EXE), str(pbip)])
    label = args.label or pbip.parent.name
    print(f"[INFO] probing {label}: {pbip}")

    deadline = time.time() + args.budget_seconds
    attempt = 0
    last = ""
    while time.time() < deadline:
        attempt += 1
        st = status()
        instances = st.get("instances") or [{}]
        inst = instances[0] if instances else {}
        state = f"bridge={inst.get('bridgeStatus')} file={'yes' if inst.get('currentFilePath') else 'no'}"
        if state != last:
            print(f"[{attempt:>3}] {state}")
            last = state
        if inst.get("currentFilePath"):
            kill_desktop()
            print(f"[OPENED] {label} opened after {attempt} poll(s)")
            return 0
        time.sleep(10)

    kill_desktop()
    print(f"[FAILED] {label} did not open within {args.budget_seconds}s")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))