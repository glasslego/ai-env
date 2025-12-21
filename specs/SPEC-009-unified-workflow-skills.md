---
id: SPEC-009
title: Unified Workflow Skills — Commands → Skills 통합 및 프로젝트 오케스트레이터
status: draft
created: 2026-03-08
updated: 2026-03-08
origin: drama-fashion/handoff-2026-03-08-custom-agent-plan.md
---

# SPEC-009: Unified Workflow Skills

## 1. 배경 및 문제

### 1.1 현재 구조의 문제점

현재 워크플로우 시스템은 **commands**(wf-*.md)와 **skills**(SKILL.md)가 혼재되어 있고,
ai-env의 topics YAML + Obsidian vault에 강결합되어 있다.

```
현재 구조:
  .claude/commands/wf-*.md  ← 프롬프트 템플릿 (topics YAML 의존)
  ~/.claude/skills/         ← 도메인 스킬 (독립적)
  프로젝트/.claude/skills/  ← 프로젝트 스킬 (고립)
```

| 문제 | 영향 |
|------|------|
| wf-* commands가 topics YAML + Obsidian vault에 강결합 | drama-fashion 같은 자체 specs/ 체계를 가진 프로젝트에서 사용 불가 |
| commands는 scripts/references 번들링 불가 | 복잡한 로직을 프롬프트 텍스트에만 의존 |
| 기능 중복: review + simplify + wf-review | 어떤 것을 써야 할지 혼란 |
| 프로젝트 스킬과 글로벌 스킬 간 연결 없음 | 오케스트레이션 수동 |
| spec-generator와 wf-spec 역할 중복 | 프로젝트별 spec 포맷 미지원 |

### 1.2 drama-fashion 핸드오프의 핵심 요구

drama-fashion 프로젝트에서 도출된 요구사항:

1. **프로젝트 컨텍스트 자동 감지** — 프로젝트마다 다른 spec 구조/아키텍처/테스트 방식 인식
2. **오케스트레이터** — 리서치 → 스펙 → 구현 → 리뷰 → 완료 표시를 하나의 진입점으로
3. **상태 추적** — 어디까지 진행했는지 파악 가능
4. **데이터 운영 통합** — 수집/파이프라인 등 프로젝트 고유 작업도 워크플로우에 편입
5. **SpecOps** — spec 완료 표시, plan-spec 동기화, task 상태 관리

### 1.3 설계 원칙 (Codex 제안에서 채택한 것)

- "코드 생성기"가 아니라 **"작업 운영 시스템"** 관점
- spec/task 없이 구현 금지
- 리뷰 결과를 spec/task에 환류
- 수집/파이프라인 결과를 구조적으로 기록

### 1.4 설계 원칙 (채택하지 않은 것)

| Codex 제안 | 불채택 사유 |
|-----------|------------|
| SQLite agent_state.db | 과도한 복잡도. YAML/frontmatter로 충분 |
| 별도 CLI agent (bin/drama-fashion-agent) | Claude Code 자체가 agent. Skills로 충분 |
| 5개 독립 서브에이전트 프로세스 | Skills = 프롬프트 수준 역할 분리로 동일 효과 |
| repo-local launcher | `.claude/project-profile.yaml`로 대체 |

## 2. 목표 아키텍처

### 2.1 3-Layer Skills Architecture

```
Layer 1: Core Ops Skills (글로벌, 프로젝트 무관)
  ├── spec-manager      — 스펙 생성/관리/상태 추적
  ├── task-implement      — TDD 구현 (스펙 기반)
  ├── code-review    — 코드 리뷰 + 스펙 정합성 검증
  └── research  — 멀티소스 리서치 통합

Layer 2: Project Orchestrator (글로벌 스킬, 프로젝트 컨텍스트 주입)
  └── project-workflow — project-profile.yaml 읽고 Layer 1 스킬 오케스트레이션

Layer 3: Domain Skills (프로젝트 로컬)
  └── collect-fashion, process-pipeline 등 (프로젝트별 .claude/skills/)
```

### 2.2 프로젝트 프로파일 (컨텍스트 주입)

각 프로젝트 루트에 `.claude/project-profile.yaml`을 두어
글로벌 스킬이 프로젝트 컨텍스트를 자동 감지한다.

