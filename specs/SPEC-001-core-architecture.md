---
id: SPEC-001
title: Core Architecture & Config Management
status: implemented
created: 2025-06-01
updated: 2026-02-13
---

# SPEC-001: Core Architecture & Config Management

## 1. 개요

ai-env는 여러 AI 개발 도구(Claude, Gemini, Codex, ChatGPT 등)의 설정과 MCP 서버를 **단일 YAML 소스**에서 관리하고, 각 도구가 요구하는 형식으로 자동 변환하여 배포하는 CLI 도구다.

### 핵심 흐름

```
config/settings.yaml + config/mcp_servers.yaml   ← YAML 설정 소스
.env                                              ← 시크릿 (gitignored)
         ↓  (ai-env sync)
├─ Claude Desktop   (claude_desktop_config.json)
├─ ChatGPT Desktop  (config.json)
├─ Antigravity      (mcp_config.json)
├─ Claude Code      (settings.json, settings.glocal.json)
├─ Codex CLI        (config.toml)
├─ Gemini CLI       (settings.json)
└─ Shell exports    (shell_exports.sh + vibe 함수)
```

## 2. 프로젝트 구조

```
ai-env/
├── config/
│   ├── settings.yaml          # 메인 설정 (provider, outputs, agent_priority)
│   └── mcp_servers.yaml       # MCP 서버 정의
├── .env                       # 시크릿 (gitignored)
├── src/ai_env/
│   ├── core/
│   │   ├── __init__.py        # 공개 API re-export
│   │   ├── config.py          # Pydantic 모델 + YAML 로더
│   │   ├── secrets.py         # SecretsManager
│   │   └── sync.py            # Claude 글로벌 설정 동기화
│   ├── mcp/
│   │   ├── __init__.py        # MCPConfigGenerator re-export
│   │   └── generator.py       # 타겟별 MCP 설정 생성
│   └── cli.py                 # Click CLI + Rich UI
├── .claude/
│   ├── global/                # CLAUDE.md, settings.json.template
│   ├── commands/              # 슬래시 커맨드 (.md 파일)
│   ├── skills/                # 개인 스킬 (fallback)
│   └── settings.glocal.json   # 다른 프로젝트용 MCP 템플릿
├── megan-skills/skills/       # 개인 스킬 (우선)
├── cde-*skills/               # 팀 스킬 심링크 (opt-in)
├── generated/                 # 생성된 파일 (gitignored)
├── tests/                     # pytest 테스트
└── pyproject.toml             # 프로젝트 메타 (hatchling, Python >=3.11)
```

## 3. Pydantic 데이터 모델 (`core/config.py`)

모든 설정은 Pydantic v2 `BaseModel`로 정의되며, YAML 파일을 파싱하여 인스턴스화한다.

### 3.1 모델 계층

```
Settings
├── version: str                          # 설정 버전 (기본 "1.0")
├── default_agent: str                    # 기본 에이전트 (기본 "claude")
├── env_file: str                         # .env 경로 (기본 ".env")
├── agent_priority: list[str]             # vibe fallback 순서 (기본 ["claude", "codex"])
├── providers: dict[str, ProviderConfig]  # AI 프로바이더 정의
└── outputs: OutputsConfig                # 출력 경로 설정

ProviderConfig
├── enabled: bool     # 활성 여부 (기본 True)
└── env_key: str      # API 키 환경변수명 (기본 "")

OutputsConfig
├── claude_desktop: str     # ~/Library/Application Support/Claude/...
├── chatgpt_desktop: str    # ~/Library/Application Support/ChatGPT/...
├── antigravity: str        # ~/.gemini/antigravity/...
├── claude_global: str      # ~/.claude/settings.json
├── codex_global: str       # ~/.codex/config.toml
├── gemini_global: str      # ~/.gemini/settings.json
├── claude_local: str       # ./.claude/settings.glocal.json
├── codex_local: str        # ./.codex/config.toml
├── gemini_local: str       # ./.gemini/settings.local.json
└── shell_exports: str      # ./generated/shell_exports.sh

MCPConfig
└── mcp_servers: dict[str, MCPServerConfig]

MCPServerConfig
├── enabled: bool                       # 활성 여부 (기본 True)
├── type: str                           # "stdio" 또는 "sse" (기본 "stdio")
├── command: str | None                 # 실행 명령 (stdio용)
├── args: list[str]                     # 명령 인자 (기본 [])
├── env_keys: list[str]                 # 필요한 환경변수 키 (기본 [])
├── url_env: str | None                 # SSE 서버 URL 환경변수명
├── targets: list[str]                  # 배포 대상 (기본 [])
└── startup_timeout_sec: int | None     # Codex MCP 기동 타임아웃 (초)
```

