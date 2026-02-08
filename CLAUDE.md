# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

ai-env는 여러 AI 개발 환경(Claude, Gemini, Codex, Antigravity)과 MCP 서버 설정을 통합 관리하는 도구입니다. 토큰을 중앙화하여 관리하고, 여러 AI CLI 도구의 설정을 동기화합니다.

## 개발 명령어

```bash
# 의존성 설치
uv sync

# 개발 의존성 포함 설치
uv sync --all-extras
pre-commit install  # Git 훅 설정

# CLI 실행
uv run ai-env --help
uv run ai-env status

# 테스트 실행
uv run pytest                    # 전체 테스트
uv run pytest tests/test_ai_env.py  # 단일 파일
uv run pytest -k test_config     # 특정 테스트만

# 커버리지 포함 테스트
uv run pytest --cov
uv run pytest --cov --cov-report=html  # HTML 리포트

# 린트
uv run ruff check .
uv run ruff check . --fix        # 자동 수정

# 타입 체크
uv run mypy src/

# 코드 포맷
uv run ruff format .
```

## 아키텍처

### 핵심 모듈

**config.py** (`src/ai_env/core/config.py`)
- Pydantic 모델로 설정 검증
- `Settings`: AI 프로바이더와 출력 경로를 포함한 메인 설정
- `MCPConfig`: MCP 서버 정의
- `load_settings()`, `load_mcp_config()`: `config/` 디렉토리의 YAML 설정 로드

**secrets.py** (`src/ai_env/core/secrets.py`)
- `SecretsManager`: `.env` 파일의 환경변수 관리
- `python-dotenv`로 읽기/쓰기
- `${VAR}` 문법으로 변수 치환 지원
- `export_to_shell()`: bash export 스크립트 생성

**generator.py** (`src/ai_env/mcp/generator.py`)
- `MCPConfigGenerator`: 각 타겟별 MCP 설정 생성
- 타겟(claude_desktop, antigravity 등)에 따라 서버 설정 빌드
- stdio(Docker/npx)와 SSE 서버 타입 모두 처리
- SecretsManager의 환경변수 치환

**cli.py** (`src/ai_env/cli.py`)
- Click 기반 CLI, 명령어 그룹: `secrets`, `config`, `generate`, `sync`, `status`, `setup`
- Rich로 터미널 UI(테이블, 색상) 구현

**sync.py** (`src/ai_env/core/sync.py`)
- `sync_claude_global_config()`: Claude Code 글로벌 설정 동기화
- `.claude/global/` → `~/.claude/` 동기화 (CLAUDE.md, settings.json.template)
- `.claude/commands/` → `~/.claude/commands/` (.md 파일만)
- skills 동기화: personal(`.claude/skills/`) + team(`cde-*skills/` 심링크) 병합 → `~/.claude/skills/`
- `settings.json.template`에서 환경변수 치환 후 `settings.json` 생성

### 설정 흐름

1. 사용자가 `ai-env secrets set KEY VALUE`로 `.env`에 시크릿 저장
2. `config/`의 YAML 파일들이 프로바이더와 MCP 서버 정의
3. Generator가 둘을 읽어서 타겟별 설정 생성:
   - `claude_desktop_config.json`: Claude Desktop용
   - `mcp_config.json`: Antigravity용
   - `settings.local.json`: Claude Code 로컬 프로젝트용
   - `config.toml`: Codex용
   - Shell export 스크립트
4. `ai-env sync`가 모든 설정을 목적지 경로에 저장

### MCP 서버 타겟

`config/mcp_servers.yaml`의 각 MCP 서버는 `targets` 리스트로 배포 대상을 명시합니다.

**타겟 → 출력 경로:**
| 타겟 | 출력 경로 | 설명 |
|------|----------|------|
| `claude_desktop` | `~/Library/Application Support/Claude/claude_desktop_config.json` | Claude Desktop 앱 (stdio만 지원) |
| `chatgpt_desktop` | `~/Library/Application Support/ChatGPT/config.json` | ChatGPT Desktop 앱 |
| `antigravity` | `~/.gemini/antigravity/mcp_config.json` | Gemini Antigravity |
| `claude_local` | `./.claude/settings.glocal.json` | 프로젝트용 템플릿 (glocal) |
| `claude_global` | `~/.claude/settings.json` | 글로벌 Claude Code |
| `codex` | `~/.codex/config.toml`, `./.codex/config.toml` | Codex CLI (글로벌/로컬) |
| `gemini` | `~/.gemini/settings.json`, `./.gemini/settings.local.json` | Gemini CLI (글로벌/로컬) |

**참고**: SSE 타입 서버는 Claude Desktop/ChatGPT Desktop에서 지원하지 않음 (stdio만 지원)

### 환경변수 치환

