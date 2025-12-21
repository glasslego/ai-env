# 통합된 서비스 목록

ai-env에서 관리하는 모든 MCP 서버와 연동 서비스 목록입니다.

## GitHub

### github
- **대상**: Public GitHub (glasslego)
- **URL**: https://github.com/glasslego
- **환경변수**: `GITHUB_GLASSLEGO_TOKEN`
- **용도**: 개인 프로젝트, 오픈소스

## Atlassian

### jira-wiki-mcp
- **대상**: Jira & Confluence
- **환경변수**:
  - `JIRA_URL`
  - `JIRA_PERSONAL_TOKEN`
  - `CONFLUENCE_URL`
  - `CONFLUENCE_PERSONAL_TOKEN`
- **용도**: 이슈 관리, 문서 검색/작성

## Notion

### notion
- **대상**: Notion Workspace
- **환경변수**: `NOTION_API_TOKEN`
- **용도**: 페이지/데이터베이스 관리, 회의록 작성
- **가이드**: `NOTION_SETUP.md`
- **주의**: Integration에 명시적으로 페이지 공유 필요

## 개발 도구

### playwright
- **타입**: NPX 기반
- **용도**: 웹 브라우저 자동화, 스크린샷, 테스트
- **환경변수**: 없음

### sequential-thinking
- **타입**: NPX 기반
- **용도**: 복잡한 추론 작업을 단계별로 수행
- **환경변수**: 없음

## Kakao 내부 서비스 (SSE)

### kkoto-mcp
- **타입**: SSE
- **환경변수**: `KKOTO_MCP_URL`
- **용도**: 카카오 내부 서비스 연동

### cdp-mcp-server
- **타입**: SSE
- **환경변수**: `CDP_MCP_URL`
- **용도**: CDP (Customer Data Platform) 연동

## 배포 대상

모든 MCP 서버는 다음 AI 도구에 자동 배포됩니다:

| 서비스 | Desktop | CLI 글로벌 | CLI 로컬 |
|--------|---------|-----------|----------|
| **github** | ✅ Claude<br>✅ ChatGPT<br>✅ Antigravity | ✅ | ✅ |
| **jira-wiki-mcp** | ✅ Claude<br>✅ ChatGPT<br>✅ Antigravity | ✅ | ✅ |
| **notion** | ✅ Claude<br>✅ ChatGPT<br>✅ Antigravity | ✅ | ✅ |
| **playwright** | ✅ Claude | ✅ Codex<br>✅ Gemini | ✅ |
| **sequential-thinking** | ✅ Antigravity | - | ✅ |
| **kkoto-mcp** | ✅ Antigravity | ✅ Gemini | ✅ |
| **cdp-mcp-server** | ✅ Antigravity | ✅ Gemini | ✅ |

## 빠른 참조

### 환경변수 설정

`.env` 파일을 생성하고 편집:

```bash
# .env.example을 복사
cp .env.example .env

# .env 파일 편집
vi .env
```

`.env` 파일 내용:

```bash
# AI API Keys
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...

# GitHub
GITHUB_GLASSLEGO_TOKEN=ghp_...

# Jira & Confluence
JIRA_URL=https://jira.daumkakao.com
JIRA_PERSONAL_TOKEN=...
CONFLUENCE_URL=https://wiki.daumkakao.com
CONFLUENCE_PERSONAL_TOKEN=...

# Notion
NOTION_API_TOKEN=ntn_...

# Kakao Internal (SSE)
KKOTO_MCP_URL=http://...
CDP_MCP_URL=http://...
```

동기화:

```bash
uv run ai-env sync
```

### 상태 확인

```bash
# 전체 상태
uv run ai-env status

# 환경변수 확인 (마스킹됨)
uv run ai-env secrets

# 환경변수 실제 값 확인
uv run ai-env secrets --show
```

### 개별 서비스 비활성화

`config/mcp_servers.yaml`에서:
```yaml
mcp_servers:
  notion:
    enabled: false  # Notion 비활성화
```

재동기화:
```bash
uv run ai-env sync
```

## 서비스별 가이드

- **Notion 연동**: `NOTION_SETUP.md`
- **전체 설정**: `SETUP.md`
