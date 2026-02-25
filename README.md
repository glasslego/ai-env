# ai-env

AI 도구(Claude, Gemini, Codex 등)의 MCP 서버와 설정을 한 곳에서 관리하는 CLI.

## 빠른 시작

```bash
git clone <repository-url> ai-env && cd ai-env
uv sync
vi .env                           # API 키 입력 (SETUP.md 참조)
uv run ai-env sync                # 전체 동기화
source ./generated/shell_exports.sh
```

## 동작 원리

```
.env (토큰) + config/settings.yaml + config/mcp_servers.yaml
                         │
                   ai-env sync
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
  Claude Desktop    Gemini/Codex     ~/.claude/
  ChatGPT Desktop   Codex Desktop  (commands, skills)
                    Antigravity    shell_exports.sh
```

## CLI 명령어

```bash
# 설정 관리
ai-env setup                   # 초기 설정 점검 가이드
ai-env status                  # 전체 상태 확인
ai-env doctor [--json]         # 환경 건강 검사
ai-env secrets [--show]        # 환경변수 목록 (--show로 값 표시)
ai-env config show             # settings/mcp 설정 확인

# 동기화
ai-env sync                    # 전체 동기화
ai-env sync --dry-run          # 미리보기
ai-env sync --claude-only      # Claude 설정만
ai-env sync --mcp-only         # MCP 설정만
ai-env sync --skills-include <dir>  # 팀 스킬 포함
ai-env sync --skills-exclude <dir>  # 팀 스킬 제외

# 개별 생성 (stdout)
ai-env generate all
ai-env generate claude-desktop [-o FILE]
ai-env generate chatgpt-desktop [-o FILE]
ai-env generate codex-desktop [-o FILE]
ai-env generate antigravity [-o FILE]
ai-env generate shell [-o FILE]

# 리서치 파이프라인
ai-env pipeline list                     # 등록된 토픽 목록
ai-env pipeline info <topic_id>          # 토픽 상세 정보
ai-env pipeline research <topic_id>      # Phase 1 실행 (자동검색)
ai-env pipeline dispatch <topic_id>      # Deep Research API 디스패치
ai-env pipeline status <topic_id>        # 리서치 진행 상황
ai-env pipeline scaffold <topic_id>      # Obsidian 워크스페이스 생성
ai-env pipeline workflow <topic_id>      # 워크플로우 진행 상태
```

## 동기화 대상

| 대상 | 출력 경로 |
|------|----------|
| Claude Desktop | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| ChatGPT Desktop | `~/Library/Application Support/ChatGPT/config.json` |
| Codex Desktop | `~/.codex/codex.config.json` |
| Claude Code (글로벌) | `~/.claude/settings.json`, `CLAUDE.md`, `commands/`, `skills/` |
| Codex CLI (글로벌) | `~/.codex/config.toml`, `AGENTS.md` |
| Gemini CLI (글로벌) | `~/.gemini/settings.json`, `GEMINI.md` |
| Antigravity | `~/.gemini/antigravity/mcp_config.json` |
| Claude Local | `.claude/settings.glocal.json` |
| Codex Local | `.codex/config.toml` |
| Gemini Local | `.gemini/settings.local.json` |
| Shell exports | `generated/shell_exports.sh` |

## claude --fallback

`ai-env sync`가 생성하는 `claude()` 쉘 함수. `config/settings.yaml`의 `agent_priority` 순서대로 에이전트를 시도하고, rate-limit 시 자동 전환.

```bash
claude --fallback              # claude → claude:sonnet → codex 자동 전환
claude --fallback -2           # 2순위부터 시작
claude --fallback --auto       # 모든 에이전트 자동 승인 모드
claude --fallback -l           # 우선순위 목록 출력
claude                         # 일반 실행 (passthrough)
```

| 옵션 | 설명 |
|------|------|
| `--auto` | Claude에 `--dangerously-skip-permissions` 주입. Codex는 프롬프트 실행 시 `codex exec -c "approval_policy='never'" -s workspace-write`로 동작 |
| `--dangerously-skip-permissions` | `--auto`와 동일 (wrapper가 소비) |
| `-N` | N순위부터 시작 (예: `-2`) |

- `/exit`으로 종료 시 다음 에이전트로 전환하지 않고 깨끗하게 종료
- 새 세션 시작 시 항상 Claude(Opus)부터 시도 (이전 cooldown 무시)

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
  targets:              # 배포 대상
    - claude_desktop
    - claude_local
    - antigravity
```

> Claude Desktop/ChatGPT Desktop은 stdio만 지원. Codex Desktop은 stdio + SSE(url) 지원.

## 개발

```bash
uv sync --all-extras && pre-commit install
uv run pytest              # 테스트
uv run ruff check . && uv run ruff format .  # 린트·포맷
uv run mypy src/           # 타입 체크
```