### 3.2 모델 상세

| 모델 | 역할 | 소스 파일 |
|------|------|-----------|
| `Settings` | 메인 설정 (버전, 에이전트, 프로바이더, 출력 경로) | `config/settings.yaml` |
| `ProviderConfig` | 개별 AI 프로바이더 활성/비활성, API 키 매핑 | `config/settings.yaml` |
| `OutputsConfig` | 각 대상 도구의 설정 파일 출력 경로 (Desktop, CLI global, local, shell) | `config/settings.yaml` |
| `MCPConfig` | MCP 서버 컬렉션 | `config/mcp_servers.yaml` |
| `MCPServerConfig` | 개별 MCP 서버 (stdio/sse, 타겟, 환경변수) | `config/mcp_servers.yaml` |

### 3.3 출력 경로 분류

| 분류 | 키 | 기본 경로 | 설명 |
|------|-----|-----------|------|
| Desktop 앱 | `claude_desktop` | `~/Library/Application Support/Claude/claude_desktop_config.json` | Claude Desktop |
| | `chatgpt_desktop` | `~/Library/Application Support/ChatGPT/config.json` | ChatGPT Desktop |
| | `antigravity` | `~/.gemini/antigravity/mcp_config.json` | Antigravity (Gemini Desktop) |
| CLI 글로벌 | `claude_global` | `~/.claude/settings.json` | Claude Code (template 기반 생성) |
| | `codex_global` | `~/.codex/config.toml` | Codex CLI |
| | `gemini_global` | `~/.gemini/settings.json` | Gemini CLI |
| 로컬 프로젝트 | `claude_local` | `./.claude/settings.glocal.json` | Claude Code glocal (git 추적) |
| | `codex_local` | `./.codex/config.toml` | Codex 로컬 |
| | `gemini_local` | `./.gemini/settings.local.json` | Gemini 로컬 |
| 기타 | `shell_exports` | `./generated/shell_exports.sh` | 셸 환경변수 + vibe 함수 |

## 4. YAML 설정 로딩

### 4.1 공통 로더

```python
def _load_yaml_model(model_cls: type[_T], config_path: Path, label: str) -> _T
```

| 동작 | 설명 |
|------|------|
| 파일 미존재 | `model_cls()` 반환 (기본값 인스턴스) |
| YAML 비어있음 (`None`) | `model_cls()` 반환 |
| YAML 파싱 오류 | `ValueError` 발생 |
| 검증 실패 | `ValueError` 발생 |

`TypeVar[_T, bound=BaseModel]`을 사용해 제네릭하게 구현되어 있으며, 모든 YAML 로딩이 이 함수를 거친다.

### 4.2 로드 함수

| 함수 | 기본 경로 | 반환 타입 |
|------|-----------|-----------|
| `load_settings(config_path?)` | `<project_root>/config/settings.yaml` | `Settings` |
| `load_mcp_config(config_path?)` | `<project_root>/config/mcp_servers.yaml` | `MCPConfig` |

### 4.3 경로 확장

```python
def expand_path(path: str) -> Path:
    """~ 와 $VAR 확장 후 Path 반환"""
    return Path(os.path.expandvars(os.path.expanduser(path)))
```

### 4.4 프로젝트 루트 탐색

