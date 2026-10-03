#!/usr/bin/env python3
"""
build_visual_catalog.py — Merge every machine-derived fact about the gallery's visuals
into one reviewable file.

Why this exists
---------------
Three facts about each visual currently live in three places that can disagree:

  * the manifest carries identity and version for the 26 custom visuals
  * each .pbiviz carries its real data roles, but only on a machine that has the package
  * the HTML prototype's allowlist carries the native type list and why types are excluded

The consequence is already visible: `scripts/generate_visual_allowlist.py` reads roles out
of each .pbiviz and silently emits `roles: []` for all 26 custom visuals on a clone that
has not run the fetcher. Nothing fails. The mockup drawer just quietly loses every role
name.

So the roles are captured **once, into a committed file**, and everything downstream reads
that file instead of the binaries.

Inputs
------
    manifest.csv               identity, version, publisher, certification, image + SHA
    *.pbiviz capabilities      data roles, when the packages happen to be present
    visual-allowlist.json      native type list, exclusion reasons, no-role types
    icons.lock.json            vendored icon per native type, and its tier
    content.json               authored prose: display name, family, use-when, not-for
    the gallery PBIR           which page demonstrates each visual type

Output
------
    visual-catalog.json        generated, committed, the single source for the gallery

Split of responsibilities: this script never invents prose and never hand-edits content.
`content.json` is the authored part and survives regeneration untouched; everything in
the output that is not prose is derived and can be re-derived at any time.

Usage:
    python3 scripts/build_visual_catalog.py
    python3 scripts/build_visual_catalog.py --check    # fail if the output is stale
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ASSETS = REPO / "samples" / "visual-gallery-assets"
MANIFEST = ASSETS / "manifest.csv"
PBIVIZ = ASSETS / "PBIVIZ"
IMAGES = ASSETS / "Images"
LOCK = ASSETS / "icons" / "icons.lock.json"
CONTENT = ASSETS / "content.json"
OUT = ASSETS / "visual-catalog.json"
ALLOWLIST = REPO / "templates" / "html-prototype" / "visual-allowlist.json"
GALLERY_PAGES = REPO / "samples" / "pbip-visual-gallery" / "VisualGallery.Report" / "definition" / "pages"


class Fail(Exception):
    pass


def read_json(path: Path) -> dict:
    if not path.is_file():
        raise Fail(f"missing input: {path.relative_to(REPO)}")
    return json.loads(path.read_text(encoding="utf-8"))


def manifest_rows() -> list[dict[str, str]]:
    with MANIFEST.open(newline="", encoding="utf-8-sig") as fh:
        return [r for r in csv.DictReader(fh) if (r.get("Visual") or "").strip()]


def roles_from_package(pkg: Path) -> list[dict]:
    """Read capabilities.dataRoles out of a .pbiviz. Empty list when unavailable."""
    if not pkg.is_file():
        return []
    try:
        with zipfile.ZipFile(pkg) as zf:
            entry = next(n for n in zf.namelist() if n.endswith(".pbiviz.json"))
            caps = json.loads(zf.read(entry).decode("utf-8-sig"))
    except (zipfile.BadZipFile, StopIteration, json.JSONDecodeError, KeyError, OSError):
        return []
    return [
        {"name": r.get("name", ""), "kind": r.get("kind", ""), "required": bool(r.get("required"))}
        for r in caps.get("capabilities", {}).get("dataRoles", [])
    ]


def gallery_pages() -> dict[str, list[str]]:
    """visualType -> displayName of every page that demonstrates it.

    Derived from the PBIR rather than maintained by hand, so it cannot disagree with
    samples/pbip-visual-gallery/. A type can appear on several pages; textbox appears on
    all 36 because it is page chrome, which is why consumers should treat an empty list as
    "not demonstrated" rather than assuming one page.
    """
    out: dict[str, set[str]] = defaultdict(set)
    for page_json in sorted(GALLERY_PAGES.glob("*/page.json")):
        name = json.loads(page_json.read_text(encoding="utf-8")).get("displayName")
        if not name:
            continue
        for vjson in (page_json.parent / "visuals").glob("*/visual.json"):
            vt = (json.loads(vjson.read_text(encoding="utf-8")).get("visual") or {}).get("visualType")
            if vt:
                out[vt].add(name)
    return {k: sorted(v) for k, v in out.items()}


def build() -> dict:
    allow = read_json(ALLOWLIST)
    content = read_json(CONTENT)
    lock = read_json(LOCK)
    lock = {k: v for k, v in lock.items() if not k.startswith("_")}
    pages = gallery_pages()
    no_role = set(allow["native"]["noRoleTypes"])

    # Roles already captured from a package, so the build is idempotent whether or not
    # the .pbiviz files are on disk. Without this, running on a machine that has not run
    # the fetcher - CI, a fresh clone - would emit roles: [] for all 26 custom visuals and
    # report the committed catalog as stale. Which would be a false alarm caused by a
    # missing input, not by a real change. Packages remain the source of truth; this only
    # keeps their findings from being forgotten.
    known_roles: dict[str, list[dict]] = {}
    if OUT.is_file():
        try:
            prior = json.loads(OUT.read_text(encoding="utf-8"))
            known_roles = {
                v["visualType"]: v.get("roles") or []
                for v in prior.get("visuals", [])
                if v.get("kind") == "custom" and v.get("rolesAreCanonical")
            }
        except (json.JSONDecodeError, KeyError, AttributeError):
            pass

    n_content, c_content = content.get("native", {}), content.get("custom", {})
    missing_prose: list[str] = []
    icons: list[dict] = []

    # ---- native: allowed, then excluded ------------------------------------------
    for vt in sorted(set(allow["native"]["allowed"]) | set(allow["excludedNative"])):
        excluded = vt in allow["excludedNative"]
        c = n_content.get(vt)
        if not c or not c.get("useWhen"):
            missing_prose.append(f"native:{vt}")
        lock_entry = lock.get(vt)
        if not lock_entry:
            raise Fail(f"no vendored icon for native type {vt!r}; run scripts/vendor_native_icons.py")

        pages_for = pages.get(vt, [])
        icons.append({
            "name": (c or {}).get("name", vt),
            "kind": "excluded" if excluded else "native",
            "visualType": vt,
            "authorable": not excluded,
            "exclusionReason": allow["excludedNative"].get(vt, ""),
            "family": (c or {}).get("family", ""),
            "useWhen": (c or {}).get("useWhen", ""),
            "notFor": (c or {}).get("notFor", ""),
            "roles": [] if (excluded or vt in no_role) else [
                {"name": "Category", "kind": "", "required": False, "note": "derived role contract"}
            ],
            "rolesAreCanonical": False,
            "thumbnail": {"tier": lock_entry["tier"], "kind": "icon",
                          "src": f"icons/{vt}.svg", "icon": lock_entry["icon"],
                          "reason": lock_entry["reason"]},
            "galleryPages": pages_for,
            "demoPage": pages_for[0] if pages_for else None,
        })

    # ---- custom: from the manifest, roles from the package when present ------------
    for row in manifest_rows():
        name = row["Visual"].strip()
        guid = row["VisualGuid"].strip()
        c = c_content.get(guid)
        if not c or not c.get("useWhen"):
            missing_prose.append(f"custom:{guid}")

        pkg = PBIVIZ / (row.get("PBIVIZ") or "").strip()
        roles = roles_from_package(pkg)
        if not roles and guid in known_roles:
            roles = known_roles[guid]
        # True whenever the roles came out of a package, whether that happened on this
        # run or an earlier one. Flipping it per-run would make the output differ between
        # a machine that has fetched the packages and one that has not, which is exactly
        # the false staleness this carry-forward exists to prevent.
        canonical = bool(roles)
        img_name = (row.get("Image") or "").strip()
        img_path = IMAGES / img_name

        pages_for = pages.get(guid, [])
        icons.append({
            "name": name,
            "kind": "custom",
            "visualType": guid,
            "authorable": True,
            "publisher": row.get("Publisher", "").strip(),
            "certified": row.get("Certified", "").strip(),
            "version": row.get("Version", "").strip(),
            "package": row.get("PBIVIZ", "").strip(),
            "roles": roles,
            "rolesAreCanonical": canonical,
            "family": (c or {}).get("family", ""),
            "useWhen": (c or {}).get("useWhen", ""),
            "notFor": (c or {}).get("notFor", ""),
            "nativeAlternative": (c or {}).get("nativeAlternative"),
            "thumbnail": {
                "tier": "photo" if img_path.is_file() else "missing",
                "kind": "image",
                "src": f"Images/{img_name}" if img_name else None,
                "sha256": (row.get("Image_SHA256") or "").strip().upper(),
                "source": (row.get("Image_Source") or "").strip(),
            },
            "galleryPages": pages_for,
            "demoPage": pages_for[0] if pages_for else None,
            "provenance": {
                "sourceCommit": row.get("SourceCommit", "").strip(),
                "pbivizSource": row.get("PBIVIZ_Source", "").strip(),
                "pbivizSha256": (row.get("PBIVIZ_SHA256") or "").strip().upper(),
            },
        })

    counts = {
        "native": sum(1 for i in icons if i["kind"] == "native"),
        "excluded": sum(1 for i in icons if i["kind"] == "excluded"),
        "custom": sum(1 for i in icons if i["kind"] == "custom"),
        "rolesFromPackages": sum(1 for i in icons if i.get("rolesAreCanonical")),
        "thumbPhoto": sum(1 for i in icons if i["thumbnail"]["tier"] == "photo"),
        "thumbSchematic": sum(1 for i in icons if i["thumbnail"]["tier"] == "schematic"),
        "thumbMissing": sum(1 for i in icons if i["thumbnail"]["tier"] == "missing"),
    }

    return {
        "_comment": (
            "Generated by scripts/build_visual_catalog.py - do not edit by hand. "
            "Authored prose lives in content.json; everything else here is derived from "
            "manifest.csv, the .pbiviz packages when present, visual-allowlist.json, "
            "icons.lock.json and the gallery PBIR."
        ),
        "generatedFrom": {
            "identity": "samples/visual-gallery-assets/manifest.csv",
            "roles": "each .pbiviz capabilities.dataRoles, captured once so a clone without packages still has them",
            "nativeTypes": "templates/html-prototype/visual-allowlist.json (from powerbi-report-author catalog list)",
            "exclusions": "templates/html-prototype/visual-allowlist.json excludedNative, with a reason each",
            "thumbnails": "samples/visual-gallery-assets/icons/icons.lock.json + Images/",
            "prose": "samples/visual-gallery-assets/content.json (authored)",
            "demoPages": "samples/pbip-visual-gallery/VisualGallery.Report/definition/pages",
        },
        "counts": counts,
        "visuals": icons,
        "_missingProse": sorted(missing_prose),
    }


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="exit 1 if the committed output is not what this script produces")
    args = ap.parse_args(argv)

    doc = build()
    text = json.dumps(doc, indent=2, ensure_ascii=False) + "\n"

    if args.check:
        if not OUT.is_file():
            print(f"[FAIL] {OUT.relative_to(REPO)} does not exist. Run scripts/build_visual_catalog.py")
            return 1
        if OUT.read_text(encoding="utf-8") != text:
            print(f"[FAIL] {OUT.relative_to(REPO)} is stale. Run scripts/build_visual_catalog.py")
            return 1
        print("[PASS] visual-catalog.json is up to date.")
        return 0

    OUT.write_text(text, encoding="utf-8", newline="\n")
    c = doc["counts"]
    print(f"[PASS] {OUT.relative_to(REPO)}  ({OUT.stat().st_size:,} B)")
    print(f"       native={c['native']} excluded={c['excluded']} custom={c['custom']}")
    print(f"       thumbnails: photo={c['thumbPhoto']} schematic={c['thumbSchematic']} missing={c['thumbMissing']}")
    print(f"       roles: {c['rolesFromPackages']} custom visual(s) carry package-derived roles")

    if doc["_missingProse"]:
        print(f"\n[WARN] {len(doc['_missingProse'])} visual(s) have no authored useWhen in content.json:")
        for m in doc["_missingProse"]:
            print(f"       {m}")
        print("       Run scripts/verify_html_gallery.py - it fails on these.")
        return 1
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except Fail as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        raise SystemExit(1)