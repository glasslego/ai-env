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
- 2026-02-16: Codex Desktop 타겟, doctor 명령어, fallback 개선 (SPEC-007)
- 2026-02-18: Deep Research API Dispatch, 프롬프트 MD 전환 (SPEC-008)

## v1.3 (2026-02-18)

- Deep Research API Dispatch 구현 (`SPEC-008`)
  - Gemini Deep Research API (`deep-research-pro-preview-12-2025`) 자동 호출
  - OpenAI Deep Research API (`o4-mini-deep-research`) 자동 호출
  - `ai-env pipeline dispatch {topic_id}` CLI 커맨드 추가
  - API 키 없으면 프롬프트 파일 생성으로 graceful fallback
  - httpx AsyncClient 기반, asyncio.gather 병렬 호출
- 심층리서치 프롬프트 Markdown frontmatter 방식 전환
  - `config/prompts/{topic_id}/*.md` 디렉토리 구조
  - YAML frontmatter (track, output, focus) + 본문 (프롬프트)
  - `load_deep_research_prompts()` MD 로더 구현
- Model-level fallback (`--fallback`) 개선
  - Opus → Sonnet → Codex 모델 단위 전환
  - 핸드오프 시 컨텍스트 전달 (Claude → Codex)
- 3-Track 리서치 파이프라인 + Agent-Teams 병렬 처리
- 6-Phase 워크플로우 자동화 (Obsidian 템플릿 + scaffold CLI)
- config/ 정리: 중복 SPEC 파일, 미사용 README 삭제

## v1.2 (2026-02-16)

- Codex Desktop 동기화 타겟 추가 (`~/.codex/codex.config.json`)
  - `generate_codex_desktop()` 메서드 추가 (JSON 형식, SSE url 지원)
  - 공통 MCP 세트 + Docker/SSE 서버에 `codex_desktop` 타겟 등록
  - `ai-env generate codex-desktop` 서브커맨드 추가
- `ai-env doctor` 건강 검사 명령어 구현 (`SPEC-007`)
  - 4개 카테고리: 환경변수, 도구 설치, 동기화 드리프트, 쉘 설정
  - `--json` 옵션으로 CI/자동화 출력 지원
- `claude --fallback` 개선
  - Rate-limit 감지: 종료 코드와 무관하게 로그에서 키워드 검색
  - `--auto` 옵션: 에이전트별 자동 승인 플래그 주입
  - `--to` 옵션: fallback 대상 런타임 지정
- README.md 전면 개선
- Codex 기본 모델 기본값 반영
  - `config/settings.yaml`에 `codex_model`/`codex_model_reasoning_effort` 추가
  - `generate_codex()`에서 `model`/`model_reasoning_effort`를 TOML 생성에 반영

## v1.1 (2026-02-14)

- 권한 정책 완화 (개인 자동화 작업용)
  - Codex deny 규칙을 `rm -rf` 계열 4개로 단순화
  - Claude glocal/global permissions를 `Bash(*)`, `mcp__*`, `WebSearch`, `WebFetch` 중심으로 조정
  - `SPEC-002`, `SPEC-006` 문서 동기화
