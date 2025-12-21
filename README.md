# ai-env 🤖

AI 개발 환경 및 MCP 서버 통합 관리 도구

> **핵심 가치**: 여러 AI 도구(Claude Code, Claude Desktop, Gemini, Codex)의 설정을 한 곳에서 관리하고, 한 번의 명령으로 모든 설정을 동기화합니다.

## 주요 기능

- 🔐 **환경변수 중앙 관리**: `.env` 파일로 모든 API 키와 토큰 관리
- 🔌 **MCP 서버 통합**: 한 번 정의하면 모든 AI 도구에 자동 배포
- 🔄 **원클릭 동기화**: `ai-env sync` 한 번으로 모든 설정 적용
- 📦 **Claude Skills 관리**: 커스텀 스킬을 글로벌/로컬로 관리
- 🚀 **즉시 사용 가능**: 복잡한 JSON 설정 파일 수동 편집 불필요

## 빠른 시작

```bash
# 1. 프로젝트 클론 및 설치
cd /Users/megan/work/ai-env
uv sync

# 2. 환경변수 설정
cp .env.example .env
vi .env  # API 키 입력

# 3. 초기 설정 확인
ai-env setup

# 4. 모든 설정 동기화
ai-env sync
```

완료! 이제 Claude Code, Claude Desktop, Gemini 등 모든 AI 도구가 동일한 설정을 사용합니다.

## 사용 가이드

### 1️⃣ 환경변수 관리

#### 환경변수 설정

`.env.example`을 복사하여 `.env` 파일 생성 후 편집:

```bash
cp .env.example .env
vi .env
```

필수 환경변수:

```bash
# AI API Keys
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...

# GitHub (glasslego)
GITHUB_GLASSLEGO_TOKEN=ghp_...

# Jira/Confluence
JIRA_URL=https://jira.daumkakao.com
JIRA_PERSONAL_TOKEN=...
CONFLUENCE_URL=https://wiki.daumkakao.com
CONFLUENCE_PERSONAL_TOKEN=...

# Notion
NOTION_API_TOKEN=ntn_...
```

#### 환경변수 조회

```bash
# 마스킹된 목록 (안전)
ai-env secrets

# 실제 값 표시 (민감)
ai-env secrets --show
```

### 2️⃣ 설정 동기화

#### 전체 동기화 (권장)

```bash
# 한 번에 모든 설정 생성 및 배포
ai-env sync

# 미리보기 (파일 생성 안함)
ai-env sync --dry-run
```

이 명령이 동기화하는 항목:

| 대상 | 경로 | 내용 |
|------|------|------|
| Claude Code (글로벌) | `~/.claude/` | CLAUDE.md, settings.json, commands/, skills/ |
| Claude Desktop | `~/Library/Application Support/Claude/` | MCP 서버 설정 |
| Antigravity (Gemini) | `~/.gemini/antigravity/` | MCP 서버 설정 |
| Shell 환경변수 | `./generated/shell_exports.sh` | export 스크립트 |

#### 부분 동기화

```bash
# Claude 글로벌 설정만
ai-env sync --claude-only

# MCP 설정만
ai-env sync --mcp-only
```

### 3️⃣ 상태 확인

```bash
# 전체 상태 요약
ai-env status

# 설정 파일 내용 확인
ai-env config show
```

## 설정 파일 구조

### MCP 서버 설정 (`config/mcp_servers.yaml`)

```yaml
mcp_servers:
  # GitHub MCP
  github:
    enabled: true
    type: stdio
    command: docker
    args:
      - run
      - -i
      - --rm
      - -e
      - GITHUB_GLASSLEGO_TOKEN
      - ghcr.io/github/github-mcp-server
    env_keys:
      - GITHUB_GLASSLEGO_TOKEN
    targets:
      - claude_desktop
      - antigravity

  # Jira/Confluence MCP
  jira-wiki-mcp:
    enabled: true
    type: sse
    url_env: JIRA_WIKI_MCP_URL
    targets:
      - claude_desktop
      - claude_local
```

**타겟 종류**:
- `claude_desktop`: Claude Desktop 앱
- `claude_local`: Claude Code 로컬 프로젝트 설정
- `antigravity`: Gemini CLI

### AI 프로바이더 설정 (`config/settings.yaml`)

