---
id: SPEC-002
title: MCP Config Generator
status: implemented
created: 2025-06-01
updated: 2026-02-13
---

# SPEC-002: MCP Config Generator

## 개요

`MCPConfigGenerator`는 하나의 MCP 서버 정의(`config/mcp_servers.yaml`)로부터 6개 AI 도구 타겟의 설정 파일을 자동 생성한다. 각 타겟의 고유 포맷(JSON, TOML)과 제약사항(Desktop은 stdio만, Codex는 permissions 기반 등)을 처리한다.

**소스 파일**: `src/ai_env/mcp/generator.py`

## 데이터 모델

### MCPServerConfig (Pydantic)

```python
class MCPServerConfig(BaseModel):
    enabled: bool = True
    type: str = "stdio"          # "stdio" | "sse"
    command: str | None = None   # stdio: 실행 명령어
    args: list[str] = []         # stdio: 명령어 인수
    env_keys: list[str] = []     # 필요한 환경변수 키 목록
    url_env: str | None = None   # sse: URL이 저장된 환경변수명
    targets: list[str] = []      # 배포 대상 타겟 목록
    startup_timeout_sec: int | None = None  # Codex 서버별 기동 타임아웃
```

### 설정 소스

| 파일 | 역할 |
|------|------|
| `config/mcp_servers.yaml` | MCP 서버 정의 (이름, 타입, 타겟, 환경변수) |
| `config/settings.yaml` | 출력 경로, agent_priority, provider 설정 |
| `.env` | 시크릿 값 (SecretsManager가 로드) |

## MCPConfigGenerator 클래스

### 생성자

```python
def __init__(self, secrets: SecretsManager):
```

`SecretsManager`를 주입받고, `load_mcp_config()`와 `load_settings()`로 YAML 설정을 로드한다.

### 환경변수 키 매핑 (ENV_KEY_MAPPING)

일부 MCP 서버는 내부 환경변수 키와 다른 이름을 요구한다. `ENV_KEY_MAPPING`이 이를 변환한다.

```python
ENV_KEY_MAPPING = {
    "GITHUB_GLASSLEGO_TOKEN": "GITHUB_PERSONAL_ACCESS_TOKEN",
    "GITHUB_KAKAO_TOKEN": "GITHUB_PERSONAL_ACCESS_TOKEN",
}
```

**동작**: `.env`에서 `GITHUB_GLASSLEGO_TOKEN` 값을 읽되, MCP 서버에는 `GITHUB_PERSONAL_ACCESS_TOKEN`이라는 키 이름으로 전달한다. 이를 통해 하나의 머신에서 여러 GitHub 인스턴스(github.com, github.daumkakao.com) 토큰을 구분하여 관리할 수 있다.

## 핵심 메서드

### _build_server_config(name, server, target) -> dict | None

단일 MCP 서버의 설정을 생성한다.

**처리 흐름**:
1. `enabled=False`이거나 `target`이 서버의 `targets`에 없으면 `None` 반환
2. **stdio 서버**: `command`, `args`(환경변수 치환), `env`(키 매핑 적용) 생성
3. **sse 서버**: `url_env`에서 URL을 조회하여 `{"type": "sse", "url": ...}` 생성
4. **Codex 타겟**: `startup_timeout_sec` 추가 (서버별 값 또는 기본 30초)

### _generate_mcp_servers_for_target(target) -> dict

전체 서버 목록을 순회하며 해당 타겟에 해당하는 서버들만 필터링하여 설정 딕셔너리를 반환한다.

### 타겟별 생성 메서드

#### generate_claude_desktop() -> dict

```json
{"mcpServers": {"github": {...}, "jira-wiki-mcp": {...}, ...}}
```

stdio 서버만 지원 (Desktop 앱 제약).

#### generate_chatgpt_desktop() -> dict

Claude Desktop과 동일한 구조. stdio만 지원.

