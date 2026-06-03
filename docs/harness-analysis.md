# Harness 분석: kcai-claude & cde-skills

> 2026-04-12 작성. kcai-claude / cde-skills 두 레포의 harness 구현 분석.

---

## 1. Harness란?

AI 에이전트가 **어떤 도구를 쓰고, 어떤 권한으로, 어떤 순서로 일하는지를 코드로 정의하는 인프라 계층**.

```
Skill  (What)  — 도구 + 도메인 지식
Agent  (Who)   — 전문가 페르소나, 독립 컨텍스트
Command (When) — 워크플로우 레시피, 실행 순서
Harness        — 이 셋을 연결하는 조직 체계
```

핵심 원칙: **Mechanism(인프라) vs Policy(정책) 분리**
- Mechanism: K8s Job 관리, 시크릿, 워크스페이스 구성, 프로세스 제어
- Policy: Recipe, Agent 역할, Skill 지식, 리뷰 기준

Policy 변경은 git push만으로 반영. Mechanism 변경은 배포 필요.

---

## 2. kcai-claude — 원격 자율 에이전트 하네스

**레포**: `/Users/megan/work/KCAI/kcai-claude`

### 2.1 아키텍처 개요

Gateway(상시 Deployment) + Orchestrator(1회성 K8s Job) 구조.

```
Jira 웹훅 (assignee → kcai.bot / /kc rerun)
    ↓
Gateway (FastAPI Deployment)
    ├─ jira.py router → channel_dispatcher → job_manager
    └─ K8s Job 생성: kcai-orch-{ticket}-{job_type}-{trial_id}
    ↓
Orchestrator Pod (K8s Job, one-shot)
    ├─ Vault 시크릿 로드 (Claude 토큰 풀)
    ├─ Jira 이슈 상세 fetch
    ├─ Git auth 설정
    ├─ 워크스페이스 구성:
    │   ├─ recipes/ fetch (GitHub, fallback: local)
    │   ├─ copy_recipes() → extends 상속 해결
    │   ├─ copy_agents() → extends 상속 해결
    │   ├─ copy_skills() → remote 필터링 + 제약 주입
    │   ├─ apply_profile(remote.json) → settings.json 생성
    │   └─ inject_personal_tokens()
    ├─ WORKLOG.md 스캐폴딩
    ├─ claude -p 실행 루프:
    │   ├─ Orchestrator → @dev (코드 구현, TDD)
    │   ├─ Orchestrator → @reviewer (리뷰, 커밋)
    │   ├─ NEEDS_CLARIFICATION → Jira 코멘트 → 신호 대기
    │   └─ Rate limit → 토큰 로테이션 → 재시도
    ├─ PR 생성 → Jira 상태 전환
    └─ S3 세션 백업
```

### 2.2 디렉토리 구조

```
kcai-claude/
├── harness/                    # Mechanism (Python 패키지)
│   ├── gateway/                # FastAPI 웹훅 서버
│   │   ├── app.py              # 라우터 등록, 레지스트리/리뷰 초기화
│   │   ├── job_manager.py      # K8s Job/Service/Ingress CRUD
│   │   ├── job_registry.py     # In-memory + S3 상태 레지스트리
│   │   ├── review_manager.py   # GitHub PR 자동 리뷰 트리거
│   │   ├── channel_dispatcher.py  # ChannelEvent → 핸들러 라우팅
│   │   ├── command_parser.py   # /kc 커맨드 파싱
│   │   ├── token_status.py     # Claude 토큰 상태 추적
│   │   └── routers/            # jira, github, probe, registry
│   ├── orchestrator/           # K8s Job 실행 로직
│   │   ├── main.py             # 진입점: 워크스페이스 구성 + claude -p 루프
│   │   ├── config.py           # 환경 설정 + 시크릿 로드 + trial ID
│   │   ├── recipe_loader.py    # Recipe 파싱, extends 상속, GitHub fetch
│   │   ├── jira_client.py      # Jira REST API
│   │   ├── log_parser.py       # claude.log 스트림 JSON 파싱
│   │   └── reporter.py         # Jira 코멘트 포맷팅/게시
│   ├── profiles/
│   │   └── remote.json         # 권한 프로파일: PreToolUse 훅
│   ├── scripts/
│   │   ├── validate-remote-bash.sh   # 위험 명령 하드 차단
│   │   ├── validate-remote-read.sh
│   │   └── validate-remote-write.sh
│   └── storage/
│       └── session_store.py    # Local + S3 세션 저장소
├── agents/
│   ├── common.md               # 공통 규칙 (base)
│   ├── dev.md                  # extends: common.md — TDD 코드 구현
│   └── reviewer.md             # extends: common.md — 리뷰 + 커밋
├── recipes/
│   ├── common.md               # Master Orchestrator 레시피
│   ├── bugfix.md               # extends: common.md
│   ├── python-api.md           # extends: common.md — FastAPI
│   ├── diagnosis.md            # 진단 모드
│   └── retrospective.md        # 회고 모드
├── skills/                     # ~24개 스킬 (SKILL.md + scripts/)
├── hooks/hooks.json            # SessionStart: setup.sh
├── commands/                   # 슬래시 커맨드
└── docker/                     # Dockerfile + entrypoint
```

