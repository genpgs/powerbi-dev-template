#!/usr/bin/env node
/**
 * build_gallery_report.mjs — Generate the PBIR pages of the VisualGallery report.
 *
 * Why a generator rather than hand-edited JSON
 * ---------------------------------------------
 * The gallery is ~36 pages and ~110 visuals. Hand-writing that much PBIR invites
 * transcription errors in the one field that matters most, `queryRef`, and makes
 * layout arithmetic unreviewable. This script holds a declarative page plan and
 * emits deterministic PBIR: same input, byte-identical output, so a re-run gives
 * an empty diff and every change is reviewable in the plan itself.
 *
 * Field references are never written by hand. C() / M() / A() build the Column /
 * Measure / Aggregation expressions and derive `queryRef` from the same
 * (entity, property) pair, which is what keeps the two in sync.
 *
 * Roles come from `powerbi-report-author catalog describe` for native visuals and
 * from each package's `capabilities.dataRoles` for the custom ones. Where the CLI
 * has no metadata - custom visual formatting objects above all - nothing is
 * invented, so a custom visual page carries bindings and geometry only.
 *
 * Run:  node scripts/build_gallery_report.mjs
 */
import { mkdirSync, writeFileSync, rmSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const REPORT = join(
  dirname(fileURLToPath(import.meta.url)),
  "..",
  "samples",
  "pbip-visual-gallery",
  "VisualGallery.Report",
);
const PAGES_DIR = join(REPORT, "definition", "pages");

// Schemas copied from the files already in this report. Never invent a version.
const SCHEMA = {
  page: "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json",
  visual:
    "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.13.0/schema.json",
  pagesMeta:
    "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json",
};

// FHD is the documented greenfield canvas default (design-brief.md:86,212).
const CANVAS = { width: 1920, height: 1080 };
const MARGIN = 32;
const GUTTER = 24;
const TITLE_H = 46;
const TITLE_Y = MARGIN;
const SUBTITLE_Y = TITLE_Y + TITLE_H + 4;
const SUBTITLE_H = 30;
const CONTENT_Y = SUBTITLE_Y + SUBTITLE_H + 12;
const CONTENT_W = CANVAS.width - 2 * MARGIN;
const CONTENT_H = CANVAS.height - CONTENT_Y - MARGIN;

// ── Field reference builders ──────────────────────────────────────────────────
const AGG = { Sum: 0, Average: 1, Count: 2, Min: 3, Max: 4, CountNonNull: 5, DistinctCount: 6 };

/** A raw column, for Grouping roles. */
const C = (entity, property) => ({ kind: "Column", entity, property, queryRef: `${entity}.${property}` });

/** A measure, for Measure roles. */
const M = (entity, property) => ({ kind: "Measure", entity, property, queryRef: `${entity}.${property}` });

/** An explicit aggregation over a column. */
const A = (entity, property, fn = "Sum") => {
  if (!(fn in AGG)) throw new Error(`Unknown aggregation ${fn}`);
  return { kind: "Aggregation", entity, property, fn, queryRef: `${fn}(${entity}.${property})` };
};

function projection(f) {
  const src = { SourceRef: { Entity: f.entity } };
  if (f.kind === "Column") {
    return { field: { Column: { Expression: src, Property: f.property } }, queryRef: f.queryRef, nativeQueryRef: f.property };
  }
  if (f.kind === "Measure") {
    return { field: { Measure: { Expression: src, Property: f.property } }, queryRef: f.queryRef, nativeQueryRef: f.property };
  }
  return {
    field: {
      Aggregation: {
        Expression: { Column: { Expression: src, Property: f.property } },
        Function: AGG[f.fn],
      },
    },
    queryRef: f.queryRef,
    nativeQueryRef: f.property,
  };
}

/** { Role: field | [field, ...] } -> a PBIR queryState. */
function queryState(roles, where) {
  const out = {};
  for (const [role, spec] of Object.entries(roles)) {
    const fields = Array.isArray(spec) ? spec : [spec];
    for (const f of fields) {
      if (!f) throw new Error(`${where}: role "${role}" has an undefined field`);
    }
    out[role] = { projections: fields.map(projection) };
  }
  return out;
}

// ── Layout ────────────────────────────────────────────────────────────────────
const distribute = (total, n) => {
  const base = Math.floor(total / n);
  const rem = total - base * n;
  return Array.from({ length: n }, (_, i) => base + (i < rem ? 1 : 0));
};

/**
 * Tile a page body and return a placement function.
 *
 * Widths are distributed, then positions accumulated, so cells tile the content
 * area exactly with gutters between them. Integer arithmetic throughout, so there
 * is no float rounding to produce an accidental overlap or overflow for
 * validate_report.py to catch after the fact.
 *
 *   place(col, row, colspan?, rowspan?) -> {x, y, width, height}
 */
function layout(cols, rows) {
  const ws = distribute(CONTENT_W - (cols - 1) * GUTTER, cols);
  const hs = distribute(CONTENT_H - (rows - 1) * GUTTER, rows);
  const startsX = [];
  let x = MARGIN;
  for (const w of ws) {
    startsX.push(x);
    x += w + GUTTER;
  }
  const startsY = [];
  let y = CONTENT_Y;
  for (const h of hs) {
    startsY.push(y);
    y += h + GUTTER;
  }
  return function place(col, row, colspan = 1, rowspan = 1) {
    if (col + colspan > cols || row + rowspan > rows) {
      throw new Error(`place(${col},${row},${colspan},${rowspan}) exceeds a ${cols}x${rows} grid`);
    }
    return {
      x: startsX[col],
      y: startsY[row],
      width: ws.slice(col, col + colspan).reduce((a, b) => a + b, 0) + (colspan - 1) * GUTTER,
      height: hs.slice(row, row + rowspan).reduce((a, b) => a + b, 0) + (rowspan - 1) * GUTTER,
    };
  };
}

// ── PBIR literal helpers ──────────────────────────────────────────────────────
const L = {
  bool: (v) => String(v),
  text: (v) => `'${String(v).replace(/'/g, "''")}'`,
  dec: (v) => `${v}D`,
};
const one = (properties) => [{ properties }];
const lit = (value) => ({ expr: { Literal: { Value: value } } });

function titleObjects(text, size = 12) {
  return one({
    show: lit(L.bool(true)),
    text: lit(L.text(text)),
    fontSize: lit(L.dec(size)),
    bold: lit(L.bool(true)),
    alignment: lit(L.text("left")),
  });
}

const noChrome = () => ({
  background: one({ show: lit(L.bool(false)) }),
  border: one({ show: lit(L.bool(false)) }),
  padding: one({
    top: lit(L.dec(0)),
    bottom: lit(L.dec(0)),
    left: lit(L.dec(0)),
    right: lit(L.dec(0)),
  }),
});

// ── Visual factories ──────────────────────────────────────────────────────────

/**
 * A textbox. `runs` is [{text, size, color, weight}].
 * Pass `band: "title" | "sub"` to place it in the page heading band instead of
 * the content area.
 */
function textbox(runs, position, alt) {
  const paragraphs = runs.map((r) => ({
    textRuns: [
      {
        value: r.text,
        textStyle: {
          fontFamily: r.weight === 600 ? "Segoe UI Semibold" : "Segoe UI",
          fontSize: `${r.size}px`,
          color: r.color ?? "#1B1B1F",
        },
      },
    ],
    horizontalTextAlignment: "left",
  }));
  return {
    type: "textbox",
    position,
    visual: { visualType: "textbox", objects: { general: one({ paragraphs }) } },
    visualContainerObjects: { ...noChrome(), ...(alt ? { general: one({ altText: lit(L.text(alt)) }) } : {}) },
  };
}

/**
 * A data-bound visual.
 * `roles` may be omitted for visual types that take no fields: textbox, shape,
 * basicShape, image (static), pageNavigator, bookmarkNavigator, aiNarratives.
 */
function viz(type, title, alt, roles, position, extra = {}) {
  const visual = { visualType: type };
  if (roles && Object.keys(roles).length > 0) visual.query = { queryState: queryState(roles, `${type} "${title}"`) };
  if (extra.objects) visual.objects = extra.objects;

  const visualContainerObjects = { title: titleObjects(title), ...(extra.vco ?? {}) };
  if (alt) visualContainerObjects.general = one({ altText: lit(L.text(alt)) });

  return { type, title, position, visual, visualContainerObjects };
}

/** A paragraph of explanatory text inside the content area. */
function note(text, position, size = 14) {
  return textbox([{ text, size, color: "#444746" }], position, text);
}

/**
 * objects.image for the `image` visual.
 *
 * The image visual takes no query roles: `sourceType` selects where the picture
 * comes from, and exactly one of `sourceUrl` (a literal URL) or `sourceField`
 * (a "Table[Column]" reference to a column carrying dataCategory ImageUrl)
 * supplies it. Guessing a queryState role here yields PBIR_ROLE_UNKNOWN.
 */
function imageObject({ sourceUrl, sourceField, fit, altText }) {
  const props = { sourceType: lit(L.text("imageUrl")) };
  if (sourceUrl) props.sourceUrl = lit(L.text(sourceUrl));
  if (sourceField) props.sourceField = lit(L.text(sourceField));
  if (fit) props.fit = lit(L.text(fit));
  if (altText) props.altText = lit(L.text(altText));
  return { image: one(props) };
}

// ─────────────────────────────────────────────────────────────────────────────
// Model field shorthands
// ─────────────────────────────────────────────────────────────────────────────
const cal = {
  date: C("Calendar", "Date"),
  year: C("Calendar", "CalendarYear"),
  yearLabel: C("Calendar", "FiscalYearLabel"),
  month: C("Calendar", "CalendarMonth"),
  monthNum: C("Calendar", "CalendarMonthNumber"),
  period: C("Calendar", "FiscalPeriodLabel"),
  quarter: C("Calendar", "FiscalQuarter"),
};
const sales = {
  total: M("FactSales", "Total Sales"),
  profit: M("FactSales", "Total Gross Profit"),
  margin: M("FactSales", "Gross Margin %"),
  orders: M("FactSales", "Total Orders"),
  qty: M("FactSales", "Total Quantity"),
  aov: M("FactSales", "Average Order Value"),
  ytd: M("Calendar", "Sales YTD"),
  py: M("Calendar", "Sales Previous Year"),
  yoyPct: M("Calendar", "Sales YoY %"),
  fytd: M("Calendar", "Sales FYTD"),
  rolling: M("Calendar", "Sales Rolling 12M"),
};
const prod = {
  name: C("DimProduct", "ProductName"),
  cat: C("DimProduct", "Category"),
  sub: C("DimProduct", "Subcategory"),
  color: C("DimProduct", "ColorName"),
  image: C("DimProduct", "ProductImage"),
};
const cust = { city: C("DimCustomer", "City"), cont: C("DimCustomer", "Continent"), country: C("DimCustomer", "Country"), seg: C("DimCustomer", "Segment") };
const store = { name: C("DimStore", "StoreName"), region: C("DimStore", "Region"), channel: C("DimStore", "Channel"), cont: C("DimStore", "Continent"), type: C("DimStore", "StoreType") };

// Custom-visual tables
const kpi = {
  name: C("KpiTargets", "IndicatorName"),
  unit: C("KpiTargets", "BusinessUnit"),
  date: C("KpiTargets", "PeriodDate"),
  actual: M("KpiTargets", "KPI Actual"),
  target: M("KpiTargets", "KPI Target"),
  comparison: M("KpiTargets", "KPI Comparison"),
  attainment: M("KpiTargets", "KPI Attainment %"),
  index: C("KpiTargets", "KpiIndex"),
  sort: C("KpiTargets", "SortOrder"),
  status: C("KpiTargets", "StatusLabel"),
  icon: C("KpiTargets", "Icon"),
  link: C("KpiTargets", "Hyperlink"),
};
const flow = {
  source: C("Flow", "Source"),
  dest: C("Flow", "Destination"),
  value: M("Flow", "Flow Value"),
  linkType: C("Flow", "LinkType"),
  sourceType: C("Flow", "SourceType"),
  targetType: C("Flow", "TargetType"),
};
const pts = {
  name: C("ScatterPoints", "PointName"),
  cat: C("ScatterPoints", "Category"),
  series: C("ScatterPoints", "Series"),
  x: C("ScatterPoints", "XValue"),
  y: C("ScatterPoints", "YValue"),
  size: C("ScatterPoints", "SizeValue"),
  shape: C("ScatterPoints", "ShapeValue"),
  gradient: C("ScatterPoints", "GradientValue"),
  rotation: C("ScatterPoints", "RotationValue"),
  dot: C("ScatterPoints", "DotValue"),
  r1: M("ScatterPoints", "Scatter Radar 1"),
  r2: M("ScatterPoints", "Scatter Radar 2"),
  r3: M("ScatterPoints", "Scatter Radar 3"),
  r4: M("ScatterPoints", "Scatter Radar 4"),
  image: C("ScatterPoints", "ImageUrl"),
};
const words = { term: C("WordFrequency", "Term"), freq: M("WordFrequency", "Term Frequency"), topic: C("WordFrequency", "Topic"), image: C("WordFrequency", "ImageUrl"), excludes: C("WordFrequency", "Excludes") };
const gantt = {
  task: C("GanttTasks", "TaskName"),
  parent: C("GanttTasks", "ParentTask"),
  start: C("GanttTasks", "StartDate"),
  end: C("GanttTasks", "EndDate"),
  duration: M("GanttTasks", "Gantt Value"),
  completion: M("GanttTasks", "Gantt Completion"),
  resource: C("GanttTasks", "Resource"),
  legend: C("GanttTasks", "Legend"),
  milestone: C("GanttTasks", "Milestone"),
};
const tree = { l1: C("HierarchyNodes", "Level1"), l2: C("HierarchyNodes", "Level2"), l3: C("HierarchyNodes", "Level3"), value: M("HierarchyNodes", "Node Value") };
const price = { ts: C("PriceSeries", "Timestamp"), series: C("PriceSeries", "SeriesName"), value: M("PriceSeries", "Series Value"), avg: M("PriceSeries", "Series Average"), min: M("PriceSeries", "Series Min"), max: M("PriceSeries", "Series Max"), baseline: M("PriceSeries", "Series Average"), eventTitle: C("PriceSeries", "EventTitle"), eventSize: C("PriceSeries", "EventSize") };
const bullet = {
  cat: C("BulletThresholds", "Category"),
  value: M("BulletThresholds", "Bullet Actual"),
  target: M("BulletThresholds", "Bullet Target"),
  min: M("BulletThresholds", "Bullet Minimum"),
  max: M("BulletThresholds", "Bullet Maximum"),
  attain: M("BulletThresholds", "Bullet Attainment %"),
};

// ─────────────────────────────────────────────────────────────────────────────
// Page plan
// ─────────────────────────────────────────────────────────────────────────────

/** Builds one page: heading band + a tiled body. */
function page(displayName, title, subtitle, cols, rows, items) {
  const place = layout(cols, rows);
  return { displayName, title, subtitle, items: items(place) };
}

const PAGES = [];

// ── 00 Home ───────────────────────────────────────────────────────────────────
PAGES.push(
  page("00 Home", "Visual Gallery", "Every Power BI visual type available to PBIR authoring, in one project.", 2, 3, (p) => [
    viz("pageNavigator", "All pages", "Page navigator listing every page in this report.", null, p(0, 0)),
    viz("bookmarkNavigator", "Bookmarks", "Bookmark navigator. No bookmarks are defined in this sample yet.", null, p(1, 0)),
    textbox(
      [
        { text: "What this gallery is", size: 18, weight: 600 },
        { text: "A reference for PBIR authoring, not a finished report. Each page isolates one visual type (or one small family of related types) so its bindings, sizing and known pitfalls can be read off directly.", size: 14, color: "#444746" },
        { text: "The 26 custom-visual pages need their .pbiviz packages installed locally; run scripts/extract_custom_visuals.py after cloning, then open the project in Power BI Desktop.", size: 14, color: "#444746" },
      ],
      p(0, 1, 2),
      "Explanation of what this gallery covers and how to run it.",
    ),
    viz(
      "actionButton",
      "Button",
      "Action button. Its destination is not set in PBIR: the report-author CLI exposes no metadata for action button navigation, so wire the action in Desktop rather than guessing an encoding.",
      null,
      p(0, 2),
    ),
    viz(
      "image",
      "Image",
      "Static image visual showing a placeholder image loaded from a URL.",
      null,
      p(1, 2),
      { objects: imageObject({ sourceUrl: "https://picsum.photos/seed/pbi-gallery-banner/640/320" }) },
    ),
  ]),
);

// ── 01 Native Cartesian ───────────────────────────────────────────────────────
PAGES.push(
  page(
    "01 Native - Cartesian",
    "Native - Cartesian charts",
    "Category (Grouping) plus Y (Measure), with optional Series, Y2 and Rows.",
    4,
    4,
    (p) => [
      viz("columnChart", "Column", "Total sales by fiscal year. The unclustered column chart.", { Category: cal.yearLabel, Y: sales.total }, p(0, 0)),
      viz("clusteredColumnChart", "Clustered column", "Total sales by fiscal year, split by channel.", { Category: cal.yearLabel, Series: store.channel, Y: sales.total }, p(1, 0)),
      viz("lineChart", "Line", "Total sales by fiscal year.", { Category: cal.yearLabel, Y: sales.total }, p(2, 0)),
      viz("barChart", "Bar", "Total sales by store region.", { Category: store.region, Y: sales.total }, p(3, 0)),
      viz("clusteredBarChart", "Clustered bar", "Total sales by product subcategory, sorted by value.", { Category: prod.sub, Y: sales.total }, p(0, 1)),
      viz("hundredPercentStackedColumnChart", "100% stacked column", "Share of sales by category within each fiscal period.", { Category: cal.period, Series: prod.cat, Y: sales.total }, p(1, 1)),
      viz("hundredPercentStackedBarChart", "100% stacked bar", "Share of sales by category.", { Y: sales.total, Category: prod.cat }, p(2, 1)),
      viz("ribbonChart", "Ribbon", "Sales by subcategory, with the second-lowest value drawn as the ribbon.", { Category: prod.sub, Series: store.channel, Y: sales.total }, p(3, 1)),
      viz("areaChart", "Area", "Total sales across the calendar year. The unclustered area chart.", { Category: cal.month, Y: sales.total }, p(0, 2)),
      viz("stackedAreaChart", "Stacked area", "Sales volume over the calendar year, split by sales channel.", { Category: cal.month, Series: store.channel, Y: sales.total }, p(1, 2)),
      viz("hundredPercentStackedAreaChart", "100% stacked area", "Channel mix across the calendar year.", { Category: cal.month, Series: prod.cat, Y: sales.total }, p(2, 2)),
      viz("lineClusteredColumnComboChart", "Combo (clustered column)", "Profit as columns against sales as a line, by fiscal period.", { Category: cal.period, Series: prod.cat, Y: sales.total, Y2: sales.profit }, p(3, 2)),
      viz("lineStackedColumnComboChart", "Combo (stacked column)", "Stacked profit columns against a sales line.", { Category: cal.period, Series: prod.cat, Y: sales.profit, Y2: sales.total }, p(0, 3)),
      viz("lineChart", "Line with secondary axis", "Sales against a rolling 12-month measure on the second axis.", { Category: cal.yearLabel, Y: sales.total, Y2: sales.rolling }, p(1, 3)),
      note(
        "Every cartesian visual here shares one role contract: Category is the axis, Y is the measure, Series becomes the legend, and Y2 is the secondary axis. A combo chart differs only in that Category alone is required and Y and Y2 are both optional, so it still needs at least one of them bound.",
        p(2, 3, 2),
      ),
    ],
  ),
);

// ── 02 Native Distribution ────────────────────────────────────────────────────
PAGES.push(
  page(
    "02 Native - Distribution",
    "Native - Distribution and part-to-whole",
    "Scatter, treemap, waterfall, funnel, pie and donut.",
    3,
    2,
    (p) => [
      viz("scatterChart", "Scatter", "Sales against gross profit by store region, sized by order quantity.", { X: sales.total, Y: sales.profit, Category: store.region, Size: sales.qty }, p(0, 0)),
      viz("treemap", "Treemap", "Sales by category, drilled into subcategory.", { Values: A("FactSales", "SalesAmount"), Group: prod.cat, Details: prod.sub }, p(1, 0)),
      viz("waterfallChart", "Waterfall", "Contribution of each product category to total sales.", { Category: prod.cat, Y: sales.total }, p(2, 0)),
      viz("funnel", "Funnel", "Pipeline volume falling from leads to renewal.", { Category: flow.source, Y: A("Flow", "Value") }, p(0, 1)),
      viz("pieChart", "Pie", "Share of sales by product category.", { Category: prod.cat, Y: sales.total }, p(1, 1)),
      viz("donutChart", "Donut", "Share of sales by store region.", { Category: store.region, Y: sales.total }, p(2, 1)),
    ],
  ),
);

// ── 03 Native KPI ─────────────────────────────────────────────────────────────
PAGES.push(
  page(
    "03 Native - KPI",
    "Native - Cards, KPI and gauge",
    "cardVisual takes Data; kpi takes Indicator with optional TrendLine and Goal; gauge takes Y.",
    4,
    2,
    (p) => [
      viz("cardVisual", "Total sales", "Big number: total sales for the current filter selection.", { Data: sales.total }, p(0, 0)),
      viz("cardVisual", "Sales YTD", "Big number: sales year to date on the calendar.", { Data: sales.ytd }, p(1, 0)),
      viz("cardVisual", "Gross margin", "Big number formatted as a percentage.", { Data: sales.margin }, p(2, 0)),
      viz("cardVisual", "Orders", "Big number: distinct order count.", { Data: sales.orders }, p(3, 0)),
      viz("cardVisual", "Card with multiple values", "A single card bound to several measures at once.", { Data: [sales.total, sales.profit, sales.orders] }, p(0, 1)),
      viz("cardVisual", "Card small multiples", "One card per sales channel, using the Rows role.", { Data: sales.total, Rows: store.channel }, p(1, 1)),
        viz("kpi", "KPI vs target", "Actual against target over the indicator's own period date. All three roles come from KpiTargets so the trend axis and the measures agree; binding Indicator from one table and TrendLine from another leaves the visual with no value to show.", { Indicator: kpi.actual, TrendLine: kpi.date, Goal: kpi.target }, p(2, 1)),
      viz("gauge", "Gauge", "Gross margin as a gauge. Min, max and target are left on auto-scale.", { Y: sales.margin }, p(3, 1)),
    ],
  ),
);

// ── 04 Native Table ───────────────────────────────────────────────────────────
PAGES.push(
  page(
    "04 Native - Table",
    "Native - Table and matrix",
    "tableEx takes Values only; pivotTable takes Values with optional Rows and Columns.",
    2,
    2,
    (p) => [
      viz("tableEx", "Table", "Product rows with sales, profit and margin measures.", { Values: [prod.name, prod.cat, sales.total, sales.profit, sales.margin] }, p(0, 0)),
      viz("tableEx", "Table with image column", "Products with their ImageUrl column, which renders as a thumbnail.", { Values: [prod.image, prod.name, sales.total] }, p(1, 0)),
      viz("pivotTable", "Matrix by year", "Sales pivoted by continent and year, with channel on columns.", { Rows: store.cont, Columns: cal.year, Values: sales.total }, p(0, 1)),
      viz("pivotTable", "Matrix by category", "Profit pivoted by product category and sales channel.", { Rows: prod.cat, Columns: store.channel, Values: sales.profit }, p(1, 1)),
    ],
  ),
);

// ── 05 Native Map ─────────────────────────────────────────────────────────────
PAGES.push(
  page(
      "05 Native - Map",
      "Native - Maps",
      "Bing Maps (map, filledMap) needs no account. Azure Maps (azureMap) needs one, so it is not demonstrated here.",
      2,
      2,
      (p) => [
        viz("map", "Customers by city", "Customer locations plotted by latitude and longitude, sized by sales. Latitude and Longitude must be aggregated as Average: bound as bare columns the visual treats them as text and reports 'Remove Location to display latitude and longitude pairs'.", { Category: cust.city, Y: A("DimCustomer", "Latitude", "Average"), X: A("DimCustomer", "Longitude", "Average"), Size: sales.total, Tooltips: sales.orders }, p(0, 0)),
        viz("filledMap", "Sales by continent", "Regions shaded by sales, as a choropleth. Bing Maps, so no account is needed.", { Category: store.cont, Series: store.region, Y: sales.total, Tooltips: sales.profit }, p(1, 0)),
        viz("shapeMap", "Shape map", "Shape map. Its bundled geography is US states, and this model's DimStore is keyed on continent and region, so no shape matches and the map stays unshaded - bind it to a geography your data actually keys on.", { Category: store.cont, Series: store.region, Value: sales.total, Tooltips: sales.profit }, p(0, 1)),
        note(
          "Bing Maps roles are inverted: the role named Y is Latitude and the role named X is Longitude, and both need an aggregate. filledMap uses Y for the value where shapeMap uses Value. Azure Maps (azureMap) is deliberately absent: it requires a provisioned Azure Maps account, so it renders empty in a self-contained sample.",
          p(1, 1),
        ),
      ],
    ),
  );

// ── 06 Native AI ──────────────────────────────────────────────────────────────
PAGES.push(
  page(
      "06 Native - AI & Insights",
      "Native - AI and insight visuals",
      "Desktop-hosted capabilities. Narrative summarises a page or visual you point it at; the older smartNarrative is not used here.",
      3,
      2,
      (p) => [
        viz("decompositionTreeVisual", "Decomposition tree", "Decomposition of total sales, explained by product subcategory.", { Analyze: sales.total, ExplainBy: prod.sub }, p(0, 0)),
        viz("keyDriversVisual", "Key influencers", "Key drivers of total sales, explained by sales channel, detailed by category, with product subcategory as a related factor.", { Target: sales.total, ExplainBy: store.channel, Details: prod.cat, Related: prod.sub }, p(1, 0)),
        viz("narrative", "Narrative", "Narrative summarising the table beside it. Narrative reads a page or visual rather than taking a role of its own.", null, p(2, 0)),
        viz("tableEx", "Narrative source", "The table the narrative above summarises. Narrative picks up the selection or filter context of what it is placed beside.", { Values: [sales.total, sales.profit, sales.margin], Category: store.channel }, p(2, 1)),
      ],
    ),
  );

// ── 07 Native Slicers ─────────────────────────────────────────────────────────
PAGES.push(
  page(
    "07 Native - Slicers",
    "Native - Slicer types and modes",
    "slicer data.mode values: Basic, Dropdown, Between, Before, After, Relative, RelativeTime. Dropdown and Between both need h = 60 + top + bottom.",
    4,
    2,
    (p) => [
      slicer("Dropdown - fiscal year", cal.yearLabel, "Dropdown", "Fiscal year", p(0, 0)),
      slicer("Dropdown - region", store.region, "Dropdown", "Store region", p(1, 0)),
      slicer("Basic - category", prod.cat, "Basic", "Product category", p(2, 0)),
      slicer("Between - order date", cal.date, "Between", "Order date", p(3, 0)),
      viz("listSlicer", "List slicer - continent", "Scrollable list slicer over customer continent.", { Values: cust.cont }, p(0, 1)),
      viz("listSlicer", "List slicer - subcategory", "Scrollable list slicer over product subcategory.", { Values: prod.sub }, p(1, 1)),
      viz("advancedSlicerVisual", "Button slicer - colour", "Tile/button slicer over product colour.", { Values: prod.color }, p(2, 1)),
      viz("advancedSlicerVisual", "Button slicer - channel", "Tile/button slicer over sales channel.", { Values: store.channel }, p(3, 1)),
    ],
  ),
);

function slicer(title, field, mode, headerText, position) {
  return viz(
    "slicer",
    title,
    `Classic slicer in ${mode} mode over ${field.queryRef}.`,
    { Values: field },
    position,
    { objects: { data: one({ mode: lit(L.text(mode)) }) } },
  );
}

// ── 08 Native Media & Shapes ──────────────────────────────────────────────────
PAGES.push(
  page(
    "08 Native - Media & Shapes",
    "Native - Image, shapes and layout objects",
    "Data-bound images require dataCategory: ImageUrl on the column; see image.md.",
    3,
    2,
    (p) => [
      viz(
        "image",
        "Image grid from data",
        "Product images loaded from the DimProduct ProductImage column, which carries dataCategory ImageUrl.",
        null,
        p(0, 0),
        {
          // The image visual has NO query roles. A data-bound image names its
          // column in objects.image.sourceField, not in a queryState role.
          objects: imageObject({
            sourceField: "DimProduct[ProductImage]",
            fit: "Fill",
            altText: "Product image",
          }),
          vco: { padding: one({ top: lit(L.dec(8)), bottom: lit(L.dec(8)), left: lit(L.dec(8)), right: lit(L.dec(8)) }) },
        },
      ),
      viz(
        "image",
        "Static image",
        "Single image loaded directly from a URL, with no data binding.",
        null,
        p(1, 0),
        {
          objects: imageObject({
            sourceUrl: "https://picsum.photos/seed/pbi-gallery-static/480/320",
            fit: "Fit",
            altText: "Static placeholder image",
          }),
          vco: { padding: one({ top: lit(L.dec(8)), bottom: lit(L.dec(8)), left: lit(L.dec(8)), right: lit(L.dec(8)) }) },
        },
      ),
      viz("shape", "Shape", "Shape visual used as a background container behind neighbouring visuals.", null, p(2, 0)),
      viz("basicShape", "Basic shape", "Basic shape, the lighter sibling of the shape visual.", null, p(0, 1)),
      note("Shapes sit on the z-order beneath data visuals. Raise the data visual's z rather than lowering a shape: a shape drawn on top will intercept clicks and block tooltips.", p(1, 1, 2)),
    ],
  ),
);

// ─────────────────────────────────────────────────────────────────────────────
// Custom visuals. `visualType` is the GUID from samples/visual-gallery-assets/
// manifest.csv, which is also the folder name under <Report>/CustomVisuals/.
// ─────────────────────────────────────────────────────────────────────────────

const G = {
  asterisk: "AsterPlot1443303142064",
  bullet: "BulletChart1443347686880",
  chiclet: "ChicletSlicer1448559807354",
  chord: "ChordChart1444757060245",
  dot: "DotPlot1442374105856",
  dualKpi: "PBI_CV_3C80B1F2_09AF_4123_8E99_C3CBC46B23E0",
  scatter: "EnhancedScatterChart1443994985041",
  force: "ForceGraph1449359463895",
  gantt: "Gantt1448688115699",
  infographic: "PBI_CV_73744D90_4DC9_4F18_8BA5_EE8FA5C98035",
  lineDot: "LineDotChart1460463831201",
  mekko: "MekkoChart1449744733038",
  multiKpi: "multiKpiEA8DA325489E436991F0E411F2D85FF3",
  powerKpi: "powerKPI462CE5C2666F4EC8A8BDD7E5587320A3",
  powerKpiMatrix: "powerKPIMatrixEB2381CC88A8425FBEB1B07FF57784E6",
  pulse: "PulseChart1459209850231",
  radar: "RadarChart1446119667547",
  sandDance: "SandDance201929976D117A654D0BAB8E96507442D80B",
  sankey: "sankey02300D1BE6F5427989F3DE31CCA9E0F32020",
  stream: "StreamGraph1446659696222",
  sunburst: "Sunburst1445472000808",
  heatmap: "TableHeatMap1443716069308",
  textFilter: "textFilter25A4896A83E0487089E2B90C9AE57C8A",
  timeline: "Timeline1447991079100",
  tornado: "TornadoChart1452517688218",
  wordCloud: "WordCloud1447959067750",
};

PAGES.push(page("10 Custom - Aster Plot", "Aster Plot", "Roles: Category (Grouping), Y (Measure).", 1, 2, (p) => [
  viz(G.asterisk, "Y against category", "Aster plot of the measure Y grouped by category.", { Category: pts.cat, Y: A("ScatterPoints", "YValue") }, p(0, 0)),
  note("Aster Plot shows how a measure is distributed within each category. Bind Category to the grouping you want to compare and Y to the measure. Roles: Category, Y.", p(0, 1)),
]));

PAGES.push(page("11 Custom - Bullet Chart", "Bullet Chart", "Roles: Category plus up to nine Measure thresholds.", 2, 1, (p) => [
  viz(
    G.bullet,
    "Full threshold set",
    "Bullet chart showing actual against target with the full nine-threshold scale.",
    {
      Category: bullet.cat,
      Value: bullet.value,
      TargetValue: bullet.target,
      Minimum: bullet.min,
      Maximum: bullet.max,
      Satisfactory: M("BulletThresholds", "Bullet Target"),
      Good: M("BulletThresholds", "Bullet Maximum"),
    },
    p(0, 0),
  ),
  viz(G.bullet, "Actual vs target", "Minimal bullet chart: category, actual value and target only.", { Category: bullet.cat, Value: bullet.value, TargetValue: bullet.target }, p(1, 0)),
]));

PAGES.push(page("12 Custom - Chiclet Slicer", "Chiclet Slicer", "Roles: Category, Values, Image.", 1, 1, (p) => [
  viz(G.chiclet, "Term frequencies", "Chiclet slicer over word frequency terms, each with an image.", { Category: words.term, Values: words.freq, Image: words.image }, p(0, 0)),
]));

PAGES.push(page("13 Custom - Chord", "Chord", "Roles: Category, Series, Y.", 1, 1, (p) => [
  viz(G.chord, "Pipeline transitions", "Chord diagram of flow between pipeline stages.", { Category: flow.source, Series: flow.dest, Y: flow.value }, p(0, 0)),
]));

PAGES.push(page("14 Custom - Dot Plot", "Dot Plot", "Roles: Category, Values.", 2, 1, (p) => [
  viz(G.dot, "Sales by subcategory", "Dot plot of sales by product subcategory.", { Category: prod.sub, Values: sales.total }, p(0, 0)),
  viz(G.dot, "Scatter dot value", "Dot plot over the generated scatter points.", { Category: pts.cat, Values: A("ScatterPoints", "DotValue") }, p(1, 0)),
]));

PAGES.push(page("15 Custom - Dual KPI", "Dual KPI", "Roles: axis, topvalues, bottomvalues, toppercentdate, bottompercentdate.", 2, 1, (p) => [
  viz(G.dualKpi, "Actual vs target", "Dual KPI comparing actual against target, split on period date.", { axis: kpi.name, topvalues: kpi.actual, bottomvalues: kpi.target, toppercentdate: kpi.date, bottompercentdate: kpi.date }, p(0, 0)),
  viz(G.dualKpi, "Actual vs prior", "Dual KPI comparing actual against the comparison measure.", { axis: kpi.name, topvalues: kpi.actual, bottomvalues: kpi.comparison }, p(1, 0)),
]));

  PAGES.push(page("16 Custom - Enhanced Scatter", "Enhanced Scatter", "Fifteen optional roles. Its dataViewMappings declare five mutually exclusive combinations, and binding a pair that none of them allows fails with \"There are too many columns\". Each visual below matches one combination.", 2, 2, (p) => [
    viz(G.scatter, "Size, gradient, shape and rotation", "The fullest combination: Category, X, Y, Size, Gradient, Shape and Rotation, with no Series, ColorFill or Image.", { Category: pts.cat, X: A("ScatterPoints", "XValue"), Y: A("ScatterPoints", "YValue"), Size: A("ScatterPoints", "SizeValue"), Gradient: A("ScatterPoints", "GradientValue"), Shape: A("ScatterPoints", "ShapeValue"), Rotation: A("ScatterPoints", "RotationValue") }, p(0, 0)),
    viz(G.scatter, "Image", "Category, X, Y, Size and Image. Image excludes Gradient, ColorFill and Shape.", { Category: pts.cat, X: A("ScatterPoints", "XValue"), Y: A("ScatterPoints", "YValue"), Size: A("ScatterPoints", "SizeValue"), Image: pts.image }, p(1, 0)),
    viz(G.scatter, "Colour fill", "Category, X, Y, Size and ColorFill. ColorFill excludes Gradient and Image.", { Category: pts.cat, X: A("ScatterPoints", "XValue"), Y: A("ScatterPoints", "YValue"), Size: A("ScatterPoints", "SizeValue"), ColorFill: pts.series }, p(0, 1)),
    viz(G.scatter, "Series", "Category, Series, X, Y, Size and ColorFill. Series requires ColorFill or Image, so it cannot stand alone.", { Category: pts.cat, Series: pts.series, X: A("ScatterPoints", "XValue"), Y: A("ScatterPoints", "YValue"), Size: A("ScatterPoints", "SizeValue"), ColorFill: pts.series }, p(1, 1)),
  ]));

PAGES.push(page("17 Custom - Force-Directed Graph", "Force-Directed Graph", "Roles: Source, Target, Weight, LinkType, SourceType, TargetType.", 2, 1, (p) => [
  viz(G.force, "Weighted links", "Force-directed graph of weighted links between pipeline stages.", { Source: flow.source, Target: flow.dest, Weight: A("Flow", "Value") }, p(0, 0)),
  viz(G.force, "Typed links", "Force-directed graph separating link, source and target types.", { Source: flow.source, Target: flow.dest, Weight: A("Flow", "Value"), LinkType: flow.linkType, SourceType: flow.sourceType, TargetType: flow.targetType }, p(1, 0)),
]));

PAGES.push(page("18 Custom - Gantt", "Gantt", "Roles: Task, Parent, StartDate, Duration, Completion, Resource, Legend, Milestones.", 1, 1, (p) => [
  viz(
    G.gantt,
    "Programme schedule",
    "Gantt chart of project tasks grouped by parent phase.",
    {
      Task: gantt.task,
      Parent: gantt.parent,
      StartDate: gantt.start,
      Duration: gantt.duration,
      Completion: gantt.completion,
      Resource: gantt.resource,
      Legend: gantt.legend,
      Milestones: gantt.milestone,
    },
    p(0, 0),
  ),
]));

PAGES.push(page("19 Custom - Infographic Designer", "Infographic Designer", "Roles: Category, Values, Columns, Rows, Legend.", 2, 2, (p) => [
  viz(G.infographic, "Category and values", "Infographic with a single category and value pairing.", { Category: prod.cat, Values: A("FactSales", "SalesAmount") }, p(0, 0)),
  viz(G.infographic, "Rows and columns", "Infographic using Rows and Columns to facet the layout.", { Columns: prod.cat, Rows: store.channel, Values: A("FactSales", "SalesAmount") }, p(1, 0)),
  viz(G.infographic, "Legend and values", "Infographic using a legend field to split the shape.", { Legend: prod.cat, Values: sales.profit }, p(0, 1)),
  note("Infographic Designer has no fixed layout: it picks one from the fields you give it. If it renders a plain list, the usual cause is an under-specified Values role rather than a binding error.", p(1, 1)),
]));

PAGES.push(page("20 Custom - LineDot Chart", "LineDot Chart", "Roles: Date, Values, Counter.", 2, 1, (p) => [
  viz(G.lineDot, "Series over time", "Line and dot chart of the price series over time.", { Date: price.ts, Values: price.value }, p(0, 0)),
  viz(G.lineDot, "With counter line", "LineDot chart including the counter line.", { Date: price.ts, Values: price.value, Counter: price.avg }, p(1, 0)),
]));

PAGES.push(page("21 Custom - Mekko Chart", "Mekko Chart", "Roles: Category, Series, Y, Width.", 2, 1, (p) => [
  viz(G.mekko, "Sales with width series", "Mekko chart where bar width encodes a second measure.", { Category: prod.cat, Series: store.channel, Y: sales.total, Width: A("FactSales", "Quantity") }, p(0, 0)),
  viz(G.mekko, "Profit with width series", "Mekko chart of gross profit with quantity as the width measure.", { Category: prod.cat, Series: store.channel, Y: sales.profit, Width: A("FactSales", "Quantity") }, p(1, 0)),
]));

PAGES.push(page("22 Custom - Multi KPI", "Multi KPI", "Roles: dateColumn, valueColumn, warningStateColumn, tooltipColumn, changeStartDateColumn.", 2, 2, (p) => [
  viz(G.multiKpi, "Date and value", "Multi KPI over the price series date and value.", { dateColumn: price.ts, valueColumn: price.value }, p(0, 0)),
  viz(G.multiKpi, "With tooltip", "Multi KPI including a tooltip field.", { dateColumn: price.ts, valueColumn: price.value, tooltipColumn: price.series }, p(1, 0)),
  viz(G.multiKpi, "With change start date", "Multi KPI including the comparison start date.", { dateColumn: price.ts, valueColumn: price.value, changeStartDateColumn: price.ts }, p(0, 1)),
  note("Multi KPI ships a cluster of small KPI tiles rather than one chart. Its roles are lowercase in the capability definition (dateColumn, valueColumn, warningStateColumn, tooltipColumn, changeStartDateColumn) and are case-sensitive.", p(1, 1)),
]));

PAGES.push(page("23 Custom - Power KPI", "Power KPI", "Roles: Axis, Values, KPI, KPIIndicatorValue.", 2, 2, (p) => [
  viz(G.powerKpi, "Actual with indicator", "Power KPI showing actual value with its status indicator.", { Axis: kpi.name, Values: kpi.actual, KPI: kpi.attainment, KPIIndicatorValue: kpi.status }, p(0, 0)),
  viz(G.powerKpi, "Actual with target", "Power KPI comparing actual to target.", { Axis: kpi.name, Values: kpi.actual, KPI: kpi.target }, p(1, 0)),
  viz(G.powerKpi, "With secondary values", "Power KPI adding the prior-period comparison.", { Axis: kpi.name, Values: kpi.actual, SecondaryValues: kpi.comparison, KPI: kpi.attainment }, p(0, 1)),
  note("Power KPI's Axis role is the category, Values is the figure shown large, and KPI is the comparison drawn behind it. KPIIndicatorValue supplies the status dot.", p(1, 1)),
]));

PAGES.push(page("24 Custom - Power KPI Matrix", "Power KPI Matrix", "Roles: category, date, actualValue, targetValue, kpiIndicatorIndex, kpiIndicatorValue, sortOrderColumn and more.", 1, 1, (p) => [
  viz(
    G.powerKpiMatrix,
    "Indicator matrix",
    "Matrix of indicators with actual, target and status indicator values.",
    {
      category: kpi.name,
      date: kpi.date,
      actualValue: kpi.actual,
      targetValue: kpi.target,
      kpiIndicatorIndex: kpi.index,
      kpiIndicatorValue: kpi.status,
      secondComparisonValue: kpi.comparison,
      sortOrderColumn: kpi.sort,
      image: kpi.icon,
      hyperlink: kpi.link,
    },
    p(0, 0),
  ),
]));

PAGES.push(page("25 Custom - Pulse Chart", "Pulse Chart", "Roles: Timestamp, Value, RunnerCounter, EventTitle, EventSize.", 2, 2, (p) => [
  viz(G.pulse, "Value with runner counter", "Pulse chart with the smoothed counter drawn as the second trace.", { Timestamp: price.ts, Value: price.value, RunnerCounter: price.avg }, p(0, 0)),
  viz(G.pulse, "With events", "Pulse chart with titled, sized event markers.", { Timestamp: price.ts, Value: price.value, RunnerCounter: price.avg, EventTitle: price.eventTitle, EventSize: price.eventSize }, p(1, 0)),
  viz(G.pulse, "Single series", "Pulse chart over one named series only.", { Timestamp: price.ts, Value: price.value }, p(0, 1)),
  note("Pulse Chart is Timestamp plus Value. RunnerCounter draws the counter trace, and EventTitle/EventSize place markers on it. Without a Timestamp the visual has nothing to plot against.", p(1, 1)),
]));

PAGES.push(page("26 Custom - Radar Chart", "Radar Chart", "Roles: Category, Y.", 2, 1, (p) => [
  viz(G.radar, "Four radar axes", "Radar chart with four measures plotted against the category.", { Category: pts.cat, Y: [pts.r1, pts.r2, pts.r3, pts.r4] }, p(0, 0)),
  viz(G.radar, "Single axis", "Radar chart with a single measure, one axis per category.", { Category: pts.cat, Y: A("ScatterPoints", "YValue") }, p(1, 0)),
]));

PAGES.push(page("27 Custom - SandDance", "SandDance", "Single `values` role taking several columns; X, Y, Z, Category and ID come from capability names.", 1, 1, (p) => [
  viz(G.sandDance, "3D scatter of points", "SandDance placing each point on X, Y and Z with category and id.", { values: [C("ScatterPoints", "XValue"), C("ScatterPoints", "YValue"), C("ScatterPoints", "SizeValue"), pts.name, pts.cat] }, p(0, 0)),
]));

PAGES.push(page("28 Custom - Sankey Chart", "Sankey Chart", "Roles: Source, Destination, Weight.", 2, 2, (p) => [
  viz(G.sankey, "Pipeline flow", "Sankey diagram of the lead-to-renewal pipeline.", { Source: flow.source, Destination: flow.dest, Weight: A("Flow", "Value") }, p(0, 0, 2)),
  viz(G.sankey, "Source labels", "Sankey diagram using the optional SourceLabels measure.", { Source: flow.source, Destination: flow.dest, Weight: A("Flow", "Value"), SourceLabels: A("Flow", "Value") }, p(1, 1)),
  note("Sankey needs Source, Destination and Weight on one table. Here both Source and Destination come from Flow, and Weight is the same table's Value measure.", p(0, 1)),
]));

PAGES.push(page("29 Custom - Stream Graph", "Stream Graph", "Roles: Category, Series, Y.", 2, 1, (p) => [
  viz(G.stream, "Channel mix over the year", "Stream graph of sales by channel across the calendar year.", { Category: cal.month, Series: store.channel, Y: sales.total }, p(0, 0)),
  viz(G.stream, "Category mix over the year", "Stream graph of sales by product category.", { Category: cal.month, Series: prod.cat, Y: sales.total }, p(1, 0)),
]));

PAGES.push(page("30 Custom - Sunburst", "Sunburst", "Nodes takes one projection per hierarchy level; Values is the measure.", 2, 1, (p) => [
  viz(G.sunburst, "Three levels", "Sunburst over three hierarchy levels with a value at the leaf.", { Nodes: [tree.l1, tree.l2, tree.l3], Values: tree.value }, p(0, 0)),
  viz(G.sunburst, "Two levels", "Sunburst over the first two hierarchy levels only.", { Nodes: [tree.l1, tree.l2], Values: tree.value }, p(1, 0)),
]));

PAGES.push(page("31 Custom - Table Heatmap", "Table Heatmap", "Roles: Category, Y.", 2, 1, (p) => [
  viz(G.heatmap, "Sales by category and year", "Table heatmap of sales across category and calendar year.", { Category: prod.cat, Y: sales.total }, p(0, 0)),
  viz(G.heatmap, "Profit by region and year", "Table heatmap of gross profit across region and year.", { Category: store.region, Y: sales.profit }, p(1, 0)),
]));

PAGES.push(page("32 Custom - Text Filter", "Text Filter", "Single `field` role.", 2, 2, (p) => [
  viz(G.textFilter, "Filter by term", "Text filter letting a reader type a term to filter on.", { field: words.term }, p(0, 0)),
  viz(G.textFilter, "Filter by product", "Text filter over product name.", { field: prod.name }, p(1, 0)),
  note("Text Filter takes exactly one field and is the only filter control here that is a custom visual rather than a slicer. The Chiclet and Timeline visuals below are also filters, but they are custom visuals rather than slicers in the slicer sense.", p(0, 1, 2)),
]));

PAGES.push(page("33 Custom - Timeline Slicer", "Timeline Slicer", "Single `Time` role, over a date column.", 1, 1, (p) => [
  viz(G.timeline, "Order date range", "Timeline slicer brushing a date range from order date.", { Time: cal.date }, p(0, 0)),
]));

PAGES.push(page("34 Custom - Tornado Chart", "Tornado Chart", "Roles: Category, Series, Values.", 2, 1, (p) => [
  viz(G.tornado, "Variance by region", "Tornado chart of sales against target by region.", { Category: store.region, Series: prod.cat, Values: sales.total }, p(0, 0)),
  viz(G.tornado, "Profit against sales", "Tornado chart contrasting gross profit with total sales.", { Category: store.channel, Series: prod.cat, Values: sales.profit }, p(1, 0)),
]));

PAGES.push(page("35 Custom - Word Cloud", "Word Cloud", "Roles: Category, Values, Excludes.", 2, 2, (p) => [
  viz(G.wordCloud, "Term frequencies", "Word cloud sized by term frequency.", { Category: words.term, Values: words.freq }, p(0, 0)),
  viz(G.wordCloud, "With exclusions", "Word cloud excluding stop words through the Excludes role.", { Category: words.term, Values: words.freq, Excludes: words.excludes }, p(1, 0)),
  viz(G.wordCloud, "By topic", "Word cloud over terms grouped by topic.", { Category: words.term, Values: words.freq, Excludes: words.topic }, p(0, 1)),
  note("Word Cloud sizes each word by its Values measure. A cloud where every word is the same size almost always means the measure is being aggregated away - check that Values is bound to a measure, not a column.", p(1, 1)),
]));

// ── 36 Custom - How To ────────────────────────────────────────────────────────
PAGES.push(
  page(
    "36 Custom - How To",
    "Custom visuals - binding reference",
    "GUID, roles and the tables in this model that satisfy them.",
    1,
    1,
    (p) => [
      textbox(
        [
          { text: "How a custom visual binds in PBIR", size: 18, weight: 600 },
          { text: "Two places carry the GUID: report.json -> publicCustomVisuals[] declares the visual, and visual.json -> visual.visualType names it. Desktop also needs the package payload at <Report>/CustomVisuals/<guid>/, which scripts/extract_custom_visuals.py pulls from the local staging folder. Those packages are publisher binaries and are not committed.", size: 14, color: "#444746" },
          { text: "The report-author CLI has no metadata for custom visual types, so it cannot check custom formatting objects or role names. The role lists below are read from each package's capabilities.dataRoles, not from the CLI. Confirm them with the package after upgrading a visual.", size: 14, color: "#444746" },
          { text: "Not authorable here: Input slicer (no catalog type, and textSlicer is not a verified alias), Q&A (deprecated December 2026), Python and R visuals (runtime dependency), Power Apps, Power Automate and ArcGIS (no catalog type), and the paginated report visual (needs a separate RDL). The legacy types card, multiRowCard, table, matrix, map and filledMap are deliberately absent: use cardVisual, tableEx, pivotTable and azureMap instead.", size: 14, color: "#444746" },
        ],
        p(0, 0),
        "Explanation of how custom visuals bind, and which visual types are not authorable.",
      ),
    ],
  ),
);

// ─────────────────────────────────────────────────────────────────────────────
// Emit
// ─────────────────────────────────────────────────────────────────────────────
const hex = (n, width) => n.toString(16).padStart(width, "0");

function buildVisual(item, visualName, z) {
  const container = {
    $schema: SCHEMA.visual,
    name: visualName,
    position: {
      x: item.position.x,
      y: item.position.y,
      z,
      height: item.position.height,
      width: item.position.width,
      tabOrder: z,
    },
    visual: item.visual,
  };
  // visualContainerObjects is a sibling of objects, i.e. inside "visual", not a
  // sibling of "visual". PBIR_VISUAL_VCO_AT_ROOT rejects the other arrangement.
  if (item.visualContainerObjects) container.visual.visualContainerObjects = item.visualContainerObjects;
  return container;
}

function pageTitleBand(title, subtitle, pageName, seq) {
  const band = (runs, y, h, alt) => ({
    position: { x: MARGIN, y, width: CANVAS.width - 2 * MARGIN, height: h },
    type: "textbox",
    visual: {
      visualType: "textbox",
      objects: {
        general: [
          {
            properties: {
              paragraphs: [
                {
                  textRuns: runs.map((r) => ({
                    value: r.text,
                    textStyle: {
                      fontFamily: r.weight === 600 ? "Segoe UI Semibold" : "Segoe UI",
                      fontSize: `${r.size}px`,
                      color: r.color,
                    },
                  })),
                  horizontalTextAlignment: "left",
                },
              ],
            },
          },
        ],
      },
    },
    visualContainerObjects: {
      ...noChrome(),
      ...(alt ? { general: one({ altText: lit(L.text(alt)) }) } : {}),
    },
  });

  return [
    band([{ text: title, size: 24, weight: 600, color: "#1B1B1F" }], TITLE_Y, TITLE_H, `Page title: ${title}`),
    band([{ text: subtitle, size: 13, color: "#5F6368" }], SUBTITLE_Y, SUBTITLE_H, `Page subtitle: ${subtitle}`),
  ];
}

// Wipe the generated pages so a page removed from the plan cannot linger on disk
// unnoticed. Report-level files (report.json, version.json) are left alone.
if (existsSync(PAGES_DIR)) rmSync(PAGES_DIR, { recursive: true, force: true });
mkdirSync(PAGES_DIR, { recursive: true });

const pageOrder = [];
let visualSeq = 0;

PAGES.forEach((p, pageIndex) => {
  const pageName = "ReportSection" + hex(pageIndex + 1, 24);
  const dir = join(PAGES_DIR, pageName);
  mkdirSync(join(dir, "visuals"), { recursive: true });

  const band = pageTitleBand(p.title, p.subtitle, pageName, pageIndex);
  const items = [...band, ...p.items];

  items.forEach((item, i) => {
    const visualName = hex(++visualSeq, 20);
    const dir2 = join(dir, "visuals", visualName);
    mkdirSync(dir2, { recursive: true });
    writeFileSync(join(dir2, "visual.json"), JSON.stringify(buildVisual(item, visualName, (i + 1) * 1000), null, 2) + "\n", "utf8");
  });

  writeFileSync(
    join(dir, "page.json"),
    JSON.stringify(
      {
        $schema: SCHEMA.page,
        name: pageName,
        displayName: p.displayName,
        displayOption: "FitToPage",
        height: CANVAS.height,
        width: CANVAS.width,
      },
      null,
      2,
    ) + "\n",
    "utf8",
  );

  pageOrder.push(pageName);
});

writeFileSync(
  join(PAGES_DIR, "pages.json"),
  JSON.stringify(
    {
      $schema: SCHEMA.pagesMeta,
      pageOrder,
      activePageName: pageOrder[0],
    },
    null,
    2,
  ) + "\n",
  "utf8",
);

console.log(`[OK] ${PAGES.length} pages, ${visualSeq} visuals written to ${PAGES_DIR}`);