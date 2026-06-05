# ai-env

**Claude Code + Codex CLI** 개발 환경의 MCP 서버와 설정을 한 곳에서 관리하는 CLI.
(Gemini / Antigravity / ChatGPT Desktop 지원은 SPEC-013 정리에서 제거됨. Deep Research API
디스패치만 별도 기능으로 잔존.)

> **사용 예시**: 시나리오별 상세 가이드는 [docs/USAGE-EXAMPLES.md](docs/USAGE-EXAMPLES.md) 참조.

## 빠른 시작

```bash
git clone <repository-url> ai-env && cd ai-env
uv sync
vi .env                           # API 키 입력 (SETUP.md 참조)
uv run ai-env sync                # 전체 동기화
source ./generated/shell_exports.sh
```

## 공용 에이전트 가이드라인 운영

Spec-Task-Test-Commit 규칙의 단일 원본(SSOT)은 다음 파일입니다.

- `.claude/global/CLAUDE.md`

주요 포함 내용:
- Spec-Task-Test-Commit 워크플로우
- 시크릿/환경변수 관리 (하드코딩 금지, gitleaks)
- pre-commit + ruff 자동 수정
- PySpark 컨벤션 (UDF 지양, cache/unpersist 쌍)
- 권장 라이브러리 (pydantic, loguru, matplotlib, Pillow 등)

가이드라인 수정 후 동기화:

```bash
uv run ai-env sync --claude-only
```

동기화 대상:
- `~/.claude/CLAUDE.md` (Claude Code)
- `~/.codex/AGENTS.md`, `~/.codex/skills/`, `~/.codex/commands/`, `~/.codex/project-profile.yaml` (Codex CLI)

## 동작 원리

```
.env (토큰) + config/settings.yaml + config/mcp_servers.yaml
                         │
                   ai-env sync
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
  Claude Desktop    Codex CLI/Desktop  ~/.claude/
  Claude Local      ~/.codex/AGENTS.md  (commands, skills, hooks)
                    ~/.codex/skills/   shell_exports.sh
                    ~/.codex/commands/
                    ~/.codex/project-profile.yaml
```

ai-env는 Claude + Codex 두 타겟만 지원한다 (SPEC-013).

## CLI 명령어

```bash
# 설정 관리
ai-env setup                   # 초기 설정 점검 가이드
ai-env bedrock setup           # Claude Code on Bedrock AWS SSO 프로필 자동 구성
ai-env bedrock status          # Bedrock SSO 설정 상태 확인
ai-env bedrock login           # AWS SSO 브라우저 로그인
ai-env status                  # 전체 상태 확인
ai-env doctor [--json]         # 환경 건강 검사
ai-env secrets [--show]        # 환경변수 목록 (--show로 값 표시)
ai-env config show             # settings/mcp 설정 확인

# 동기화
ai-env sync                    # 전체 동기화
ai-env sync --dry-run          # 미리보기
ai-env sync --claude-only      # Claude 설정만
ai-env sync --mcp-only         # MCP 설정만
ai-env sync --skills-all            # 모든 팀 스킬 포함 (develop pull 포함)
ai-env sync --skills-only           # 스킬만 빠르게 동기화
ai-env sync --skills-include <dir>  # 특정 팀 스킬 포함
ai-env sync --skills-exclude <dir>  # 특정 팀 스킬 제외

# 개별 생성 (stdout)
ai-env generate all
ai-env generate claude-desktop [-o FILE]
ai-env generate codex-desktop [-o FILE]
ai-env generate shell [-o FILE]

# 프로젝트 로컬 Claude → Codex 연결
ai-env project sync-codex                           # 현재 프로젝트의 CLAUDE.md, .claude/skills 연결
ai-env project sync-codex --skills-only            # skills만 연결
ai-env project sync-codex --agents-only            # AGENTS.md만 연결
ai-env project sync-codex --copy                   # 심볼릭 링크 대신 복사
ai-env project sync-codex --project-dir /path/to/repo

# 리서치 파이프라인
ai-env pipeline list                     # 등록된 토픽 목록
ai-env pipeline info <topic_id>          # 토픽 상세 정보
ai-env pipeline research <topic_id>      # Phase 1 실행 (자동검색)
ai-env pipeline dispatch <topic_id>      # Deep Research API 디스패치
ai-env pipeline status <topic_id>        # 리서치 진행 상황
ai-env pipeline scaffold <topic_id>      # Obsidian 워크스페이스 생성
ai-env pipeline workflow <topic_id>      # 워크플로우 진행 상태

# Obsidian 세션 저장 (SPEC-013)
ai-env session save --note "<메모>"                      # 기본 vault의 00_session/에 저장
ai-env session save --note "..." --subdir 01_Inbox      # 다른 디렉토리
ai-env session save --note "..." --vault ~/Vaults/Other  # 다른 vault
ai-env session save --note "..." --dry-run               # 본문 미리보기
```

