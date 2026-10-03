# Power BI visual coverage

**Checked:** 2026-10-01  
**Authoring catalog:** `powerbi-report-author` 0.4.0

This page separates three things that are easy to conflate:

1. A visual exists in Power BI Desktop.
2. The local `powerbi-report-author` catalog recognizes its PBIR visual type.
3. This template has an authoring recipe or runnable sample for it.

A catalog entry is not proof that a visual is available in every Desktop build,
can be serialized by the current PBIR schema, or has been rendered successfully.
Before authoring, inspect the exact type with `powerbi-report-author catalog
describe <visualType>` and validate the report. For visuals without a gallery
sample, use Desktop to create a known-good instance before attempting PBIR
authoring.

## Standard Power BI Desktop visuals

The table follows the current Microsoft Learn visual overview. Type names are
the PBIR names where the CLI maps a Desktop visual to one; the CLI catalog is
not itself the canonical list of everything visible in the Desktop pane.

| Desktop visual or family | PBIR type(s) in the local CLI catalog | Gallery coverage |
|---|---|---|
| Bar and column: basic, stacked, 100% stacked, clustered | `barChart`, `clusteredBarChart`, `columnChart`, `clusteredColumnChart`, `hundredPercentStackedBarChart`, `hundredPercentStackedColumnChart` | Gallery 01 Native - Cartesian |
| Line | `lineChart` | Gallery 01 Native - Cartesian |
| Area: basic, stacked, 100% stacked | `areaChart`, `stackedAreaChart`, `hundredPercentStackedAreaChart` | Gallery 01 Native - Cartesian |
| Combo: line and clustered/stacked column | `lineClusteredColumnComboChart`, `lineStackedColumnComboChart` | Gallery 01 Native - Cartesian |
| Ribbon | `ribbonChart` | Gallery 01 Native - Cartesian |
| Waterfall | `waterfallChart` | Gallery 02 Native - Distribution |
| Pie and donut | `pieChart`, `donutChart` | Gallery 02 Native - Distribution |
| Treemap | `treemap` | Gallery 02 Native - Distribution |
| Funnel | `funnel` | Gallery 02 Native - Distribution |
| Scatter/bubble | `scatterChart` | Gallery 02 Native - Distribution |
| Table and matrix | `tableEx`, `pivotTable` | Gallery 04 Native - Table |
| Azure Maps | `azureMap` | Gallery 05 Native - Maps |
| Shape map (preview) | `shapeMap` | Gallery 05 Native - Maps |
| Bing Maps and filled maps | `map`, `filledMap` | not created - use azureMap |
| Card | `cardVisual` | Gallery 03 Native - KPI |
| KPI and gauge | `kpi`, `gauge` | Gallery 03 Native - KPI |
| Decomposition tree | `decompositionTreeVisual` | Gallery 06 Native - AI & Insights |
| Key influencers | `keyDriversVisual` | Gallery 06 Native - AI & Insights |
| Smart narrative | `aiNarratives` | Gallery 06 Native - AI & Insights |
| Anomaly detection | A line-chart capability, not a separate visual type | `lineChart` on Gallery 01; no dedicated page |
| Slicer: list, dropdown, date range, relative date/time, single, before/after | `slicer` | Gallery 07 Native - Slicers |
| Button slicer | `advancedSlicerVisual` | Gallery 07 Native - Slicers |
| List slicer (preview) | `listSlicer` | Gallery 07 Native - Slicers |
| **Input slicer** | **No matching Desktop input-slicer type in the local CLI catalog** | **Not authorable through the documented PBIR workflow yet. Do not guess a visual type or substitute `textSlicer` without Desktop-authored evidence** |
| Image, text box, and shapes | `image`, `textbox`, `shape`, `basicShape` | Gallery 08 Native - Media & Shapes |
| Buttons and page/bookmark navigators | `actionButton`, `pageNavigator`, `bookmarkNavigator` | Gallery 00 Home |
| Paginated report visual | `rdlVisual` | not authorable - needs a separate paginated report |
| Q&A | `qnaVisual` | not authorable - deprecated December 2026 |
| Python and R visuals | `pythonVisual`, `scriptVisual` | not authorable - runtime dependent |
| Power Apps visual | No recognized type in the local CLI catalog | not authorable - no catalog type |
| Power Automate visual | No recognized type in the local CLI catalog | not authorable - no catalog type |
| ArcGIS for Power BI | No recognized type in the local CLI catalog | not authorable - no catalog type |
| Goals/scorecards | `scorecard` is cataloged, but its mapping to the current Desktop experience is not confirmed here | excluded - mapping to the current Desktop experience unconfirmed |

