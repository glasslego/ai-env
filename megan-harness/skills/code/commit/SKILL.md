---
name: commit
description: 변경사항을 task(기능) 단위로 나눠 spec/task 컨벤션 커밋을 생성한다. diff 분석 → task 그룹핑 → 테스트 → 커밋까지, pre-commit 자동수정 재-stage 루프와 branch-guard 연계까지 처리한다. 사용자가 "/commit", "커밋해줘", "커밋 나눠서", "task 단위로 커밋", "commit" 을 말하면 트리거.
---

# Commit (spec/task 단위 커밋)

> `.claude/commands/commit.md` 를 대체·통합. diff → task 분할 → spec/task 메시지 → pre-commit 루프 → 보고.
> `<type>(spec-<id>/task-<id>): <summary>` 컨벤션(ai-env/글로벌 CLAUDE.md)을 그대로 따른다.

## When to invoke
- `/commit`, "커밋해줘", "task 단위로 나눠서 커밋", "commit"
- 여러 작업이 한 워킹트리에 섞여 있어 논리적으로 쪼개 커밋해야 할 때

## 0. 브랜치 가드 (먼저)
- `git branch --show-current` 확인. default(main/master/develop)면 커밋 전에 **새 브랜치 생성을 제안**한다
  (branch-guard / git-branch 스킬과 연계). 사용자가 main 직접 커밋을 명시하면 존중.

## 1. 변경 수집 & task 분할
- `git status --short` + `git diff`(staged+unstaged)로 전체 변경 파악.
- 변경을 **작업(기능) 단위**로 그룹핑한다:
  - 세션 시작 전부터 있던 uncommitted 작업이 섞였는지 확인 — 다른 spec 일 수 있으므로 처리 방향을 사용자에게 확인.
  - 한 파일이 여러 작업에 걸쳐 수정됐으면 hunk 분리가 필요한데, 비대화형 환경엔 `git add -p`/`-i` 가 없다.
    → 그 파일을 **주 작업(dominant) 커밋에 배정**하고, 어느 커밋에 묶였는지 보고에 명시한다.
- spec/task 식별자 확정: `specs/` 문서가 있으면 그 번호(`spec-013`), 없으면 의미 있는 라벨(`spec-narrow/task-scope`).

## 2. task별 스테이징 & 커밋 (그룹마다 반복)
1. `git add <해당 경로들>` — 삭제/이동도 경로를 add 하면 스테이징된다.
   rename 은 **old(삭제) + new(추가) 경로를 함께 add** 하면 git 이 `R`(rename)로 감지해 **history 를 보존**한다.
2. `git diff --cached --name-only` 로 staged 목록을 **검증** — 다른 작업 파일이 섞이지 않았는지 sanity 체크.
3. (권장) task 관련 테스트 실행. 실패 상태에서는 커밋하지 않는다.
4. `git commit -F -` (heredoc)로 본문 포함 커밋.

## 3. 커밋 메시지 컨벤션
- 제목: `<type>(spec-<id>/task-<id>): <summary>` — type ∈ feat/fix/refactor/docs/chore/test …
  - 예: `refactor(spec-narrow/task-scope): ai-env를 Claude/Codex 설정 동기화 전용으로 축소`
- 본문: 무엇을/왜. 공유 파일이 여러 작업에 걸쳤으면 그 사실을 본문에 한 줄 명시.
- 꼬리에 항상:
  `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`

## 4. pre-commit 자동수정 재-stage 루프
pre-commit(ruff `--fix`, ruff-format, end-of-file-fixer 등)이 파일을 고치면 커밋이 exit≠0 로 **중단**된다:
- hook 이 수정한 파일을 **다시 `git add` 후 동일 메시지로 재커밋**한다 (수정 내용이 커밋에 포함되도록).
- `gitleaks` 가 exit **-9(SIGKILL, 샌드박스 리소스)**로 죽으면 → 그냥 **재시도**. 대개 일시적.
  반복 실패 시에만 원인 확인 후, 사용자 승인 하에 `SKIP=gitleaks git commit` 고려(비권장).
- `mypy` 가 **패키지 외 코드**(예: 스킬 스크립트)에서 실패하면 스코프 문제다 —
  패키지(`src/`)가 아니면 exclude 를 조정하고, 통과를 위한 임의 완화(타입 무시 남발)는 금지.

## 5. 보고
- 각 커밋: **해시 + spec/task 식별자 + 한 줄 요약** (표 권장)
- 공유 파일이 어느 커밋에 묶였는지
- 실행한 테스트와 결과 / 남은 TODO·Assumption
- default 브랜치가 아니면 main 반영법 안내: `git checkout main && git merge --ff-only <branch>`

## 절대 금지
- 테스트 실패 상태 커밋 / 통과시키려 테스트·기준 완화
- 요청 범위 밖 변경을 커밋에 끼워넣기
- 사용자 승인 없이 push (push 는 별도 명시 요청 시에만)
