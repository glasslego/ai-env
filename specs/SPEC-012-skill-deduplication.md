---
id: SPEC-012
title: 스킬 중복 제거 및 등록 체계 정리
status: in-progress
created: 2026-03-14
updated: 2026-03-15
---

# SPEC-012: 스킬 중복 제거 및 등록 체계 정리

## 1. 배경

현재 시스템 메시지에 스킬이 **54개** 이상 등록되어 있으며, 3가지 유형의 중복이 발생한다.

### 중복 유형

**Type A — 완전 중복 (같은 이름 2회 등장)**

Personal 스킬 15개가 시스템 메시지에 정확히 2번 나타남:
`research`, `wiki-manager`, `spec-manager`, `code-review`, `task-implement`,
`doc-sync`, `python-env`, `pyspark-best-practices`, `agit-search`, `harness`,
`elasticsearch-query`, `skill-creator`, `spark-debug`, `project-workflow`, `jira-weekly-update`

Commands도 마찬가지: `wf-code`, `wf-spec`, `wf-init`, `wf-research`, `wf-review`,
`wf-run`, `commit`, `sync`, `setup`, `handoff`, `cleanup-branches`, `git-summary`,
`fix-github-issue`, `rename-files`, `upgrade-ai-tools`, `add-mcp`, `token-rotate`

**Type B — 기능적 중복 (다른 이름, 같은 기능)**

| 기능 | 중복 스킬들 | 비고 |
|------|------------|------|
| 스펙 관리 | `spec-manager`, `spec-ops` | 이름만 다름 |
| 코드 리뷰 | `code-review`, `review-ops`, `review-code`, `review` | 4개 중복 |
| Task 구현 | `task-implement`, `code-ops`, `wf-code`, `code-from-spec` | skill+command 중복 |
| 리서치 | `research`, `research-ops`, `wf-research` | skill+command 중복 |
| 문서 동기화 | `doc-sync` (2회) | 완전 동일 |
| 워크플로우 | `project-workflow` (2회), `wf-init`/`workflow-init` | command 중복 |

**Type C — Personal ↔ Team 스킬 중복**

| Personal | Team (cde-skills) | 중복도 |
|----------|-------------------|--------|
| `wiki-manager` | `wiki` | 95% |
| `agit-search` | `agit` | 80% |
| `elasticsearch-query` | `elasticsearch` | 50% |
| `jira-weekly-update` | `jira-weekly` | 85% |

### 영향

- AI가 유사 스킬 중 어떤 것을 트리거할지 비결정적
- 토큰 낭비 (시스템 메시지에 중복 description 반복)
- 유지보수 부담 (같은 기능을 여러 곳에서 수정)

## 2. 목표

1. 시스템 메시지의 스킬 목록에서 중복을 제거한다
2. Personal ↔ Team 스킬 간 역할 경계를 명확히 한다
3. Skill ↔ Command 간 기능 중복을 해소한다

## 3. Task 목록

### Task-01: Type A 중복 원인 파악 및 수정

같은 이름의 스킬/커맨드가 시스템 메시지에 2번 나타나는 원인을 찾아 수정한다.

**가설**: `sync.py`가 personal 스킬을 `~/.claude/skills/`로 복사할 때, 원본과 복사본이 모두 인식되거나, commands와 skills가 별도 등록되면서 중복 발생.

**AC:**
- [x] 중복 등록 원인 규명: Claude Code가 프로젝트 `.claude/skills/`와 글로벌 `~/.claude/skills/` 양쪽 인식
- [x] 동일 이름 스킬이 1번만 나타나도록 수정: `.claude/skills/` → `.claude/skill-src/`, `.claude/commands/` → `.claude/cmd-src/`로 이름 변경하여 Claude Code 자동 인식 방지
- [ ] `ai-env sync` 후 `~/.claude/skills/` 내용 검증 스크립트 추가

### Task-02: Type B 기능적 중복 통합

같은 기능의 스킬들을 하나로 통합한다.

**통합 방안:**

| 유지할 스킬 | 제거/리다이렉트 | 이유 |
|------------|----------------|------|
| `spec-manager` | `spec-ops` 제거 | `-manager` 접미사가 CRUD 의미 명확 |
| `code-review` | `review-ops`, `review-code` 제거, `review`는 command로 유지 | skill은 1개, command는 별도 용도 |
| `task-implement` | `code-ops` 제거, `code-from-spec` 제거 | `wf-code`는 command로 유지 (Phase 4 진입점) |
| `research` | `research-ops` 제거 | `wf-research`는 command로 유지 (Phase 2 진입점) |
| `project-workflow` | 중복 등록 제거 | `wf-init`/`workflow-init` 중 하나 제거 |