The Desktop inventory and deployment requirements can change by Desktop build,
preview-feature setting, tenant configuration, and region. Check Microsoft
Learn before relying on preview, map, AI, embedded-app, or licensed features.

The **Gallery coverage** column points at a page of
[`samples/pbip-visual-gallery/`](../samples/pbip-visual-gallery/) rather than
describing a capability. Every claim in that column is checked mechanically by
`scripts/verify_gallery_coverage.py`, so it cannot go stale silently. "Not
authorable" rows are deliberately absent from the gallery; they are listed on the
gallery's own `36 Custom - How To` page with the reason.

### CLI entries that need extra caution

`catalog list` includes legacy types (`card`, `multiRowCard`, `table`, `matrix`,
`map`, `filledMap`), a known-but-unsupported `qnaVisual`, and entries whose
current Desktop-pane availability has not been verified (for example
`accessibleTable`, `animatedNumber`, `dataQueryVisual`, `filterSlicer`,
`heatMap`, `realTimeLineChart`, and `textSlicer`). Treat these as schema/catalog
metadata, not as a recommendation to create them. Follow the legacy migration
rules in [authoring.md](../.agents/skills/powerbi-report-cli/references/authoring.md).

## Slicers and filtering controls

Microsoft's current slicer overview describes the classic Slicer visual, Button
slicer, List slicer (preview), and Input slicer. The local PBIR guide has
templates for classic dropdown/list/date modes, `listSlicer`, and
`advancedSlicerVisual`. It does not yet have a verified Input slicer encoding.

Supported documented classic modes include `Basic`, `Dropdown`, `Single`,
`Between`, `Before`, `After`, `Relative`, and `RelativeTime`. These are modes
of the classic `slicer` type, not separate visuals. The separate list and
button types do not use `data.mode`. See
[slicers.md](../.agents/skills/powerbi-report-cli/references/authoring/slicers.md)
for sizing, hierarchy, sync, and PBIR constraints.

## Microsoft-published custom visuals

Microsoft Learn identifies AppSource as a source for custom visuals and notes
that Microsoft and community publishers both provide visuals there. AppSource
also carries separate publisher licensing terms, automatic update behavior,
and security/privacy considerations. A Marketplace listing is therefore not
equivalent to a built-in Desktop visual or an approved redistributable binary.

### Microsoft-published listings in the supplied Marketplace snapshot

