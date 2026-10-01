# Power BI visual gallery sample

Open `VisualGallery.pbip` in Power BI Desktop. This self-contained PBIP includes
a copy of the calendar-baseline sample semantic model.

The gallery contains:

| Page | Visuals |
|---|---|
| Core Visuals | `cardVisual`, `clusteredColumnChart`, `tableEx`, `slicer` (Dropdown) |
| Slicer Options | `slicer` (Basic), `listSlicer`, `advancedSlicerVisual` |

The copied source model has only two sample fact rows. It demonstrates PBIR bindings
and visual types, not realistic chart design or data distributions. Do not use
the resulting chart shapes as design examples. In particular, it is too sparse
to demonstrate a meaningful time trend.

The sample intentionally uses only built-in visual types supported by the
local report-author CLI. It does not bundle `.pbiviz` packages. For the current
Desktop/authoring coverage matrix and Microsoft-published custom visual status,
see [Power BI visual coverage](../../docs/POWER_BI_VISUAL_COVERAGE.md).

Validate after editing:

```powershell
powerbi-report-author validate samples/pbip-visual-gallery/VisualGallery.Report
```

The report is schema-validated in CI/local tooling, but it is not visually
verified until opened and reviewed in Power BI Desktop.