```json
{"mcpServers": {...}}
```

#### generate_antigravity() -> dict

stdio + SSE 모두 지원.

```json
{"mcpServers": {...}}
```

#### generate_claude_local() -> dict

프로젝트별 `.claude/settings.glocal.json`용. permissions 블록 포함.

```json
{
  "permissions": {
    "allow": ["Bash(*)", "WebSearch", "WebFetch", "mcp__*", "mcp__ide__getDiagnostics"],
    "deny": ["Bash(rm -rf /)", "Bash(rm -rf /*)", "Bash(rm -rf ~)", "Bash(rm -rf ~/*)"],
    "ask": [],
    "defaultMode": "acceptEdits"
  },
  "mcpServers": {...}
}
```

#### generate_codex() -> str (TOML)

Codex CLI 전용 TOML 포맷. permissions 기반 보안 정책 포함.

```toml
trust_level = "trusted"
approval_policy = "never"
sandbox_mode = "danger-full-access"

[permissions]
allow = ["Read(*)", "Edit(**)", ...]
deny = ["Bash(rm -rf /)", "Bash(rm -rf /*)", "Bash(rm -rf ~)", "Bash(rm -rf ~/*)"]
teammateMode = "tmux"

[permissions.env]
CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS = "1"

[features]
rmcp_client = true

[mcp_servers.playwright]
command = "npx"
args = ["-y", "@executeautomation/playwright-mcp-server"]
startup_timeout_sec = 30
```

#### generate_gemini() -> dict

Gemini CLI용. SSE 서버는 `type` 필드 없이 `url`만 포함.

```json
{
  "security": {"auth": {"selectedType": "oauth-personal"}},
  "mcpServers": {
    "github": {"command": "docker", "args": [...]},
    "kkoto-mcp": {"url": "https://..."}
  }
}
```

#### generate_shell_functions() -> str

`settings.yaml`의 `agent_priority` 기반 `vibe()` bash 함수를 생성한다.

**동작**:
- 우선순위대로 AI 에이전트 실행 시도
- 비정상 종료(exit code != 0) 시 다음 에이전트로 자동 전환
- Claude Code 중첩 세션 감지 및 건너뛰기
- `-l` 옵션으로 우선순위 목록 출력, `-N` 옵션으로 N순위부터 시작

### save_all(dry_run=False) -> dict[str, Path]

모든 타겟 설정을 한 번에 생성하고 저장한다.

**저장 대상** (10개 파일):

| 이름 | 출력 경로 | 포맷 |
|------|-----------|------|
| claude_desktop | `~/Library/Application Support/Claude/claude_desktop_config.json` | JSON |
| chatgpt_desktop | `~/Library/Application Support/ChatGPT/config.json` | JSON |
| antigravity | `~/.gemini/antigravity/mcp_config.json` | JSON |
| codex_global | `~/.codex/config.toml` | TOML |
| gemini_global | `~/.gemini/settings.json` | JSON |
| claude_local | `./.claude/settings.glocal.json` | JSON |
| codex_local | `./.codex/config.toml` | TOML |
| gemini_local | `./.gemini/settings.local.json` | JSON |
| shell_exports | `./generated/shell_exports.sh` | Bash |

> **참고**: `claude_global` (~/.claude/settings.json)은 `save_all()`에서 생성하지 않는다. template 기반으로 `sync_claude_global_config()`에서 별도 처리된다.

> **참고**: `shell_exports`는 `SecretsManager.export_to_shell()` 출력 + `generate_shell_functions()` 출력을 합쳐서 저장한다.

## Codex 전용 상수