Direct AppSource requests returned HTTP 403 during this inventory. The user
supplied the
[DataChant Marketplace export](https://github.com/DataChant/PowerBI-Visuals-AppSource/blob/main/Visuals%20Summary.csv).
Its repository describes a daily refresh from Microsoft Marketplace; this
snapshot was retrieved on 2026-10-01 and contained 1,150 visual records. The
tables below include the 36 records whose `Publisher` value contains
`Microsoft`: 27 published as `Microsoft Corporation` and 9 as
`Microsoft Dynamics 365`. This is a dated snapshot, not a live AppSource query;
confirm current listing, version, publisher, availability, license, and
certification before adding a visual to a report.

**Publisher: Microsoft Corporation (27 listings)**

| Visual | Version | Release date | Certification | Visual GUID | AppSource |
|---|---:|---|---|---|---|
| Dual KPI | 2.2.3.0 | 2026-09-07 | Certified | `PBI_CV_3C80B1F2_09AF_4123_8E99_C3CBC46B23E0` | [Listing](https://appsource.microsoft.com/en-us/product/power-bi-visuals/WA104380774) |
| Chiclet Slicer | 2.2.3.0 | 2026-08-27 | Certified | `ChicletSlicer1448559807354` | [Listing](https://appsource.microsoft.com/en-us/product/power-bi-visuals/WA104380756) |
| Tornado chart | 3.2.1.0 | 2026-08-21 | Certified | `TornadoChart1452517688218` | [Listing](https://appsource.microsoft.com/en-us/product/power-bi-visuals/WA104380768) |
| Visio Visual | 3.3.16.1 | 2026-06-30 | Certified | `Visio_PBI_CV_D7C10B1A_506B_4123_878E_39E8698FD30A` | [Listing](https://appsource.microsoft.com/en-us/product/power-bi-visuals/WA104381132) |
| Power KPI | 3.1.0.0 | 2026-06-16 | Certified | `powerKPI462CE5C2666F4EC8A8BDD7E5587320A3` | [Listing](https://appsource.microsoft.com/en-us/product/power-bi-visuals/WA104381083) |
| Gantt | 3.4.8.0 | 2026-05-26 | Certified | `Gantt1448688115699` | [Listing](https://appsource.microsoft.com/en-us/product/power-bi-visuals/WA104380765) |
| Timeline Slicer | 2.5.14.0 | 2025-07-22 | Certified | `Timeline1447991079100` | [Listing](https://appsource.microsoft.com/en-us/product/power-bi-visuals/WA104380786) |
| Mekko Chart | 3.7.0.0 | 2025-07-21 | Certified | `MekkoChart1449744733038` | [Listing](https://appsource.microsoft.com/en-us/product/power-bi-visuals/WA104380785) |
| Sunburst | 2.7.0.0 | 2025-07-21 | Certified | `Sunburst1445472000808` | [Listing](https://appsource.microsoft.com/en-us/product/power-bi-visuals/WA104380767) |
| SandDance | 4.2.0.3 | 2025-07-08 | Certified | `SandDance201929976D117A654D0BAB8E96507442D80B` | [Listing](https://appsource.microsoft.com/en-us/product/power-bi-visuals/WA200000430) |
| Aster Plot | 1.7.3.0 | 2025-06-06 | Certified | `AsterPlot1443303142064` | [Listing](https://appsource.microsoft.com/en-us/product/power-bi-visuals/WA104380759) |
| Sankey Chart | 3.4.5.0 | 2025-06-06 | Certified | `sankey02300D1BE6F5427989F3DE31CCA9E0F32020` | [Listing](https://appsource.microsoft.com/en-us/product/power-bi-visuals/WA104380777) |
| Chord | 2.4.1.0 | 2025-03-10 | Certified | `ChordChart1444757060245` | [Listing](https://appsource.microsoft.com/en-us/product/power-bi-visuals/WA104380761) |
| Bullet Chart | 2.4.2.0 | 2024-12-23 | Certified | `BulletChart1443347686880` | [Listing](https://appsource.microsoft.com/en-us/product/power-bi-visuals/WA104380755) |
| Dot Plot | 2.0.1.0 | 2024-12-23 | Certified | `DotPlot1442374105856` | [Listing](https://appsource.microsoft.com/en-us/product/power-bi-visuals/WA104380760) |
| Enhanced Scatter | 3.0.9.0 | 2024-12-23 | Certified | `EnhancedScatterChart1443994985041` | [Listing](https://appsource.microsoft.com/en-us/product/power-bi-visuals/WA104380762) |
| Force-Directed Graph | 2.0.2.0 | 2024-12-23 | Certified | `ForceGraph1449359463895` | [Listing](https://appsource.microsoft.com/en-us/product/power-bi-visuals/WA104380764) |
| Infographic Designer | 1.9.700.0 | 2024-12-23 | Certified | `PBI_CV_73744D90_4DC9_4F18_8BA5_EE8FA5C98035` | [Listing](https://appsource.microsoft.com/en-us/product/power-bi-visuals/WA104380898) |
| LineDot Chart | 2.0.3.0 | 2024-12-23 | Certified | `LineDotChart1460463831201` | [Listing](https://appsource.microsoft.com/en-us/product/power-bi-visuals/WA104380766) |
| Multi KPI | 2.2.1.0 | 2024-12-23 | Certified | `multiKpiEA8DA325489E436991F0E411F2D85FF3` | [Listing](https://appsource.microsoft.com/en-us/product/power-bi-visuals/WA104381763) |
| Power KPI Matrix | 3.1.1.0 | 2024-12-23 | Certified | `powerKPIMatrixEB2381CC88A8425FBEB1B07FF57784E6` | [Listing](https://appsource.microsoft.com/en-us/product/power-bi-visuals/WA104381299) |
| Pulse Chart | 3.3.6.0 | 2024-12-23 | Certified | `PulseChart1459209850231` | [Listing](https://appsource.microsoft.com/en-us/product/power-bi-visuals/WA104381006) |
| Radar Chart | 3.1.3.0 | 2024-12-23 | Certified | `RadarChart1446119667547` | [Listing](https://appsource.microsoft.com/en-us/product/power-bi-visuals/WA104380771) |
| Stream Graph | 3.0.9.0 | 2024-12-23 | Certified | `StreamGraph1446659696222` | [Listing](https://appsource.microsoft.com/en-us/product/power-bi-visuals/WA104380772) |
| Table Heatmap | 3.5.0.0 | 2024-12-23 | Certified | `TableHeatMap1443716069308` | [Listing](https://appsource.microsoft.com/en-us/product/power-bi-visuals/WA104380818) |
| Text Filter | 2.2.9.0 | 2024-12-23 | Certified | `textFilter25A4896A83E0487089E2B90C9AE57C8A` | [Listing](https://appsource.microsoft.com/en-us/product/power-bi-visuals/WA104381309) |
| Word Cloud | 2.3.4.0 | 2024-12-23 | Certified | `WordCloud1447959067750` | [Listing](https://appsource.microsoft.com/en-us/product/power-bi-visuals/WA104380752) |

**Publisher: Microsoft Dynamics 365 (9 listings)**

The snapshot also includes these Microsoft Dynamics 365-published visuals:

| Visual | Publisher | Version | Release date | Certification | Visual GUID | AppSource |
|---|---|---:|---|---|---|---|
| Comment - Dynamics 365 Finance business performance planning | Microsoft Dynamics 365 | 1.17.3505.2 | 2026-08-13 | Not Certified | `msdynxPnAComment_c1b0431e724a4fb6b34c449ff0431a4f` | [Listing](https://appsource.microsoft.com/en-us/product/power-bi-visuals/mscrm.d365_business_performance_planning_comment) |
| Copy - Dynamics 365 Finance business performance planning | Microsoft Dynamics 365 | 1.17.3505.2 | 2026-08-13 | Not Certified | `msdynxPnACopy_e752d978c5334590aacf10aa7e2717d8` | [Listing](https://appsource.microsoft.com/en-us/product/power-bi-visuals/mscrm.d365_business_performance_planning_copy) |
| Graphical planning - Dynamics 365 Finance business performance planning | Microsoft Dynamics 365 | 1.17.3505.2 | 2026-08-13 | Not Certified | `msdynxPnAVisualPlanning_0361ca99cfca4abf98f32300584ae294` | [Listing](https://appsource.microsoft.com/en-us/product/power-bi-visuals/mscrm.d365_business_performance_planning_graphicalplan) |
| Matrix planning - Dynamics 365 Finance business performance planning | Microsoft Dynamics 365 | 1.17.3505.2 | 2026-08-13 | Not Certified | `msdynxPnAMatrixCloud_0106a54fd1364e47a0afd26102ef77a3` | [Listing](https://appsource.microsoft.com/en-us/product/power-bi-visuals/mscrm.d365_business_performance_planning_matrix) |
| Reporting - Dynamics 365 Finance business performance planning | Microsoft Dynamics 365 | 1.17.3505.2 | 2026-08-13 | Not Certified | `msdynxPnAReportingDev_c95947939075419987e99768a4090001` | [Listing](https://appsource.microsoft.com/en-us/product/power-bi-visuals/mscrm.d365_business_performance_planning_reporting) |
| Table edit - Dynamics 365 Finance business performance planning | Microsoft Dynamics 365 | 1.17.3505.2 | 2026-08-13 | Not Certified | `msdynxPnADimEditor_46a64748937f429fa9793cb689599b11` | [Listing](https://appsource.microsoft.com/en-us/product/power-bi-visuals/mscrm.d365_business_performance_planning_tabledit) |
| Variance - Dynamics 365 Finance business performance planning | Microsoft Dynamics 365 | 1.17.3505.2 | 2026-08-13 | Not Certified | `msdynxPnAVariance_f9544bd4d1c14210aaba7c7802ae191e` | [Listing](https://appsource.microsoft.com/en-us/product/power-bi-visuals/mscrm.d365_business_performance_planning_variance) |
| Power Automate Process Mining - Process Map Visual | Microsoft Dynamics 365 | 1.0.20260618.2 | 2026-06-22 | Certified | `processMapEE4E02B949754395AD0F88751FCB5864` | [Listing](https://appsource.microsoft.com/en-us/product/power-bi-visuals/mscrm.powerautomate-processmining-processmap) |
| Power Automate Process Mining - Variant DNA Visual | Microsoft Dynamics 365 | 1.0.20260618.2 | 2026-06-22 | Certified | `variantDNAEE4E02B949754395AD0F88751FCB5864` | [Listing](https://appsource.microsoft.com/en-us/product/power-bi-visuals/mscrm.powerautomate-processmining-variantdna) |

This is a catalog of options, not an authoring guarantee. The current report
author CLI does not have a verified custom-package authoring recipe or gallery
sample for these visuals. Import the selected visual from its official listing
in Power BI Desktop, preserve its publisher terms, then use a Desktop-authored
PBIP instance to establish package registration and visual JSON. Do not infer
that a Microsoft publisher or certified listing permits bundling its `.pbiviz`
binary in this repository.

For general import and security considerations, see Microsoft's
[custom visuals overview](https://learn.microsoft.com/en-us/power-bi/developer/visuals/power-bi-custom-visuals)
and [visualization overview](https://learn.microsoft.com/en-us/power-bi/visuals/power-bi-visualizations-overview).

## Sample gallery

The curated local sample is
[`samples/pbip-visual-gallery/`](../samples/pbip-visual-gallery/). It is a
36-page, 190-visual PBIP covering **every** native visual type this project
supports plus all 26 Microsoft-published custom visuals in the manifest below.

The coverage is asserted, not asserted-in-prose.
`scripts/verify_gallery_coverage.py` checks that every allowed native type
appears in the gallery, that no excluded type does, that every manifest GUID
appears, that nothing is declared outside the allowlist, and that
`report.json -> publicCustomVisuals` matches the GUIDs actually in use.

### Browsable reference

For choosing a visual rather than reading its PBIR, open
[`templates/visuals-gallery/index.html`](../templates/visuals-gallery/index.html).
It lists all 84 native, excluded and custom visuals with the data roles each
takes and the substitution rule that should stop you reaching for it. It is a
single self-contained file, so it opens straight off disk.

Its content is generated — prose is authored in
`samples/visual-gallery-assets/content.json` and merged with derived facts into
`samples/visual-gallery-assets/visual-catalog.json`, so the prose survives
regeneration and can be reviewed as a diff:

```bash
python3 scripts/vendor_native_icons.py         # only when re-pinning the icon set
python3 scripts/build_visual_catalog.py        # merge manifest + capabilities + allowlist
python3 scripts/build_html_gallery.py          # emit the page
python3 scripts/verify_html_gallery.py         # 17 assertions over the result
```

`verify_html_gallery.py` asserts allowlist parity in both directions, GUID
agreement with `report.json`, that every custom visual's roles came from a real
package, that every thumbnail resolves, that every shared glyph and every
schematic records its reason, and that the page is self-contained and
well-formed. It fails on a stale build, so the generated page cannot drift from
its sources.

### Thumbnails are labels, not screenshots

The gallery contains no screenshot of Power BI. Native visuals carry a generic
chart-type glyph from [Tabler Icons](https://github.com/tabler/tabler-icons)
(MIT), vendored verbatim from a pinned commit under
`samples/visual-gallery-assets/icons/` with a per-file SHA-256 lock. Custom
visuals carry the reference image exported from AppSource. Ten native types have
no honest glyph and get a drawn schematic instead, from `scripts/schematics.py`.

The distinction is stated on the page because a thumbnail a reader cannot
interpret as evidence is worse than no thumbnail. Desktop screenshots were ruled
out because they need a Windows machine with the Desktop Bridge and their DPI and
theme depend on whichever machine last generated them; Learn documentation
images were ruled out because they are Microsoft's content, licensed for internal
use rather than redistribution — the same reasoning that keeps the `.pbiviz`
packages below out of the repository. The 28 stand-ins are listed in
`samples/visual-gallery-assets/EXCEPTIONS.md` as a review list.

The allowed set itself is generated into
[`templates/html-prototype/visual-allowlist.json`](../templates/html-prototype/visual-allowlist.json)
by `scripts/generate_visual_allowlist.py`, from `catalog list` and the manifest,
with an explicit exclusion table recording a reason per withheld type. The HTML
prototype reads that same contract and flags any visual or slicer outside it.

Regenerate rather than hand-edit:

```bash
python3 scripts/generate_visual_allowlist.py
node   scripts/build_gallery_report.mjs
python3 scripts/verify_gallery_coverage.py
```

### What is deliberately absent

- The six legacy types (`card`, `multiRowCard`, `table`, `matrix`, `map`,
  `filledMap`) — use `cardVisual`, `tableEx`, `pivotTable`, `azureMap`.
- `qnaVisual` — unsupported in PBIR authoring, deprecated December 2026.
- Seven catalog entries whose Desktop availability is unverified
  (`accessibleTable`, `animatedNumber`, `dataQueryVisual`, `filterSlicer`,
  `heatMap`, `realTimeLineChart`, `textSlicer`) and `scorecard`.
- Python, R, Power Apps, Power Automate, ArcGIS, `rdlVisual`, Input slicer.

### Local asset staging folder

The `samples/visual-gallery-assets/` folder holds source material used when
extending the gallery. Four things in it are **tracked**, because they are
contracts and derived descriptions rather than payload:

```text
samples/visual-gallery-assets/
├── manifest.csv          tracked - the fetch contract (URL, version, GUID, SHA-256)
├── content.json          tracked - authored use-when / not-for prose
├── visual-catalog.json   tracked - derived; identity, roles, thumbnail, demo page
├── EXCEPTIONS.md         tracked - generated list of stand-in thumbnails
├── Images/               tracked - 26 reference images for the custom visuals (169 KB)
├── icons/                tracked - 58 vendored SVG glyphs, MIT (31 KB)
├── PBIVIZ/               ignored - publisher binaries
├── PBIX/                 ignored - 12 MB of sample workbooks
└── PBIR/                 ignored - third-party sample reports, reference material
```

A clone therefore ships a full description of the gallery without a single
publisher binary in it. The binaries are fetched and verified on demand:

```bash
python3 scripts/fetch_gallery_assets.py             # PBIVIZ + Images, SHA-256 verified
python3 scripts/fetch_gallery_assets.py --with-pbix # add the 12 MB of PBIX workbooks
python3 scripts/fetch_gallery_assets.py --check     # verify what is on disk, download nothing
python3 scripts/extract_custom_visuals.py           # install the payloads into the report
```

PBIX is opt-in because the PBIP examples cover the same content; it is 12 MB of
workbooks that nothing in the pipeline needs.

It is populated from the matching folders in
[DataChant/PowerBI-Visuals-AppSource](https://github.com/DataChant/PowerBI-Visuals-AppSource),
filtered to the Microsoft-publisher records in the catalog. The initial local
snapshot was retrieved from source commit
[`ffa7579`](https://github.com/DataChant/PowerBI-Visuals-AppSource/commit/ffa7579657dc0831231aafc93de80846ad939833)
on 2026-10-01: 26 PBIX examples, 26 versioned PBIVIZ packages, and 26 images.
`manifest.csv` records each source, version, visual GUID, and local SHA-256.
The PBIVIZ files retain the source's versioned filenames so each package can be
matched to its catalog version. These files remain local and ignored; do not
copy packages into tracked report projects unless their publisher terms permit
it.

Two consequences of pinning worth noting. The manifest's URLs are GitHub `blob/`
HTML pages, so `scripts/fetch_gallery_assets.py` rewrites them to
`raw.githubusercontent.com`; and they are branch-anchored, so it also replaces the
ref with the manifest's own `SourceCommit` pin. That is what makes the SHA-256
columns mean something — a clone at a given manifest SHA gets byte-identical
packages, and taking a new upstream version is an explicit edit to the manifest
rather than silent drift.

One provenance caveat, recorded rather than resolved: the reference images in
`Images/` were packaged by DataChant, a third party, but they depict Microsoft
AppSource listings, so DataChant is not the copyright holder. `manifest.csv`
records a source URL and SHA-256 per image, which establishes where each came
from, not who owns it.

PBIX-to-PBIP conversion is not automated here. Power BI Desktop must open each
PBIX and save it as a Power BI Project (PBIP); the Desktop Bridge CLI exposes
open/reload/screenshot operations but no conversion or Save As operation.

#### Custom visual registration

`scripts/extract_custom_visuals.py` registers the packages into the gallery
report. It unzips each `.pbiviz` into
`VisualGallery.Report/CustomVisuals/<guid>/`, writes the GUID list into
`report.json`, and cross-checks every package against `manifest.csv`.

The extracted packages are **not committed**. `.gitignore` excludes
`**/CustomVisuals/` and `*.pbiviz`, so a clone gets a report that references its
custom visuals by GUID but has no package payloads. Run the extractor locally
before opening the gallery. A Microsoft publisher or certified listing does not
by itself permit redistributing the binary.

Two version-comparison details worth keeping: several packages declare a
three-component version (`2.0.2`) where the manifest and filename say four
(`2.0.2.0`) — these are the same version, so trailing zero components are
normalised away before comparing; and the GUID check is strict, because a
GUID mismatch means the manifest and the binary describe different visuals.

## Official references

- [Power BI visualization overview](https://learn.microsoft.com/en-us/power-bi/visuals/power-bi-visualizations-overview)
- [Map visualizations overview](https://learn.microsoft.com/en-us/power-bi/visuals/power-bi-map-visualizations-overview)
- [Slicers overview](https://learn.microsoft.com/en-us/power-bi/visuals/power-bi-visualization-slicers)
- [Acquiring custom visuals](https://learn.microsoft.com/en-us/power-bi/developer/visuals/power-bi-custom-visuals)
- [Import a visual file](https://learn.microsoft.com/en-us/power-bi/developer/visuals/import-visual)
