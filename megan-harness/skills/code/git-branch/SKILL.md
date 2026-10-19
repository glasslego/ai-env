---
name: git-branch
description: CDETEAM-XXXX Jira 키 그대로(없으면 CDETEAM-NOJIRA-YYYYMMDDHH) git 브랜치를 생성한다. codex/claude 등 에이전트 이름은 브랜치명에 절대 넣지 않는다. 사용자가 "/branch", "브랜치 만들어", "CDETEAM-1234 브랜치" 등을 말하면 트리거. 기본 base 는 `develop` 또는 default branch. branch-guard 와 짝.
---

# Git Branch

> 신규 브랜치를 표준 네이밍으로 생성. branch-guard 가 보호 규칙을 강제하므로 본 스킬은 **생성/네이밍**만 담당.

## When to invoke

- 사용자가 새 작업 시작 표시: "이 티켓 시작할게", "브랜치 따자"
- `/branch CDETEAM-1234` 또는 Jira 없이 `/branch`
- branch-guard 가 차단했을 때 새 브랜치를 만들어야 하는 경우

## 네이밍 규칙

| 입력 | 결과 브랜치 |
|---|---|
| `CDETEAM-1234` | `CDETEAM-1234` |
| `CDETEAM-1234 add backfill` | `CDETEAM-1234` (요약은 버림) |
| Jira 키 없음 | `CDETEAM-NOJIRA-YYYYMMDDHH` (예: `CDETEAM-NOJIRA-2026101914`) |

- 브랜치명에 `codex`, `claude` 등 에이전트·도구 이름을 절대 넣지 않는다 (`codex/...`, `claude/...` 금지).
- `feat/`·`fix/` prefix, 요약 slug 를 붙이지 않는다.
- worktree 디렉터리명도 같은 브랜치명을 쓴다.
- ai-env 저장소는 main 단일 브랜치 정책이 우선이므로 브랜치를 만들지 않는다.

## 실행

```bash
~/.claude/skills/git-branch/scripts/create.sh CDETEAM-1234
~/.claude/skills/git-branch/scripts/create.sh --base main CDETEAM-1234
~/.claude/skills/git-branch/scripts/create.sh --dry-run          # NOJIRA
```

## 동작

1. dirty tree 면 stash 권유 (자동 stash 안 함)
2. base 브랜치(`develop` → `main` → 현재 default branch fallback) 로 fetch + checkout
3. 새 브랜치 생성 (`git checkout -b`)
4. (옵션) `BRANCH_TRACK_ORIGIN=1` 이면 push -u origin

## Out of scope

- protected 브랜치 push 차단 → branch-guard
- PR 생성 → github-pr
- CDETEAM 외 다른 ticket prefix 인식 → 필요 시 `BRANCH_TICKET_PATTERN` 환경변수
