# Power BI Development Instructions

**Target**: Power BI Standard workspace. Linux is the authoring and source-control environment; Windows Power BI Desktop is the rendering and publishing validator.

**Do NOT assume**: Fabric capacity, Fabric Git integration, deployment pipelines, XMLA write, or OneLake connectivity.

## Agent Skill Library

All agent skills live in `.agents/skills/`. **Load the relevant `SKILL.md` before starting any task.**

| Task | Skill |
|------|-------|
| Report planning, design, authoring, publish | `.agents/skills/powerbi-report-cli/SKILL.md` |
| Semantic model, TMDL, DAX, measures, deploy | `.agents/skills/semantic-model-authoring/SKILL.md` |
| Natural-language data Q&A over reports | `.agents/skills/fabriciq/SKILL.md` *(requires FabricIQ MCP endpoint)* |

Common reference docs (referenced by skills): `.agents/common/COMMON-CORE.md`, `COMMON-CLI.md`, `ITEM-DEFINITIONS-CORE.md`.

## Core Rules

- **Plan before editing.** Never work directly on `main`.
- **Never invent schema objects**, workspace GUIDs, or data values.
- **Never expose secrets or credentials** — use `.env` (gitignored) or CI secrets only.
- **Never write to production** — publish only after the release-reviewer returns GO.
- **Never claim visual correctness** without rendering evidence from Power BI Desktop.
- **Before nontrivial DAX, time-intelligence, or M work**: consult `.github/instructions/reference-resources.instructions.md` and record references used.

## Fiscal Calendar

This repo ships both month-aligned (`fnCalendar`) and week-based (`fnCalendarWeekBased`) Power Query functions. The active pattern is set in `config/fiscal-calendar.json`. Week-based calendars (4-4-5, 4-5-4, 5-4-4, 13-period) require custom DAX for time intelligence — do NOT use standard `TOTALYTD`/`DATESYTD` with these patterns.

## Validation

Always run before committing:
```bash
python3 scripts/validate_repo.py
python3 scripts/validate_date_table.py
bash scripts/validate_pbir.sh
python3 scripts/validate_m_expressions.py
```

## PBIP authoring guardrails

These five defects pass every schema-level check and still fail on open, on refresh, or on
deploy. `validate_m_expressions.py`, `validate_pbir_schema.py`, and `validate_repo.py` enforce
them — do not hand off work that has not been run through all three.

- **Partition paths come from a parameter (GAP-08).** `File.Contents` resolves a relative
  path against the M engine's working directory, not the PBIP root. Use
  `File.Contents(BasePath & "data/x.csv")` with a declared `IsParameterQuery=true`
  expression, never `File.Contents("data/x.csv")`.
- **No `;` on the terminating `in` expression (GAP-07).** M has no `;` statement terminator.
  A trailing semicolon makes the parser demand a token identifier, and the offending `;` is
  usually on the line *after* `in`.
- **Write PBIP files the way Desktop does (GAP-09).** `themeCollection` is an object with a
  `baseTheme` entry, `resourcePackages` is a flat `{name, type, items}` list (not wrapped in
  `{"resourcePackage": {...}}`), `report.json` omits `layoutOptimization`, and
  `version.json` carries both `$schema` and `version: "2.0.0"`. Deviations open without error
  but break theme rendering or get rewritten on first save.
- **The `.pbip` manifest lists the report and nothing else (GAP-11).** `artifacts` must be
  exactly `[{"report": {"path": "<Name>.Report"}}]`. A `semanticModel` entry is *prohibited*,
  not merely unrecognised, and makes Desktop refuse to open the project outright:
  `Property 'semanticModel' has not been defined and the schema does not allow additional
  properties`. The model is already reached via `definition.pbir` → `datasetReference.byPath`,
  so do not add it. This is the one defect in this list that is a hard stop rather than a
  silent deviation, and `validate_repo.py` §5 enforces it.
- **A `.Report` folder needs `.platform` and every definition file needs `$schema`
  (GAP-10).** Write a `.platform` into *both* the `.Report` and `.SemanticModel` folders, with
  a stable `config.logicalId` UUID generated once and never changed. `pages.json` and every
  `page.json` need `$schema`, and `page.json` also needs `displayOption` (`FitToPage`).
  Desktop opens all of these without complaint and the Fabric toolchain rejects them, so
  "it opens in Desktop" is not evidence of correctness. Prefer `scaffold_pbir.py`, which
  emits all of it.

- **Aggregate in M is `List.*`, not `Number.*` (GAP-12).** `MAX()`/`MIN()` are DAX and
  Excel idioms; the `Number` module has no `Max`, `Min`, `Sum`, `Average` or `Count`. Writing
  `Number.Max(a, b)` parses fine, imports fine, and only fails on refresh with
  `The import Number.Max matches no module reference`. Use `List.Max({a, b})` and
  `List.Min({a, b})` — the braces are required, since `List.Max` takes one list argument.
  Same trap for `Text.Len` → `Text.Length`, `Text.Concat` → `Text.Combine`,
  `Number.IsBlank(x)` → `x = null`. Fix the `.m` reference file as well as the TMDL body, or
  the next generation reintroduces it.

Never commit Desktop-generated state (`**/.pbi/`, `diagramLayout.json`,
`semanticModelDiagramLayout.json`) — it is rewritten on every open and save.
