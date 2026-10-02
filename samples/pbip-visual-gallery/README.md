# Power BI visual gallery sample

Open `VisualGallery.pbip` in Power BI Desktop. 36 pages, 190 visuals, covering
every native visual type this project supports plus the 26 Microsoft-certified
custom visuals in `samples/visual-gallery-assets/manifest.csv`.

It is a reference for PBIR authoring, not a finished report. Each page isolates
one visual type, or one small family of related types, so its bindings, sizing
and known pitfalls can be read off directly.

## Before opening: install the custom visual packages

The 26 custom pages need their `.pbiviz` payloads. They are **not committed** —
they are publisher binaries, and redistributing them in this repository is a
licensing decision that is not ours to make (see
[the coverage matrix](../../docs/POWER_BI_VISUAL_COVERAGE.md)).

```bash
python3 scripts/extract_custom_visuals.py     # extract packages + write publicCustomVisuals
python3 scripts/extract_custom_visuals.py --check   # verify without writing
```

This populates `VisualGallery.Report/CustomVisuals/<guid>/` from the local
staging folder. If you have not staged that folder, the custom pages render as
missing visuals while the native pages still work.

## Page map

| Page | Visuals |
|---|---|
| 00 Home | `pageNavigator`, `bookmarkNavigator`, `actionButton`, `image` |
| 01 Native - Cartesian | `columnChart`, `clusteredColumnChart`, `lineChart`, `barChart`, `clusteredBarChart`, `hundredPercentStackedColumnChart`, `hundredPercentStackedBarChart`, `ribbonChart`, `areaChart`, `stackedAreaChart`, `hundredPercentStackedAreaChart`, `lineClusteredColumnComboChart`, `lineStackedColumnComboChart` |
| 02 Native - Distribution | `scatterChart`, `treemap`, `waterfallChart`, `funnel`, `pieChart`, `donutChart` |
| 03 Native - KPI | `cardVisual` (single, multi-value, small multiples), `kpi`, `gauge` |
| 04 Native - Table | `tableEx`, `pivotTable` |
| 05 Native - Maps | `azureMap`, `shapeMap` |
| 06 Native - AI & Insights | `decompositionTreeVisual`, `keyDriversVisual`, `aiNarratives` |
| 07 Native - Slicers | `slicer` (Dropdown, Basic, Between), `listSlicer`, `advancedSlicerVisual` |
| 08 Native - Media & Shapes | `image` (data-bound and static), `shape`, `basicShape` |
| 10–35 Custom | one page per Microsoft custom visual, named `NN Custom - <name>` |
| 36 Custom - How To | how a custom visual binds in PBIR, and what is not authorable |

Every page also carries a title and subtitle textbox, so the page count is
higher than the visual count suggests.

## The model

`VisualGallery.SemanticModel` is fully generated — inline M only, no external
CSV or workbook, and a deterministic seed so a refresh produces identical data
and a screenshot can be compared across runs.

| Table | Feeds |
|---|---|
| `Calendar` | all time visuals; 445 week-based fiscal calendar via `fnCalendarWeekBased` |
| `DimProduct`, `DimCustomer`, `DimStore` | categories, geography, images, cost and price |
| `FactSales` | 24,000 order lines with a trend plus monthly seasonality |
| `Flow` | Sankey, Chord, force-directed graph |
| `KpiTargets` | Power KPI, Power KPI Matrix, Dual KPI |
| `PriceSeries` | Pulse Chart, LineDot, Timeline Slicer, Multi KPI |
| `GanttTasks` | Gantt |
| `HierarchyNodes` | Sunburst |
| `ScatterPoints` | Enhanced Scatter, SandDance, Aster Plot, Radar, Dot Plot |
| `WordFrequency` | Word Cloud, Text Filter, Chiclet Slicer |
| `BulletThresholds` | Bullet Chart |

The data is synthetic and shaped so each visual has something meaningful to
draw — for example bullet thresholds follow metric direction, so a lower-is-better
metric like defect rate does not get an ascending threshold bar.

## Regenerating and validating

```bash
node   scripts/build_gallery_report.mjs        # regenerate all pages from the plan
python3 scripts/extract_custom_visuals.py      # (re)register custom packages
python3 scripts/verify_gallery_coverage.py     # assert coverage against the allowlist

powerbi-report-author validate samples/pbip-visual-gallery/VisualGallery.Report
python3 scripts/validate_report.py             # canvas overlap and bounds
```

The report's pages are generated from the declarative plan in
`build_gallery_report.mjs`, so edit the plan rather than the JSON. Output is
deterministic: an unchanged plan reproduces byte-identical files.

## Known gaps

- **Not refreshed in Desktop.** The TMDL parses and the model imports, but the
  generated rows have only been verified once, locally. If a visual renders
  empty, check the semantic model refreshed before suspecting the binding.
- **Custom visual formatting is not authored.** The report-author CLI has no
  metadata for custom visual types, so custom pages carry bindings and geometry
  only. Configure appearance in Desktop, or read the package's
  `capabilities` for the supported objects.
- **`actionButton` has no destination.** The CLI exposes no metadata for action
  button navigation, so the action is left unwired rather than guessed at.
- **AI visuals** (`aiNarratives`, `keyDriversVisual`, `decompositionTreeVisual`)
  depend on the Desktop build and service entitlement.
- **Not authorable at all**, documented on page 36 rather than faked: Input
  slicer, Q&A, Python, R, Power Apps, Power Automate, ArcGIS, the paginated
  report visual, and the six legacy types.