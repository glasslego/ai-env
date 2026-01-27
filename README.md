# ai-env

Claude, Gemini, Codex 등 여러 AI 도구의 MCP 서버와 설정을 한 곳에서 관리합니다.

## 빠른 시작

```bash
git clone <repository-url> ai-env && cd ai-env
uv sync
cp .env.example .env   # API 키 입력
uv run ai-env sync     # 전체 동기화
```

## 주요 명령어

```bash
ai-env status               # 전체 상태 확인
ai-env sync                 # 전체 동기화
ai-env sync --dry-run       # 미리보기
ai-env sync --claude-only   # Claude 설정만
ai-env sync --mcp-only      # MCP 설정만
ai-env secrets              # 환경변수 목록
ai-env secrets --show       # 값 표시
ai-env generate claude-desktop  # 특정 타겟 생성 (stdout)
```

> 모든 명령어는 `uv run` 접두사 필요.

## 동작 원리

```
.env (토큰)  +  config/mcp_servers.yaml (서버 정의)
                         │
                   ai-env sync
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
  Claude Desktop    Gemini/Codex     ~/.claude/
  ChatGPT Desktop   Antigravity    (commands, skills)
```

`.env`의 토큰과 `config/mcp_servers.yaml`의 서버 정의를 조합해서 각 AI 도구별 설정 파일을 자동 생성합니다.

## 동기화 대상

| 대상 | 출력 경로 |
|------|----------|
| Claude Desktop | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| ChatGPT Desktop | `~/Library/Application Support/ChatGPT/config.json` |
| Claude Code (글로벌) | `~/.claude/settings.json`, `CLAUDE.md`, `commands/`, `skills/` |
| Antigravity | `~/.gemini/antigravity/mcp_config.json` |
| Gemini CLI | `~/.gemini/settings.json` |
| Codex CLI | `~/.codex/config.toml` |

## MCP 서버 추가

`config/mcp_servers.yaml`에 항목을 추가하고 `ai-env sync`를 실행합니다.

```yaml
my-server:
  enabled: true
  type: stdio              # stdio 또는 sse
  command: docker
  args: [run, -i, --rm, my-image]
  env_keys: [MY_TOKEN]     # .env에서 가져올 키
  targets:                 # 배포할 대상
    - claude_desktop
    - antigravity
    - claude_local
```

SSE 서버는 `url_env`로 URL을 지정합니다. Desktop 앱(Claude/ChatGPT)은 stdio만 지원합니다.

## 개발

```bash
uv sync --all-extras && pre-commit install
uv run pytest              # 테스트
uv run ruff check .        # 린트
uv run mypy src/           # 타입 체크
```

## 라이선스

MIT
