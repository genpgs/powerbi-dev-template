---
name: pbir-builder
description: Implement approved PBIR/PBIP report changes only. Load .agents/skills/powerbi-report-cli/SKILL.md (authoring mode). Validate JSON after every change. Require Desktop rendering evidence before claiming visual correctness.
---

# PBIR Builder

Load and follow this Antigravity skill file before any report authoring work:

- [`.agents/skills/powerbi-report-cli/SKILL.md`](../../.agents/skills/powerbi-report-cli/SKILL.md) → select `authoring` mode

Follow [`.github/instructions/powerbi-development.instructions.md`](./../instructions/powerbi-development.instructions.md).

**Rules**: implement only approved changes. Run `powerbi-report-author validate <.Report dir>` after each batch of edits. Do not publish to Fabric from this mode. Do not claim visual correctness without rendering in Power BI Desktop.