```python
def get_project_root() -> Path:
    return Path(__file__).parent.parent.parent.parent
    # src/ai_env/core/config.py → 4단계 올라감 → ai-env/
```

파일 시스템 경로 기반으로 프로젝트 루트를 결정한다. git이나 마커 파일 탐색 없이, 모듈 위치로부터 고정된 단계 수를 역산한다.

## 5. SecretsManager (`core/secrets.py`)

`.env` 파일에서 시크릿을 로드하고, 환경변수 치환을 수행하는 읽기 전용 관리자.

### 5.1 생성자

```python
SecretsManager(env_file: str = ".env")
```

- `dotenv_values()`로 `.env` 파일 로드
- `None` 값은 필터링하여 `_cache: dict[str, str]`에 저장
- 파일이 없으면 빈 캐시

### 5.2 메서드

| 메서드 | 시그니처 | 설명 |
|--------|----------|------|
| `get()` | `(key, default="") -> str` | 조회 우선순위: `_cache` -> `os.environ` -> `default` |
| `list()` | `() -> dict[str, str]` | 전체 캐시 복사본 반환 |
| `list_masked()` | `() -> dict[str, str]` | 마스킹된 값 반환 |
| `export_to_shell()` | `() -> str` | bash `export` 스크립트 생성 |
| `substitute()` | `(template) -> str` | `${VAR}` 플레이스홀더 치환 |

### 5.3 마스킹 규칙 (`list_masked`)

| 조건 | 결과 | 예시 |
|------|------|------|
| `len(value) > 8` | 앞 4자 + `*` 반복 + 뒤 4자 | `sk-1***************xyz9` |
| `len(value) <= 8` | 전체 `*` | `********` |
| 빈 문자열 | `"(empty)"` | `(empty)` |

### 5.4 셸 Export 생성

```bash
# Auto-generated by ai-env - DO NOT EDIT
# Source: /path/to/.env

export KEY=value
export SPECIAL_KEY="value with $pecial chars"
```