```yaml
# .claude/project-profile.yaml
project:
  name: drama-fashion
  type: api-server            # api-server | library | data-pipeline | cli-tool
  description: "드라마 셀럽 착장 룩북 API"

architecture:
  pattern: 3-layer             # 3-layer | hexagonal | monolith | microservice
  layers:
    api: app/api/v1/endpoints/
    service: app/services/
    repository: app/repositories/

specs:
  directory: specs/
  format: SPEC-NNN             # SPEC-NNN | free-form
  template: null               # 커스텀 템플릿 경로 (없으면 기본 템플릿)
  plan_file: plan-spec.md      # 전체 plan 추적 파일

tests:
  framework: pytest
  command: "pytest tests/ -x -q"
  lint_command: "ruff check app/ && mypy app/"

status:
  file: _project-status.yaml   # 워크플로우 상태 파일

# 프로젝트 고유 ops (선택)
domain_ops:
  - skill: collect-fashion
    phase: data-collection
    description: "착장 데이터 수집"
  - skill: process-pipeline
    phase: data-processing
    description: "이미지 처리 파이프라인"

# 리서치 소스 (선택, research에서 사용)
research:
  obsidian_base: "51_자동화시스템/03_드라마패션룩북"
  sources_dir: null            # 프로젝트 내 리서치 디렉토리
```

### 2.3 프로젝트 상태 파일

`_project-status.yaml` — SQLite 대신 git-trackable YAML로 상태 관리.

```yaml
# _project-status.yaml (자동 생성/갱신)
last_updated: "2026-03-08"
current_phase: implementing    # intake | research | spec | implementing | review | done

specs:
  SPEC-007:
    title: "Data Collection Pipeline"
    status: done
    tasks_total: 5
    tasks_done: 5
  SPEC-009:
    title: "Data Modeling"
    status: in_progress
    tasks_total: 8
    tasks_done: 3
    current_task: "task-09-4"
  SPEC-010A:
    title: "Editorial"
    status: planned
    tasks_total: 0
    tasks_done: 0

reviews:
  SPEC-007:
    date: "2026-02-20"
    must_fix: 0
    nice_to_have: 2
    resolved: true
```

## 3. Layer 1: Core Ops Skills 상세

### 3.1 spec-manager

**통합 대상**: wf-spec (command) + spec-generator (skill)

```
.claude/skills/spec-manager/
├── SKILL.md
├── scripts/
│   └── parse_spec_status.py    # specs/ 디렉토리 파싱 → 진행률 계산
└── references/
    ├── spec-template.md        # 범용 SPEC 템플릿
    └── frontmatter-schema.md   # YAML frontmatter 필수 필드 정의
```

**SKILL.md 핵심 기능:**

| 트리거 | 동작 |
|--------|------|
| "스펙 작성해줘" / "spec 만들어" | 리서치/요구사항 → SPEC-NNN 문서 생성 |
| "스펙 상태" / "spec status" | specs/ 전체 진행률 대시보드 |
| "스펙 완료 표시" / "close spec" | frontmatter status 갱신 + _project-status.yaml 동기화 |
| "task 분해" | SPEC 내 Tasks 섹션 자동 생성 (acceptance criteria 포함) |

**프로젝트 컨텍스트 활용:**
- `project-profile.yaml`의 `specs.directory`, `specs.format`, `specs.template` 참조
- 프로파일 없으면 현재 디렉토리에서 `specs/` 자동 탐색

**spec frontmatter 표준:**

```yaml
---
spec_id: SPEC-009
title: Data Modeling
status: in_progress          # planned | in_progress | review_required | done | blocked
created: 2026-03-01
updated: 2026-03-08
source_evidence: []          # 리서치 근거 파일 목록 (선택)
owners: []                   # 담당자 (선택)
---
```

**Task 상태 5단계**: `planned → in_progress → review_required → done → blocked`
- spec 문서 내 체크박스(`- [x]`)와 _project-status.yaml를 **동시 갱신**

### 3.2 task-implement

**통합 대상**: wf-code (command) + coding-standards (skill)

```
.claude/skills/task-implement/
├── SKILL.md
└── references/
    └── tdd-workflow.md        # TDD 절차 상세 (Red → Green → Refactor)
```

**SKILL.md 핵심 기능:**

| 트리거 | 동작 |
|--------|------|
| "task 구현" / "implement task" | spec에서 task 하나 → TDD 구현 |
| "다음 task" / "next task" | _project-status에서 다음 pending task 찾아 구현 |
| "체크포인트 확인" | _code-status.yaml 읽고 재개 지점 표시 |

