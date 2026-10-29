---
spec_id: SPEC-016
title: 문서 작업의 LLM Wiki 검색·등록 연계
status: review_required
created: 2026-10-29
updated: 2026-10-29
---

# SPEC-016: 문서 작업의 LLM Wiki 검색·등록

## 계약

- Vault 경로: `--vault` → `OBSIDIAN_BASE` → `~/Documents/Obsidian Vault`.
- `ai-env wiki search QUERY`: 종합 페이지와 등록한 출처를 로컬 키워드 검색하고 JSON 반환. 읽기 전용.
- `ai-env wiki register FILE`: 명시한 UTF-8 Markdown의 경로·제목·SHA-256 등록. 외부 파일과 Vault 작업 기록(`00_session/agent-logs/`, gzip 보관으로 본문이 바뀜)은 `00_inbox/llm-wiki/<content-hash>.md`에 불변 스냅샷으로 보관.
- Vault 안 원본은 복사·수정하지 않는다. 외부 원본도 수정하지 않는다.
- 동일 경로·내용 재등록은 무변경. 변경 시 이전 스냅샷 보존. `--dry-run`은 파일을 만들지 않는다.
- 레지스트리: `_meta/llm-wiki-registry.json`, 버전 1, 원본 절대 경로별 최신 등록. 잠금·원자적 저장으로 동시 등록 손실 방지.
- 경로 이탈·심링크를 통한 저장 경로 이탈을 차단하고, 손상된 레지스트리는 덮어쓰지 않는다.
- 개인·투자 영역은 검색 제외, 등록은 `--allow-private`로 지정한 문서에 한해 허용. 허용한 문서도 기본 검색에서는 제외.
- 종합·메타·스냅샷의 재등록은 건너뛰어 자기 증식을 막는다.
- 공용 규칙과 distill/session-curator에서 작성 전 검색, 완료된 문서 등록, 관련 종합 최대 3개 갱신을 연결한다.
- 자동화는 에이전트의 문서 작업 절차로 실행한다. OS watcher·백그라운드 LLM·새 외부 API를 추가하지 않는다.
- CLI는 출처 등록과 관련 페이지 탐색을 담당한다. 종합 내용·인덱스·로그는 에이전트가 실제 근거를 읽고 갱신한다.

## Task

- [x] TASK-01: CLI·등록 저장소·공용 워크플로우를 구현하고 검증한다.
  - AC: 한글 검색, 외부 문서 스냅샷, 멱등성·내용 변경·dry-run·원본 보존·개인 영역·경로 이탈·손상·동시 등록 검증.
  - Test: core/CLI pytest, 전체 회귀·ruff·mypy·문서 정합성·pre-commit.

## 제외와 가정

- 기존 `.env.example` 변경 보존. 라이브러리·모델·인증·프록시 설정 변경 없음.
- macOS/Linux 로컬 파일 잠금 사용. 검색은 키워드 기반이며 의미 검색 재현율을 보장하지 않는다.
- 결과 문서에 재사용 가능한 지식이 있을 때만 자동 등록한다. 지침 파일·단순 링크 수정·변경 없는 재검토는 등록하지 않는다.
- 외부 웹 문서 자체는 가져오지 않는다. 작성·확인한 로컬 Markdown 결과물을 등록한다.

## 검증 결과

- 전체 pytest 225개 통과, 커버리지 79.45% (기준 65%). 신규 core·CLI 테스트 11개 포함.
- 변경 Python 파일 ruff·format, 전체 `mypy src/`, 문서 정합성, 변경 파일 pre-commit 통과.
- 전체 저장소 lint에는 기존 파일 오류 9건과 기존 포맷 대상 3개가 남아 있다. 이번 Task 범위 밖이므로 수정하지 않았다.
- 실제 Vault에서 검색·외부 운영 가이드 등록·재등록 `unchanged` 확인. 관련 종합에 근거 연결.
- Claude·Codex 공용 지침·해당 규칙·distill·session-curator만 선택 배포. 인증·모델·프록시·MCP 설정은 변경하지 않았다.
- Vault 최신 운영 규칙을 반영해 종합 노트에는 수동 해시 필드를 추가하지 않는다. 해시는 CLI 등록부에서 자동 관리한다.
