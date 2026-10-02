# HTML report prototype

`dashboard-template.html` is a design and layout harness for planning a Power BI
report page before writing any PBIR. It is not part of the authoring pipeline —
nothing consumes it — so its contract is enforced by a checker inside the page
rather than by the skill.

## The rule it enforces

The mockup may only declare visual types and slicer types that this project can
actually author. Not "should" — the page flags anything else, in the UI and in
the browser console.

That matters because the most common way a prototype misleads is by offering a
visual that looks plausible and cannot be built. A Sankey drawn in a mockup and
then discovered to need a custom package, or a pie chart that the design
guidance rejects for having twelve slices, both cost a redesign.

## Allowed visual and slicer contract

The contract lives in [`visual-allowlist.json`](visual-allowlist.json) and is
**generated** — do not hand-edit either it or [`visual-allowlist.js`](visual-allowlist.js):

```bash
python3 scripts/generate_visual_allowlist.py
```

Sources:

| Group | Source of truth |
|---|---|
| Native types | `powerbi-report-author catalog list` |
| Custom types | `samples/visual-gallery-assets/manifest.csv` |
| Custom roles | each `.pbiviz` package's `capabilities.dataRoles` |
| Exclusions | an explicit table in the generator, each with a recorded reason |

There is a `.js` wrapper alongside the `.json` because the mockup is usually
opened straight off disk, and `fetch()` of a sibling file is blocked by CORS on
`file://` URLs. A classic `<script src>` is not. Both files are emitted from the
same in-memory document, so they cannot disagree.

## Declaring a visual in the mockup

```html
<div data-pbi-visual-type="lineChart" data-pbi-visual-roles="Category,Y"> … </div>

<div data-pbi-slicer-type="slicer"
     data-pbi-slicer-mode="Dropdown"
     data-pbi-visual-roles="Values"> … </div>
```

`data-pbi-visual-type` must be a PBIR `visualType` — either a native type from the
allowlist or a custom visual's GUID. The drawer lists every custom visual with its
GUID and its expected roles, so there is no need to guess a role name.

## Slicer sizing

| Type / mode | Height |
|---|---|
| `slicer` `Dropdown` | `h = 60 + top padding + bottom padding` |
| `slicer` `Between`, side by side | `h = 60 + top + bottom` |
| `slicer` `Between`, stacked vertically | `h = 84 + top + bottom` |

The 60px is chrome: a header around 28px plus a 32px selector field. Changing
`data.mode` without resizing is the most common slicer defect, and the value does
not scale with the number of items — a dropdown stays 60px whatever you select.

## Canvas

1920 × 1080 with a 32px margin and a 24px gutter. This matches the documented
greenfield default in
[`design-brief.md`](../../.agents/skills/powerbi-report-cli/references/design/design-brief.md).
An earlier version of this template specified 1280 × 720, which contradicted the
default the gallery is actually built at.

## If the visual you want is not on the list

Treat it as a finding, not an obstruction:

1. Confirm it is a real visual type, not a near-miss you assumed. In particular
   `textSlicer` is **not** a verified stand-in for the Input slicer, which has no
   type in the catalog at all.
2. If it is missing because the catalog or the gallery does not carry it, add it
   there first.
3. Regenerate the allowlist, then use it.

Never substitute a similar-looking type to work around the list.