# ai-env 설정 가이드

이 가이드는 ai-env를 사용하여 모든 AI 도구가 동일한 환경을 공유하도록 설정하는 방법을 설명합니다.

## 목표

**하나의 설정 소스**로 다음 도구들이 모두 같은 MCP 서버와 환경변수를 사용:

- 🖥️ **Desktop 앱**: Claude Desktop, ChatGPT Desktop, Antigravity
- 💻 **CLI 도구 (글로벌)**: Claude Code, Codex, Gemini CLI
- 📁 **CLI 도구 (로컬)**: 각 프로젝트별 설정

## 초기 설정

### 1. 의존성 설치

```bash
cd /Users/megan/work/ai-env
uv sync
```

### 2. 환경변수 설정

`.env.example`을 복사하여 `.env` 파일을 만들고 필요한 값을 입력합니다:

```bash
# .env.example을 복사
cp .env.example .env

# .env 파일 편집
vi .env
```

`.env` 파일 내용:

```bash
# AI API 키
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...

# GitHub Enterprise (Kakao) - 메인
GITHUB_GLASSLEGO_TOKEN=ghp_...

# GitHub glasslego - 개인 프로젝트용
GITHUB_GLASSLEGO_TOKEN=ghp_...

# Jira & Confluence
JIRA_URL=https://jira.daumkakao.com
JIRA_PERSONAL_TOKEN=...
CONFLUENCE_URL=https://wiki.daumkakao.com
CONFLUENCE_PERSONAL_TOKEN=...

# Notion
NOTION_API_TOKEN=ntn_...

# CDP MCP 서버 (SSE)
KKOTO_MCP_URL=http://...
CDP_MCP_URL=http://...
```

### 3. 설정 확인

```bash
# 등록된 환경변수 확인 (마스킹됨)
uv run ai-env secrets

# 실제 값 확인
uv run ai-env secrets --show

# 현재 상태 확인
uv run ai-env status
```

### 4. 모든 설정 동기화

```bash
# 실제로 파일 생성하기 전 미리보기
uv run ai-env sync --dry-run

# 모든 AI 도구 설정 생성 및 배포
uv run ai-env sync
```

## 생성되는 파일들

### Desktop 앱 설정

| 파일 경로 | 용도 |
|----------|------|
| `~/Library/Application Support/Claude/claude_desktop_config.json` | Claude Desktop |
| `~/Library/Application Support/ChatGPT/config.json` | ChatGPT Desktop |
| `~/.gemini/antigravity/mcp_config.json` | Antigravity |

### CLI 글로벌 설정 (시스템 전체)

| 파일 경로 | 용도 |
|----------|------|
| `~/.claude/settings.json` | Claude Code 글로벌 |
| `~/.codex/config.toml` | Codex 글로벌 |
| `~/.gemini/settings.json` | Gemini CLI 글로벌 |

### CLI 로컬 설정 (이 프로젝트 전용)

| 파일 경로 | 용도 |
|----------|------|
| `./.claude/settings.local.json` | Claude Code 로컬 |
| `./.codex/config.toml` | Codex 로컬 |
| `./.gemini/settings.local.json` | Gemini CLI 로컬 |

### 기타

| 파일 경로 | 용도 |
|----------|------|
| `./generated/shell_exports.sh` | Shell export 스크립트 |

## MCP 서버 추가하기

### 1. config/mcp_servers.yaml 수정

```yaml
mcp_servers:
  my-new-server:
    enabled: true
    type: stdio  # 또는 sse
    command: docker  # 또는 npx
    args:
      - run
      - -i
      - --rm
      - my-mcp-image
    env_keys:
      - MY_API_KEY
    targets:
      - claude_desktop
      - claude_local
      - gemini
```

### 2. 필요한 환경변수 등록

```bash
uv run ai-env secrets set MY_API_KEY "..."
```

### 3. 재동기화

```bash
uv run ai-env sync
```

이제 모든 AI 도구가 새 MCP 서버를 사용할 수 있습니다!

## 일상적인 사용

### MCP 서버 설정 변경 후

```bash
# config/mcp_servers.yaml 수정
vim config/mcp_servers.yaml

# 재동기화
uv run ai-env sync
```

### 환경변수 추가/수정

