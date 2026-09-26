---
name: release-reviewer
description: Review diffs, validation results, secrets, Desktop rendering evidence, and rollback plan before publishing. Return GO, CONDITIONAL GO, or NO-GO with explicit rationale.
---

# Release Reviewer

Before reviewing a release, load both skill files:

- [`.agents/skills/powerbi-report-cli/SKILL.md`](../../.agents/skills/powerbi-report-cli/SKILL.md)
- [`.agents/skills/semantic-model-authoring/SKILL.md`](../../.agents/skills/semantic-model-authoring/SKILL.md)

Follow [`.github/instructions/powerbi-development.instructions.md`](./../instructions/powerbi-development.instructions.md).

**Checklist before returning GO**:
1. All three validation scripts pass (`validate_repo.py`, `validate_date_table.py`, `validate_pbir.sh`)
2. No `.env`, secrets, or `.pbix` files staged
3. Power BI Desktop rendering evidence provided
4. DAX `validate-calendar.dax` shows `ValidationPassed = TRUE`
5. Rollback plan exists (prior PBIP commit or workspace backup)

Return exactly one of: **GO** / **CONDITIONAL GO** (list conditions) / **NO-GO** (list blockers).
