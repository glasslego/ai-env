---
name: project-workflow
description: |
  프로젝트 워크플로우 오케스트레이터.
  사용자가 워크플로우, workflow, 대시보드, status, 구현 시작을 요청할 때 트리거.
  "워크플로우", "workflow", "워크플로우 시작", "status", "대시보드", "프로젝트 상태" 등에 반응.
  .claude/project-profile.yaml을 자동 감지하여 프로젝트 컨텍스트를 주입하고,
  spec-manager, task-implement, code-review, research 등 Core Ops 스킬을 오케스트레이션한다.
  프로젝트의 도메인 스킬(domain_ops)도 워크플로우에 통합한다.
---

# Project Workflow Orchestrator

프로젝트의 전체 개발 워크플로우를 관리하는 오케스트레이터 스킬.
Core Ops 스킬들을 Phase 순서대로 조율하고, 프로젝트 상태를 추적한다.

## 프로젝트 컨텍스트 자동 감지

`.claude/project-profile.yaml` → `specs/` → `pyproject.toml`/`package.json` 순서로 프로젝트 감지. 모두 없으면 사용자에게 질문.

## 모드 판별

| 사용자 요청 | 모드 |
|------------|------|
| "워크플로우" / "workflow" | Overview (상태 확인 + 다음 단계 제안) |
| "워크플로우 시작" / "workflow start" | Run (Phase 0부터 순차 실행) |
| "status" / "대시보드" / "프로젝트 상태" | Dashboard (진행률 대시보드) |
| "구현 시작" / "implement" | Implement (다음 미완료 task → task-implement) |
| "리서치" | research로 위임 |
| "스펙" / "spec" | spec-manager로 위임 |
| "리뷰" / "review" | code-review로 위임 |

---

## Overview 모드

### Step 1: 프로젝트 컨텍스트 로드

`.claude/project-profile.yaml`을 Read로 읽는다.

### Step 2: 현재 상태 파악

`_project-status.yaml`이 있으면 Read. 없으면 `scripts/detect_project.py`로 초기 스캔:

```bash
python .claude/skills/project-workflow/scripts/detect_project.py
```

또는 수동으로:
- specs/ 디렉토리 파싱 (spec-manager의 Status 모드와 동일)
- 테스트 실행 상태 확인
- git 상태 확인

### Step 3: 상태 보고 + 다음 단계 제안

Project/Phase/Specs 상태 + Next 액션 제안 출력. 도메인 ops가 있으면 함께 표시.

---

## Run 모드

Phase 0부터 순차 실행한다. 각 Phase에서 Gate Check 통과 후 다음으로 진행.

### Phase 0: 초기화

1. project-profile.yaml 확인
2. specs/ 현재 상태 파악
3. _project-status.yaml 초기 생성/갱신 (`scripts/update_status.py`)

### Phase 1: 리서치 (선택)

- research 스킬의 기능을 활용
- 리서치 소스가 이미 있으면 건너뛰기 가능
- 사용자에게 "리서치가 필요한가요?" 확인

### Phase 2: 스펙 작성

- spec-manager 스킬의 Create 모드 활용
- **Gate**: SPEC 파일 존재 + 500자 이상 + 빈 플레이스홀더 없음
- Gate 실패 시 사용자에게 알리고 중단

### Phase 3: 구현

- task-implement 스킬의 Implement/Next Task 모드 활용
- Task 단위 순차 구현
- **Gate**: 전체 테스트 통과 + lint 클린
- Gate 실패 시 최대 3회 재시도, 이후 중단

### Phase 4: 리뷰

- code-review 스킬의 Spec Conformance 모드 활용
- **Gate**: Must Fix 0건
- Must Fix 있으면 수정 후 재리뷰 안내

### Phase 5: 완료 표시

- spec-manager 스킬의 Close 모드 활용
- _project-status.yaml 갱신
- plan 파일 갱신 (있는 경우)

### Phase D: 도메인 Ops (선택)

- project-profile.yaml의 `domain_ops` 섹션에 정의된 스킬 호출
- 독립적으로 언제든 실행 가능
- 실행 결과를 _project-status.yaml에 기록

---

## Dashboard 모드

spec-manager의 Status 모드 + 추가 정보를 종합하여 대시보드 표시.
Phase, Specs 진행률 테이블(ID/Title/Status/Tasks/Progress), Reviews, Domain Ops 포함.

---

## Implement 모드

task-implement의 Next Task 모드를 직접 호출하는 단축 진입점.

1. _project-status.yaml에서 현재 in_progress spec의 다음 미완료 task 탐색
2. 찾으면 해당 task의 spec 파일을 읽고 task-implement Implement 모드로 전환
3. 없으면 "모든 task가 완료되었습니다. 리뷰를 진행하시겠습니까?" 안내

---

## Gate Check 정의

| Phase | Gate 조건 | 실패 시 |
|-------|----------|---------|
| Phase 2 (Spec) | SPEC 파일 존재 + 500자 초과 + 플레이스홀더 없음 | 중단, 스펙 보완 안내 |
| Phase 3 (Code) | 전체 테스트 통과 + lint 클린 | 최대 3회 재시도 후 중단 |
| Phase 4 (Review) | Must Fix 0건 | 수정 후 재리뷰 안내 |
| Phase 5 (Close) | 모든 AC 충족 | Close 거부, 미충족 AC 표시 |

---

## 절대 금지

- Phase를 건너뛰지 마라 (리서치 Phase만 선택적 건너뛰기 가능)
- Gate Check 실패 시 강제로 다음 Phase로 넘어가지 마라
- 사용자 확인 없이 스펙을 자동 완료 처리하지 마라
