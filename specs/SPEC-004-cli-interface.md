---
id: SPEC-004
title: CLI Interface
status: implemented
created: 2025-06-01
updated: 2026-02-13
---

# SPEC-004: CLI Interface

## 개요

ai-env CLI는 Click 프레임워크 기반의 명령줄 인터페이스로, Rich 라이브러리를 활용하여 터미널 출력을 렌더링한다. AI 개발 환경의 설정 상태 확인, 환경변수 관리, 설정 파일 생성 및 동기화를 하나의 도구로 수행한다.

## 기술 스택

| 구성 요소 | 라이브러리 | 역할 |
|-----------|-----------|------|
| CLI 프레임워크 | Click (`>=8.1.0`) | 명령어 파싱, 옵션 처리, 그룹 구성 |
| 터미널 출력 | Rich (`>=13.0.0`) | 테이블, 색상, JSON 포맷 출력 |

**엔트리포인트**: `pyproject.toml`의 `[project.scripts]`에서 정의

```toml
[project.scripts]
ai-env = "ai_env.cli:main"
```

## 명령어 구조

```
ai-env                     # Click group (root)
├── setup                  # 초기 설정 가이드
├── status                 # 현재 상태 확인
├── secrets [--show]       # 환경변수 목록 조회
├── sync [options]         # 설정 동기화
├── config                 # Click group
│   └── show               # 현재 설정 표시
└── generate               # Click group
    ├── all [--dry-run]    # 모든 설정 파일 생성
    ├── claude-desktop [-o] # Claude Desktop 설정
    ├── chatgpt-desktop [-o]# ChatGPT Desktop 설정
    ├── antigravity [-o]    # Antigravity 설정
    └── shell [-o]          # Shell export 스크립트
```

## 명령어 레퍼런스

### 최상위 명령어

#### `ai-env setup`

초기 사용자를 위한 인터랙티브 설정 가이드.