### 2.3 Agent 정의: extends 상속

```yaml
# agents/common.md (base)
---
name: common
description: 공유 규칙
---
# 시크릿 금지, git push 금지, CLAUDE.md 필독 등

# agents/dev.md
---
name: dev
extends: common.md
tools: Read, Write, Edit, Glob, Grep, Bash
model: opus
---
# TDD 구현, 커밋/푸시 금지

# agents/reviewer.md
---
name: reviewer
extends: common.md
tools: Read, Glob, Grep, Bash    # Write/Edit 물리적 차단
model: opus
---
# 리뷰 + 커밋 권한
```

`recipe_loader.py`의 `resolve_extends()`가 빌드 타임에 체인 병합:
- frontmatter: child가 parent 덮어씀 (shallow merge)
- body: parent + `\n\n` + child
- `extends` 필드는 최종 출력에서 제거

### 2.4 Recipe 시스템

레시피 = 워크플로우 매뉴얼. Agent와 별개로 "어떤 절차로 일하는지" 정의.

```
recipes/common.md          ← Master Orchestrator (워크플로우, Git 컨벤션)
  ├── recipes/bugfix.md    ← extends: common.md
  ├── recipes/python-api.md
  └── recipes/diagnosis.md
```

Orchestrator가 Jira 티켓 유형에 따라 레시피 선택 → `claude -p` 프롬프트에 주입.

### 2.5 이중 보안 계층

| 계층 | 위치 | 동작 |
|------|------|------|
| Soft (프롬프트) | `copy_skills()` → SKILL.md에 제약 텍스트 주입 | "이 환경에서는 X 불가" |
| Hard (OS 훅) | `validate-remote-bash.sh` → PreToolUse 훅 | regex 매칭으로 물리 차단 |

차단 대상: `git push --force`, `rm -rf /`, DDL SQL, 프로덕션 Airflow trigger, K8s delete 등.

### 2.6 토큰 관리

- Vault에 `owner=token` 쌍으로 저장
- 시작 시 풀에서 랜덤 선택
- 429/401 → 해당 owner 소진, 다음 토큰으로 교체
- 전체 소진 → exit code 42, Jira에 보고

### 2.7 Job 모드

| `JOB_TYPE` | 트리거 | 레시피 | 용도 |
|------------|--------|--------|------|
| `work` | kcai.bot 할당 / `/kc rerun` | common.md + 선택 레시피 | 티켓 구현 |
| `diagnosis` | `/kc diagnose` | diagnosis.md | 실패 분석 |
| `retrospective` | Jira Done 전환 | retrospective.md | 개선 제안 |
| `review` | GitHub PR 이벤트 | reviewer agent | PR 자동 리뷰 |

---

## 3. cde-skills — 로컬 팀 스킬 하네스

**레포**: `/Users/megan/work/cde/cde-skills`

### 3.1 아키텍처 개요

3-Tier 오케스트레이션: Command → Agent → Skill

```
Commands (.claude/commands/)
    │  워크플로우 레시피, 사용자 게이트 포함
    ↓
Agents (.claude/agents/)
    │  독립 컨텍스트, 스킬 주입, 모델/권한 설정
    ↓
Skills (skills/<name>/SKILL.md + scripts/)
        도구 라이브러리, Python CLI 스크립트
```

### 3.2 디렉토리 구조

```
cde-skills/
├── .claude/
│   ├── agents/
│   │   ├── oncall-investigator.md  # opus, plan, worktree
│   │   ├── researcher.md           # sonnet, plan
│   │   ├── code-reviewer.md        # sonnet, plan
│   │   └── skeptic.md              # sonnet, plan
│   ├── commands/
│   │   ├── ultrawork.md            # 병렬 서브에이전트 오케스트레이션
│   │   ├── plan-and-build.md       # EBP 기반 설계 + 구현
│   │   ├── oncall_agent.md         # 온콜 대응 프로세스
│   │   ├── sddj.md                 # Spec-Driven Dev w/ Jira
│   │   └── ...                     # data-demo, ontology 등
│   ├── settings.local.json         # 로컬 권한 설정
│   └── handoff/                    # 세션 간 컨텍스트 전달
├── skills/                         # 39개 스킬
│   ├── <name>/
│   │   ├── SKILL.md                # 도구 설명 + frontmatter
│   │   ├── scripts/                # Python CLI (argparse)
│   │   │   ├── <name>_base.py      # API 클라이언트
│   │   │   └── <name>_*.py         # 서브커맨드
│   │   └── references/             # 보충 문서
│   ├── common/                     # 공통: auth_check, vault_reader
│   └── _shared/                    # 공유 컨벤션, 인증
├── docs/
│   ├── skills_vs_agents.md         # 3-Layer 설계 가이드
│   └── skill_standardization.md    # SKILL.md 포맷 스펙
├── templates/SKILL.md              # 스킬 생성 템플릿
└── CLAUDE.md                       # 프로젝트 규칙
```

### 3.3 Agent 정의: Claude Code 네이티브 frontmatter

