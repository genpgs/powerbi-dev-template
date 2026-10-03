# HTML visual gallery

`index.html` is a browsable reference for every visual this project can author: the
Power BI built-ins, the catalogued types deliberately withheld, and the 26
Microsoft-published custom visuals. Each entry carries the data roles it takes and the
substitution rule that should stop you reaching for it.

Open `index.html` in a browser. There is no build step, no server and no network
requirement — it works from `file://`.

## It is generated. Do not edit it.

```bash
python3 scripts/build_html_gallery.py
```

Content lives in two places upstream:

| File | Contains | Hand-maintained? |
|---|---|---|
| `samples/visual-gallery-assets/content.json` | Display names, family, use-when, not-for, native alternative | **yes** — this is where prose is edited |
| `samples/visual-gallery-assets/visual-catalog.json` | Identity, version, roles, thumbnail, demo page | no — derived by `scripts/build_visual_catalog.py` |

Anything edited directly into `index.html` is lost on the next run. `verify_html_gallery.py`
fails on a stale build, so drift cannot merge quietly.

## Why it is one file

It is meant to be opened by double-clicking. `fetch()` of a sibling data file is blocked by
CORS on `file://` URLs — the constraint already documented in
[`../html-prototype/README.md`](../html-prototype/README.md) — so the catalog is inlined as a
JSON script block rather than loaded.

The custom-visual PNGs are the one exception: they are referenced relatively, because
images are not CORS-restricted on `file://` and inlining 169 KB of base64 to save a path
would make the file worse to review.

The native icons *are* inlined, for a different reason: an `<img>` pointing at an SVG cannot
inherit `currentColor`, so a referenced icon would be stuck black in a dark theme.

## What a thumbnail is, and is not

**No thumbnail in this gallery is a screenshot of Power BI.** That is a deliberate choice,
not an omission.

| Tier | What it is |
|---|---|
| `photo` | The reference image exported for a custom visual from AppSource |
| `icon` | A generic chart-type glyph from Tabler Icons (MIT). A **label** for the visual type |
| `schematic` | A diagram drawn by `scripts/schematics.py`, because no honest glyph exists |
| `collision` | A glyph shared with a sibling visual type; the reason is on the card |

An icon says *"this is a waterfall"*. It does not say *"this is what a waterfall will look
like with your data"*. Screenshots would make the second claim, and that is what ruled them
out: Desktop captures need a Windows machine with the Desktop Bridge, and their DPI and
theme depend on whichever machine last regenerated them, so only one machine could ever
refresh the gallery.

Microsoft Learn documentation images were the other candidate and are ruled out for a
different reason: they are Microsoft's copyrighted content, licensed for internal use
rather than redistribution — the same reasoning that keeps the `.pbiviz` packages out of
this repository. See [`../../docs/POWER_BI_VISUAL_COVERAGE.md`](../../docs/POWER_BI_VISUAL_COVERAGE.md).

Schematics are drawn from the *concept* of each visual rather than traced from a reference.
A normalised stack is columns of equal height because that is what the visual does. No
Microsoft icon silhouette, card geometry or pixel styling is reproduced.

The 28 stand-ins are listed in
[`../../samples/visual-gallery-assets/EXCEPTIONS.md`](../../samples/visual-gallery-assets/EXCEPTIONS.md)
as a review list. Replacing one with a real render needs a `.pbix` opened in Desktop.

## Rendering the custom visuals

The gallery needs nothing to display. The **sample report** does:

```bash
python3 scripts/fetch_gallery_assets.py     # download + SHA-256 verify the packages
python3 scripts/extract_custom_visuals.py   # install them into the gallery report
```