**AC:**
- [x] 기능 중복 스킬 제거: `spec-ops`, `review-ops`, `code-ops`, `research-ops` (글로벌) 삭제 완료
- [x] 중복 커맨드 제거: `code-from-spec`, `research-pipeline`, `review-code`, `synthesize-spec`, `workflow-init` (글로벌) 삭제 완료
- [ ] Skill vs Command 역할 분담 문서화

### Task-03: Type C Personal ↔ Team 스킬 정책 수립

**정책안:**

```
Personal 스킬: 프로젝트 워크플로우 핵심 (spec-manager, task-implement 등)
Team 스킬:     도메인 도구 (wiki, agit, elasticsearch, jira 등)
```

중복 발생 시 Team 스킬을 우선하고 Personal은 제거한다.

| 조치 | 스킬 | 이유 |
|------|------|------|
| Personal 제거 | `wiki-manager` | Team `wiki`가 동일 기능 |
| Personal 제거 | `agit-search` | Team `agit`가 상위 호환 (Jira 연동 포함) |
| 유지 (특화) | `elasticsearch-query` | Team `elasticsearch`와 범위 다름 (gift 특화) → 이름을 `es-gift-ranking`으로 변경 |
| 판단 필요 | `jira-weekly-update` | Team `jira-weekly`와 계층 구조만 다름 → 사용자 확인 |

**AC:**
- [x] Personal ↔ Team 스킬 중복 정책 결정: Team 우선, Personal 제거
- [x] `wiki-manager`, `agit-search` Personal 스킬 제거 완료
- [x] `elasticsearch-query` → `es-gift-ranking` 이름 변경 완료
- [x] `jira-weekly-update` Personal 스킬 제거 완료 (Team `jira-weekly` 사용)
- [ ] 정책을 CLAUDE.md 또는 project-profile.yaml에 문서화

### Task-04: Skill ↔ Command 역할 분담 명확화

현재 혼재:
- `/wf-code` (command) ≈ `task-implement` (skill)
- `/wf-research` (command) ≈ `research` (skill)
- `/review` (command) ≈ `code-review` (skill)

**분담 원칙:**
```
Command (/wf-*):  워크플로우 Phase 진입점. topic_id를 받아 Phase 컨텍스트 설정.
                  내부에서 해당 Skill을 호출하는 오케스트레이터.
Skill:            도메인 로직 캡슐화. Command 없이도 독립 사용 가능.
```

**AC:**
- [ ] Command는 Skill을 호출하는 thin wrapper로 역할 정리
- [ ] Command와 Skill의 description이 명확히 다르게 작성 (트리거 혼동 방지)
- [ ] Command에 `# 이 커맨드는 {skill-name} 스킬을 Phase 컨텍스트로 호출합니다` 주석 추가

### Task-05: 스킬 등록 검증 자동화

중복이 재발하지 않도록 CI에서 검증한다.

**AC:**
- [ ] `scripts/check_skill_duplicates.py` 작성
  - 모든 SKILL.md의 name 필드 수집
  - 이름 중복 검출
  - description 유사도 검출 (선택)
- [ ] CI workflow에 추가 (`.github/workflows/ci.yml`)
- [ ] `ai-env doctor`에 스킬 중복 검사 항목 추가

## 4. 구현 순서

```
Task-01 (Type A 원인 파악) → Task-02 (기능 중복 통합) → Task-03 (Personal/Team 정책)
                                                          ↘
                                                    Task-04 (Skill/Command 분담)
                                                          ↘
                                                    Task-05 (CI 검증)
```

## 5. 예상 결과

| 지표 | Before | After |
|------|--------|-------|
| 시스템 메시지 스킬 수 | ~54개 (중복 포함) | ~30개 |
| 완전 중복 (Type A) | 15개 스킬 × 2 | 0 |
| 기능 중복 (Type B) | 6그룹 ~12개 | 0 |
| Personal/Team 중복 (Type C) | 4쌍 | 0-1쌍 |
| 토큰 절약 (시스템 메시지) | — | ~40% 감소 추정 |

## 6. 리스크

- Team 스킬 제거 시 다른 프로젝트에서 해당 스킬을 사용 중일 수 있음 → Team 스킬은 건드리지 않고 Personal만 정리
- Command 제거 시 기존 워크플로우 습관이 깨질 수 있음 → alias 또는 리다이렉트 메시지로 전환 유도
- `elasticsearch-query` 이름 변경 시 기존 트리거 키워드가 동작하지 않을 수 있음 → SKILL.md description에 기존 키워드 유지
