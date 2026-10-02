#!/usr/bin/env python3
"""
make_bisect_pbip.py — Build a minimal PBIP containing a reduced semantic model.

reduce_model.py narrows the model but the gallery report still references all 13
tables, so a load failure could still come from the report side. This builds a
throwaway PBIP whose report is the known-good calendar-baseline report (one page,
two visuals) with its datasetReference repointed at the reduced model, keeping the
model as the only variable.

Usage:
    python3 scripts/make_bisect_pbip.py SRC_SEMANTIC_MODEL DST_PBIP_DIR TableA,TableB,...
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reduce_model import reduce  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
BASELINE = REPO / "samples/pbip-calendar-baseline/CalendarBaseline.Report"

PBIP = """{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
  "version": "1.0",
  "artifacts": [
    {
      "report": {
        "path": "Bisect.Report"
      }
    }
  ],
  "settings": {
    "enableAutoRecovery": true
  }
}
"""


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n")


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 2
    src = Path(argv[0])
    dst = Path(argv[1])
    keep = [t.strip() for t in argv[2].split(",") if t.strip()]

    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)

    # Report: the baseline's, which is known to open, repointed at our model.
    report = dst / "Bisect.Report"
    shutil.copytree(BASELINE, report, ignore=shutil.ignore_patterns(".pbi"))
    pbir = json.loads((report / "definition.pbir").read_text(encoding="utf-8"))
    pbir["datasetReference"]["byPath"]["path"] = "../Bisect.SemanticModel"
    write_json(report / "definition.pbir", pbir)
    platform = json.loads((report / ".platform").read_text(encoding="utf-8"))
    platform["metadata"]["displayName"] = "Bisect"
    write_json(report / ".platform", platform)

    # Semantic model: reduced set, with the project's own properties files.
    model = dst / "Bisect.SemanticModel"
    model.mkdir()
    for name in (".platform", "definition.pbism"):
        text = (src / name).read_text(encoding="utf-8")
        text = text.replace('"displayName": "VisualGallery"', '"displayName": "Bisect"')
        (model / name).write_text(text, encoding="utf-8", newline="\n")
    reduce(src / "definition", model / "definition", keep)

    (dst / "Bisect.pbip").write_text(PBIP, encoding="utf-8", newline="\n")
    print(f"[INFO] built {dst / 'Bisect.pbip'} with: {', '.join(sorted(keep))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
