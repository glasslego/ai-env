# ai-env Spec Registry

> 이 문서는 ai-env 프로젝트의 모든 SPEC 문서를 추적합니다.
> SPEC 변경 이력은 `specs/CHANGELOG.md`에서 관리합니다.

## SPEC 목록

| ID | 제목 | 상태 | 최초 구현 | 문서화 | 파일 |
|----|------|------|-----------|--------|------|
| SPEC-001 | Core Architecture & Config Management | implemented | 2025-12-22 | 2026-02-14 | [SPEC-001](SPEC-001-core-architecture.md) |
| SPEC-002 | MCP Config Generator | implemented | 2025-12-22 | 2026-02-14 | [SPEC-002](SPEC-002-mcp-generator.md) |
| SPEC-003 | Claude Global Sync & Skills Management | implemented | 2026-01-06 | 2026-02-14 | [SPEC-003](SPEC-003-sync-and-skills.md) |
| SPEC-004 | CLI Interface | implemented | 2025-12-22 | 2026-02-14 | [SPEC-004](SPEC-004-cli-interface.md) |
| SPEC-005 | Agent Fallback (claude --fallback) | implemented | 2026-02-13 | 2026-02-14 | [SPEC-005](SPEC-005-agent-fallback.md) |
| SPEC-006 | Codex CLI Integration (Permissions & Teammate Mode) | implemented | 2026-02-13 | 2026-02-14 | [SPEC-006](SPEC-006-codex-integration.md) |
| SPEC-007 | Doctor Health Check | implemented | 2026-02-16 | 2026-02-16 | [SPEC-007](SPEC-007-doctor-health-check.md) |
| SPEC-008 | Deep Research API Dispatch | implemented | 2026-02-18 | 2026-02-18 | [SPEC-008](SPEC-008-deep-research-dispatch.md) |

## 상태 정의

| 상태 | 설명 |
|------|------|
| `draft` | 초안 작성 중. 검토/구현 전 |
| `approved` | 승인됨. 구현 대기 |
| `in-progress` | 구현 진행 중 |
| `implemented` | 구현 완료 |
| `deprecated` | 폐기됨. 더 이상 유효하지 않음 |

## 네이밍 규칙

- 파일명: `SPEC-{NNN}-{kebab-case-title}.md`
- ID: 3자리 숫자 (001~999)
- 새 SPEC 추가 시 이 README의 SPEC 목록과 `CHANGELOG.md`를 함께 업데이트