**프로젝트 컨텍스트 활용:**
- `tests.command`, `tests.lint_command` → 프로젝트별 테스트 실행 방식
- `architecture.pattern` → 코드 생성 시 레이어 구조 강제

**기존 wf-code와의 차이:**
- topics YAML 의존 제거
- spec 경로를 project-profile 또는 직접 인자로 받음
- 체크포인트 파일 경로도 프로젝트 루트 기준으로 변경

### 3.3 code-review

**통합 대상**: wf-review (command) + review (command) + simplify (skill)

```
.claude/skills/code-review/
├── SKILL.md
└── references/
    └── review-checklist.md    # 리뷰 체크리스트 (AC 매핑, 운영 관점)
```

**SKILL.md 핵심 기능:**

| 트리거 | 동작 |
|--------|------|
| "리뷰" / "review" | 스펙 정합성 + 코드 품질 리뷰 |
| "simplify" / "개선" | 코드 리뷰 → 리팩토링 제안 → 적용 |
| "spec review" | AC별 충족 여부 매트릭스 생성 |

**3가지 리뷰 모드:**

1. **Quick Review**: `git diff` 기반 변경사항만 리뷰 (기존 `review` command)
2. **Spec Conformance Review**: SPEC 파일 AC ↔ 코드 매핑 검증 (기존 `wf-review`)
3. **Simplify**: 코드 개선 + 리팩토링 (기존 `simplify`)

**리뷰 결과 환류:**
- Must Fix 발견 시 → spec의 해당 task를 `review_required`로 변경
- _project-status.yaml에 리뷰 결과 기록

### 3.4 research

**통합 대상**: wf-research (command)

```
.claude/skills/research/
├── SKILL.md
└── references/
    └── cross-analysis.md      # 4-Way 교차 분석 가이드
```

**SKILL.md 핵심 기능:**

| 트리거 | 동작 |
|--------|------|
| "리서치" / "research" | 멀티소스 리서치 수행 (수동 파일 + API) |
| "brief 생성" | 리서치 결과 30% 이하 압축 |
| "교차 분석" | Consensus/Divergence/Unique/Confidence 분석 |

**프로젝트 컨텍스트 활용:**
- `research.obsidian_base` → Obsidian vault 연결 (있는 경우)
- `research.sources_dir` → 프로젝트 내 리서치 파일 (없으면 Obsidian fallback)
- 어느 쪽도 없으면 사용자에게 리서치 소스 경로 질문

**기존 wf-research와의 차이:**
- Obsidian vault 경로가 선택 사항으로 변경 (필수 → 선택)
- ai-env pipeline dispatch 통합은 유지 (Gemini/GPT API 호출)
- topics YAML의 research 섹션 대신 project-profile.yaml 사용

## 4. Layer 2: Project Orchestrator

### 4.1 project-workflow 스킬

```
.claude/skills/project-workflow/
├── SKILL.md
├── scripts/
│   ├── detect_project.py       # project-profile.yaml 탐지 + 파싱
│   └── update_status.py        # _project-status.yaml 갱신
└── references/
    └── phase-map.md            # Phase → 스킬 매핑 + Gate Check 정의
```

**SKILL.md 핵심 기능:**

| 트리거 | 동작 |
|--------|------|
| "워크플로우" / "workflow" | 현재 상태 확인 + 다음 단계 제안 |
| "워크플로우 시작" / "workflow start" | Phase 0부터 순차 실행 |
| "status" / "대시보드" | 전체 스펙/task 진행률 대시보드 |
| "implement" / "구현 시작" | 다음 미완료 task 자동 선택 → task-implement 호출 |

### 4.2 Phase 매핑

```
Phase 0: 초기화
  → project-profile.yaml 확인
  → specs/ 현재 상태 파악 (scripts/detect_project.py)
  → _project-status.yaml 초기 생성

Phase 1: 리서치 (선택)
  → research 스킬 호출
  → 리서치 소스 유무에 따라 건너뛰기 가능

Phase 2: 스펙 작성
  → spec-manager 스킬 호출
  → Gate: SPEC 파일 존재 + 500자 이상 + 빈 플레이스홀더 없음

Phase 3: 구현
  → task-implement 스킬 호출 (task 단위 순차)
  → Gate: 전체 테스트 통과 + lint 클린

Phase 4: 리뷰
  → code-review 스킬 호출 (Spec Conformance 모드)
  → Gate: Must Fix 0건

Phase 5: 완료 표시
  → spec-manager "close spec" 호출
  → _project-status.yaml 갱신
  → plan-spec.md 갱신 (있는 경우)

Phase D: 도메인 Ops (프로젝트 profile의 domain_ops)
  → 해당 프로젝트 로컬 스킬 호출
  → 독립적으로 언제든 실행 가능
```

