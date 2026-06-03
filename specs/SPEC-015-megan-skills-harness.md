---
id: SPEC-015
title: Megan Skills Harness — Claude/Codex compatible personal automation
status: done
---

# SPEC-015: Megan Skills Harness

## Problem

Megan wants to use Codex more heavily while keeping Claude Code and Codex skills
fully compatible. Current personal skills exist, but the long-term harness needs
clear ownership boundaries:

- `cde-skills` and `cde-ranking-skills` are canonical team/domain libraries.
- `megan-skills` should encode Megan's personal work style, automation defaults,
  token-saving wrappers, and session memory.
- Every coding-agent session must leave durable traces for handoff and Obsidian
  ontology building.

## Acceptance Criteria

### AC-1: Team Skill Delegation

- `megan-skills` wrappers stay short and delegate domain details to
  `cde-skills` / `cde-ranking-skills`.
- A token report identifies the largest skill files and likely compaction
  targets.

### AC-2: Claude/Codex Compatibility

- Claude sync writes personal/team skills to `~/.claude/skills`.
- Codex sync writes normalized skills to both `~/.codex/skills` and
  `~/.agents/skills`.
- Codex hooks are generated without unsupported `async` fields.
- Codex strict config execution succeeds.

### AC-3: Mandatory Session Memory

- Claude and Codex receive session lifecycle hooks.
- Session end writes project-local `.claude/handoff/latest.md`.
- Session end appends global `~/.claude/handoffs/index.jsonl`.
- Session end stores an Obsidian markdown note through `ai-env session save`.
- Session notes contain an `## Ontology Seeds` section.

### AC-4: Harness Roadmap

- A roadmap documents the harness architecture, token strategy, session memory
  contract, and remaining risks.

## Tasks

- [x] Task-01: Merge Codex compatibility branch into local `main`.
- [x] Task-02: Add token report generation for skill files.
- [x] Task-03: Add Megan harness roadmap.
- [x] Task-04: Sync Codex hooks and generate hooks.json from ai-env.
- [x] Task-05: Add Obsidian ontology seed section to session notes.
- [x] Task-06: Add ontology extraction script from session notes.
- [x] Task-07: Compact top cde-ranking wrapper skills into references-backed
  summaries.
- [x] Task-08: Add Claude agent definitions for Megan harness roles.
- [x] Task-09: Store coding-agent session notes in Obsidian `00_session`.

## Notes

- Initial `cde-skills` and `cde-ranking-skills` pull from `develop` failed
  because SSH to `github.daumkakao.com:22` timed out.
- After VPN connection, both symlinked repositories pulled successfully and were
  already up to date.
