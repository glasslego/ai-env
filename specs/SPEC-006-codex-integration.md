---
id: SPEC-006
title: Codex CLI Integration (Permissions & Teammate Mode)
status: implemented
created: 2025-06-01
updated: 2026-02-13
---

# SPEC-006: Codex CLI Integration (Permissions & Teammate Mode)

## 1. 개요

Codex CLI는 OpenAI의 터미널 기반 AI 코딩 에이전트다. ai-env는 Codex CLI의 TOML 설정 파일(`config.toml`)을 자동 생성하여, 권한 관리(permissions), MCP 서버 연동, 그리고 Claude Code와의 팀메이트 모드(teammate mode)를 중앙에서 통합 관리한다.

### 핵심 설계 결정

- **TOML 포맷**: Codex CLI는 JSON이 아닌 TOML을 설정 형식으로 사용한다. ai-env는 TOML 라이브러리 없이 문자열 조합으로 직접 생성한다.
- **글로벌 + 로컬 이중 생성**: 동일한 `generate_codex()` 결과를 `~/.codex/config.toml`(글로벌)과 `./.codex/config.toml`(로컬) 양쪽에 저장한다.
- **Teammate Mode**: Codex가 Claude Code의 MCP 서버에 tmux를 통해 접근하므로, Docker 기반 등 무거운 서버를 중복 기동하지 않는다.

## 2. 설정 파일 경로

| 구분 | 경로 | 용도 |
|------|------|------|
| 글로벌 | `~/.codex/config.toml` | 모든 프로젝트에 적용되는 기본 설정 |
| 로컬 | `./.codex/config.toml` | ai-env 프로젝트 내 로컬 설정 (glocal 패턴) |

`config/settings.yaml`에서 경로를 정의한다:

```yaml
outputs:
  codex_global: ~/.codex/config.toml
  codex_local: ./.codex/config.toml
```

## 3. 생성되는 TOML 구조

`generate_codex()` 메서드가 생성하는 전체 설정 구조:

```toml
# === 기본 신뢰 설정 ===
trust_level = "trusted"
approval_policy = "never"
sandbox_mode = "danger-full-access"
model = "gpt-5.3-codex"
model_reasoning_effort = "high"

# === 권한 (Permissions) ===
[permissions]
allow = ["Read(*)", "Edit(**)", "Bash(git:*)", "Bash(npm:*)", "Bash(*)", "WebFetch(*)", "mcp__*", "WebSearch", "mcp__ide__getDiagnostics"]
deny = ["Bash(rm -rf /)", "Bash(rm -rf /*)", "Bash(rm -rf ~)", "Bash(rm -rf ~/*)"]
teammateMode = "tmux"

[permissions.env]
CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS = "1"

# === 기능 플래그 ===
[features]
rmcp_client = true

# === MCP 서버 (직접 연결 대상만) ===
[mcp_servers.playwright]
command = "npx"
args = ["-y", "@executeautomation/playwright-mcp-server"]
startup_timeout_sec = 30

[mcp_servers.desktop-commander]
command = "npx"
args = ["-y", "@wonderwhy-er/desktop-commander"]
startup_timeout_sec = 60

[mcp_servers.brave-search]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-brave-search"]
startup_timeout_sec = 30

[mcp_servers.brave-search.env]
BRAVE_API_KEY = "<substituted>"

[mcp_servers.context7]
command = "npx"
args = ["-y", "@upstash/context7-mcp@latest"]
startup_timeout_sec = 30

[mcp_servers.fetch]
command = "uvx"
args = ["mcp-server-fetch"]
startup_timeout_sec = 30

[mcp_servers.filesystem]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-filesystem", "."]
startup_timeout_sec = 30

[mcp_servers.git]
command = "uvx"
args = ["mcp-server-git"]
startup_timeout_sec = 30

[mcp_servers.memory]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-memory"]
startup_timeout_sec = 30

[mcp_servers.supabase]
command = "npx"
args = ["-y", "mcp-remote", "https://mcp.supabase.com/mcp"]
startup_timeout_sec = 60

[mcp_servers.browserbase]
command = "npx"
args = ["-y", "mcp-remote", "<BROWSERBASE_MCP_URL>"]
startup_timeout_sec = 60

[mcp_servers.sequential-thinking]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-sequential-thinking"]
startup_timeout_sec = 30
```

## 4. 권한 시스템 (Permissions)

### 4.1 마이그레이션 배경

