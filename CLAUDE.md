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

# CLI 실행 (두 가지 방법 - ai-env 또는 축약형 aie)
uv run ai-env --help
uv run aie status  # 축약형

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
- `.claude/skills/` → `~/.claude/skills/` (서브디렉토리 전체)
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

시스템이 지원하는 "타겟"들 (각기 다른 AI 도구):
- `claude_desktop`: 글로벌 Claude Desktop 앱
- `claude_local`: 프로젝트별 Claude Code 설정
- `antigravity`: Gemini의 MCP 클라이언트
- `codex`: OpenAI Codex CLI
- `gemini`: Google Gemini CLI

`config/mcp_servers.yaml`의 각 MCP 서버는 `targets` 리스트로 지원 타겟을 명시합니다.

### 환경변수 치환

`${VAR}` 문법으로 환경변수 치환 가능:
- `mcp_servers.yaml`: MCP 서버 설정의 `args`에서 사용
- `.claude/global/settings.json.template`: Claude Code 설정에서 사용

Generator/Sync 동작:
1. SecretsManager에서 변수 조회 (`.env` 확인 후 `os.environ` 확인)
2. MCP 설정: `args`에서 치환하거나 `env_keys`로 직접 전달
3. SSE 서버: `url_env` 키에서 URL 환경변수명 읽기
4. settings.json: 템플릿에서 치환 후 생성

## 프로젝트 구조 규칙

- `config/`: YAML 설정 템플릿 (git에 커밋)
- `generated/`: 생성된 설정들 (gitignore)
- `.env`: 시크릿 파일 (gitignore)
- `src/ai_env/`: AI 환경 관리 메인 패키지
  - `core/`: 설정, 시크릿, 동기화 관리 (config.py, secrets.py, sync.py)
  - `mcp/`: MCP 설정 생성 (generator.py)
- `src/ai_assistant/`: AI 어시스턴트 유틸리티 모음
  - `notion_to_obsidian/`: Notion 내보내기를 Obsidian vault로 변환
- `.claude/`: Claude Code 설정 소스 (동기화 대상)
  - `global/`: 글로벌 설정 (CLAUDE.md, settings.json.template)
  - `commands/`: 슬래시 커맨드
  - `skills/`: 커스텀 스킬
- `tests/`: pytest 테스트

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

## 추가 도구

### Notion to Obsidian 변환기

`src/ai_assistant/notion_to_obsidian/`: Notion 내보내기를 Obsidian vault로 변환하는 독립 도구

**사용법**:
```bash
# 기본 변환
python -m ai_assistant.notion_to_obsidian.cli /path/to/notion/export /path/to/obsidian/vault

# 미리보기 (파일 쓰지 않음)
python -m ai_assistant.notion_to_obsidian.cli /path/to/export /path/to/vault --dry-run

# 폴더 구조 평탄화 (모든 노트를 루트에)
python -m ai_assistant.notion_to_obsidian.cli /path/to/export /path/to/vault --flatten

# 첨부파일 제외
python -m ai_assistant.notion_to_obsidian.cli /path/to/export /path/to/vault --no-attachments
```

**주요 기능**:
- Notion 내보내기 마크다운을 Obsidian 호환 형식으로 변환
- ID가 포함된 파일/폴더 이름을 정리 (예: `Page abc123.md` → `Page.md`)
- 내부 링크를 Obsidian 위키링크로 변환 (`[[Page]]`)
- 이미지/PDF 등 첨부파일 복사
- 폴더 구조 유지 또는 평탄화 옵션

## 중요 사항

- `.env`는 절대 커밋하지 않음 (민감한 토큰 포함)
- `generated/` 디렉토리는 gitignore 처리됨
- 모든 경로 확장(~, 환경변수)은 config.py의 `expand_path()`로 처리
- SecretsManager는 안전한 시크릿 표시를 위해 `list_masked()` 제공
- CLI는 Rich Console 사용 - `print()` 대신 `console.print()` 사용
- 두 CLI 진입점 모두 작동: `ai-env` 및 `aie`(축약형)