```python
CODEX_PERMISSION_ALLOW = [
    "Read(*)", "Edit(**)", "Bash(git:*)", "Bash(npm:*)", "Bash(*)",
    "WebFetch(*)", "mcp__*", "WebSearch", "mcp__ide__getDiagnostics",
]

CODEX_PERMISSION_DENY = [
    "Bash(sudo:*)", "Bash(rm -rf /)", "Bash(rm -rf /*)",
    "Bash(rm -rf ~)", "Bash(rm -rf ~/*)", "Bash(mkfs*)",
    "Bash(dd if=*of=/dev/*)", "Bash(chmod -R 777 /)",
    "Bash(chown -R * /)", "Bash(shutdown*)", "Bash(reboot*)",
    "Bash(init 0*)", "Bash(git push * --force)",
    "Bash(git clean -fdx /)", "Bash(DROP DATABASE*)", "Bash(DROP TABLE*)",
]

CODEX_PERMISSION_ENV = {"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"}
CODEX_TEAMMATE_MODE = "tmux"
CODEX_DEFAULT_STARTUP_TIMEOUT_SEC = 30
```

## MCP 서버 목록 및 타겟 매트릭스

### stdio 서버

| 서버 | 실행 방식 | claude_desktop | chatgpt_desktop | antigravity | claude_local | codex | gemini |
|------|-----------|:-:|:-:|:-:|:-:|:-:|:-:|
| github | docker | O | O | O | O | | O |
| github-kakao | docker | O | O | O | O | | O |
| jira-wiki-mcp | docker | O | O | O | O | | O |
| playwright | npx | O | O | O | O | O | O |
| desktop-commander | npx | O | O | O | O | O | O |
| brave-search | npx | O | O | O | O | O | O |
| context7 | npx | O | O | O | O | O | O |
| mem0 | npx | O | O | O | O | | O |
| fetch | uvx | O | O | O | O | O | O |
| sequential-thinking | npx | O | O | O | O | O | O |

### sse 서버

| 서버 | 상태 | antigravity | claude_local | codex | gemini |
|------|------|:-:|:-:|:-:|:-:|
| browseract | **disabled** | O | O | O | O |
| kkoto-mcp | enabled | O | O | | O |
| cdp-mcp-server | enabled | O | O | | O |

> **참고**: SSE 서버는 Desktop 앱(claude_desktop, chatgpt_desktop)에서 지원되지 않으므로 타겟에 포함되지 않는다.

### 서버별 커스텀 타임아웃

| 서버 | startup_timeout_sec |
|------|:-------------------:|
| github | 45 |
| github-kakao | 45 |
| jira-wiki-mcp | 60 |
| desktop-commander | 60 |
| mem0 | 30 |
| kkoto-mcp | 30 |
| cdp-mcp-server | 30 |
| (기타 미지정) | 30 (Codex 기본값) |

## 타겟 간 차이점 요약

| 타겟 | 포맷 | stdio | sse | 고유 특성 |
|------|------|:-----:|:---:|-----------|
| claude_desktop | JSON | O | X | Desktop 앱 제약 (stdio만) |
| chatgpt_desktop | JSON | O | X | Desktop 앱 제약 (stdio만) |
| antigravity | JSON | O | O | SSE 포함, mcpServers만 |
| claude_local | JSON | O | O | permissions 블록 포함 (glocal 템플릿) |
| codex | TOML | O | O | permissions allow/deny, teammateMode, 서버별 timeout, features 블록 |
| gemini | JSON | O | O | security.auth 블록, SSE는 url만 (type 필드 제거) |

## 환경변수 치환 흐름

```
config/mcp_servers.yaml의 args:
  - "-e"
  - "JIRA_URL=${JIRA_URL}"
       ↓ _substitute_env()
  SecretsManager.substitute()
       ↓ (.env → os.environ 순서 조회)
  "JIRA_URL=https://jira.example.com"
```

```
env_keys: [GITHUB_GLASSLEGO_TOKEN]
       ↓ SecretsManager.get()
  값: "ghp_abc123..."
       ↓ _map_env_key()
  키: "GITHUB_PERSONAL_ACCESS_TOKEN"
       ↓
  env: {"GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_abc123..."}
```