### 4.3 자동 컨텍스트 감지

project-workflow는 시작 시 다음 순서로 프로젝트 컨텍스트를 감지한다:

```
1. .claude/project-profile.yaml 존재? → 프로파일 로드
2. specs/ 디렉토리 존재? → spec 기반 프로젝트로 추정
3. pyproject.toml / package.json 존재? → 프로젝트 타입 추론
4. 위 모두 없음? → 사용자에게 프로젝트 정보 질문
```

프로파일 없이도 동작 가능하되, 프로파일이 있으면 더 정확한 컨텍스트 제공.

## 5. 마이그레이션 계획

### 5.1 Phase 1: Core Ops Skills 생성 (이 SPEC의 범위)

| Task | 내용 | 우선순위 |
|------|------|----------|
| task-09-1 | spec-manager 스킬 생성 (SKILL.md + parse_spec_status.py) | P0 |
| task-09-2 | task-implement 스킬 생성 (SKILL.md + tdd-workflow.md) | P0 |
| task-09-3 | code-review 스킬 생성 (SKILL.md + review-checklist.md) | P0 |
| task-09-4 | research 스킬 생성 (SKILL.md + cross-analysis.md) | P1 |
| task-09-5 | project-workflow 스킬 생성 (SKILL.md + detect_project.py + update_status.py) | P0 |
| task-09-6 | project-profile.yaml 스키마 정의 + drama-fashion용 프로파일 생성 | P0 |
| task-09-7 | _project-status.yaml 파서/업데이터 구현 | P1 |

### 5.2 Phase 2: 기존 wf-* commands와의 공존

- 기존 wf-* commands는 **삭제하지 않는다** (ai-env topics 워크플로우에서 계속 사용)
- 새 스킬은 wf-* commands와 독립적으로 동작
- 점진적으로 wf-* commands가 Core Ops Skills의 thin wrapper가 되도록 리팩토링 (Phase 3)

### 5.3 Phase 3: (향후) wf-* commands를 스킬 래퍼로 전환

```
Phase 3 (이 SPEC 범위 밖):
  wf-spec.md → "spec-manager 스킬을 topics YAML 컨텍스트로 호출"하는 2줄 래퍼
  wf-code.md → "task-implement 스킬을 topics YAML 컨텍스트로 호출"하는 2줄 래퍼
  wf-review.md → "code-review 스킬을 호출"하는 2줄 래퍼
```

## 6. 통합 전후 비교

### 6.1 Before (현재)

```
글로벌:
  commands/  wf-init.md, wf-research.md, wf-spec.md, wf-code.md,
             wf-review.md, wf-run.md, commit.md, review.md
  skills/    spec-generator, coding-standards, skill-creator + 도메인 스킬들

프로젝트:
  skills/    collect-fashion, process-pipeline (고립)

사용법:
  /wf-run bitcoin-automation    ← topics YAML 필수
  /review                       ← 단순 코드 리뷰
  (drama-fashion에서는 wf-* 사용 불가)
```

### 6.2 After (목표)

```
글로벌:
  commands/  commit.md (유지), wf-*.md (레거시 유지, 향후 래퍼화)
  skills/    spec-manager, task-implement, code-review, research,     ← Layer 1
             project-workflow,                                  ← Layer 2
             skill-creator + 도메인 스킬들                      ← 기존 유지

프로젝트:
  .claude/project-profile.yaml  ← 프로젝트 컨텍스트 정의
  .claude/skills/               ← 도메인 스킬 (project-workflow와 연결)
  _project-status.yaml          ← 상태 추적 (자동 생성)

사용법:
  "워크플로우 시작"              ← project-profile 자동 감지, 아무 프로젝트에서나
  "다음 task 구현"              ← _project-status에서 자동 선택
  "스펙 상태"                   ← specs/ 파싱 → 진행률 대시보드
  /wf-run bitcoin-automation    ← 기존 topics 워크플로우도 계속 동작
```

### 6.3 스킬 수 변화