초기 Codex 설정은 `[rules]` 섹션에 `rm -rf` 금지 규칙만 포함하는 단순한 형태였다. `7a2c537` 커밋에서 전체 `[permissions]` allow/deny 리스트 기반으로 리팩토링되었다.

### 4.2 Allow 리스트

코드 내 `CODEX_PERMISSION_ALLOW` 클래스 상수로 정의:

| 권한 | 설명 |
|------|------|
| `Read(*)` | 모든 파일 읽기 |
| `Edit(**)` | 모든 파일 편집 (재귀) |
| `Bash(git:*)` | 모든 git 명령 |
| `Bash(npm:*)` | 모든 npm 명령 |
| `Bash(*)` | 모든 bash 명령 (deny가 우선) |
| `WebFetch(*)` | 웹 페이지 조회 |
| `mcp__*` | 모든 MCP 도구 호출 |
| `WebSearch` | 웹 검색 |
| `mcp__ide__getDiagnostics` | IDE 진단 정보 접근 |

`Bash(*)`가 포함되어 사실상 모든 쉘 명령을 허용하되, deny 리스트로 위험한 명령을 차단하는 **화이트리스트 + 블랙리스트 혼합** 방식이다.

### 4.3 Deny 리스트

코드 내 `CODEX_PERMISSION_DENY` 클래스 상수로 정의. 실수로 인한 대량 삭제 방지를 위해 `rm -rf` 계열만 차단한다:

| 카테고리 | 차단 패턴 | 이유 |
|----------|----------|------|
| 파일 삭제 | `Bash(rm -rf /)`, `Bash(rm -rf /*)` | 루트 파일시스템 삭제 |
| 홈 삭제 | `Bash(rm -rf ~)`, `Bash(rm -rf ~/*)` | 사용자 홈 전체 삭제 |

### 4.4 기본 정책

```toml
trust_level = "trusted"        # Codex가 로컬 환경을 신뢰
approval_policy = "never"      # 사용자 승인 없이 자동 실행
sandbox_mode = "danger-full-access"  # 샌드박스 미적용 (전체 접근)
```

이 설정은 개발자의 로컬 환경(특히 `~/work/glasslego` 하위 개인 프로젝트)에서 최대 자율성을 부여하고, `rm -rf` 실수만 최소한으로 방지하는 철학을 반영한다.

## 5. Teammate Mode

### 5.1 개념

Teammate Mode는 Codex CLI가 Claude Code의 MCP 서버에 tmux 세션을 통해 접근하는 기능이다. 이를 통해 Codex는 자체적으로 모든 MCP 서버를 기동하지 않고, Claude Code가 이미 실행 중인 서버를 공유한다.

### 5.2 설정

```toml
[permissions]
teammateMode = "tmux"

[permissions.env]
CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS = "1"
```

- `teammateMode = "tmux"`: tmux를 통해 Claude Code의 MCP 서버에 접근
- `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS = "1"`: 실험적 에이전트 팀 기능 활성화 환경변수

코드 내 상수:

```python
CODEX_TEAMMATE_MODE = "tmux"
CODEX_PERMISSION_ENV = {"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"}
```

### 5.3 Teammate Mode 도입 근거

| 문제 | 해결 |
|------|------|
| Docker 기반 MCP 서버(github, jira-wiki-mcp 등)는 컨테이너 기동에 시간과 리소스 소모 | Claude Code가 이미 기동한 서버를 공유하여 중복 제거 |
| 클라우드 메모리(mem0) 등 인증이 필요한 서버의 시크릿 관리 | Claude Code 세션의 인증 정보를 재사용 |
| SSE 기반 사내 서버(kkoto-mcp, cdp-mcp-server)의 접근 | Claude Code를 통해 간접 접근 |
| 서버 수가 많아질수록 Codex 기동 시간 증가 | 필수 서버만 직접 연결하여 기동 시간 최소화 |

### 5.4 MCP 서버 분류

#### Codex가 직접 연결하는 서버 (codex 타겟 포함)

가벼운 npx/uvx 기반 서버로, Docker 없이 빠르게 기동 가능하거나 독립 실행이 필요한 서버:

