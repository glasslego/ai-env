# MCP Config Generator Skill

이 skill은 다양한 AI 클라이언트용 MCP 설정 파일을 생성합니다.

## 지원 대상

| 클라이언트 | 설정 형식 | 출력 경로 |
|-----------|----------|----------|
| Claude Desktop | JSON | ~/Library/Application Support/Claude/claude_desktop_config.json |
| Antigravity | JSON | ~/.gemini/antigravity/mcp_config.json |
| Claude Code (local) | JSON | .claude/settings.local.json |
| Codex | TOML | .codex/config.toml |
| Gemini CLI | JSON | .gemini/settings.local.json |

## 설정 소스

1. **config/mcp_servers.yaml**: MCP 서버 정의
2. **.env**: 환경변수 및 토큰

## MCP 서버 타입

### STDIO (Docker/NPX)
```yaml
github:
  enabled: true
  type: stdio
  command: docker
  args: [run, -i, --rm, ...]
  env_keys: [GITHUB_GLASSLEGO_TOKEN]
  targets: [claude_desktop, antigravity]
```

### SSE (Server-Sent Events)
```yaml
kkoto-mcp:
  enabled: true
  type: sse
  url_env: KKOTO_MCP_URL
  targets: [antigravity]
```

## 사용법

```bash
uv run ai-env sync
```
