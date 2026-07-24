---
name: run-tests
description: 프로젝트 표준 테스트 명령을 자동 인식해 실행한다. 사용자가 "/test", "테스트 돌려", "run tests", "pytest 돌려", "테스트 통과 확인" 을 말하면 트리거. .claude/project-profile.yaml 의 test_cmd 우선, 없으면 pyproject.toml/package.json/Cargo.toml 에서 추론.
---

# Run Tests

> Spec-Task-Test-Commit 워크플로우의 **Test** 단계. task-implement / pr-evaluator 후속으로 호출 권장.

## When to invoke

- 사용자가 테스트 의사: "테스트 돌려", "통과해?", "/test"
- task-implement 가 코드 작성 후 자동 호출
- PR 만들기 전 (pr-evaluator 의 카테고리 2 점검)

## 명령 결정 우선순위

1. `--cmd "..."` 인자
2. `.claude/project-profile.yaml` 의 `test_cmd` (있으면 그대로)
3. 자동 추론:
   - `pyproject.toml` 에 pytest → `uv run pytest`
   - `pyproject.toml` 에 unittest 만 → `uv run python -m unittest`
   - `package.json` 의 `scripts.test` → `npm test`
   - `Cargo.toml` → `cargo test`
   - `go.mod` → `go test ./...`
4. 모두 실패 → 사용자에게 명령 요구 (자동 추측 금지)

## 실행

```bash
~/.claude/skills/run-tests/scripts/run.sh                 # 전체
~/.claude/skills/run-tests/scripts/run.sh tests/core/     # 경로/필터 통과
~/.claude/skills/run-tests/scripts/run.sh -k test_sync    # pytest -k
~/.claude/skills/run-tests/scripts/run.sh --cmd "make test"
~/.claude/skills/run-tests/scripts/run.sh --changed       # git diff 기준 변경된 모듈만
```

## 동작

1. cwd 가 git 루트인지 확인 (아니면 git 루트로 이동)
2. 명령 결정 후 stdout/stderr 그대로 흘림 (test runner 의 진행 출력 보존)
3. exit code 그대로 반환 (Spec-Task-Test-Commit 의 "테스트 통과 후 커밋" 정책)

## --changed 모드

- `git diff --name-only $(git merge-base HEAD origin/HEAD)..HEAD` 기준
- pytest: `*_test.py` / `test_*.py` 매칭 + import path 역추적은 단순 휴리스틱
- npm: `--changed` flag 가 있는 jest 만 지원 (없으면 전체로 fallback)

## Out of scope

- 커버리지 리포트 가공 → 별도 (project 의 ci.yml 참조)
- 테스트 코드 자체 수정 → 절대 금지 (CLAUDE.md 정책)
- 통과 위해 점수/threshold 낮춤 → 절대 금지