```bash
# .env 파일 편집
vi .env

# 새로운 환경변수 추가
# NEW_TOKEN=...

# config/mcp_servers.yaml에서 사용
# env_keys에 NEW_TOKEN 추가

# 재동기화
uv run ai-env sync
```

### 특정 도구만 설정 생성

```bash
# Claude Desktop만
uv run ai-env generate claude-desktop

# Antigravity만
uv run ai-env generate antigravity

# Shell exports만
uv run ai-env generate shell
```

## 설정 구조 이해하기

### 타겟 시스템

`config/mcp_servers.yaml`의 각 MCP 서버는 `targets` 리스트로 어느 도구에 배포될지 지정:

- `claude_desktop`: Claude Desktop 앱
- `chatgpt_desktop`: ChatGPT Desktop 앱
- `antigravity`: Antigravity (Gemini MCP 클라이언트)
- `claude_local`: Claude Code 로컬 프로젝트
- `codex`: Codex
- `gemini`: Gemini CLI

### 글로벌 vs 로컬

**글로벌 설정** (`~/.claude/` 등):
- 모든 프로젝트에서 공통으로 사용
- Claude Code를 어디서 실행하든 동일한 MCP 서버 접근

**로컬 설정** (`./.claude/` 등):
- 이 프로젝트(ai-env)에서만 사용
- 테스트나 프로젝트별 커스터마이징 가능

일반적으로는 **글로벌 설정만 사용**하면 됩니다. 로컬 설정은 ai-env 프로젝트 자체 개발 시에만 활용됩니다.

### Notion 사용하기

Notion MCP 서버를 통해 AI 도구에서 Notion 페이지와 데이터베이스에 접근할 수 있습니다.

**주요 기능**:
- 페이지 검색 및 조회
- 데이터베이스 쿼리 및 필터링
- 페이지/데이터베이스 생성 및 수정
- 블록(content) 읽기/쓰기

**사용 예시**:
```
User: "Notion에서 'Meeting Notes' 페이지 찾아서 내용 요약해줘"
User: "Tasks 데이터베이스에 새 항목 추가: '문서 작성'"
User: "오늘 회의록을 Notion에 정리해줘"
```

**상세 가이드**: `NOTION_SETUP.md` 참조

### GitHub 두 개 사용하기

이 프로젝트는 **Kakao GitHub**(메인)과 **glasslego GitHub** 두 개를 동시에 지원합니다:

**github-kakao** (메인):
- Kakao Enterprise GitHub (`https://github.daumkakao.com`)
- 회사 업무, 내부 프로젝트용
- 환경변수: `GITHUB_GLASSLEGO_TOKEN`, `

**github-glasslego**:
- Public GitHub (`https://github.com/glasslego`)
- 개인 프로젝트, 오픈소스 기여용
- 환경변수: `GITHUB_GLASSLEGO_TOKEN`

두 MCP 서버가 동시에 활성화되어, AI 도구에서 두 GitHub 모두 접근 가능합니다.

**예시 - Claude Code에서 사용**:
```
User: "github-kakao에서 최근 PR 목록 보여줘"
Claude: [Kakao GitHub의 PR 목록 조회]

User: "github-glasslego에서 내 stargazer 많은 레포 알려줘"
Claude: [glasslego GitHub의 레포 목록 조회]
```

## 트러블슈팅

### Desktop 앱이 설정을 인식 못함

1. 앱 완전 종료 (Cmd+Q)
2. 설정 파일 경로 확인
3. 앱 재시작

### MCP 서버 연결 실패

1. 환경변수 확인: `uv run ai-env secrets list`
2. Docker 이미지 확인: `docker pull <image>`
3. 로그 확인 (각 앱의 개발자 도구)

### 설정 파일 위치 확인

```bash
# Claude Desktop
ls -la ~/Library/Application\ Support/Claude/

# Antigravity
ls -la ~/.gemini/antigravity/

# Claude Code 글로벌
ls -la ~/.claude/
```

## 팁

### Shell에서 환경변수 로드

```bash
source ./generated/shell_exports.sh
```

### 설정 백업

```bash
# .env 파일 백업 (중요!)
cp .env .env.backup

# 또는 안전한 곳에 저장
cp .env ~/Dropbox/ai-env.backup
```

### pre-commit hook 활성화

```bash
uv run pre-commit install
```

이제 git commit 시 자동으로 코드 품질 검사가 실행됩니다.
