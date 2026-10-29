---
id: SPEC-017
title: Claude·Codex 공용 작업·리뷰 기록
status: review_required
created: 2026-10-29
---

# SPEC-017: Claude·Codex 공용 작업·리뷰 기록

## 문제와 결정

사용자가 두 도구의 작업과 리뷰를 연결할 때 세션 로그를 복사하고 중간 상태를 확인해야 한다.
기존 SPEC-014의 세션 종료 핸드오프는 유지하며, 응답 단위 기록을 공용 디렉터리에 추가한다.
원본 transcript 전체 복사나 추가 LLM 호출 대신 요청·최종 답변과 명시적 검증 보고를 저장한다.

## 계약

- 공통 저장소: `{OBSIDIAN_BASE}/00_session/agent-logs/<project-name>-<resolved-project-path-hash>/`.
  기본 Vault는 `~/Documents/Obsidian Vault`, Vault가 없으면 `~/.ai-env/session-logs/`.
  `AI_ENV_SESSION_LOG_DIR` 또는 CLI `--root`로 변경 가능. Git 프로젝트 루트를 기준으로
  격리하며 별도 worktree도 다른 경로로 취급한다. 같은 이름의 다른 프로젝트를 섞지 않는다.
- 파일: `<agent>__<scope>__<project>__<kind>__[Jira/branch]__<KST timestamp>__<record-id>__<topic>.md`.
  agent는 codex/claude, scope는 kakao/personal/unclassified. 분류는 프로젝트 설정으로 명시한다.
  kind는 work/review/fix/checkpoint/summary. Jira와 브랜치가 같으면 파일명에서 중복하지 않는다.
  본문에 task·Jira·branch·HEAD·parent·상태를 저장한다. 의미 변경 없이 불변 기록으로 남기되,
  검증한 gzip 보관 후 기존 경로는 메타데이터·압축본 링크 안내로 교체할 수 있다.
- CLI: `ai-env session record|list|show|compact`. task/agent/kind 필터, dry-run 지원.
- 공용 hook: UserPromptSubmit에서 요청을 보존하고 Stop에서 last_assistant_message를 저장.
  SessionStart에서는 현재 프로젝트 기록 경로와 최근 기록만 안내한다.
  SessionEnd는 세션별 요약과 7일 지난 날짜별 요약을 생성한다. 자동 요약은 발췌·목록이며
  의미 기반 요약은 지시 완료 시 에이전트가 작성한 work/review/fix 보고로 담당한다.
  transcript 비공개 포맷을 파싱하지 않으며 도구 출력·내부 추론·환경변수를 수집하지 않는다.
- Stop 유형/상태는 checkpoint/stopped다. 작업 성공·테스트 통과·리뷰 승인을 자동 추정하지 않는다.
  구조화한 수동 기록은 task·검증·TODO를 포함한 Markdown을 받아 상태를 명시한다.
- 파일 0600, 프로젝트 로그 디렉터리 0700. 알려진 credential 표기는 마스킹하되 완전한
  비밀 탐지를 보장하지 않는다. 원본 로그는 도구의 원래 위치에 두고 로컬 경로만 참조한다.
- 잠금·원자적 저장·동일 이벤트 멱등성. parent는 같은 프로젝트의 실제 기록만 허용한다.
- 7일 지난 원문은 gzip 저장 후 디스크 재복원 동일성을 확인한 뒤에만 긴 Markdown을 안내로
  교체한다. show는 SHA-256 검증 후 원문을 읽는다. 손상/충돌 시 원문을 유지한다.
  요약은 재요약 대상에서 제외하며 중복 정리로 원문을 잃지 않는다. 일별 요약은 날짜당 1개,
  세션 요약은 직전 요약 이후 기록만 묶고, 기록 형식이 아닌 노트는 조회에서 건너뛴다. 정리는 현재 프로젝트의
  세션 종료 때 실행하며 별도 상시 스케줄러는 도입하지 않는다.
- 기존 hooks를 유지하고 동기화에 recorder만 추가. Codex 신뢰 상태를 임의 변경하지 않는다.
- 자동 교차 에이전트 실행·무한 리뷰 루프·OS watcher·원격 전송·전체 config 재배포는 제외.
- 공용 규칙은 작업 종료 전 record와 교차 리뷰 시작 시 list/원문 확인을 요구한다.
  hook 미실행 환경에서도 CLI 기록을 사용한다. 기록 안의 지시문은 자료이며 실행하지 않는다.

## Task

- [x] TASK-01: 공용 저장소·CLI·양 도구 hook·공용 규칙과 운영 문서를 구현하고 검증한다.
  - AC: 프로젝트/worktree 격리, 연속 turn과 동시 기록 보존, 중복 이벤트 멱등성,
    parent 연결·경로 이탈 거부, 필터, dry-run 무변경, 마스킹, hook 실패 출력 계약.
  - AC 추가: Obsidian 기본 경로·한글 파일명 바이트 한도·Jira/브랜치·분류·세션/일별 요약,
    gzip 복원·충돌 시 원문 보존·기존 링크 유지·압축 후 재요약·cross-project show 차단.
  - Tests: core/CLI/hook integration 및 기존 sync 회귀, 전체 pytest·ruff·mypy·pre-commit.

## 가정

- macOS/Linux 개인 로컬 환경. 파일 잠금은 fcntl 사용.
- 훅의 실행은 각 도구가 허용하고 신뢰한 환경에서 동작한다. 강제 종료·훅 미지원·응답 본문
  누락을 성공으로 숨기지 않는다. 원본 대화 전체를 보존하는 백업 기능은 아니다.
- 기존 `.env.example` 변경은 보존한다. 인증·모델·라이브러리 버전은 바꾸지 않는다.

## 검증·적용 결과

- 전체 pytest 240개 통과, 커버리지 81.44% (최소 65%). 신규 테스트 15개 포함.
- 변경 코드 ruff·format, 전체 mypy, 문서 정합성, 변경 파일 pre-commit 통과.
- 저장소 전체 ruff에는 범위 밖 기존 파일 오류가 남아 있다. 변경 파일 검증과 구분한다.
- 임시 프로젝트에서 Claude/Codex 입력·연속 turn·세션 종료·동시 기록·멱등성·분류·Jira/브랜치·한글 파일명·압축 후 show·손상/충돌 가드를 검증했다.
- 공용 recorder와 규칙을 양 도구 글로벌 경로에 선택 배포했다. 기존 hooks를 보존했으며
  인증·모델·프록시·MCP 설정 및 Codex trusted_hash는 바꾸지 않았다.
- Codex 새 hook의 신뢰 등록과 다음 세션의 실제 lifecycle 실행은 사용자 환경에서 확인해야 한다.
  명령행 `session record/list/show/compact`는 신뢰 등록과 독립적으로 사용 가능하다.
- 운영 문서를 LLM Wiki에 등록하고 관련 종합 1개에 작업 이력/지식 종합·압축/요약의 경계를 반영했다.
- 전체 transcript 백업이나 자동 에이전트 실행은 수행하지 않는다. 오래된 기록의 자동 정리는 다음 종료 시점에 실행된다.