```yaml
providers:
  claude:
    enabled: true
    env_key: ANTHROPIC_API_KEY
  gemini:
    enabled: true
    env_key: GOOGLE_API_KEY
  codex:
    enabled: true
    env_key: OPENAI_API_KEY
```

## 디렉토리 구조

```
ai-env/
├── .env                      # 환경변수/시크릿 (gitignored)
├── .env.example              # 환경변수 템플릿
│
├── config/                   # 설정 정의 (YAML, git 추적)
│   ├── settings.yaml         # AI 프로바이더 설정
│   ├── mcp_servers.yaml      # MCP 서버 정의
│   └── github/               # GitHub 프로필 (멀티 계정)
│
├── src/ai_env/               # Python 패키지
│   ├── cli.py                # CLI 진입점
│   ├── core/
│   │   ├── config.py         # Pydantic 설정 모델
│   │   └── secrets.py        # 환경변수 관리
│   └── mcp/
│       └── generator.py      # MCP 설정 생성기
│
├── .claude/                  # Claude Code 설정
│   ├── CLAUDE.md             # 프로젝트별 지시사항
│   ├── settings.local.json   # 로컬 설정 (gitignored)
│   ├── commands/             # 슬래시 커맨드 → ~/.claude/commands/
│   ├── skills/               # 스킬 모음 → ~/.claude/skills/
│   └── global/               # 글로벌 템플릿
│       ├── CLAUDE.md         # → ~/.claude/CLAUDE.md
│       └── settings.json.template  # → ~/.claude/settings.json
│
├── generated/                # 생성된 설정 (gitignored)
│   ├── claude_desktop_config.json
│   ├── mcp_config.json
│   └── shell_exports.sh
│
└── tests/                    # 테스트
```

## 고급 사용법

### Claude Skills 관리

ai-env에는 여러 유용한 스킬이 포함되어 있습니다:

**내장 스킬**:
- `jira-weekly-update`: JIRA 주간 보고서 생성
- `wiki-manager`: Confluence 위키 관리
- `trino-analyst`: Trino DB 쿼리 분석
- `skill-creator`: 새 스킬 생성 가이드

**스킬 위치**:
- **프로젝트 스킬**: `.claude/skills/` (ai-env 프로젝트에서만 사용)
- **글로벌 스킬**: `~/.claude/skills/` (모든 프로젝트에서 사용)

**스킬 동기화**:

```bash
# .claude/skills/ → ~/.claude/skills/ 동기화
ai-env sync --claude-only

# Claude Code가 자동으로 ~/.claude/skills/ 로드
```

### 환경변수 치환

MCP 서버 설정에서 `${VAR}` 문법 사용:

```yaml
mcp_servers:
  my-server:
    args:
      - --host
      - ${TRINO_HOST}  # .env의 TRINO_HOST 값으로 치환
```

### 멀티 GitHub 계정 관리

`config/github/profiles.json`에서 여러 GitHub 계정 관리:

```json
{
  "profiles": [
    {
      "name": "glasslego",
      "host": "https://github.com",
      "token_env": "GITHUB_GLASSLEGO_TOKEN"
    }
  ]
}
```

## 개발

### 개발 환경 설정

```bash
# 개발 의존성 포함 설치
uv sync --all-extras

# pre-commit 훅 설치
pre-commit install
```

### 테스트

```bash
# 전체 테스트
uv run pytest

# 커버리지 포함
uv run pytest --cov

# 특정 테스트
uv run pytest tests/test_config.py
```

### 코드 품질

```bash
# 린트 (ruff)
uv run ruff check .

# 포맷팅
uv run ruff format .

# 타입 체크
uv run mypy src/
```

## 문제 해결

### .env 파일이 없다는 에러

```bash
cp .env.example .env
vi .env  # 필수 값 입력
```

### MCP 서버가 작동하지 않음

1. 환경변수 확인: `ai-env secrets --show`
2. 설정 상태 확인: `ai-env status`
3. 재동기화: `ai-env sync`
4. Claude Desktop 재시작

### 글로벌 설정이 적용되지 않음

```bash
# 설정 재동기화
ai-env sync --claude-only

# Claude Code 재시작
```

## 관련 문서

- **[SETUP.md](./SETUP.md)**: 상세 설치 및 설정 가이드
- **[SERVICES.md](./SERVICES.md)**: 지원하는 서비스 목록
- **[NOTION_SETUP.md](./NOTION_SETUP.md)**: Notion API 설정

## 라이선스

MIT
