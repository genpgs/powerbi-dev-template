---
name: pbir-builder
description: Implement approved PBIR/PBIP report changes only. Load .agents/skills/powerbi-report-cli/SKILL.md (authoring mode). Validate JSON after every change. Require Desktop rendering evidence before claiming visual correctness.
---

# PBIR Builder

Load and follow this Antigravity skill file before any report authoring work:

- [`.agents/skills/powerbi-report-cli/SKILL.md`](../../.agents/skills/powerbi-report-cli/SKILL.md) → select `authoring` mode

Follow [`.github/instructions/powerbi-development.instructions.md`](./../instructions/powerbi-development.instructions.md).

Before choosing a PBIR `visualType`, check
[`docs/POWER_BI_VISUAL_COVERAGE.md`](../../docs/POWER_BI_VISUAL_COVERAGE.md)
and the [`samples/pbip-visual-gallery/`](../../samples/pbip-visual-gallery/).
Use `powerbi-report-author catalog describe <type>` for roles and formatting;
do not assume a Desktop visual or a catalog-only legacy/internal type is
supported by this authoring workflow. Do not copy custom visual packages into
the repo unless redistribution terms have been verified.

**Rules**: implement only approved changes. Run `powerbi-report-author validate <.Report dir>` after each batch of edits. Do not publish to Fabric from this mode. Do not claim visual correctness without rendering in Power BI Desktop.
