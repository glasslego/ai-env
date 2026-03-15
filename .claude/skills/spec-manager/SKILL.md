---
name: spec-manager
description: |
  Spec 문서 생성/관리/상태 추적 스킬.
  사용자가 스펙 작성, 스펙 상태 확인, 스펙 완료 표시, task 분해를 요청할 때 트리거.
  "스펙 만들어", "spec status", "spec 완료", "task 분해", "close spec" 등의 키워드에 반응.
  프로젝트의 .claude/project-profile.yaml이 있으면 프로젝트 컨텍스트를 자동 로드한다.
---

# Spec Manager

프로젝트의 스펙 문서를 생성·관리·추적하는 통합 스킬.

## 프로젝트 컨텍스트 로드

`.claude/project-profile.yaml`이 있으면 `specs.directory`, `specs.format`, `specs.template`, `specs.plan_file`을 로드. 없으면 `specs/` 자동 탐색.

## 모드 판별

사용자 요청에 따라 아래 모드 중 하나를 실행한다:

- **"스펙 작성" / "spec create"** → Create 모드
- **"스펙 상태" / "spec status"** → Status 모드
- **"스펙 완료" / "close spec"** → Close 모드
- **"task 분해" / "break down tasks"** → Task Decompose 모드

---

## Create 모드

### Step 1: 입력 수집

- 사용자가 제공한 요구사항/리서치/컨텍스트를 파악
- 기존 SPEC 파일 번호를 Glob으로 확인하여 다음 번호 결정
  - `specs/SPEC-*.md` 패턴으로 검색
  - 가장 높은 번호 + 1

### Step 2: Spec 문서 생성

`references/spec-template.md` 템플릿을 참조하여 스펙 작성.
프로젝트 profile에 `specs.template`이 지정되어 있으면 해당 템플릿 우선 사용.

필수 frontmatter 필드:
```yaml
---
spec_id: SPEC-NNN
title: "<제목>"
status: planned
created: <오늘 날짜>
updated: <오늘 날짜>
source_evidence: []
---
```

### Step 3: _project-status.yaml 갱신

`scripts/parse_spec_status.py`를 실행하여 상태 파일을 갱신한다.
```bash
python ~/.claude/skills/spec-manager/scripts/parse_spec_status.py <specs_dir> <status_file>
```

스크립트가 없는 환경에서는 수동으로 _project-status.yaml에 새 스펙 엔트리를 추가:
```yaml
specs:
  SPEC-NNN:
    title: "<제목>"
    status: planned
    tasks_total: 0
    tasks_done: 0
```

### Step 4: 보고

- 생성된 스펙 파일 경로
- frontmatter 요약
- 다음 단계 안내: "task 분해를 원하시면 'task 분해 SPEC-NNN'을 요청하세요"

---

## Status 모드

### Step 1: 스펙 디렉토리 스캔

- `specs/SPEC-*.md` 파일들을 Glob으로 수집
- 각 파일의 frontmatter에서 `spec_id`, `title`, `status` 추출
- 체크박스 (`- [x]`, `- [ ]`) 카운트로 task 진행률 계산

### Step 2: 대시보드 출력

Spec ID / Title / Status / Tasks (done/total) / Progress bar 테이블 출력.

### Step 3: _project-status.yaml 동기화

현재 스캔 결과로 _project-status.yaml을 갱신한다.

---

## Close 모드

### Step 1: 대상 스펙 확인

- 사용자가 지정한 SPEC-ID의 파일을 Read
- 모든 task가 완료(`- [x]`) 상태인지 확인
- 미완료 task가 있으면 경고 후 사용자 확인

### Step 2: 상태 갱신

1. 스펙 파일의 frontmatter `status`를 `done`으로 변경
2. `updated` 날짜를 오늘로 갱신
3. _project-status.yaml의 해당 스펙 상태를 `done`으로 갱신

### Step 3: plan 파일 갱신 (있는 경우)

profile의 `specs.plan_file`이 지정되어 있으면:
- plan-spec.md에서 해당 스펙 항목을 찾아 완료 표시

---

## Task Decompose 모드

### Step 1: 스펙 파일 읽기

- 지정된 SPEC 파일을 Read
- Goal, Scope, Non-Goals, Data Model, API 섹션 분석

### Step 2: Task 분해

각 task에 다음을 포함:
```markdown
## Tasks

- [ ] Task NNN-1: <제목>
  - **AC**: <acceptance criteria>
  - **Test**: <테스트 전략>
  - **Files**: <예상 변경 파일>

- [ ] Task NNN-2: <제목>
  ...
```

### Step 3: 스펙 파일 업데이트

- Tasks 섹션을 스펙 파일에 추가/갱신 (Edit)
- frontmatter `status`가 `planned`면 `in_progress`로 변경
- _project-status.yaml의 `tasks_total` 갱신

---

## Task 상태 전환 규칙

```
planned → in_progress → review_required → done
                ↑               |
                └── blocked ←───┘
```

- `planned`: 아직 시작 안 함
- `in_progress`: 구현 중
- `review_required`: 구현 완료, 리뷰 필요 (code-review에서 설정)
- `done`: 리뷰 통과, 완료
- `blocked`: 외부 의존성/이슈로 중단