`${VAR}` 문법으로 환경변수 치환 가능:
- `mcp_servers.yaml`: MCP 서버 설정의 `args`에서 사용
- `.claude/global/settings.json.template`: Claude Code 설정에서 사용

Generator/Sync 동작:
1. SecretsManager에서 변수 조회 (`.env` 확인 후 `os.environ` 확인)
2. MCP 설정: `args`에서 치환하거나 `env_keys`로 직접 전달
3. SSE 서버: `url_env` 키에서 URL 환경변수명 읽기
4. settings.json: 템플릿에서 치환 후 생성

**환경변수 키 매핑** (`generator.py`의 `ENV_KEY_MAPPING`):
일부 MCP 서버는 다른 키 이름을 요구함:
- `GITHUB_GLASSLEGO_TOKEN` → `GITHUB_PERSONAL_ACCESS_TOKEN` (GitHub MCP)
- `GITHUB_KAKAO_TOKEN` → `GITHUB_PERSONAL_ACCESS_TOKEN` (GitHub Kakao MCP)

## 프로젝트 구조 규칙

- `config/`: YAML 설정 템플릿 (git에 커밋)
- `generated/`: 생성된 설정들 (gitignore)
- `.env`: 시크릿 파일 (gitignore)
- `src/ai_env/`: AI 환경 관리 메인 패키지
  - `core/`: 설정, 시크릿, 동기화 관리 (config.py, secrets.py, sync.py)
  - `mcp/`: MCP 설정 생성 (generator.py)
- `.claude/`: Claude Code 설정 소스 (동기화 대상)
  - `global/`: 글로벌 설정 (CLAUDE.md, settings.json.template)
  - `commands/`: 슬래시 커맨드
  - `skills/`: 개인 스킬 (personal)
  - `settings.glocal.json`: 다른 프로젝트용 템플릿 (git 추적)
  - `settings.local.json`: 이 프로젝트 전용 (gitignore, 수동 관리)
- `cde-*skills` 심링크: 팀 공유 스킬 (team) - `cde-skills`, `cde-ranking-skills` 등
- `tests/`: pytest 테스트

### glocal vs local 설정

```
.claude/
├── settings.glocal.json  ← sync로 생성, git 추적, 다른 프로젝트용 템플릿
└── settings.local.json   ← 수동 관리, gitignore, 이 프로젝트 전용 permissions
```

- **glocal**: "global template for local" - MCP 설정 + 기본 permissions
- **local**: 프로젝트별 커스텀 permissions (sync가 덮어쓰지 않음)

### skills 동기화 구조

`ai-env sync`는 personal + team 스킬을 합쳐서 `~/.claude/skills/`에 동기화:

```
personal: .claude/skills/*/             ← 이 저장소의 개인 스킬
team:     cde-*skills/ (symlink) →      ← 팀 공유 스킬 저장소 심링크
          ├── .claude/skills/*/SKILL.md   (nested 구조 우선)
          └── */SKILL.md                  (flat 구조 폴백)
                    ↓
          ~/.claude/skills/             ← 최종 병합 결과
```

팀 스킬 심링크는 `cde-`로 시작하고 `skills`로 끝나는 이름 패턴을 따름.

## 주요 개발 시나리오

### 새 MCP 서버 추가

1. `config/mcp_servers.yaml`에 항목 추가
2. `type`(stdio 또는 sse), `command`/`args` 또는 `url_env` 지정
3. 필요시 `env_keys` 리스트 작성
4. `targets` 리스트 설정
5. `uv run ai-env sync`로 설정 재생성

### 새 AI 프로바이더 추가

1. `config/settings.yaml`의 `providers`에 항목 추가
2. 필요시 `MCPConfigGenerator`에 생성 메서드 구현
3. 필요시 `cli.py`에 새 명령어 추가

### 설정 생성/동기화

```bash
# 미리보기 (파일 쓰지 않음)
uv run ai-env sync --dry-run

# 전체 동기화 (Claude 글로벌 + 모든 MCP 설정)
uv run ai-env sync

# Claude 글로벌 설정만 동기화 (CLAUDE.md, commands/, skills/, settings.json)
uv run ai-env sync --claude-only

# MCP 설정만 동기화 (Claude Desktop, Gemini, Codex 등)
uv run ai-env sync --mcp-only

# 특정 타겟만 생성 (stdout 출력)
uv run ai-env generate claude-desktop
uv run ai-env generate antigravity
uv run ai-env generate shell
```

## 중요 사항

- `.env`는 절대 커밋하지 않음 (민감한 토큰 포함)
- `generated/` 디렉토리는 gitignore 처리됨
- 모든 경로 확장(~, 환경변수)은 config.py의 `expand_path()`로 처리
- SecretsManager는 안전한 시크릿 표시를 위해 `list_masked()` 제공
- CLI는 Rich Console 사용 - `print()` 대신 `console.print()` 사용
- CLI 진입점: `uv run ai-env`
