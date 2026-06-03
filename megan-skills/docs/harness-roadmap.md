# Megan Skills Harness Roadmap

## Goal

Build `megan-skills` as a token-efficient personal harness that works in both
Claude Code and Codex:

- Use `cde-skills` and `cde-ranking-skills` as canonical domain tool libraries.
- Keep `megan-skills` as thin wrappers for Megan's working style, routing, and
  automation preferences.
- Record every coding-agent session into project-local `latest.md`, global
  handoff index, and Obsidian notes for later ontology construction.

## Current Findings

- `cde-ranking-skills` has the highest context cost. The largest skills are:
  `service-onboard`, `ranking-data-verify`, `feature-crud`,
  `forme-trino-lookup`, and `forme-redis-lookup`.
- `cde-skills` already uses compact category-level plugin skills
  (`data`, `development`, `operations`, `orchestration`, `platform`,
  `productivity`). These are good delegation anchors.
- `megan-skills` should not copy long domain procedures. It should point to team
  skills and add Megan-specific defaults, safety gates, output formats, and
  Obsidian logging conventions.

## Harness Pattern

Use an orchestrator-subagent pattern:

1. **Router layer**: keyword and command matching, zero-token where possible.
2. **Wrapper skill layer**: short personal workflow and delegation instructions.
3. **Team skill layer**: cde domain details and scripts.
4. **Session memory layer**: hooks write local handoff + Obsidian note.
5. **Ontology layer**: session notes use stable frontmatter and sections for
   future graph/ontology extraction.

## Claude and Codex Compatibility Contract

All personal skills must satisfy:

- `SKILL.md` has strict YAML frontmatter with `name` and `description`.
- Body stays concise; detailed references live under `references/` or team
  skills.
- Scripts are executable, deterministic, and avoid agent-specific APIs.
- Claude receives skills under `~/.claude/skills`.
- Codex receives normalized skills under both `~/.codex/skills` and
  `~/.agents/skills`.
- Codex hooks must not contain unsupported `async` fields.

## Session Recording Contract

Every coding-agent session should produce:

- Project latest handoff: `.claude/handoff/latest.md`
- Project archive: `.claude/handoff/archive/*.md`
- Global index: `~/.claude/handoffs/index.jsonl`
- Obsidian note: `{obsidian_base}/00_Sessions/YYYY-MM-DD-*.md`

The Obsidian note should include:

- agent, session id, cwd, branch, timestamp
- git status, recent commits, diff stat
- last task or extracted transcript summary
- explicit `## Ontology Seeds` section for entities, tools, decisions, and TODOs

## Work Plan

1. Sync cde repos from `develop` when network access is available.
2. Generate a token report for team and Megan skills.
3. Keep or create Megan wrapper skills only where they add policy or workflow.
4. Move long examples into `references/` when a wrapper exceeds roughly 450
   words.
5. Enforce session recording via Claude and Codex hooks.
6. Add an ontology extraction script after the note schema stabilizes.

## Open Risks

- Current SSH access to `github.daumkakao.com:22` timed out, so cde repos could
  not be refreshed in this run.
- Codex hook support is evolving; sync must sanitize unsupported fields before
  writing `~/.codex/hooks.json`.
