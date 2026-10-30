---
id: SPEC-018
title: 코딩 에이전트 토큰·속도 최적화
status: in_progress
created: 2026-10-30
---

# SPEC-018: 코딩 에이전트 토큰·속도 최적화

## 문제와 결정

매 세션 시작 컨텍스트와 매 턴 hook 지연이 누적된다. 측정(2026-10-30):

| 항목 | 측정값 |
|---|---|
| 기록 1건 저장 시 git 호출 | 약 12회(회당 약 27ms). 압축 테스트 1개 22초 |
| hook 1회 지연(UserPromptSubmit) | 0.24~0.30초. 그중 CLI 전체 import 0.38초 대비 hook 모듈만 0.16초 |
| Codex `~/.codex/AGENTS.md` | 43KB, 그중 스킬 목록 28KB. Codex는 `~/.agents/skills`를 자체 예산(기본 8천 자)으로 이미 읽는다 |
| ai-env에서 Claude 규칙 | `~/.claude/rules`와 원본 `.claude/rules`가 같은 내용으로 두 번 로드(약 33KB 중복) |

동작 계약(기록 내용·경로·규칙 문구)은 바꾸지 않고 중복 로드와 반복 호출만 줄인다.

## Task

- [x] TASK-01: 세션 기록 hook 경로를 가볍게 만든다.
  - AC: 프로세스 안에서 저장소 구조 조회(toplevel·common-dir·git-dir·origin)는 경로별 1회만 git을 호출한다.
    branch·HEAD·status는 매번 조회한다. hook 스크립트는 CLI 전체 대신 hook 모듈 진입점을 실행하며
    stdin/stdout JSON·실패 시 systemMessage 계약을 유지한다.
  - Tests: 저장 1건의 git 호출 수 상한, hook 진입점 입출력·실패 메시지, 기존 session 테스트.
- [ ] TASK-02: Codex AGENTS.md에서 스킬 목록을 뺀다.
  - AC: AGENTS.md는 글로벌 지침과 규칙 인덱스만 담는다. 스킬은 `~/.agents/skills`·`~/.codex/skills` 배포를 유지한다.
  - Tests: sync 결과 AGENTS.md에 스킬 목록이 없고 스킬 디렉터리 배포는 그대로.
- [ ] TASK-03: ai-env 세션에서 규칙 원본의 중복 로드를 막는다.
  - AC: 프로젝트 `.claude/settings.json`의 `claudeMdExcludes`로 ai-env `.claude/rules/**`만 제외한다.
    글로벌 `~/.claude/rules`는 계속 로드된다.
  - Tests: 설정 파일 JSON 유효성, 패턴이 글로벌 규칙 경로와 겹치지 않음.

## 제외·후속 결정

- 상시 로드 규칙의 범위 축소, 팀 스킬과 겹치는 개인 wrapper 스킬 정리는 규칙 적용 범위가 바뀌므로 사용자 결정 후 별도 Task로 진행한다.
- 모델·라이브러리 버전, 팀 스킬 원본은 바꾸지 않는다.
