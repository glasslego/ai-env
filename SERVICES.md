# MCP 서비스 카탈로그

ai-env에서 관리하는 MCP 서버 목록. 설정: `config/mcp_servers.yaml`

## GitHub

| 서버 | 대상 | 환경변수 | 용도 |
|------|------|---------|------|
| **github** | Public GitHub (glasslego) | `GITHUB_GLASSLEGO_TOKEN` | 개인 프로젝트, 오픈소스 |
| **github-kakao** | Kakao Enterprise GitHub | `GITHUB_KAKAO_TOKEN` | 회사 업무, 내부 프로젝트 |

## Atlassian

| 서버 | 환경변수 | 용도 |
|------|---------|------|
| **jira-wiki-mcp** | `JIRA_URL`, `JIRA_PERSONAL_TOKEN`, `CONFLUENCE_URL`, `CONFLUENCE_PERSONAL_TOKEN` | 이슈 관리, 문서 검색/작성 |

## 개발 도구

| 서버 | 타입 | 환경변수 | 용도 |
|------|------|---------|------|
| **playwright** | stdio (npx) | - | 웹 브라우저 자동화, 테스트 |
| **desktop-commander** | stdio (npx) | - | 데스크톱 자동화 |
| **brave-search** | stdio (npx) | `BRAVE_API_KEY` | 웹 검색 |
| **context7** | stdio (npx) | - | Upstash 컨텍스트 |
| **mem0** | stdio (npx) | `MEM0_API_KEY` | 메모리 서비스 |
| **fetch** | stdio (uvx) | - | HTTP fetch |
| **filesystem** | stdio (npx) | - | 로컬 파일시스템 |
| **git** | stdio (uvx) | - | Git 작업 |
| **memory** | stdio (npx) | - | 멀티턴 메모리 |
| **sequential-thinking** | stdio (npx) | - | 단계별 추론 |
| **supabase** | stdio (npx) | - | 원격 MCP 엔드포인트 |

## Kakao 내부 서비스 (SSE)

| 서버 | 환경변수 | 용도 |
|------|---------|------|
| **kkoto-mcp** | `KKOTO_MCP_URL` | 카카오 내부 서비스 연동 |
| **cdp-mcp-server** | `CDP_MCP_URL` | CDP (Customer Data Platform) |
| **browserbase** | `BROWSERBASE_MCP_URL` | Browserbase 브라우저 래퍼 |

## 서비스 비활성화

`config/mcp_servers.yaml`에서 `enabled: false` 설정 후 `uv run ai-env sync`.
