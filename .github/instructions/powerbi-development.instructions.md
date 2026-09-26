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
```
