---
name: branch-guard
description: git push 직전 main/master/develop 직접 push, force-push, 미커밋 변경 병행 push 등 위험 동작을 차단·경고. 사용자가 "/branch-guard", "branch guard", "푸시 전 점검" 을 말하면 트리거. pre-push hook 형태로도 등록 가능.
---

# Branch Guard

> Origin: jackie-skills/branch-guard. CLI 모드 + git pre-push hook 모드 양쪽 지원.

## When to invoke

- 사용자가 git push 의도 표시: "푸시할게", "push 해줘", "force push"
- `/branch-guard` 슬래시
- pre-push hook (Phase 6.5 옵션 등록)

## 검사 항목

| Check | 차단 조건 |
|---|---|
| protected branch direct push | 현재 브랜치 ∈ {main, master, develop} **AND** push target = 동일 |
| force push to protected | `--force` / `--force-with-lease` + protected target |
| dirty tree | uncommitted 변경 있는데 push 시도 |
| empty push | 변경사항 없이 push (단순 경고) |
| stale base | upstream 보다 N커밋 이상 오래됨 (단순 경고) |

protected 목록은 `BRANCH_GUARD_PROTECTED` 환경변수로 오버라이드 가능 (콤마 구분).

## 실행

```bash
~/.claude/skills/branch-guard/scripts/guard.sh check
~/.claude/skills/branch-guard/scripts/guard.sh check --target main --force

# pre-push hook 등록 (옵션)
~/.claude/skills/branch-guard/scripts/install_hook.sh
```

## 동작

- 위험 검출 → `exit 1` (push 차단), stderr 에 사유.
- 경고 수준 (stale base 등) → `exit 0`, stderr 에 경고.
- protected 검출 시 사용자가 의도적이면 `BRANCH_GUARD_OVERRIDE=1` 환경변수로 우회.
