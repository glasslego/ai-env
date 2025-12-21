---
name: task-implement
description: |
  Spec/Task 기반 TDD 코드 구현 스킬.
  사용자가 task 구현, 다음 task, implement, 코드 생성을 요청할 때 트리거.
  "task 구현", "implement task", "다음 task", "next task", "구현 시작" 등의 키워드에 반응.
  반드시 spec/task를 입력으로 받아 구현하며, task 범위 밖 수정은 금지.
  프로젝트의 .claude/project-profile.yaml이 있으면 테스트/린트 명령, 아키텍처 패턴을 자동 로드한다.
---

# Task Implement

Spec의 Task 단위로 TDD 방식 코드 구현을 수행하는 스킬.

## 프로젝트 컨텍스트 로드

`.claude/project-profile.yaml`이 있으면 `tests.command`, `tests.lint_command`, `architecture.pattern`, `specs.directory`를 로드. 없으면 기본값 사용.

## 모드 판별

- **"task 구현" / "implement task NNN-N"** → Implement 모드 (지정된 task)
- **"다음 task" / "next task"** → Next Task 모드 (자동 선택)
- **"체크포인트 확인"** → Checkpoint 모드

---

## Implement 모드

### Step 1: Task 확인

- 지정된 SPEC 파일을 Read
- 해당 Task의 AC, Test 전략, 예상 변경 파일 확인
- Task 상태가 `done`이면 "이미 완료된 task입니다" 안내

### Step 2: TDD — Red (테스트 먼저)

- Task의 AC를 기반으로 테스트 코드 작성
- 핵심 유스케이스 + 경계 조건 + 에러 케이스
- 외부 API/DB는 mock 처리
- 테스트 파일명: `test_{feature}_{context}.py`

### Step 3: TDD — Green (최소 구현)

- 테스트를 통과하는 **최소한의 구현**
- type hints 필수
- 기존 모듈의 함수를 재활용 (중복 금지)
- 아키텍처 패턴이 지정되어 있으면 해당 레이어 구조 준수

### Step 4: TDD — Test 실행

```bash
# project-profile.yaml의 tests.command 사용 (없으면 기본값)
{tests.command}
```

- **성공**: Step 5로 진행
- **실패**: 구현 코드만 수정 (테스트 코드 수정 금지!)
- 최대 3회 반복. 3회 후에도 실패하면 사용자에게 보고

### Step 5: TDD — Refactor

- 테스트 통과 확인 후 코드 정리
- 중복 제거, 네이밍 개선
- 리팩토링 후 테스트 재실행으로 기능 보존 확인

### Step 6: Lint

```bash
{tests.lint_command}
```

### Step 7: 체크포인트 저장

`_code-status.yaml`에 task 상태 기록 (`status: done | failed | pending`, `tests_passed`, `tests_failed`).

### Step 8: Spec 상태 갱신

- SPEC 파일에서 해당 task 체크박스를 `[x]`로 변경
- _project-status.yaml의 `tasks_done` 증가
- 모든 task 완료 시 spec status를 `review_required`로 변경

### Step 9: 보고

테스트 결과, 변경 파일, 다음 단계를 간결하게 보고.

---

## Next Task 모드

1. `_project-status.yaml`에서 `in_progress` spec의 첫 미완료 task 선택
2. 없으면 `planned` spec의 첫 task 선택
3. task-implement Implement 모드로 전환

---

## Checkpoint 모드

`_code-status.yaml` 읽고 task별 상태(done/failed/pending) + 테스트 결과 테이블 출력.

---

## 절대 금지

- Task 범위를 넘는 구조 변경/리팩토링 금지
- spec/task 없이 구현 금지
- 글로벌 CLAUDE.md "절대 금지 사항 > 테스트 코드 관련" 항목도 적용
