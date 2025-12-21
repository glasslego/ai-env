# Codex 로컬 설정

이 디렉토리는 **ai-env 프로젝트 자체**에서 Codex를 사용할 때의 설정입니다.

## 파일

- `config.toml`: 이 프로젝트에서만 사용하는 MCP 서버 설정 (자동 생성됨)

## 글로벌 설정

시스템 전체에서 사용하는 Codex 설정은 `~/.codex/config.toml`에 있습니다.

## 생성 방법

```bash
uv run ai-env sync
```

이 명령을 실행하면 `config/mcp_servers.yaml`의 설정을 기반으로:
- 글로벌: `~/.codex/config.toml`
- 로컬: `./.codex/config.toml`

두 파일 모두 자동 생성됩니다.
