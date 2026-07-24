# megan-harness

megan 의 개인 Claude Code / Codex 스킬·에이전트 묶음. ai-env 산하에서 관리.

> 외부 팀 스킬(cde-skills, cde-ranking-skills, jackie-skills)과 외부 레퍼런스를
> 큐레이션해 **개인 워크플로우 (Obsidian + Jira + git + Trino)** 에 맞춰 재구성.

## 설치

```bash
# ai-env 가 sync 시 자동으로 ~/.claude/skills/ 에 심링크 (Phase 6 이후)
uv run ai-env sync

# 수동 (Phase 6 이전 임시)
ln -snf $(pwd)/megan-harness/skills/*/* ~/.claude/skills/
```

Codex CLI 도 동일하게 동작 (ai-env `core/codex_skills.py` 가 정규화).

## 스킬 목록

자세한 인덱스는 [SKILLS.md](SKILLS.md). 카테고리:

| 카테고리 | 용도 |
|---|---|
| `obsidian/` | hot 컨텍스트, vault lint, distill, wikilink, defuddle |
| `work/` | Jira ↔ vault, daily wrap-up |
| `data/` | Trino, Elasticsearch (cde-ranking-skills lib 재사용) |
| `code/` | Codex 2nd-opinion, branch-guard, PR 평가, spark 최적화 가이드 |
| `meta/` | auto-memory 정리 |

## 설계 철학

- Claude Code + Codex CLI 만 지원 (Gemini 는 웹).
- Obsidian vault (`~/Documents/Obsidian Vault`, 공백 포함) 가 single substrate. 분류는 dewey-style 숫자 prefix (`90_journal`, `1X_업무카카오`, `99_archive` 등). 디렉토리 매핑은 [DESIGN.md](DESIGN.md#1-원칙-why) 참조.
- Trino-only SQL.
- 외부 도메인 스킬(cde-ranking) 은 그대로 reference 하고 재구현 금지.
- 토큰 효율: SKILL.md 짧게, 상세는 `references/` lazy load.

세부 결정은 [DESIGN.md](DESIGN.md) 참조.

## ai-env 와의 관계

megan-harness 는 ai-env 의 **개인 스킬·에이전트 sync 소스**. 개인 스킬은
`megan-harness/skills/{category}/{skill}/`, 개인 에이전트는 `megan-harness/agents/`
에 모여 있고, `core/sync.py` 가 이를 personal 로 인식해 배포한다.

| ai-env 자산 | megan-harness 와의 관계 |
|---|---|
| `megan-harness/skills/ai-env/handoff-resume` | cross-cwd 인계 (SPEC-014). |
| `megan-harness/skills/ai-env/{spec-manager,task-implement,code-review,doc-sync}` | workflow 의 핵심. |
| `cde-ranking-skills/lib/` | megan 의 `data/` 스킬이 import. |
| `core/sync.py` | `megan-harness/skills/{category}/{skill}/` 와 `megan-harness/agents/` 를 personal 로 인식. 이름 충돌 시 personal 이 팀(cde-*skills) 스킬을 덮어쓴다 (personal-wins). |

## 상태 (Phase)

- [x] Phase 0 — 계획 + 스캐폴딩
- [x] Phase 1 — Obsidian core (hot-context, distill, vault-lint)
- [x] Phase 2 — Work (jira-task skeleton, wrap-up). pull/push API wiring 은 P2.5
- [x] Phase 3 — Data (trino-query, es-query) — cde-skills 위임 wrapper
- [x] Phase 4 — Code (second-opinion, branch-guard, pr-evaluator, spark-optimize)
- [x] Phase 5 — Defuddle (auto-wikilink, auto-session-archive 는 후속)
- [x] Phase 6 — ai-env sync 통합 (`core/sync.py` 의 `_collect_skill_sources` 가 megan-harness 자동 인식, personal-wins dedup)
- [ ] Phase 7 — (선택) 별도 git repo 분리

## 라이선스 / 출처

- jackie-skills 패턴 — `/Users/megan/work/cde/jackie-skills` 에서 차용
- cde-skills, cde-ranking-skills — 그대로 외부 참조
- kepano/obsidian-skills, AgriciDaniel/claude-obsidian — 패턴 영감

각 스킬 SKILL.md 첫 부분에 `# Origin:` 으로 출처를 명시한다.
