---
name: git-branch
description: CDE-XXXX 또는 spec/task 컨벤션으로 git 브랜치를 생성한다. 사용자가 "/branch", "브랜치 만들어", "feature 브랜치", "spec 브랜치 따자", "CDE-1234 브랜치" 등을 말하면 트리거. 기본 base 는 `develop` 또는 default branch. branch-guard 와 짝.
---

# Git Branch

> 신규 브랜치를 표준 네이밍으로 생성. branch-guard 가 보호 규칙을 강제하므로 본 스킬은 **생성/네이밍**만 담당.

## When to invoke

- 사용자가 새 작업 시작 표시: "이 티켓 시작할게", "feature 브랜치 따자"
- `/branch CDE-1234` 또는 `/branch spec-015/task-02 짧은요약`
- branch-guard 가 차단했을 때 새 브랜치를 만들어야 하는 경우

## 네이밍 컨벤션

| 입력 | 결과 브랜치 |
|---|---|
| `CDE-1234` (Jira 키만) | `feat/CDE-1234` |
| `CDE-1234 add backfill` | `feat/CDE-1234-add-backfill` |
| `spec-015/task-02 sync rework` | `feat/spec-015-task-02-sync-rework` |
| `fix CDE-999 oom` | `fix/CDE-999-oom` |
| `chore docs` | `chore/docs` |

prefix 자동 추론:
- `fix`, `bug`, `oom`, `crash` → `fix/`
- `chore`, `docs`, `refactor`, `test` → 해당 prefix
- 그 외 → `feat/`

소문자, 공백→`-`, 특수문자 제거. CDE 키는 대문자 유지.

## 실행

```bash
~/.claude/skills/git-branch/scripts/create.sh "CDE-1234 add backfill"
~/.claude/skills/git-branch/scripts/create.sh --base main "fix CDE-999 oom"
~/.claude/skills/git-branch/scripts/create.sh --dry-run "chore docs"
```

## 동작

1. dirty tree 면 stash 권유 (자동 stash 안 함)
2. base 브랜치(`develop` → `main` → 현재 default branch fallback) 로 fetch + checkout
3. 새 브랜치 생성 (`git checkout -b`)
4. (옵션) `BRANCH_TRACK_ORIGIN=1` 이면 push -u origin

## Out of scope

- protected 브랜치 push 차단 → branch-guard
- PR 생성 → github-pr
- CDE 외 다른 ticket prefix 인식 → 필요 시 `BRANCH_TICKET_PATTERN` 환경변수
