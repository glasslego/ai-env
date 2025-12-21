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

# CLI 실행
uv run ai-env --help
uv run ai-env status

# 테스트 실행
uv run pytest

# 커버리지 포함 테스트
uv run pytest --cov

# 린트
uv run ruff check .

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
- Click 기반 CLI, 명령어 그룹: `secrets`, `config`, `generate`, `sync`, `status`
- Rich로 터미널 UI(테이블, 색상) 구현

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

시스템이 지원하는 "타겟"들 (각기 다른 AI 도구):
- `claude_desktop`: 글로벌 Claude Desktop 앱
- `claude_local`: 프로젝트별 Claude Code 설정
- `antigravity`: Gemini의 MCP 클라이언트
- `codex`: OpenAI Codex CLI
- `gemini`: Google Gemini CLI

`config/mcp_servers.yaml`의 각 MCP 서버는 `targets` 리스트로 지원 타겟을 명시합니다.

### 환경변수 치환

`mcp_servers.yaml`의 템플릿에서 `${VAR}` 문법 사용 가능. Generator는:
1. SecretsManager에서 변수 조회(`.env` 확인 후 `os.environ` 확인)
2. `args`에서 치환하거나 `env_keys`에 직접 사용
3. SSE 서버는 `url_env` 키에서 읽기

## 프로젝트 구조 규칙

- `config/`: YAML 설정 템플릿 (git에 커밋)
- `generated/`: 생성된 설정들 (gitignore)
- `.env`: 시크릿 파일 (gitignore)
- `src/ai_env/`: Python 패키지
  - `core/`: 설정 및 시크릿 관리
  - `mcp/`: MCP 설정 생성
  - `providers/`: AI 프로바이더별 로직 (향후)
  - `integrations/`: 외부 서비스 연동 (향후)
  - `sync/`: 백업/복원 로직 (향후)

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

### 설정 생성 테스트

```bash
# 파일 쓰지 않고 미리보기
uv run ai-env generate all --dry-run

# 특정 타겟만 생성
uv run ai-env generate claude-desktop
uv run ai-env generate antigravity
uv run ai-env generate shell

# 미리보기로 동기화
uv run ai-env sync --dry-run
```

## 중요 사항

- `.env`는 절대 커밋하지 않음 (민감한 토큰 포함)
- `generated/` 디렉토리는 gitignore 처리됨
- 모든 경로 확장(~, 환경변수)은 config.py의 `expand_path()`로 처리
- SecretsManager는 안전한 시크릿 표시를 위해 `list_masked()` 제공
- CLI는 Rich Console 사용 - `print()` 대신 `console.print()` 사용
- 두 CLI 진입점 모두 작동: `ai-env` 및 `aie`(축약형)
