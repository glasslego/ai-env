# ai-env

Claude, Gemini, Codex 등 여러 AI 도구의 MCP 서버와 설정을 한 곳에서 관리합니다.

## 빠른 시작

```bash
git clone <repository-url> ai-env && cd ai-env
uv sync
cp .env.example .env   # API 키 입력
uv run ai-env sync     # 전체 동기화
```

## 주요 명령어

```bash
uv run ai-env setup                                 # 초기 설정 점검 가이드
uv run ai-env status                                # 전체 상태 확인
uv run ai-env sync                                  # 전체 동기화
uv run ai-env sync --dry-run                        # 미리보기
uv run ai-env sync --claude-only                    # Claude 설정만
uv run ai-env sync --mcp-only                       # MCP 설정만
uv run ai-env sync --claude-only --skills-include cde-skills
uv run ai-env sync --claude-only --skills-include cde-ranking-skills
uv run ai-env sync --claude-only --skills-exclude cde-ranking-skills
uv run ai-env secrets                               # 환경변수 목록
uv run ai-env secrets --show                        # 값 표시
uv run ai-env config show                           # settings/mcp 설정 확인
uv run ai-env generate claude-desktop               # 특정 타겟 생성 (stdout)
```

> 프로젝트 내에서 실행 시 `uv run` 접두사를 사용합니다.

## 동작 원리

```
.env (토큰)  +  config/mcp_servers.yaml (서버 정의)  +  config/settings.yaml
                         │
                   ai-env sync
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
  Claude Desktop    Gemini/Codex     ~/.claude/
  ChatGPT Desktop   Antigravity    (commands, skills)
                                   shell_exports.sh (vibe 함수)
```

`.env`의 토큰과 `config/mcp_servers.yaml`의 서버 정의를 조합해서 각 AI 도구별 설정 파일을 자동 생성합니다.

## 스킬 동기화 정책

- 개인 스킬 기본 소스: `megan-skills/skills/`
- fallback 소스: `.claude/skills/` (`megan-skills/skills/`가 없을 때)
- 동기화 대상: `~/.claude/skills/`
- 기본 `sync` 동작: 개인 스킬만 동기화
- 팀 스킬(`cde-skills`, `cde-ranking-skills`)은 옵션으로만 포함
  - `--skills-include <dir>`: 지정한 팀 스킬만 추가
  - `--skills-exclude <dir>`: 팀 스킬에서 지정 항목 제외

예시:

```bash
# 개인 스킬만
uv run ai-env sync --claude-only

# 개인 + cde-skills
uv run ai-env sync --claude-only --skills-include cde-skills

# 개인 + (모든 팀 - cde-ranking-skills)
uv run ai-env sync --claude-only --skills-exclude cde-ranking-skills
```

## 동기화 대상

| 대상 | 출력 경로 |
|------|----------|
| Claude Desktop | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| ChatGPT Desktop | `~/Library/Application Support/ChatGPT/config.json` |
| Claude Code (글로벌) | `~/.claude/settings.json`, `CLAUDE.md`, `commands/`, `skills/` |
| Antigravity | `~/.gemini/antigravity/mcp_config.json` |
| Codex CLI (글로벌) | `~/.codex/config.toml` |
| Gemini CLI (글로벌) | `~/.gemini/settings.json` |
| Claude Local (프로젝트) | `.claude/settings.glocal.json` |
| Codex Local (프로젝트) | `.codex/config.toml` |
| Gemini Local (프로젝트) | `.gemini/settings.local.json` |
| Shell exports | `generated/shell_exports.sh` (환경변수 + vibe 함수) |

## 추천 MCP 목록

기본적으로 아래 MCP를 "공통 생산성 세트"로 사용합니다.

| MCP 서버 | 용도 | 기본 상태 |
|---------|------|-----------|
| `desktop-commander` | 로컬 파일/프로세스 작업 자동화 | enabled |
| `playwright` | 브라우저 자동화, E2E/스크래핑 | enabled |
| `brave-search` | 웹 검색 | enabled |
| `context7` | 라이브러리 공식 문서 조회 | enabled |
| `sequential-thinking` | 단계적 추론/계획 | enabled |

참고:
- `github`, `github-kakao`, `jira-wiki-mcp`, `mem0`, `kkoto-mcp`, `cdp-mcp-server`는 환경/네트워크 특성상 Codex에서 startup 실패가 잦아 기본적으로 Codex 타겟에서 제외되어 있습니다.
- Claude Desktop/ChatGPT Desktop은 `stdio` 타입 MCP만 권장됩니다.

## MCP 타겟 매트릭스 (기본 공통 세트)

| MCP 서버 | Claude Desktop | ChatGPT Desktop | Claude Code | Codex | Gemini | Antigravity |
|---------|----------------|-----------------|-------------|-------|--------|-------------|
| `desktop-commander` | Y | Y | Y | Y | Y | Y |
| `playwright` | Y | Y | Y | Y | Y | Y |
| `brave-search` | Y | Y | Y | Y | Y | Y |
| `context7` | Y | Y | Y | Y | Y | Y |
| `sequential-thinking` | Y | Y | Y | Y | Y | Y |

## vibe 함수 (Agent Fallback)

`ai-env sync` 시 `shell_exports.sh`에 자동 생성되는 쉘 함수입니다.
`config/settings.yaml`의 `agent_priority` 순서대로 AI 에이전트를 시도하고, 앞 에이전트가 세션 한도/에러로 종료되면 다음으로 자동 전환합니다.

```bash
vibe               # claude 시작 → 한도 도달 시 codex로 전환
vibe "기능 만들어줘"  # 프롬프트와 함께 시작
vibe -2            # 2순위(codex)부터 바로 시작
vibe -l            # 에이전트 우선순위 목록 출력
```

우선순위 변경: `config/settings.yaml`의 `agent_priority` 수정 후 `uv run ai-env sync`.

## MCP 서버 추가

`config/mcp_servers.yaml`에 항목을 추가하고 `uv run ai-env sync`를 실행합니다.

```yaml
my-server:
  enabled: true
  type: stdio              # stdio 또는 sse
  command: docker
  args: [run, -i, --rm, my-image]
  env_keys: [MY_TOKEN]     # .env에서 가져올 키
  targets:                 # 배포할 대상
    - claude_desktop
    - antigravity
    - claude_local
```

SSE 서버는 `url_env`로 URL을 지정합니다. Desktop 앱(Claude/ChatGPT)은 stdio만 지원합니다.

## 개발

```bash
uv sync --all-extras && pre-commit install
uv run pytest              # 테스트
uv run ruff check .        # 린트
uv run mypy src/           # 타입 체크
```

## 라이선스

MIT
