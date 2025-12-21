# ai-env 프로젝트 개요

AI 개발 환경(Claude, Gemini, Codex, Antigravity) 및 MCP 서버 토큰을 통합 관리하는 프로젝트입니다.

## 목표
- AI CLI 도구들의 환경설정을 한 곳에서 관리
- MCP 서버 토큰을 중앙화하여 관리
- 글로벌 환경설정에 동기화

## 주요 명령어

```bash
# 상태 확인
uv run ai-env status

# 시크릿 관리
uv run ai-env secrets list
uv run ai-env secrets set KEY VALUE

# 설정 동기화
uv run ai-env sync
```

## MCP 서버

| 서버 | 타입 | 용도 |
|------|------|------|
| github | docker | GitHub Enterprise MCP |
| jira-wiki-mcp | docker | Jira/Confluence MCP |
| playwright | npx | 브라우저 자동화 |
| kkoto-mcp | sse | Kakao 내부 MCP |
| cdp-mcp-server | sse | CDP MCP |

## Active Technologies
- Python 3.11+
- uv, Click, Rich, Pydantic

## Recent Changes
- Initial project setup
