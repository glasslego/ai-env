# ai-env 🤖

여러 AI 도구(Claude, Gemini, Codex)의 설정을 한 곳에서 관리하는 통합 환경 도구

## 핵심 기능

- 🔐 `.env` 파일로 모든 API 키와 환경변수 중앙 관리
- 🔌 MCP 서버를 한 번 정의하면 모든 AI 도구에 자동 배포
- 🔄 `ai-env sync` 한 번으로 전체 설정 동기화
- 📦 Claude 커스텀 스킬 글로벌/로컬 관리

## 빠른 시작

```bash
# 1. 설치
git clone <repository-url> ai-env && cd ai-env
uv sync

# 2. 환경변수 설정 (.env 파일 생성 및 편집)
cp .env.example .env
vi .env  # API 키 입력

# 3. 초기 설정 확인
uv run ai-env setup

# 4. 전체 동기화
uv run ai-env sync
```

완료! 모든 AI 도구가 동일한 설정을 사용합니다.

> **💡 Tip**: `ai-env` 또는 축약형 `aie`로 실행 가능

## 주요 명령어

```bash
# 환경변수 조회
uv run ai-env secrets              # 마스킹된 목록
uv run ai-env secrets --show       # 실제 값 표시

# 설정 동기화
uv run ai-env sync                 # 전체 동기화
uv run ai-env sync --dry-run       # 미리보기
uv run ai-env sync --claude-only   # Claude만
uv run ai-env sync --mcp-only      # MCP만

# 상태 확인
uv run ai-env status               # 전체 상태
uv run ai-env config show          # 설정 내용
```

### 동기화 대상

| 대상 | 경로 | 내용 |
|------|------|------|
| Claude Code | `~/.claude/` | CLAUDE.md, settings.json, commands/, skills/ |
| Claude Desktop | `~/Library/Application Support/Claude/` | MCP 설정 |
| Gemini (Antigravity) | `~/.gemini/antigravity/` | MCP 설정 |
| Shell | `./generated/shell_exports.sh` | export 스크립트 |

## 설정 파일

### MCP 서버 (`config/mcp_servers.yaml`)

```yaml
mcp_servers:
  github:
    enabled: true
    type: stdio          # stdio 또는 sse
    command: docker
    args:
      - run
      - -i
      - --rm
      - ghcr.io/github/github-mcp-server
    env_keys:
      - GITHUB_GLASSLEGO_TOKEN
    targets:             # 배포 대상
      - claude_desktop
      - antigravity
      - claude_local

  # SSE 서버 예시
  my-sse-server:
    enabled: true
    type: sse
    url_env: MY_SSE_URL
    targets:
      - antigravity
```

**타겟**: `claude_desktop`, `claude_local`, `antigravity`, `codex`, `gemini`

### 환경변수 (`.env`)

```bash
# AI API Keys
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...

# GitHub
GITHUB_GLASSLEGO_TOKEN=ghp_...

# Jira/Confluence
JIRA_URL=https://jira.example.com
JIRA_PERSONAL_TOKEN=...
CONFLUENCE_URL=https://wiki.example.com
CONFLUENCE_PERSONAL_TOKEN=...
```

## 프로젝트 구조

```
ai-env/
├── .env                    # 환경변수 (gitignored)
├── config/                 # 설정 정의 (git 추적)
│   ├── settings.yaml       # AI 프로바이더
│   └── mcp_servers.yaml    # MCP 서버
│
├── src/ai_env/             # 메인 패키지
│   ├── cli.py              # CLI 진입점
│   ├── core/               # 설정 및 환경변수 관리
│   └── mcp/                # MCP 설정 생성
│
├── src/ai_assistant/       # 유틸리티
│   └── notion_to_obsidian/ # Notion 변환 도구
│
├── .claude/                # Claude 설정
│   ├── commands/           # 슬래시 커맨드
│   ├── skills/             # 커스텀 스킬
│   └── global/             # 글로벌 템플릿
│
└── generated/              # 생성된 설정 (gitignored)
```

## 추가 기능

### Claude Skills 관리

```bash
# 프로젝트 스킬을 글로벌로 동기화
uv run ai-env sync --claude-only
# .claude/skills/ → ~/.claude/skills/
```

포함된 스킬: `skill-creator`, `git-worktree`, `jira-weekly-update`, `trino-analyst` 등

### 환경변수 치환

설정 파일에서 `${VAR}` 문법 사용:

```yaml
args:
  - --host
  - ${MY_HOST}  # .env의 MY_HOST 값으로 치환
```

### Notion to Obsidian 변환

```bash
python -m ai_assistant.notion_to_obsidian.cli \
  /path/to/notion/export \
  /path/to/obsidian/vault
```

옵션: `--dry-run`, `--flatten`, `--no-attachments`

## 개발

```bash
# 개발 환경 설정
uv sync --all-extras
pre-commit install

# 테스트
uv run pytest                # 전체
uv run pytest --cov          # 커버리지
uv run pytest -k test_name   # 특정 테스트

# 코드 품질
uv run ruff check .          # 린트
uv run ruff format .         # 포맷
uv run mypy src/             # 타입 체크
```

## 문제 해결

| 문제 | 해결 |
|------|------|
| `.env` 파일 없음 | `cp .env.example .env` 후 편집 |
| MCP 서버 미작동 | `ai-env status` → `ai-env sync` → AI 도구 재시작 |
| Docker MCP 오류 | `docker ps` 확인, 이미지 수동 pull |
| 글로벌 설정 미적용 | `ai-env sync --claude-only` → Claude 재시작 |

## 라이선스

MIT