| 항목 | 내용 |
|------|------|
| 옵션 | 없음 |
| 검증 단계 | 1) `.env` 파일 존재 확인 2) 필수 환경변수 카테고리별 체크 3) MCP 서버 활성화 현황 |
| 필수 변수 카테고리 | AI API Keys (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY`), GitHub (`GITHUB_GLASSLEGO_TOKEN`), Atlassian (`JIRA_URL`, `JIRA_PERSONAL_TOKEN`, `CONFLUENCE_URL`, `CONFLUENCE_PERSONAL_TOKEN`) |
| 동작 | `.env` 미존재 시 생성 안내 후 조기 종료. 존재 시 전체 점검 후 다음 단계 안내 |

#### `ai-env status`

현재 환경의 전체 상태를 테이블 형태로 출력.

| 항목 | 내용 |
|------|------|
| 옵션 | 없음 |
| 출력 테이블 | AI Providers, MCP Servers, MCP Target Coverage, Claude Global Config |

출력하는 4개의 테이블:

1. **AI Providers** - 프로바이더 이름, env_key, 설정 여부 (Configured/Missing)
2. **MCP Servers** - 서버 이름, 타입(stdio/sse), 타겟 목록 (3개 초과 시 `+N` 표시)
3. **MCP Target Coverage** - 타겟별 활성 서버 수. 타겟 순서: `claude_desktop`, `chatgpt_desktop`, `antigravity`, `claude_local`, `codex`, `gemini`
4. **Claude Global Config** - `ai-env/.claude` 소스와 `~/.claude` 타겟의 동기화 상태. 항목: `CLAUDE.md`, `settings.json`, `commands/`, `skills/`

All-client MCP 서버(모든 타겟에 포함된 서버)가 있으면 별도로 표시.

#### `ai-env secrets`

`.env` 파일의 환경변수를 조회.

| 옵션 | 단축 | 타입 | 설명 |
|------|------|------|------|
| `--show` | - | flag | 실제 값 표시 (기본: 마스킹) |

마스킹 규칙: 8자 초과 시 앞 4자 + `****` + 뒤 4자. `#`으로 시작하는 키는 필터링.

#### `ai-env sync`

중앙 설정을 각 AI 도구로 동기화하는 메인 명령어.

| 옵션 | 단축 | 타입 | 설명 |
|------|------|------|------|
| `--dry-run` | - | flag | 미리보기만 (실제 파일 변경 없음) |
| `--claude-only` | - | flag | Claude 글로벌 설정만 동기화 |
| `--mcp-only` | - | flag | MCP 설정만 동기화 |
| `--skills-include` | - | multiple | 추가할 팀 스킬 디렉토리 (여러 번 사용 가능) |
| `--skills-exclude` | - | multiple | 제외할 팀 스킬 디렉토리 (여러 번 사용 가능) |

동기화 흐름:

```
1. 사전 검증
   ├── .env 파일 존재 확인 (미존재 시 경고 후 계속)
   └── 활성 MCP 서버의 필수 환경변수 누락 확인 (최대 5개 표시)

2. Phase 1: Claude Global Config (--mcp-only가 아닌 경우)
   └── sync_claude_global_config() 호출
       → CLAUDE.md, commands/, skills/, settings.json 동기화

3. Phase 2: MCP 설정 (--claude-only가 아닌 경우)
   └── generator.save_all() 호출
       → claude_desktop, chatgpt_desktop, antigravity,
          codex_global, gemini_global, claude_local,
          codex_local, gemini_local, shell_exports 생성
```

`--claude-only`와 `--mcp-only`는 상호 배타적으로 사용. 둘 다 지정하면 아무것도 동기화되지 않음.

### config 그룹

#### `ai-env config show`

| 항목 | 내용 |
|------|------|
| 옵션 | 없음 |
| 출력 | settings (version, default_agent, env_file), providers (enabled 상태, env_key), MCP servers (enabled 상태, type, targets) |

### generate 그룹

#### `ai-env generate all`

| 옵션 | 단축 | 타입 | 설명 |
|------|------|------|------|
| `--dry-run` | - | flag | 실제 저장하지 않고 경로만 표시 |

`MCPConfigGenerator.save_all()`을 호출하여 모든 타겟 설정 파일 생성.

#### `ai-env generate claude-desktop`

| 옵션 | 단축 | 타입 | 설명 |
|------|------|------|------|
| `--output` | `-o` | string | 출력 파일 경로 (미지정 시 stdout) |

#### `ai-env generate chatgpt-desktop`

| 옵션 | 단축 | 타입 | 설명 |
|------|------|------|------|
| `--output` | `-o` | string | 출력 파일 경로 (미지정 시 stdout) |

#### `ai-env generate antigravity`

| 옵션 | 단축 | 타입 | 설명 |
|------|------|------|------|
| `--output` | `-o` | string | 출력 파일 경로 (미지정 시 stdout) |

#### `ai-env generate shell`

| 옵션 | 단축 | 타입 | 설명 |
|------|------|------|------|
| `--output` | `-o` | string | 출력 파일 경로 (미지정 시 stdout) |

## 전체 옵션 요약

| 명령어 | 옵션 | 타입 | 설명 |
|--------|------|------|------|
| `ai-env` | `--version` | flag | 버전 출력 |
| `ai-env secrets` | `--show` | flag | 마스킹 해제 |
| `ai-env sync` | `--dry-run` | flag | 미리보기 |
| `ai-env sync` | `--claude-only` | flag | Claude 글로벌만 |
| `ai-env sync` | `--mcp-only` | flag | MCP만 |
| `ai-env sync` | `--skills-include` | multiple | 팀 스킬 추가 |
| `ai-env sync` | `--skills-exclude` | multiple | 팀 스킬 제외 |
| `ai-env generate all` | `--dry-run` | flag | 미리보기 |
| `ai-env generate <target>` | `--output` / `-o` | string | 출력 경로 |

## 내부 설계

### 헬퍼 함수

| 함수 | 시그니처 | 역할 |
|------|----------|------|
| `_create_table()` | `(title, columns, rows) -> Table` | Rich 테이블 생성. `columns`는 `[(이름, 스타일), ...]`, `rows`는 `[(값, ...), ...]` |
| `_output_content()` | `(content, output) -> None` | dict이면 JSON, str이면 텍스트로 출력. `output` 경로가 있으면 파일 저장, 없으면 stdout |

### 출력 규칙

- 모든 출력은 `console.print()` 사용 (Python 내장 `print()` 사용 금지)
- JSON 출력은 `console.print_json()` 사용
- 상태 표시: `[green]✓[/green]` (성공), `[red]✗[/red]` (실패), `[yellow]○[/yellow]` (미동기화/부분)
- 리스트 초과 표시: 서버 3개, 환경변수 5개 등 최대 표시 수 제한 후 `+N more` 패턴

### 의존 모듈

```
cli.py
├── core.config    → get_project_root(), load_settings(), load_mcp_config()
├── core.secrets   → get_secrets_manager()
├── core.sync      → sync_claude_global_config()
└── mcp.generator  → MCPConfigGenerator
```

## generate vs sync 차이

| 항목 | `generate` | `sync` |
|------|-----------|--------|
| 용도 | 개별 설정 파일 생성/미리보기 | 전체 환경 일괄 동기화 |
| 출력 위치 | stdout 또는 `-o` 지정 경로 | 각 도구의 기본 설정 경로 |
| Claude 글로벌 | 미포함 | Phase 1에서 처리 |
| 사전 검증 | 없음 | `.env` 존재, 환경변수 누락 검사 |
| 권장 사용 | 디버깅, 설정 확인 | 일상 사용 |