- `#`으로 시작하는 키는 건너뜀
- 값에 특수문자(` $"'\`)가 있으면 큰따옴표로 감쌈
- 빈 값은 건너뜀

### 5.5 템플릿 치환

```python
sm.substitute("docker run -e TOKEN=${API_KEY}")
# → "docker run -e TOKEN=sk-abc123..."
```

캐시의 모든 키에 대해 `${KEY}` 패턴을 단순 문자열 치환한다.

## 6. MCP 설정 생성기 (`mcp/generator.py`)

`MCPConfigGenerator`는 `MCPConfig` + `SecretsManager`를 입력받아 각 타겟별 설정 파일을 생성한다.

### 6.1 생성 대상 및 출력 형식

| 메서드 | 타겟 키 | 출력 형식 | 비고 |
|--------|---------|-----------|------|
| `generate_claude_desktop()` | `claude_desktop` | JSON (`mcpServers`) | |
| `generate_chatgpt_desktop()` | `chatgpt_desktop` | JSON (`mcpServers`) | |
| `generate_antigravity()` | `antigravity` | JSON (`mcpServers`) | |
| `generate_claude_local()` | `claude_local` | JSON (`permissions` + `mcpServers`) | glocal 용 |
| `generate_codex()` | `codex` | TOML 문자열 | permissions, features, mcp_servers 포함 |
| `generate_gemini()` | `gemini` | JSON (`security` + `mcpServers`) | SSE는 `url`만 |
| `generate_shell_functions()` | - | bash 함수 문자열 | `vibe` fallback 함수 |

### 6.2 서버 빌드 로직 (`_build_server_config`)

```
입력: (server_name, MCPServerConfig, target_name)
  ↓
1. enabled=False → None (skip)
2. target not in targets → None (skip)
3. type == "sse" → { type: "sse", url: <resolved> }
4. type == "stdio" → { command, args (치환됨), env (매핑됨) }
5. target == "codex" → startup_timeout_sec 추가
```

### 6.3 ENV_KEY_MAPPING 패턴

MCP 서버가 요구하는 환경변수 이름이 `.env`에 저장된 이름과 다를 때 매핑한다.

```python
ENV_KEY_MAPPING = {
    "GITHUB_GLASSLEGO_TOKEN": "GITHUB_PERSONAL_ACCESS_TOKEN",
    "GITHUB_KAKAO_TOKEN": "GITHUB_PERSONAL_ACCESS_TOKEN",
}
```

**사용 예**: GitHub MCP 서버는 `GITHUB_PERSONAL_ACCESS_TOKEN`을 기대하지만, `.env`에는 용도별로 `GITHUB_GLASSLEGO_TOKEN`, `GITHUB_KAKAO_TOKEN`으로 구분 저장한다. 생성 시 키 이름을 변환하여 Docker `-e` 옵션에 올바른 이름으로 전달한다.

### 6.4 Codex 전용 설정

Codex CLI는 TOML 형식을 사용하며, MCP 서버 외에 추가 설정이 포함된다.

| 항목 | 값 |
|------|-----|
| `trust_level` | `"trusted"` |
| `approval_policy` | `"never"` |
| `sandbox_mode` | `"danger-full-access"` |
| `permissions.allow` | `Read(*)`, `Edit(**)`, `Bash(git:*)`, `Bash(npm:*)`, `Bash(*)`, `WebFetch(*)`, `mcp__*`, `WebSearch`, `mcp__ide__getDiagnostics` |
| `permissions.deny` | `sudo`, `rm -rf /`, `mkfs`, `dd`, `chmod -R 777 /` 등 위험 명령 |
| `permissions.env` | `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` |
| `features.rmcp_client` | `true` |
| `teammateMode` | `"tmux"` |
| `startup_timeout_sec` | 서버별 설정 또는 기본 30초 |

### 6.5 save_all 파이프라인

```python
def save_all(dry_run=False) -> dict[str, Path]
```

| 순서 | 이름 | 생성 메서드 | 저장 형식 |
|------|------|-------------|-----------|
| 1 | `claude_desktop` | `generate_claude_desktop()` | JSON |
| 2 | `chatgpt_desktop` | `generate_chatgpt_desktop()` | JSON |
| 3 | `antigravity` | `generate_antigravity()` | JSON |
| 4 | `codex_global` | `generate_codex()` | TOML (텍스트) |
| 5 | `gemini_global` | `generate_gemini()` | JSON |
| 6 | `claude_local` | `generate_claude_local()` | JSON |
| 7 | `codex_local` | `generate_codex()` | TOML (텍스트) |
| 8 | `gemini_local` | `generate_gemini()` | JSON |
| 9 | `shell_exports` | `export_to_shell()` + `generate_shell_functions()` | 텍스트 |

**주의**: `claude_global`은 `save_all`에서 생성하지 않는다. `sync_claude_global_config()`가 `settings.json.template` 기반으로 별도 생성한다 (permissions 보존을 위해).

### 6.6 vibe 셸 함수

`settings.yaml`의 `agent_priority` 순서대로 AI 에이전트를 시도하는 bash 함수.

```bash
vibe               # 1순위부터 시작
vibe "로그인 만들어줘"  # 프롬프트와 함께
vibe -2            # 2순위부터 시작
vibe -l            # 우선순위 목록 출력
```

| 동작 | 설명 |
|------|------|
| 정상 종료 (`exit 0`) | 완료, 다음 에이전트 시도하지 않음 |
| 비정상 종료 | 다음 순위 에이전트로 자동 전환 |
| Claude Code 세션 내부 | `CLAUDECODE` 환경변수 감지 시 건너뜀 (중첩 세션 방지) |
| 미설치 에이전트 | `command -v` 확인 후 건너뜀 |

## 7. Claude 글로벌 동기화 (`core/sync.py`)

`sync_claude_global_config()`는 ai-env 프로젝트의 `.claude/` 디렉토리를 `~/.claude/`로 동기화한다.

### 7.1 동기화 항목

| 순서 | 소스 | 대상 | 전략 |
|------|------|------|------|
| 1 | `.claude/global/CLAUDE.md` | `~/.claude/CLAUDE.md` | 파일 복사 |
| 2 | `.claude/global/settings.json.template` | `~/.claude/settings.json` | `${VAR}` 치환 후 생성 |
| 3 | `.claude/commands/*.md` | `~/.claude/commands/` | .md 파일만 복사 |
| 4 | personal + team skills | `~/.claude/skills/` | 병합 복사 |

### 7.2 스킬 동기화

스킬은 **personal**과 **team** 두 소스에서 수집 후 `~/.claude/skills/`에 병합된다.

**Personal 스킬 (항상 포함)**:
- 우선: `megan-skills/skills/` (외부 심링크)
- Fallback: `.claude/skills/`

**Team 스킬 (opt-in)**:
- 패턴: `cde-*skills/` 디렉토리 (심링크)
- `--skills-include`로 명시적 포함, `--skills-exclude`로 제외
- 옵션 미지정 시 team 스킬은 동기화하지 않음

**Team 스킬 디렉토리 구조 자동 감지**:

| 구조 | 탐색 경로 | 예시 |
|------|-----------|------|
| nested | `<repo>/.claude/skills/<skill>/SKILL.md` | 표준 Claude 프로젝트 |
| skills subdir | `<repo>/skills/<skill>/SKILL.md` | skills 서브디렉토리 |
| flat | `<repo>/<skill>/SKILL.md` | 루트에 직접 |

`SKILL.md` 파일이 존재하는 서브디렉토리만 스킬로 인식한다.

### 7.3 파일/디렉토리 동기화 전략 (`_sync_file_or_dir`)

| 소스 타입 | 전략 |
|-----------|------|
| 파일 | `shutil.copy2` (메타데이터 보존 복사) |
| `commands/` 디렉토리 | `.md` 파일만 선별 복사 |
| `skills/` 디렉토리 | 서브디렉토리 단위로 `copytree` (기존 것 삭제 후 복사) |
| 기타 디렉토리 | 전체 `copytree` (기존 것 삭제 후 복사) |

## 8. CLI 인터페이스 (`cli.py`)

Click 프레임워크 + Rich 라이브러리로 구현한 CLI.

### 8.1 명령어 구조

```
ai-env
├── setup               # 초기 설정 가이드
├── status              # 현재 상태 확인
├── secrets [--show]    # 환경변수 조회 (마스킹/원문)
├── sync                # 전체 동기화
│   ├── --dry-run
│   ├── --claude-only
│   ├── --mcp-only
│   ├── --skills-include <dir>  (여러 번 사용 가능)
│   └── --skills-exclude <dir>  (여러 번 사용 가능)
├── config
│   └── show            # 현재 설정 표시
└── generate
    ├── all [--dry-run]         # 모든 설정 생성
    ├── claude-desktop [-o]     # Claude Desktop 설정
    ├── chatgpt-desktop [-o]    # ChatGPT Desktop 설정
    ├── antigravity [-o]        # Antigravity 설정
    └── shell [-o]              # Shell export 스크립트
```

### 8.2 sync 명령어 흐름

```
1. .env 파일 존재 확인 (경고만, 중단하지 않음)
2. 활성 MCP 서버의 필수 환경변수 누락 확인 (경고만)
3. Claude 글로벌 설정 동기화 (--mcp-only 아닌 경우)
   → sync_claude_global_config()
4. MCP 설정 생성 및 저장 (--claude-only 아닌 경우)
   → MCPConfigGenerator.save_all()
```

### 8.3 출력 규칙

- 모든 출력은 `rich.console.Console`의 `console.print()` 사용 (`print()` 금지)
- 테이블은 `_create_table()` 헬퍼로 통일
- JSON 출력은 `console.print_json()` 사용

## 9. 의존성

| 패키지 | 역할 | 버전 |
|--------|------|------|
| `click` | CLI 프레임워크 | >= 8.1.0 |
| `rich` | 터미널 UI (테이블, 색상) | >= 13.0.0 |
| `pyyaml` | YAML 파싱 | >= 6.0 |
| `pydantic` | 데이터 모델 검증 | >= 2.0.0 |
| `python-dotenv` | .env 파일 로딩 | >= 1.0.0 |

빌드 시스템: `hatchling` / Python >= 3.11

## 10. 설계 결정

### 왜 Pydantic인가

- **타입 안전성**: YAML에서 로드한 데이터를 런타임에 검증한다. 잘못된 타입이나 누락된 필드를 즉시 잡는다.
- **기본값 일원화**: 모델에 기본값을 정의하면 YAML에 명시하지 않은 필드도 안전하게 처리된다. 설정 파일이 없어도 `model_cls()`로 기본 인스턴스를 생성할 수 있다.
- **IDE 지원**: 모델 필드에 대한 자동완성과 타입 힌트를 얻는다.

### 왜 YAML + .env 분리인가

- **관심사 분리**: 구조적 설정(서버 정의, 경로, 타겟 매핑)은 YAML로, 민감한 값(API 키, 토큰)은 .env로 분리한다.
- **Git 안전성**: YAML은 git으로 추적하고, .env는 gitignore 한다. 실수로 시크릿이 커밋되는 것을 구조적으로 방지한다.
- **`${VAR}` 치환**: YAML의 args에 `${JIRA_URL}` 같은 플레이스홀더를 넣으면, 생성 시점에 SecretsManager가 실제 값으로 치환한다. 설정 구조와 값을 분리하면서도 유연하게 조합할 수 있다.

### ENV_KEY_MAPPING이 필요한 이유

동일한 MCP 서버(예: GitHub MCP)를 여러 인스턴스로 운영할 때, 각 인스턴스마다 다른 토큰을 사용한다. 그러나 Docker 컨테이너 안에서는 모두 `GITHUB_PERSONAL_ACCESS_TOKEN`이라는 고정된 환경변수명을 기대한다.

```
.env:           GITHUB_GLASSLEGO_TOKEN=ghp_aaa...
                GITHUB_KAKAO_TOKEN=ghp_bbb...
                     ↓ ENV_KEY_MAPPING
Docker -e:      GITHUB_PERSONAL_ACCESS_TOKEN=ghp_aaa...  (glasslego 인스턴스)
                GITHUB_PERSONAL_ACCESS_TOKEN=ghp_bbb...  (kakao 인스턴스)
```

이렇게 `.env`에서는 용도별로 구분된 키 이름을 쓰고, 생성 시점에 서버가 요구하는 키 이름으로 변환한다.

### 왜 glocal인가

`glocal` = "global template for local"의 줄임말이다.

- `settings.glocal.json`은 ai-env 프로젝트에서 생성하여 **다른 프로젝트에서 사용할** MCP 설정 템플릿이다.
- git으로 추적되어 팀원과 공유 가능하다.
- `settings.local.json`은 프로젝트별 개인 설정(permissions 등)이며, sync가 덮어쓰지 않는다.

### 왜 claude_global은 save_all에서 제외하는가

`~/.claude/settings.json`은 `settings.json.template`에서 환경변수를 치환하여 생성된다. 이 템플릿에는 MCP 서버뿐 아니라 permissions, 기타 글로벌 설정이 포함되어 있으므로, `MCPConfigGenerator`가 MCP만으로 덮어쓰면 permissions가 사라진다. 따라서 `sync_claude_global_config()`에서 별도로 처리한다.

### 단일 설정 소스 원칙

모든 AI 도구의 설정이 `config/settings.yaml` + `config/mcp_servers.yaml` 두 파일에서 유래한다. 각 도구의 설정 파일을 직접 편집하지 않고, 항상 `ai-env sync`로 생성한다. 이렇게 하면:
- 새 MCP 서버 추가 시 한 곳만 수정하면 모든 도구에 반영된다.
- 설정 간 불일치가 구조적으로 발생하지 않는다.
- `--dry-run`으로 변경 사항을 미리 확인할 수 있다.