```yaml
# .claude/agents/oncall-investigator.md
---
name: oncall-investigator
description: 인시던트 조사 및 파이프라인 장애 진단
model: opus
permissionMode: plan           # 읽기전용
isolation: worktree            # 독립 워크트리
memory: project
effort: high
skills:
  - oncall
  - airflow
  - kubernetes
  - kafka
  - flink
  - grafana
  - elasticsearch
  - trino
  - watchtower
  - jira
---
```

| 필드 | 의미 |
|------|------|
| `model` | opus(중요) / sonnet(일반) / haiku(탐색) |
| `permissionMode: plan` | 읽기전용 — 조사만, 실행 불가 |
| `isolation: worktree` | 독립 git 워크트리에서 작업 |
| `skills` | 에이전트 컨텍스트에 SKILL.md 주입 |
| `effort: high` | 다단계 철저 조사 |

### 3.4 현재 Agent 구성

| Agent | Model | Permission | 역할 |
|-------|-------|-----------|------|
| oncall-investigator | opus | plan + worktree | 장애 진단 (10개 스킬) |
| researcher | sonnet | plan | 크로스소스 리서치 |
| code-reviewer | sonnet | plan | PR 리뷰 (컨벤션 기반) |
| skeptic | sonnet | plan | 설계 비평 (EBP 패널) |

### 3.5 Skill → Agent 연결

1. Agent frontmatter에 `skills: [airflow, k8s, ...]` 선언
2. Claude Code가 해당 SKILL.md 전문을 에이전트 컨텍스트 윈도우에 주입
3. 에이전트가 `python skills/<name>/scripts/<script>.py <command>` 실행

스킬 해결 경로:
```
SKILL.md (스크립트 목록) → scripts/*.py (argparse CLI) → *_base.py (API 클라이언트) → 외부 API
```

### 3.6 설계 원칙

| 원칙 | 설명 |
|------|------|
| 읽기/쓰기 분리 | 조사 에이전트는 `plan` 모드, 쓰기는 별도 승인 |
| 모델 티어링 | Opus(인시던트) / Sonnet(일반) / Haiku(탐색) |
| 컨텍스트 보호 | 로그/메트릭은 서브에이전트에서 처리, 메인에는 요약만 |
| 워크트리 격리 | 코드 수정 에이전트는 독립 브랜치에서 작업 |
| 에러 복구 | Fail → Retry → Adapt → Escalate (2회 실패 후 사용자에게) |

---

## 4. 두 레포 비교

| 관점 | kcai-claude | cde-skills |
|------|-------------|------------|
| **실행 환경** | K8s Pod (원격 자율) | 로컬 CLI (대화형) |
| **트리거** | Jira 웹훅 자동 | 사용자 /커맨드 |
| **Agent 정의** | extends 상속 체인 + recipe_loader | Claude Code 네이티브 frontmatter |
| **보안** | 이중 방어 (프롬프트 + OS 훅) | permissionMode: plan |
| **상태 관리** | S3 + K8s Job Registry | 로컬 handoff 파일 |
| **스킬 수** | ~24개 | ~39개 |
| **레시피** | Recipe 시스템 (extends 상속) | Command 마크다운 |
| **배포** | Docker(harness) + git push(policy) | git push만 |
| **토큰 관리** | Vault 풀 + 자동 로테이션 | 사용자 로컬 |
| **세션 복구** | S3 백업/복원 | handoff/ 파일 |

### 공통점

- 3-Layer 구조 (Skill / Agent / Workflow)
- SKILL.md frontmatter 기반 스킬 정의
- 읽기/쓰기 분리 원칙
- 독립 컨텍스트 윈도우로 에이전트 격리

### 차이점의 핵심

- kcai-claude는 **무인 자동화**(사람 없이 끝까지 실행)에 최적화 → 보안/복구/토큰 관리가 두꺼움
- cde-skills는 **로컬 대화형**(사람이 옆에서 지시)에 최적화 → 스킬 수/도메인 커버리지가 넓음

---

## 5. 프롬프트 계층 구조

### kcai-claude
```
Recipe (common.md + 선택 레시피)
  └─ Sub-Agent (dev / reviewer)
       └─ Skill (SKILL.md 주입)
            └─ Permission Profile (remote.json 훅)
```

### cde-skills
```
Command (ultrawork, plan-and-build 등)
  └─ Agent (oncall-investigator, researcher 등)
       └─ Skill (SKILL.md + scripts/)
            └─ settings.local.json (권한)
```

---

## 6. ai-env에 대한 시사점

ai-env는 이미 skills 동기화, settings.json 생성, hooks 관리를 하고 있어 "하네스의 하네스" 역할.

적용 가능한 확장:
1. **Agent 동기화**: `.claude/agents/` 도 sync 대상에 추가
2. **Permission Profile 생성**: 프로젝트별 remote.json 스타일 프로파일 자동 생성
3. **Recipe/Agent extends 해결**: ai-env sync 시 상속 체인 머지
4. **팀 에이전트 배포**: cde-*skills처럼 팀 에이전트도 심링크로 가져오기