| 서버 | 명령 | 비고 |
|------|------|------|
| `playwright` | `npx -y @executeautomation/playwright-mcp-server` | 브라우저 자동화 |
| `desktop-commander` | `npx -y @wonderwhy-er/desktop-commander` | 데스크톱 제어 |
| `brave-search` | `npx -y @modelcontextprotocol/server-brave-search` | 웹 검색 |
| `context7` | `npx -y @upstash/context7-mcp@latest` | 문서 컨텍스트 |
| `fetch` | `uvx mcp-server-fetch` | HTTP 요청 |
| `filesystem` | `npx -y @modelcontextprotocol/server-filesystem .` | 파일 시스템 접근 |
| `git` | `uvx mcp-server-git` | Git 명령 |
| `memory` | `npx -y @modelcontextprotocol/server-memory` | 로컬 메모리 |
| `supabase` | `npx -y mcp-remote https://mcp.supabase.com/mcp` | Supabase 연동 |
| `browserbase` | `npx -y mcp-remote <BROWSERBASE_MCP_URL>` | 원격 브라우저 |
| `sequential-thinking` | `npx -y @modelcontextprotocol/server-sequential-thinking` | 순차적 사고 |
| `browseract` (비활성화) | SSE 타입 | 브라우저 액션 (현재 disabled) |

#### Claude Code를 통해 간접 접근하는 서버 (codex 타겟 미포함)

Docker 기반이거나, 인증이 복잡하거나, SSE 전용인 서버:

| 서버 | 타입 | 제외 사유 |
|------|------|-----------|
| `github` | Docker (stdio) | Docker 컨테이너 기동 비용, 토큰 매핑 필요 |
| `github-kakao` | Docker (stdio) | Docker + 사내 GitHub Enterprise 인증 |
| `jira-wiki-mcp` | Docker (stdio) | Docker + 다수 환경변수(Jira/Confluence) 필요 |
| `mem0` | npx (stdio) | 클라우드 메모리 API 키 관리를 Claude Code에 위임 |
| `kkoto-mcp` | SSE | 사내 SSE 서버, Claude Code를 통해 접근 |
| `cdp-mcp-server` | SSE | 사내 SSE 서버, Claude Code를 통해 접근 |

### 5.5 Features 섹션

```toml
[features]
rmcp_client = true
```

`rmcp_client = true`는 Codex의 Remote MCP(rMCP) 클라이언트 기능을 활성화한다. Teammate Mode에서 Claude Code의 MCP 서버에 접근하기 위해 필요하다.

## 6. MCP 서버 Startup Timeout

### 6.1 동작 방식

Codex 타겟에 대해서만 `startup_timeout_sec` 필드가 설정 파일에 추가된다. 다른 타겟(Claude Desktop, Gemini 등)에는 해당 필드가 생성되지 않는다.

```python
# generator.py 내부 로직
if target == "codex":
    timeout = (
        server.startup_timeout_sec
        if server.startup_timeout_sec is not None
        else self.CODEX_DEFAULT_STARTUP_TIMEOUT_SEC
    )
    config["startup_timeout_sec"] = timeout
```

### 6.2 타임아웃 값

| 상수 | 값 | 설명 |
|------|---|------|
| `CODEX_DEFAULT_STARTUP_TIMEOUT_SEC` | 30 | 기본 타임아웃 (초) |

서버별 커스텀 타임아웃은 `config/mcp_servers.yaml`에서 `startup_timeout_sec` 필드로 지정:

```yaml
desktop-commander:
  startup_timeout_sec: 60   # 기본 30초 대신 60초

supabase:
  startup_timeout_sec: 60   # 원격 서버이므로 넉넉하게
```

커스텀 값이 없으면(`startup_timeout_sec: null` 또는 필드 미지정) 기본값 30초가 적용된다.

### 6.3 STDIO vs SSE 서버

STDIO와 SSE 모두 `startup_timeout_sec`이 동일하게 적용된다:

```toml
# STDIO 서버
[mcp_servers.playwright]
command = "npx"
args = ["-y", "@executeautomation/playwright-mcp-server"]
startup_timeout_sec = 30

# SSE 서버 (예시)
[mcp_servers.browseract]
type = "sse"
url = "https://example.com/sse"
startup_timeout_sec = 30
```

## 7. TOML 생성 방식

### 7.1 직접 문자열 조합

ai-env는 TOML 라이브러리(예: `tomli_w`)를 사용하지 않고, 문자열 포맷팅으로 직접 TOML을 생성한다:

```python
def generate_codex(self) -> str:
    """Codex용 config.toml 생성"""
    allow_str = ", ".join(f'"{item}"' for item in self.CODEX_PERMISSION_ALLOW)
    deny_str = ", ".join(f'"{item}"' for item in self.CODEX_PERMISSION_DENY)
    lines = [
        'trust_level = "trusted"',
        'approval_policy = "never"',
        'sandbox_mode = "danger-full-access"',
        "",
        "[permissions]",
        f"allow = [{allow_str}]",
        f"deny = [{deny_str}]",
        f'teammateMode = "{self.CODEX_TEAMMATE_MODE}"',
        # ...
    ]
```

