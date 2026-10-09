# SPEC-04 — Upstream Skill Installation

**Status:** Draft · **Depends on:** `SPEC-01`, `SPEC-03`

---

## 1. Purpose

`motherduckdb/agent-skills` is the upstream, MIT-licensed skill collection covering DuckDB SQL. The template's plan document proposed installing "the upstream DuckDB-SQL/CLI/exploration skills that fit local use."

**On review, that subset is smaller than first assumed.** This spec records the evidence, because getting this wrong puts MotherDuck-dependent instructions in front of local-only users — the exact failure `SPEC-01` §3 exists to prevent.

---

## 2. Upstream facts (verified)

| Fact | Value |
|---|---|
| Repository | `motherduckdb/agent-skills` |
| License | MIT |
| Skill count | 22 |
| Install routes | Vercel Skills CLI (`npx -y skills add …`), Claude Code plugin marketplace, GitHub Copilot CLI plugin, Codex plugin, Gemini CLI extension, manual directory copy |
| Runtime requirement | **Node.js ≥ 22.20** (Skills CLI `package.json`) |
| Connection behaviour | Upstream README states installing skills **does not** configure a MotherDuck connection or MCP server. |
| Telemetry | The Skills CLI collects anonymous install telemetry. Suppress with `DISABLE_TELEMETRY=1` or `DO_NOT_TRACK=1`. |

Upstream publishes a machine-readable catalog at `skills/catalog.json` with per-skill `depends_on` metadata, plus `docs/install-matrix.md` and `HARNESSES.md`.

---

## 3. Local-usable subset — corrected

The plan document listed `motherduck-duckdb-sql`, `motherduck-query`, and `motherduck-explore`. Reading the actual `SKILL.md` files contradicts two of the three.

| Skill | Evidence | Local-usable? |
|---|---|---|
| `motherduck-duckdb-sql` | Body is DuckDB SQL syntax and dialect guidance. Frontmatter is `name` / `description` / `license: MIT`. **No connection prerequisite declared.** Some guidance references MotherDuck feature-support docs. | **Yes** — the only skill that qualifies. |
| `motherduck-query` | Frontmatter `description`: "…against **MotherDuck data**." Body **Prerequisites: "An established MotherDuck connection (or an active MotherDuck MCP server)"**; workflow instructs calling `get_query_guide`; uses MotherDuck MCP `query_rw`. | **No** |
| `motherduck-explore` | Frontmatter `description`: "Discover **MotherDuck** databases, tables, columns, **shares**…". Body **Prerequisites: "An established MotherDuck connection (or an active MotherDuck MCP server)"**; instructs checking shared databases and Drive/Flight status. | **No** |
| `motherduck-cli` | This is the **MotherDuck CLI**, a different product from DuckDB's standalone CLI. Its posture assumes an authenticated CLI, `MOTHERDUCK_TOKEN`, and `MOTHERDUCK_HOME`. | **No** — excluded by `SPEC-01` §3 |
| All 18 remaining skills | Every one declares `depends_on` on `motherduck-connect` or another MotherDuck-only skill, and/or is scoped to MotherDuck product features (Dives, Flights, shares, Guides, DuckLake, REST API, security governance, pricing, migrations, dashboards, pipelines, CFA apps, partner delivery, self-serve rollout). | **No** |

**Conclusion: the local-usable subset is exactly one skill — `motherduck-duckdb-sql`.**

This is a material correction to the plan document and is recorded here rather than silently dropped. Correcting it *upward* in scope would have violated `SPEC-01` §3; correcting it downward is what the boundary requires.

---

## 4. Framing risk for the one acceptable skill

`motherduck-duckdb-sql` is DuckDB-generic in substance but MotherDuck-framed in instruction. Its guidance tells the agent to verify MotherDuck-specific command support and to check MotherDuck version-lifecycle docs before promising a feature.

Mitigations:
- Document it as **DuckDB SQL syntax reference with some MotherDuck-flavoured guidance that does not apply here.**
- State plainly that MotherDuck-specific portions are out of scope for this template.
- Do not ask users to evaluate its MotherDuck claims.

**Abandonment condition:** if the upstream skill becomes predominantly MotherDuck-scoped such that a local user following it is led astray, stop documenting it. No code depends on it, so removal is a docs-only revert. This is a key advantage of not vendoring.

---

## 5. Install-scope collision — a real hazard

Per the Skills CLI's own agent table:

| Agent | `--agent` value | Project path | Global path |
|---|---|---|---|
| OpenCode | `opencode` | **`.agents/skills/`** | `~/.config/opencode/skills/` |
| GitHub Copilot | `github-copilot` | **`.agents/skills/`** | `~/.copilot/skills/` |
| Claude Code | `claude-code` | `.claude/skills/` | `~/.claude/skills/` |

**`.agents/skills/` is this repository's canonical first-party skill directory** — the three skills listed in `CLAUDE.md:11-19`, `.github/instructions/powerbi-development.instructions.md:11-15`, and `docs/GETTING_STARTED.md:334-338`.

A project-scoped install for OpenCode or Copilot would therefore **write 22 third-party MotherDuck skills into the first-party skill tree**, where they would sit alongside first-party skills and be picked up by every harness that reads `.agents/skills/` — including agents the user never targeted. Only the requested subset would install, but the pollution of a canonical directory is the problem, not the count.

**Decision: recommend `--global` for the upstream subset.** It keeps `.agents/skills/` first-party-only, and it is also the better user experience — the upstream skill is a general DuckDB reference, useful across projects, not a property of this template.

The docs must state this reason explicitly, because `--global` is otherwise the counterintuitive recommendation and a user may "correct" it to project scope.

**Windows note:** the Skills CLI symlinks by default and supports `--copy` where symlinks are unavailable. Docs should include `--copy` in the Windows variant.

---

## 6. Node.js requirement

The Skills CLI requires **Node ≥ 22.20**. This repository's devcontainer currently pins Node `20` (`.devcontainer/devcontainer.json:5`), which is insufficient.

Resolved by `SPEC-01` D5 / PR 1: devcontainer Node → `"22"`.

Three documentation locations currently state **Node 18** and are stale relative to both the devcontainer and the real requirement:
- `docs/GETTING_STARTED.md:13`
- `README.md:104` (prerequisites)
- `mcp/mcp.json.example:16-22` (`_notes`)

All three are corrected in PR 1.

---

## 7. Documented commands (draft)

Only `motherduck-duckdb-sql` appears. No command below requires or implies MotherDuck authentication.

**OpenCode (global):**
```bash
npx -y skills add motherduckdb/agent-skills \
  --agent opencode --skill motherduck-duckdb-sql --yes --global
```

**Claude Code** — either the plugin route:
```
/plugin marketplace add motherduckdb/agent-skills
/plugin install motherduck-skills@motherduck-skills
```
or the Skills CLI:
```bash
npx -y skills add motherduckdb/agent-skills \
  --agent claude-code --skill motherduck-duckdb-sql --yes --global
```

**GitHub Copilot:**
```bash
npx -y skills add motherduckdb/agent-skills \
  --agent github-copilot --skill motherduck-duckdb-sql --yes --global
```
(add `--copy` if symlinks are unavailable)

**Manual, any harness** — copy the whole skill directory, not only `SKILL.md`:
```bash
mkdir -p ~/.agents/skills
cp -R <checkout>/skills/motherduck-duckdb-sql ~/.agents/skills/
```

**Update / verify:**
```bash
npx -y skills update -g          # global
npx -y skills list -g            # confirm installed
DISABLE_TELEMETRY=1 npx -y skills add …   # opt out of install telemetry
```

**Known compatibility limits** (from the Skills CLI's own matrix): basic skills and `allowed-tools` are supported in all three target harnesses; `context: fork` and **hooks are not supported in OpenCode**. If a skill relies on hooks it will not work there. `motherduck-duckdb-sql` declares no hooks, so this does not affect it — but the limit is recorded.

---

## 8. Requirements on our documentation

1. Name **only** `motherduck-duckdb-sql`.
2. Explicitly list what is excluded and why (the §3 table), so users who find the full catalog understand the omission.
3. Recommend `--global`, with the `SPEC-04` §5 reason.
4. Include the Node ≥ 22.20 requirement and a pointer to the devcontainer.
5. Include update and verification steps.
6. Mention telemetry suppression.
7. State that the template does not install these skills itself.
8. Do not re-teach DuckDB SQL in first-party docs — link to the installed skill instead.

---

## 9. Assumptions

| ID | Assumption | Risk if wrong |
|---|---|---|
| A12 | A MotherDuck-framed but DuckDB-generic skill is still net-useful to local users. | Medium. Mitigated by the abandonment condition in §4; no code dependency. |
| A13 | `--global` install is acceptable to template users who expect project-scoped config. | Medium. It is a deliberate trade-off against `.agents/skills/` pollution. Users can override with an explicit project-scoped command if they accept the collision. |
| A14 | Upstream will keep publishing the skill under the same name. | Low. Removal is a docs-only revert. |