## 동기화 대상

| 대상 | 출력 경로 |
|------|----------|
| Claude Desktop | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Claude Code (글로벌) | `~/.claude/settings.json`, `CLAUDE.md`, `commands/`, `skills/`, `hooks/` |
| Claude Local | `.claude/settings.glocal.json` |
| Codex Desktop | `~/.codex/codex.config.json` |
| Codex CLI (글로벌) | `~/.codex/config.toml`, `AGENTS.md`, `skills/`, `commands/`, `project-profile.yaml` |
| Codex Local | `.codex/config.toml`, `.codex/skills`, `.codex/commands`, `.codex/project-profile.yaml` |
| Shell exports | `generated/shell_exports.sh` |

## 프로젝트별 Claude Skills를 Codex와 공유

아무 프로젝트에서나 Claude용 자산을 Codex와 함께 쓰려면:

```bash
ai-env project sync-codex
```

이 명령은 기본적으로 현재 디렉토리 기준으로 다음을 연결합니다.

- `CLAUDE.md` → `AGENTS.md` (기본: 심볼릭 링크)
- `.claude/skills/` → `.codex/skills/` (Codex 호환 YAML로 정규화 복사)
- `.claude/commands/` → `.codex/commands/` (참조용 .md 트리 복사, SPEC-013)
- `.claude/project-profile.yaml` → `.codex/project-profile.yaml` (SPEC-013)

기존 일반 파일/디렉토리가 있으면 `.bak.<timestamp>`로 백업 후 교체합니다.

## 세션을 Obsidian에 저장 (SPEC-013)

대화·스킬 도중 현재 컨텍스트를 Obsidian vault의 마크다운 노트로 보존합니다.
`/handoff`(다음 세션 인계용)와 달리 외부 vault에 영구 저장되어 검색·연결 가능합니다.

```bash
ai-env session save --note "메모"                            # 기본 vault/00_session/
ai-env session save --note "..." --title "회의 결정"          # 제목 지정
ai-env session save --note "..." --subdir 01_Inbox           # 다른 폴더
ai-env session save --note "..." --vault ~/Vaults/Other      # 다른 vault
ai-env session save --note "..." --dry-run                   # 본문 미리보기
```

vault 기본 경로는 `config/settings.yaml`의 `obsidian_base`로 설정합니다.
스킬은 `.claude/skills/session-save/SKILL.md`이며 Codex CLI에서도 동일하게 동작합니다.

## claude --fallback

`ai-env sync`가 생성하는 `claude()` 쉘 함수. `config/settings.yaml`의 `agent_priority` 순서대로 에이전트를 시도하고, rate-limit 시 자동 전환.

```bash
claude --fallback              # claude → claude:sonnet → codex 자동 전환
claude --fallback -2           # 2순위부터 시작
claude --fallback --auto       # 모든 에이전트 자동 승인 모드
claude --fallback -l           # 우선순위 목록 출력
claude                         # 회사 Bedrock enterprise 프로필로 일반 실행 (~/.claude)
claude personal                # 개인 Anthropic 로그인 프로필로 실행 (~/.claude-personal)
claude enterprise              # enterprise(회사 Bedrock) 프로필 명시 실행
```

| 옵션 | 설명 |
|------|------|
| `--auto` | Claude에 `--dangerously-skip-permissions` 주입. Codex는 프롬프트 실행 시 `codex exec -c "approval_policy='never'" -s workspace-write`로 동작 |
| `--dangerously-skip-permissions` | `--auto`와 동일 (wrapper가 소비) |
| `-N` | N순위부터 시작 (예: `-2`) |

**프로필 전환 (enterprise / personal)**

`--settings`는 User 계층(`~/.claude/settings.json`)을 *대체*하지 못해 Bedrock
`env`/`apiKeyHelper`가 남는다. 그래서 프로필 격리는 `CLAUDE_CONFIG_DIR`로 user-level
config 디렉토리 자체를 바꾸는 방식으로 동작한다.

- enterprise(기본): `~/.claude`를 그대로 사용 — 회사 Bedrock(`apiKeyHelper` 게이트웨이 토큰)
- personal: `CLAUDE_CONFIG_DIR=~/.claude-personal` — Bedrock 설정이 전혀 없는
  `settings.json`만 두고, 개인 Anthropic 로그인(OAuth 토큰은 이 디렉토리에 별도 저장)
- 권한(`permissions`)·`skipDangerousModePermissionPrompt`·hooks·MCP는 두 프로필 모두 동일
  (오직 **로그인/백엔드만 분리** — Bedrock env/apiKeyHelper 제거, 모델 ID는 direct-API 형식으로 변환)