이 접근의 장점:
- 추가 의존성 없음 (toml/tomli_w 불필요)
- 출력 형식을 정밀하게 제어 가능
- Codex config.toml이 비교적 단순한 구조이므로 충분

### 7.2 MCP 서버 섹션 생성

각 서버는 `_generate_mcp_servers_for_target("codex")`로 필터링된 후, 서버 타입에 따라 다른 TOML 섹션을 생성한다:

- **STDIO 서버**: `command`, `args`, `startup_timeout_sec`, 선택적 `[mcp_servers.<name>.env]`
- **SSE 서버**: `type = "sse"`, `url`, `startup_timeout_sec`

## 8. 저장 경로 및 동기화

`save_all()` 메서드에서 Codex 설정은 두 번 저장된다:

```python
configs = [
    # ...
    ("codex_global", self.settings.outputs.codex_global, self.generate_codex()),
    # ...
    ("codex_local", self.settings.outputs.codex_local, self.generate_codex()),
    # ...
]
```

- `codex_global` -> `~/.codex/config.toml`: 새 프로젝트에서 기본 적용
- `codex_local` -> `./.codex/config.toml`: ai-env 프로젝트 내 로컬 설정

두 파일 모두 동일한 `generate_codex()` 결과를 사용한다.

## 9. 관련 커밋 히스토리

| 커밋 | 날짜 | 내용 |
|------|------|------|
| `b0d1613` | 2026-02-13 | MCP startup timeout 추가, rm -rf deny 규칙 |
| `7a2c537` | 2026-02-13 | `[rules]` -> `[permissions]` 마이그레이션, teammate mode, vibe 함수 |

## 10. 데이터 모델

### MCPServerConfig (Pydantic)

```python
class MCPServerConfig(BaseModel):
    enabled: bool = True
    type: str = "stdio"                    # stdio or sse
    command: str | None = None
    args: list[str] = Field(default_factory=list)
    env_keys: list[str] = Field(default_factory=list)
    url_env: str | None = None             # SSE 서버용 URL 환경변수
    targets: list[str] = Field(default_factory=list)
    startup_timeout_sec: int | None = None # Codex MCP startup timeout (초)
```

`startup_timeout_sec` 필드는 Codex 타겟에서만 의미가 있지만, 모델 레벨에서는 범용으로 정의되어 있다. `_build_server_config()` 내부에서 `target == "codex"` 조건으로 실제 적용 여부를 결정한다.

### MCPConfigGenerator 클래스 상수

```python
class MCPConfigGenerator:
    CODEX_DEFAULT_STARTUP_TIMEOUT_SEC = 30
    CODEX_PERMISSION_ALLOW = [...]   # 9개 항목
    CODEX_PERMISSION_DENY = [...]    # 16개 항목
    CODEX_PERMISSION_ENV = {"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"}
    CODEX_TEAMMATE_MODE = "tmux"
```

## 11. 테스트 커버리지

`tests/test_ai_env.py`의 `TestGenerateCodexConfig` 클래스에서 다음을 검증한다:

| 테스트 | 검증 내용 |
|--------|----------|
| `test_default_startup_timeout_for_codex` | 타임아웃 미지정 시 기본값 30초 적용 |
| `test_custom_startup_timeout_for_codex` | 커스텀 타임아웃(75초) 정상 반영 |
| `test_custom_startup_timeout_for_codex_sse` | SSE 서버의 타임아웃(40초) 정상 반영 |
| `test_codex_permissions_defaults_and_rmrf_rule` | allow/deny 리스트, teammate mode, 환경변수 포함 검증 |

## 12. 관련 파일

| 파일 | 역할 |
|------|------|
| `src/ai_env/mcp/generator.py` | `generate_codex()` 메서드, 권한 상수 정의 |
| `src/ai_env/core/config.py` | `MCPServerConfig` 모델 (`startup_timeout_sec` 필드) |
| `config/mcp_servers.yaml` | MCP 서버 정의 (targets에 codex 포함 여부로 직접 연결 결정) |
| `config/settings.yaml` | 출력 경로 (`codex_global`, `codex_local`) |
| `tests/test_ai_env.py` | Codex 설정 생성 테스트 (`TestGenerateCodexConfig`) |
