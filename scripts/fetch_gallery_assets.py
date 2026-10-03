#!/usr/bin/env python3
"""
fetch_gallery_assets.py — Download the gallery's source assets, verified.

Why this exists
---------------
A PBIP report binds a custom visual by GUID, and Power BI Desktop needs the actual
package payload at `<Report>/CustomVisuals/<guid>/` to render it. The packages are
publisher binaries and are never committed (see docs/POWER_BI_VISUAL_COVERAGE.md), so
a clone ships a report that references 26 custom visuals it cannot draw.

The fix is not to commit the binaries, it is to commit the *contract* that describes
where they come from and what they should hash to. That contract is
`samples/visual-gallery-assets/manifest.csv`, which is tracked, and this script is the
executable half of it.

Two details that are easy to get wrong and expensive to notice late:

1.  The manifest's URLs are GitHub `blob/` HTML pages, not downloads. Handing one to a
    HTTP client returns a web page. They must be rewritten to `raw.githubusercontent.com`.

2.  The manifest URLs are branch-anchored (`/blob/main/`). That makes a clone
    non-reproducible: upstream moves, the same manifest SHA yields different bytes, and
    the SHA-256 columns stop meaning anything. So the reference segment is replaced with
    the manifest's own `SourceCommit` pin. Upgrading to a new package version is then an
    explicit edit to the manifest plus a re-verify, rather than a silent drift.

After downloading, run scripts/extract_custom_visuals.py to install the payloads, or
pass --register to have this script chain into it.

No third-party dependencies: urllib only, so this runs anywhere Python does.

Usage:
    python3 scripts/fetch_gallery_assets.py               # PBIVIZ + Images
    python3 scripts/fetch_gallery_assets.py --with-pbix   # also the 12 MB of PBIX workbooks
    python3 scripts/fetch_gallery_assets.py --check       # verify what is on disk, download nothing
    python3 scripts/fetch_gallery_assets.py --only "Word Cloud"
    python3 scripts/fetch_gallery_assets.py --dry-run     # print resolved URLs
    python3 scripts/fetch_gallery_assets.py --register    # fetch, then install into the report
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ASSETS = REPO / "samples" / "visual-gallery-assets"
MANIFEST = ASSETS / "manifest.csv"

# manifest column -> subfolder. PBIX is excluded by default: it is 12 MB of sample
# workbooks whose content the PBIP examples already cover, so it is opt-in.
TARGETS = {"PBIVIZ": "PBIVIZ", "Image": "Images", "PBIX": "PBIX"}
DEFAULT_KINDS = ("PBIVIZ", "Image")

UA = "powerbi-dev-template/fetch_gallery_assets (repo tooling; not a browser)"


class Fail(Exception):
    """A condition the caller should report and exit non-zero on."""


def to_raw(url: str, commit: str) -> str:
    """Rewrite a GitHub blob/raw page URL to a commit-pinned raw download URL.

    `blob` URLs are HTML pages; handing one to an HTTP client returns markup, not a zip.
    `github.com/.../raw/...` does work but only via a 302 to the CDN. Both are rewritten
    to `raw.githubusercontent.com`, which is the canonical host and needs no redirect.

    Anything unrecognised is returned unchanged, so an upstream URL shape change surfaces
    as a fetch failure with the offending URL rather than as a silently mangled path.
    """
    parts = urllib.parse.urlsplit(url)
    host = parts.netloc.lower()
    segs = [s for s in parts.path.split("/") if s]

    if host in ("github.com", "www.github.com"):
        # /{owner}/{repo}/blob/{ref}/{path...}
        if len(segs) < 4 or segs[2] not in ("blob", "raw"):
            return url
        owner, repo, path = segs[0], segs[1], segs[4:]
    elif host == "raw.githubusercontent.com":
        # /{owner}/{repo}/{ref}/{path...}
        if len(segs) < 4:
            return url
        owner, repo, path = segs[0], segs[1], segs[3:]
    else:
        return url

    if not path:
        raise Fail(f"cannot pin to a commit, no file path in URL: {url}")
    quoted = "/".join(urllib.parse.quote(urllib.parse.unquote(p)) for p in path)
    return f"https://raw.githubusercontent.com/{owner}/{repo}/{commit}/{quoted}"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def download(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    tmp = dest.with_suffix(dest.suffix + ".part")
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp, tmp.open("wb") as out:
            while chunk := resp.read(1024 * 256):
                out.write(chunk)
    except urllib.error.HTTPError as exc:
        tmp.unlink(missing_ok=True)
        raise Fail(f"HTTP {exc.code} for {url}") from exc
    except urllib.error.URLError as exc:
        tmp.unlink(missing_ok=True)
        raise Fail(f"network error for {url}: {exc.reason}") from exc
    tmp.replace(dest)


def rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise Fail(
            f"manifest not found: {path}\n"
            "       It is tracked in this repo. If you are on an older commit, pull."
        )
    with path.open(newline="", encoding="utf-8-sig") as fh:
        out = [r for r in csv.DictReader(fh) if (r.get("Visual") or "").strip()]
    if not out:
        raise Fail(f"manifest has no usable rows: {path}")
    return out


def plan(rows_: list[dict[str, str]], kinds: tuple[str, ...]) -> list[tuple[str, str, Path, str, str]]:
    """Build (kind, name, dest, url, expected_sha) for every asset we handle."""
    jobs = []
    for row in rows_:
        commit = (row.get("SourceCommit") or "").strip()
        if not commit:
            raise Fail(f"{row['Visual']}: no SourceCommit pin in the manifest")
        for kind in kinds:
            fname = (row.get(kind) or "").strip()
            if not fname:
                continue
            sha = (row.get(f"{kind}_SHA256") or "").strip().upper()
            url = (row.get(f"{kind}_Source") or "").strip()
            if not sha or not url:
                raise Fail(f"{row['Visual']}: {kind} has no {'SHA256' if not sha else 'Source'} column")
            jobs.append((kind, row["Visual"].strip(), ASSETS / TARGETS[kind] / fname, to_raw(url, commit), sha))
    return jobs


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest", type=Path, default=MANIFEST)
    ap.add_argument("--with-pbix", action="store_true",
                    help="also fetch PBIX/ (12 MB). Off by default: the PBIP examples cover the same content.")
    ap.add_argument("--only", help="fetch only visuals whose name matches this substring")
    ap.add_argument("--check", action="store_true",
                    help="verify SHA-256 of what is already on disk; download nothing. Exit 1 on any mismatch.")
    ap.add_argument("--dry-run", action="store_true", help="print the resolved commit-pinned URLs and exit")
    ap.add_argument("--register", action="store_true",
                    help="chain into scripts/extract_custom_visuals.py once the download succeeds")
    ap.add_argument("--force", action="store_true", help="re-download even when the SHA-256 already matches")
    args = ap.parse_args(argv)

    kinds = ("PBIVIZ", "Image", "PBIX") if args.with_pbix else DEFAULT_KINDS
    jobs = plan(rows(args.manifest), kinds)
    if args.only:
        needle = args.only.casefold()
        jobs = [j for j in jobs if needle in j[1].casefold()]
        if not jobs:
            raise Fail(f"--only {args.only!r} matched no manifest row")

    if args.dry_run:
        for kind, name, dest, url, sha in jobs:
            print(f"{kind:6} {name:24} {url}")
            print(f"{'':6} {'':24} -> {dest.relative_to(REPO)}  sha256={sha[:16]}...")
        print(f"\n[INFO] {len(jobs)} asset(s); {len({j[1] for j in jobs})} visual(s).")
        return 0

    fetched = skipped = failures = 0
    warnings: list[str] = []

    for kind, name, dest, url, sha in jobs:
        try:
            if dest.is_file() and not args.force:
                actual = sha256(dest)
                if actual == sha:
                    skipped += 1
                    if args.check:
                        print(f"[ ok ] {kind:6} {name}")
                    continue
                warnings.append(f"{kind} {name}: on-disk SHA-256 differs, refetching")
                if args.check:
                    failures += 1
                    print(f"[FAIL] {kind:6} {name}: expected {sha[:16]}... got {actual[:16]}...")
                    continue

            if args.check:
                failures += 1
                print(f"[FAIL] {kind:6} {name}: missing at {dest.relative_to(REPO)}")
                continue

            download(url, dest)
            actual = sha256(dest)
            if actual != sha:
                dest.unlink(missing_ok=True)
                failures += 1
                print(f"[FAIL] {kind:6} {name}: SHA-256 mismatch, discarded. expected {sha[:16]}... got {actual[:16]}...")
                continue
            fetched += 1
            print(f"[PASS] {kind:6} {name:24} {dest.stat().st_size:>9,} B  {actual[:16]}...")
        except Fail as exc:
            failures += 1
            print(f"[FAIL] {kind:6} {name}: {exc}")

    for w in warnings:
        print(f"[WARN] {w}", file=sys.stderr)

    verb = "verified" if args.check else "downloaded"
    print()
    print(f"[INFO] {verb} {fetched}, already present {skipped}, failed {failures} of {len(jobs)}.")

    if failures:
        print(f"[FAIL] {failures} asset(s) did not verify. A clone at this manifest SHA should be byte-identical;")
        print("       if upstream has genuinely changed, update the manifest deliberately instead of relaxing the check.")
        return 1

    if not args.check and args.register:
        print("\n[INFO] Registering packages into the gallery report...")
        import subprocess
        proc = subprocess.run(
            [sys.executable, str(REPO / "scripts" / "extract_custom_visuals.py")],
            cwd=REPO,
        )
        return proc.returncode

    if not args.check:
        print("\n[INFO] Next: python3 scripts/extract_custom_visuals.py   (installs the payloads into the report)")
    print("[PASS] All requested assets verified against the manifest SHA-256.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except Fail as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        raise SystemExit(1)