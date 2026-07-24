---
name: pr-evaluator
description: PR 만들기 직전 또는 만든 직후 변경사항을 7개 카테고리 체크리스트로 자체 평가. 사용자가 "/pr-eval", "PR 평가", "pr 점검", "pr 만들기 전 체크" 를 말하면 트리거.
---

# PR Evaluator

> Origin: jackie-skills/pr-evaluator. 단순 체크리스트 + git diff 분석.

## When to invoke

- 사용자가 PR 생성 의사 표시 ("PR 만들자", "PR 올리려고")
- `/pr-eval`
- `branch-guard` 가 통과하면 push, push 후 `pr-eval` 호출 권장

## 7개 평가 카테고리 (체크리스트)

| # | 카테고리 | 체크 |
|---|---|---|
| 1 | Spec 정합성 | 커밋 메시지에 spec/task ID, 변경이 spec 범위 내 |
| 2 | 테스트 | 새/수정 코드에 대한 테스트 존재, 모두 통과 |
| 3 | 보안 | secret 하드코딩, 입력 검증, 권한 체크 |
| 4 | 성능 | N+1 쿼리, 큰 루프, 메모리 누수 단서 |
| 5 | 의존성 | 새 라이브러리 추가/버전 변경, license 호환 |
| 6 | 문서 | README/CLAUDE.md/주석 갱신 필요 여부 |
| 7 | rollback 안전성 | DB 마이그레이션 reversible, feature flag, deploy 영향 |

## 실행

```bash
~/.claude/skills/pr-evaluator/scripts/eval.sh
# 옵션
--base BRANCH        # 기본 main
--with-second        # second-opinion 까지 함께 호출 (chained)
--save               # 결과를 vault session 노트로 저장
```

## 동작

1. `git diff <base>..HEAD --stat` 로 변경 규모/파일 분포 출력
2. 7개 카테고리 each:
   - 결정적 sniff (예: secret 패턴 grep, 새 dependency 검출)
   - in-conversation 으로 Claude 가 항목별 평가 (이 SKILL 본문이 가이드)
3. (옵션) `--with-second` → second-opinion 결과 통합
4. (옵션) `--save` → vault session 노트로 저장

## 결정적 sniff 항목

- secret 패턴: `grep -E "(password|token|secret|api_key)\s*=\s*['\"]"`
- TODO/FIXME 추가: `git diff` 에서 `+ *(TODO|FIXME|XXX)`
- 새 dependency: `pyproject.toml`, `package.json`, `requirements*.txt` 변경
- 마이그레이션: `migrations/`, `alembic/`, `*.sql` 추가