| 구분 | Before | After | 비고 |
|------|--------|-------|------|
| 워크플로우 commands | 6개 | 6개 (유지) | 향후 래퍼화 |
| 기능 중복 skills | spec-generator, coding-standards, review | 0개 | Core Ops로 통합 |
| Core Ops skills | 0개 | 4개 | spec/code/review/research |
| Orchestrator skills | 0개 | 1개 | project-workflow |
| 도메인 스킬 | 9개 | 9개 (유지) | 변경 없음 |

## 7. drama-fashion 적용 예시

### 7.1 project-profile.yaml

```yaml
# drama-fashion/.claude/project-profile.yaml
project:
  name: drama-fashion
  type: api-server
  description: "드라마/공항/화보/SNS 셀럽 착장 룩북 API"

architecture:
  pattern: 3-layer
  layers:
    api: app/api/v1/endpoints/
    service: app/services/
    repository: app/repositories/

specs:
  directory: specs/
  format: SPEC-NNN
  plan_file: plan-spec.md

tests:
  framework: pytest
  command: "pytest tests/ -x -q"
  lint_command: "ruff check app/ && mypy app/"

status:
  file: _project-status.yaml

domain_ops:
  - skill: collect-fashion
    phase: data-collection
    description: "드라마/연예인/스타일/아이템 착장 데이터 수집"
  - skill: process-pipeline
    phase: data-processing
    description: "이미지 품질 필터링, 중복 제거, AI 태깅, 임베딩"

research:
  obsidian_base: "51_자동화시스템/03_드라마패션룩북"
```

### 7.2 실행 시나리오

```bash
# drama-fashion 프로젝트에서:
cd ~/work/glasslego/drama-fashion

# 1. 전체 상태 확인
claude "워크플로우 상태"
# → project-profile.yaml 감지
# → specs/ 파싱 → SPEC-007~010 진행률 표시
# → _project-status.yaml 자동 생성

# 2. 새 스펙 작성
claude "SPEC-011 작성 — SNS look ingestion"
# → spec-manager 트리거
# → specs/SPEC-011-sns-look-ingestion.md 생성
# → _project-status.yaml 갱신

# 3. 구현
claude "SPEC-011 구현 시작"
# → task-implement 트리거
# → 3-layer 아키텍처 강제 (profile에서 감지)
# → task 단위 TDD → pytest tests/ -x -q

# 4. 리뷰
claude "SPEC-011 리뷰"
# → code-review (Spec Conformance 모드)
# → AC 매핑 검증 → Must Fix / Nice to Have

# 5. 데이터 수집
claude "인스타그램 착장 수집"
# → collect-fashion (프로젝트 로컬 스킬) 트리거
# → project-workflow가 domain_ops에서 매핑
```

## 8. Acceptance Criteria

- [ ] AC-1: spec-manager 스킬이 `specs/` 디렉토리를 파싱하여 진행률을 표시할 수 있다
- [ ] AC-2: task-implement 스킬이 project-profile.yaml의 test/lint 커맨드를 사용하여 TDD를 수행한다
- [ ] AC-3: code-review 스킬이 SPEC AC ↔ 코드 매핑을 검증하고 리뷰 결과를 _project-status.yaml에 기록한다
- [ ] AC-4: project-workflow 스킬이 `.claude/project-profile.yaml`을 자동 감지하고 컨텍스트를 주입한다
- [ ] AC-5: project-workflow가 Phase 간 Gate Check를 수행하고 상태를 _project-status.yaml에 기록한다
- [ ] AC-6: 기존 wf-* commands가 영향 없이 계속 동작한다 (하위 호환)
- [ ] AC-7: drama-fashion 프로젝트에서 project-profile.yaml + project-workflow로 end-to-end 워크플로우가 동작한다

## 9. 제약 사항

1. **Skills는 프롬프트 수준 가이드**: 실제 "서브에이전트 프로세스"가 아닌, Claude에게 역할/절차를 지시하는 프롬프트 패키지
2. **상태 파일은 YAML**: SQLite 대비 쿼리 능력은 부족하나, git 추적/사람 가독성/단순성이 우선
3. **프로젝트 프로파일은 선택**: 없어도 기본 동작 가능. 있으면 더 정확한 컨텍스트 제공
4. **Phase 3 (wf-* 래퍼화)는 이 SPEC 범위 밖**: 기존 commands 수정 없이 새 스킬 추가만 수행
5. **research는 P1**: ai-env pipeline dispatch와의 통합이 복잡하므로 MVP에서는 후순위
