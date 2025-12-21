# ai-env 설정 가이드

**하나의 설정 소스**로 모든 AI 도구가 동일한 MCP 서버와 환경변수를 공유하도록 설정합니다.

## 초기 설정

### 1. 의존성 설치

```bash
cd ai-env
uv sync
```

### 2. 환경변수 설정

`.env` 파일을 생성하고 필요한 값을 입력합니다:

```bash
vi .env
```

`.env` 파일 내용:

```bash
# AI API 키
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...

# GitHub
GITHUB_GLASSLEGO_TOKEN=ghp_...    # Public GitHub (glasslego)
GITHUB_KAKAO_TOKEN=ghp_...        # Kakao Enterprise GitHub

# Jira & Confluence
JIRA_URL=https://jira.daumkakao.com
JIRA_PERSONAL_TOKEN=...
CONFLUENCE_URL=https://wiki.daumkakao.com
CONFLUENCE_PERSONAL_TOKEN=...

# 검색/메모리 (선택)
BRAVE_API_KEY=...
MEM0_API_KEY=...

# Kakao 내부 서비스 (SSE)
KKOTO_MCP_URL=http://...
CDP_MCP_URL=http://...
BROWSERBASE_MCP_URL=http://...
```

### 3. 설정 확인

```bash
uv run ai-env secrets           # 등록된 환경변수 확인 (마스킹됨)
uv run ai-env secrets --show    # 실제 값 확인
uv run ai-env status            # 현재 상태 확인
```

### 4. 모든 설정 동기화

```bash
uv run ai-env sync --dry-run    # 미리보기
uv run ai-env sync              # 전체 동기화
```

## 생성되는 파일들

### Desktop 앱 설정

| 파일 경로 | 용도 |
|----------|------|
| `~/Library/Application Support/Claude/claude_desktop_config.json` | Claude Desktop |
| `~/Library/Application Support/ChatGPT/config.json` | ChatGPT Desktop |
| `~/.codex/codex.config.json` | Codex Desktop |
| `~/.gemini/antigravity/mcp_config.json` | Antigravity |

### CLI 글로벌 설정

| 파일 경로 | 용도 |
|----------|------|
| `~/.claude/settings.json` | Claude Code 글로벌 |
| `~/.claude/CLAUDE.md` | Claude Code 에이전트 지침 |
| `~/.claude/commands/` | Claude Code 슬래시 커맨드 |
| `~/.claude/skills/` | Claude Code 스킬 |
| `~/.codex/config.toml` | Codex 글로벌 |
| `~/.codex/AGENTS.md` | Codex 에이전트 지침 |
| `~/.gemini/settings.json` | Gemini CLI 글로벌 |
| `~/.gemini/GEMINI.md` | Gemini CLI 에이전트 지침 |

### CLI 로컬 설정 (프로젝트별)

| 파일 경로 | 용도 |
|----------|------|
| `.claude/settings.glocal.json` | Claude Code 로컬 (MCP generator 생성) |
| `.codex/config.toml` | Codex 로컬 |
| `.gemini/settings.local.json` | Gemini CLI 로컬 |
| `generated/shell_exports.sh` | Shell export + agent fallback 함수 |

## 글로벌 vs 로컬

**글로벌** (`~/.claude/` 등): 모든 프로젝트에서 공통 사용.
**로컬** (`./.claude/` 등): 이 프로젝트에서만 사용. 프로젝트별 커스터마이징.

일반적으로 **글로벌 설정만 사용**하면 됩니다.

## GitHub 두 개 사용하기

`github` (Public GitHub, glasslego)와 `github-kakao` (Kakao Enterprise) 두 MCP 서버가 동시 활성화되어 AI 도구에서 양쪽 모두 접근 가능합니다.

- `GITHUB_GLASSLEGO_TOKEN`: Public GitHub용
- `GITHUB_KAKAO_TOKEN`: Kakao Enterprise GitHub용

## MCP 서버 추가

`config/mcp_servers.yaml`에 항목 추가:

```yaml
mcp_servers:
  my-new-server:
    enabled: true
    type: stdio  # 또는 sse
    command: docker
    args: [run, -i, --rm, my-mcp-image]
    env_keys: [MY_API_KEY]
    targets:
      - claude_desktop
      - claude_local
      - gemini
```

재동기화: `uv run ai-env sync`

## 트러블슈팅

### Desktop 앱이 설정을 인식 못함
1. 앱 완전 종료 (Cmd+Q) → 재시작
2. 설정 파일 경로 확인: `ls -la ~/Library/Application\ Support/Claude/`

### MCP 서버 연결 실패
1. 환경변수 확인: `uv run ai-env secrets`
2. Docker 이미지 확인: `docker pull <image>`
3. 건강 검사: `uv run ai-env doctor`
