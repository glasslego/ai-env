# Specs Changelog

SPEC 문서 관련 변경 이력은 이 파일에서만 관리합니다.

## v1.0 (2026-02-14)

- 초기 SPEC 문서 6개 작성 (구현 기반 역방향 설계 문서)
  - `SPEC-001-core-architecture.md`
  - `SPEC-002-mcp-generator.md`
  - `SPEC-003-sync-and-skills.md`
  - `SPEC-004-cli-interface.md`
  - `SPEC-005-agent-fallback.md`
  - `SPEC-006-codex-integration.md`
- 프로젝트 기능 반영 정비
  - MCP 서버 추가: `fetch`, `filesystem`, `git`, `memory`, `supabase`, `browserbase`
  - `vibe` rate-limit 감지 및 자동 복귀 문서 반영
  - 불필요 스킬 삭제 (5개, 1765줄)

## Timeline

- 2025-12-22: 초기 구축 (SPEC-001, 002, 004)
- 2026-01-06: Sync 모듈 (SPEC-003)
- 2026-01-27: MCP 확장 (GitHub Kakao, glocal 도입, ChatGPT Desktop 타겟)
- 2026-01-28: MCP 대량 추가 (Context7, Brave Search, Mem0, BrowserAct)
- 2026-02-04: Skills 동기화 확장 (cde-*skills, 레이아웃 자동 감지)
- 2026-02-09: ChatGPT Desktop 독립 타겟
- 2026-02-13: Codex 통합 + Agent Fallback (SPEC-005, 006)
- 2026-02-14: 정비 및 SPEC 문서 v1.0 작성

## v1.1 (2026-02-14)

- 권한 정책 완화 (개인 자동화 작업용)
  - Codex deny 규칙을 `rm -rf` 계열 4개로 단순화
  - Claude glocal/global permissions를 `Bash(*)`, `mcp__*`, `WebSearch`, `WebFetch` 중심으로 조정
  - `SPEC-002`, `SPEC-006` 문서 동기화
