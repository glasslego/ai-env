# ai-env Spec Registry

> 이 문서는 ai-env 프로젝트의 모든 SPEC 문서를 추적합니다.

## 버전 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|-----------|
| v1.0 | 2026-02-14 | 초기 SPEC 문서 6개 작성 (구현 기반 역방향 설계 문서) |

## SPEC 목록

| ID | 제목 | 상태 | 최초 구현 | 문서화 | 파일 |
|----|------|------|-----------|--------|------|
| SPEC-001 | Core Architecture & Config Management | implemented | 2025-12-22 | 2026-02-14 | [SPEC-001](SPEC-001-core-architecture.md) |
| SPEC-002 | MCP Config Generator | implemented | 2025-12-22 | 2026-02-14 | [SPEC-002](SPEC-002-mcp-generator.md) |
| SPEC-003 | Claude Global Sync & Skills Management | implemented | 2026-01-06 | 2026-02-14 | [SPEC-003](SPEC-003-sync-and-skills.md) |
| SPEC-004 | CLI Interface | implemented | 2025-12-22 | 2026-02-14 | [SPEC-004](SPEC-004-cli-interface.md) |
| SPEC-005 | Agent Fallback (vibe Function) | implemented | 2026-02-13 | 2026-02-14 | [SPEC-005](SPEC-005-agent-fallback.md) |
| SPEC-006 | Codex CLI Integration (Permissions & Teammate Mode) | implemented | 2026-02-13 | 2026-02-14 | [SPEC-006](SPEC-006-codex-integration.md) |

## 상태 정의

| 상태 | 설명 |
|------|------|
| `draft` | 초안 작성 중. 검토/구현 전 |
| `approved` | 승인됨. 구현 대기 |
| `in-progress` | 구현 진행 중 |
| `implemented` | 구현 완료 |
| `deprecated` | 폐기됨. 더 이상 유효하지 않음 |

## 구현 타임라인

```
2025-12-22  초기 구축 (SPEC-001, 002, 004)
            ├─ Pydantic 설정 모델
            ├─ SecretsManager (.env)
            ├─ MCPConfigGenerator (claude_desktop, codex, gemini)
            └─ Click CLI (status, secrets, sync, generate)

2026-01-06  Sync 모듈 (SPEC-003)
            └─ sync_claude_global_config (CLAUDE.md, commands/, skills/)

2026-01-27  MCP 확장
            ├─ GitHub Kakao MCP + ENV_KEY_MAPPING
            ├─ glocal 설정 도입 (global template for local)
            └─ ChatGPT Desktop 타겟 추가

2026-01-28  MCP 대량 추가
            ├─ Context7, Brave Search, Mem0, BrowserAct
            └─ 권한 이중 관리 구조 (glocal + local)

2026-02-04  Skills 동기화 (SPEC-003)
            ├─ cde-*skills 심링크 지원
            └─ 3가지 디렉토리 레이아웃 자동 감지

2026-02-09  ChatGPT Desktop 독립 타겟

2026-02-13  Codex 통합 + Agent Fallback (SPEC-005, 006)
            ├─ Codex permissions 기반 설정
            ├─ Teammate mode (tmux)
            ├─ vibe() 쉘 함수
            ├─ megan-skills 기본 소스 전환
            └─ skills 선택적 동기화 (include/exclude)

2026-02-14  정비 및 문서화
            ├─ MCP 서버 추가 (fetch, filesystem, git, memory, supabase, browserbase)
            ├─ vibe rate-limit 감지 및 자동 복귀
            ├─ 불필요 스킬 삭제 (5개, 1765줄)
            └─ SPEC 문서 v1.0 작성
```

## 네이밍 규칙

- 파일명: `SPEC-{NNN}-{kebab-case-title}.md`
- ID: 3자리 숫자 (001~999)
- 새 SPEC 추가 시 이 README의 SPEC 목록과 버전 이력을 함께 업데이트
