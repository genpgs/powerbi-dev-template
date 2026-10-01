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

| Desktop visual or family | PBIR type(s) in the local CLI catalog | Template coverage |
|---|---|---|
| Bar and column: basic, stacked, 100% stacked, clustered | `barChart`, `clusteredBarChart`, `columnChart`, `clusteredColumnChart`, `hundredPercentStackedBarChart`, `hundredPercentStackedColumnChart` | Cartesian patterns and design guidance; no gallery example for every variant |
| Line | `lineChart` | Authoring recipe and design guidance; no gallery example (the fixture has too few time points for a meaningful trend) |
| Area: basic, stacked, 100% stacked | `areaChart`, `stackedAreaChart`, `hundredPercentStackedAreaChart` | CLI metadata and design guidance; no gallery example |
| Combo: line and clustered/stacked column | `lineClusteredColumnComboChart`, `lineStackedColumnComboChart` | CLI metadata; use `catalog describe` for exact roles |
| Ribbon | `ribbonChart` | CLI metadata; no focused recipe/sample |
| Waterfall | `waterfallChart` | Design guidance and CLI metadata; no gallery example |
| Pie and donut | `pieChart`, `donutChart` | CLI metadata; no focused recipe/sample |
| Treemap | `treemap` | Design guidance and CLI metadata; no gallery example |
| Funnel | `funnel` | CLI metadata; no focused recipe/sample |
| Scatter/bubble | `scatterChart` | Design guidance and CLI metadata; no gallery example |
| Table and matrix | `tableEx`, `pivotTable` | Authoring recipes; no gallery example |
| Azure Maps | `azureMap` | Authoring recipe and design guidance; no gallery example |
| Shape map (preview) | `shapeMap` | CLI metadata; no focused recipe/sample |
| Bing Maps and filled maps | `map`, `filledMap` | Legacy; do not create new visuals. Prefer Azure Maps where supported |
| Card | `cardVisual` | Authoring recipe and design guidance; gallery example |
| KPI and gauge | `kpi`, `gauge` | CLI metadata; no focused recipe/sample |
| Decomposition tree | `decompositionTreeVisual` | CLI metadata; no focused recipe/sample |
| Key influencers | `keyDriversVisual` | CLI metadata; no focused recipe/sample |
| Smart narrative | `aiNarratives` | CLI metadata; no focused recipe/sample |
| Anomaly detection | A line-chart capability, not a separate visual type | CLI formatting metadata exists on `lineChart`; authoring procedure/sample not yet provided |
| Slicer: list, dropdown, date range, relative date/time, single, before/after | `slicer` | Authoring recipe; dropdown example in gallery |
| Button slicer | `advancedSlicerVisual` | Authoring recipe; gallery example |
| List slicer (preview) | `listSlicer` | Authoring recipe; gallery example |
| **Input slicer** | **No matching Desktop input-slicer type in the local CLI catalog** | **Not authorable through the documented PBIR workflow yet. Do not guess a visual type or substitute `textSlicer` without Desktop-authored evidence** |
| Image, text box, and shapes | `image`, `textbox`, `shape`, `basicShape` | Authoring recipes |
| Buttons and page/bookmark navigators | `actionButton`, `pageNavigator`, `bookmarkNavigator` | CLI metadata; no focused recipe/sample |
| Paginated report visual | `rdlVisual` | CLI metadata; requires a separate paginated report |
| Q&A | `qnaVisual` | CLI marks it unsupported in PBIR authoring. Microsoft says the Q&A visual is scheduled for deprecation in December 2026 |
| Python and R visuals | `pythonVisual`, `scriptVisual` | Runtime-dependent; not represented in the sample gallery |
| Power Apps visual | No recognized type in the local CLI catalog | Desktop/service capability; no template authoring recipe |
| Power Automate visual | No recognized type in the local CLI catalog | Desktop/service capability; no template authoring recipe |
| ArcGIS for Power BI | No recognized type in the local CLI catalog | Desktop/Esri integration; no template authoring recipe |
| Goals/scorecards | `scorecard` is cataloged, but its mapping to the current Desktop experience is not confirmed here | No verified sample |

The Desktop inventory and deployment requirements can change by Desktop build,
preview-feature setting, tenant configuration, and region. Check Microsoft
Learn before relying on preview, map, AI, embedded-app, or licensed features.

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
[`samples/pbip-visual-gallery/`](../samples/pbip-visual-gallery/). It contains
data-bound examples of a card, clustered column chart, table, classic dropdown
slicer, list slicer, and button slicer. It includes the calendar-baseline
semantic model definition in a self-contained PBIP copy and is intentionally
not a package of every visual listed above.

Custom visual binaries are not checked in. Add an approved visual to a local
report from its official source, then use a Desktop-authored PBIP instance to
establish the exact package registration and visual JSON before adding a
maintained sample.

### Local asset staging folder

The ignored `samples/visual-gallery-assets/` folder is a local-only staging
area for source material used when extending the gallery:

```text
samples/visual-gallery-assets/
├── PBIX/
├── PBIVIZ/
└── Images/
```

It is populated from the matching folders in
[DataChant/PowerBI-Visuals-AppSource](https://github.com/DataChant/PowerBI-Visuals-AppSource),
filtered to the Microsoft-publisher records in the catalog. The initial local
snapshot was retrieved from source commit
[`ffa7579`](https://github.com/DataChant/PowerBI-Visuals-AppSource/commit/ffa7579657dc0831231aafc93de80846ad939833)
on 2026-10-01: 36 PBIX examples, 36 versioned PBIVIZ packages, and 36 images.
`manifest.csv` records each source, version, visual GUID, and local SHA-256.
The PBIVIZ files retain the source's versioned filenames so each package can
be matched to its catalog version. These files remain local and ignored; do
not copy packages into tracked report projects unless their publisher terms
permit it.

PBIX-to-PBIP conversion is not automated here. Power BI Desktop must open each
PBIX and save it as a Power BI Project (PBIP); the Desktop Bridge CLI exposes
open/reload/screenshot operations but no conversion or Save As operation.
After Desktop conversion, validate the resulting project before using it as a
gallery source. The PBIX files are still useful local examples in the meantime.

## Official references

- [Power BI visualization overview](https://learn.microsoft.com/en-us/power-bi/visuals/power-bi-visualizations-overview)
- [Map visualizations overview](https://learn.microsoft.com/en-us/power-bi/visuals/power-bi-map-visualizations-overview)
- [Slicers overview](https://learn.microsoft.com/en-us/power-bi/visuals/power-bi-visualization-slicers)
- [Acquiring custom visuals](https://learn.microsoft.com/en-us/power-bi/developer/visuals/power-bi-custom-visuals)
- [Import a visual file](https://learn.microsoft.com/en-us/power-bi/developer/visuals/import-visual)
