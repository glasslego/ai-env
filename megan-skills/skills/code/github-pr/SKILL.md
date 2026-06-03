---
name: github-pr
description: 현재 브랜치의 변경사항으로 GitHub PR 을 생성한다. 사용자가 "/pr", "PR 만들어", "pr create", "올려줘" 등을 말하면 트리거. 제목/본문은 spec/task 커밋 메시지 + git log 에서 자동 도출. pr-evaluator 가 통과한 후 호출 권장.
---

# GitHub PR

> Origin: jackie-skills 패턴 + Claude Code 기본 PR 템플릿. `gh pr create` 위 thin wrapper.

## When to invoke

- 사용자가 PR 생성 의사: "PR 만들자", "올려줘", "/pr"
- branch-guard + pr-evaluator 통과 후
- push 직후 자동 후속 (옵션)

## 동작

1. 현재 브랜치 ≠ default 인지 확인 (default 브랜치면 거부)
2. upstream 미설정이면 `git push -u origin HEAD`
3. base 브랜치 결정: `develop` → `main` → default branch
4. 제목 도출 (우선순위):
   - `--title` 인자
   - 브랜치 prefix 가 `feat/CDE-XXXX-...` 면 첫 커밋 메시지 + `[CDE-XXXX]` 자동 prefix
   - 첫 커밋 메시지 첫 줄 (70자 이내)
5. 본문 도출:
   - `--body` 인자가 있으면 그대로
   - 없으면 `git log <base>..HEAD` 기반으로 `## Summary` + `## Test plan` 자동 작성
   - Spec/Task 메타가 있으면 별도 섹션 추가
6. `gh pr create --base $BASE --title ... --body ...` 실행
7. 결과 URL stdout 으로 반환

## 실행

```bash
~/.claude/skills/github-pr/scripts/create.sh
~/.claude/skills/github-pr/scripts/create.sh --base main
~/.claude/skills/github-pr/scripts/create.sh --title "..." --body-file PR.md
~/.claude/skills/github-pr/scripts/create.sh --draft
~/.claude/skills/github-pr/scripts/create.sh --dry-run    # 본문만 보여주고 종료
```

## 본문 템플릿 (자동)

```markdown
## Summary
- {commit-1 first line}
- {commit-2 first line}
- {commit-N first line}

## Test plan
- [ ] {auto-detected: pytest / npm test / 변경 파일 기반 추론}
- [ ] manual smoke test

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

## Out of scope

- 리뷰어 자동 지정 → 필요 시 `--reviewer` 직접 전달
- PR 머지 → 별도 작업 (gh pr merge 직접)
- 브랜치 생성 → git-branch 스킬

## 의존성

- `gh` CLI 가 설치/인증되어 있어야 함
- gh 미설치 시 명확한 에러 + 설치 안내