- 모델 버전도 동일하되 ID 형식만 백엔드에 맞춤. 단 Opus 기본은 백엔드 기본을 따른다:
  enterprise(회사 Bedrock)=Opus 4.7 기본, personal(개인 API)=Opus 4.8 기본 — picker엔 둘 다 노출
- 공용 자산(CLAUDE.md/commands/skills/agents/hooks)은 `~/.claude`를 가리키는 심링크로 재사용
- `ai-env sync`가 `~/.claude-personal/settings.json` + 심링크를 생성한다
- 첫 personal 실행 시 `claude personal`로 개인 계정 로그인이 필요하다
- `CLAUDE_CODE_PROFILE=personal claude ...`로도 개인 프로필을 기본 선택 가능
- `/exit`으로 종료 시 다음 에이전트로 전환하지 않고 깨끗하게 종료
- 새 세션 시작 시 항상 Claude(Opus)부터 시도 (이전 cooldown 무시)

**Codex 프로필 (CODEX_HOME 대칭 분리)**

Claude의 enterprise/personal과 대칭으로 Codex도 계정을 분리한다. Codex는 회사
Bedrock 같은 별도 백엔드가 없어 **로그인 계정(auth.json)만** 분리하면 된다.

```bash
codex                  # 기본 ~/.codex (회사 계정)
codex personal         # CODEX_HOME=~/.codex-personal (개인 ChatGPT 계정)
codex enterprise       # 기본 ~/.codex 명시
```

- personal: `CODEX_HOME=~/.codex-personal` — `auth.json`(개인 로그인)만 분리 저장
- 공용 자산(AGENTS.md/skills/commands/agents/config.toml/hooks)은 `~/.codex` 심링크로 재사용
- `ai-env sync`가 `~/.codex-personal/` 심링크를 생성한다 (auth.json은 절대 심링크 안 함)
- 첫 personal 실행 시 `codex personal login`으로 개인 계정 로그인 필요
- `CODEX_CODE_PROFILE=personal codex ...`로도 개인 프로필을 기본 선택 가능

## Claude Code on Bedrock

회사 Bedrock enterprise 프로필은 `ai-env bedrock` 명령으로 관리합니다. 수동
`aws configure sso` 대신 AWS config의 Bedrock section만 생성/갱신합니다.

```bash
ai-env bedrock setup --dry-run     # ~/.aws/config 변경 미리보기
ai-env bedrock setup               # bedrock-gateway SSO profile 생성/갱신
ai-env bedrock login               # aws sso login --profile bedrock-gateway
ai-env bedrock status --verify-auth
ai-env bedrock status --verify-auth --verify-token
```

기본값:

- profile/session: `bedrock-gateway`
- SSO start URL: `https://d-9067b92cea.awsapps.com/start`
- SSO region: `us-east-1`
- account/role: `673981388588` / `BEDROCK`

## 워크플로우 파이프라인

리서치 → Brief → Spec → TDD 코드 → 리뷰의 6-Phase 자동화 파이프라인.

```bash
# 개별 Phase 실행
claude "/wf-init topic_id"       # Phase 0: 워크스페이스 초기화
claude "/wf-research topic_id"   # Phase 2: 3-Track 리서치
claude "/wf-spec topic_id"       # Phase 3: Brief + Spec 생성
claude "/wf-code topic_id"       # Phase 4: TDD 코드 생성
claude "/wf-review topic_id"     # Phase 5: 스펙 정합성 리뷰

# 전체 자동 실행
claude "/wf-run topic_id"        # 현재 Phase부터 끝까지

# 상태 확인
ai-env pipeline workflow topic_id
```

- **체크포인트 재개**: 코드 생성 중 실패한 모듈부터 자동 재개
- **Brief 압축**: 리서치를 30% 이하로 압축 후 교차 분석
- **오류 격리**: 각 Phase 독립 재실행 가능

## MCP 서버 추가

`config/mcp_servers.yaml`에 항목 추가 후 `ai-env sync`:

```yaml
my-server:
  enabled: true
  type: stdio           # stdio 또는 sse
  command: docker
  args: [run, -i, --rm, my-image]
  env_keys: [MY_TOKEN]  # .env에서 가져올 키
  targets:              # 배포 대상 (claude_desktop, claude_local, codex, codex_desktop)
    - claude_desktop
    - claude_local
```

> Claude Desktop은 stdio만 지원. Codex Desktop은 stdio + SSE(url) 지원.

## 개발

```bash
uv sync --all-extras && pre-commit install
uv run pytest              # 테스트
uv run ruff check . && uv run ruff format .  # 린트·포맷
uv run mypy src/           # 타입 체크
```
