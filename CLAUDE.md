# CLAUDE.md

## 프로젝트 개요

ai-env는 AI 개발 환경(Claude, Gemini, Codex, ChatGPT 등)의 설정과 MCP 서버를 **하나의 소스에서 통합 관리**하는 CLI 도구다.

**핵심 가치**: 토큰·MCP 설정을 중앙화하고, 각 AI 도구 형식으로 자동 변환·배포한다.

## 개발 명령어

```bash
uv sync --all-extras && pre-commit install  # 초기 설정
uv run ai-env status                        # 상태 확인
uv run ai-env sync --dry-run                # 동기화 미리보기
uv run ai-env sync                          # 전체 동기화
uv run pytest                               # 테스트
uv run ruff check . && uv run ruff format . # 린트·포맷
```

## 아키텍처

```
config/settings.yaml + config/mcp_servers.yaml  ← 설정 소스 (YAML)
.env                                      ← 시크릿 (gitignore)
         ↓ (ai-env sync)
├─ Claude Desktop  (claude_desktop_config.json)
├─ ChatGPT Desktop (config.json)
├─ Codex Desktop   (~/.codex/codex.config.json)
├─ Antigravity     (mcp_config.json)
├─ Claude Code Global (~/.claude/settings.json, CLAUDE.md, commands/, skills/)
├─ Claude Local    (.claude/settings.glocal.json)
├─ Codex Global    (~/.codex/config.toml, AGENTS.md)
├─ Codex Local     (.codex/config.toml)
├─ Gemini CLI      (~/.gemini/settings.json, GEMINI.md, .gemini/settings.local.json)
└─ Shell exports   (shell_exports.sh)
```

### 핵심 모듈

| 모듈 | 역할 |
|------|------|
| `core/config.py` | Pydantic 모델, YAML 설정 로드 |
| `core/secrets.py` | `.env` 환경변수 관리, `${VAR}` 치환 |
| `core/sync.py` | 글로벌 설정 동기화 (Claude, Codex, Gemini) |
| `core/doctor.py` | 환경 건강 검사 (`ai-env doctor`) |
| `core/pipeline.py` | 토픽 YAML 모델, 리서치 파이프라인 유틸 |
| `core/research.py` | Deep Research API 디스패치 (Gemini/OpenAI) |
| `core/workflow.py` | 6-Phase 워크플로우 스캐폴딩, 상태 관리 |
| `mcp/generator.py` | 타겟별 MCP 설정 생성 (stdio/SSE) |
| `mcp/vibe.py` | Agent Fallback 셸 함수 생성 (`claude()` wrapper) |
| `cli/` | Click CLI + Rich UI (doctor, generate, status, sync, pipeline) |

### 환경변수 치환

`${VAR}` → SecretsManager가 `.env` → `os.environ` 순서로 조회하여 치환.
`ENV_KEY_MAPPING`으로 MCP별 키 이름 매핑 (예: `GITHUB_GLASSLEGO_TOKEN` → `GITHUB_PERSONAL_ACCESS_TOKEN`).

## 프로젝트 구조

```
config/           YAML 설정 (git 추적)
  topics/         리서치 토픽 YAML
  templates/      Obsidian + AI 프롬프트 템플릿
src/ai_env/       메인 패키지 (core/, mcp/)
.claude/
├── global/       글로벌 설정 소스 (CLAUDE.md, settings.json.template)
├── commands/     슬래시 커맨드
├── settings.glocal.json  로컬 Claude 템플릿 (MCP generator 생성, gitignore)
└── settings.local.json   프로젝트별 로컬 설정 (gitignore)
megan-skills/     개인 스킬 저장소
└── skills/       개인 스킬 (기본 동기화 소스)
cde-*skills/      팀 스킬 심링크 (cde-skills, cde-ranking-skills 등)
tests/            pytest 테스트
generated/        생성된 설정 (gitignore)
```

### Skills 동기화

`ai-env sync`는 기본적으로 personal 스킬만 `~/.claude/skills/`에 동기화한다.
team 스킬은 `--skills-include` 또는 `--skills-exclude` 옵션을 줄 때만 합쳐서 동기화한다.

```
personal(우선): megan-skills/skills/*/
personal(fallback): .claude/skills/*/
team(option): cde-*skills/ (symlink) → SKILL.md를 가진 서브디렉토리만
                ↓ 병합
          ~/.claude/skills/
```

`--skills-include`/`--skills-exclude` 옵션으로 팀 스킬 디렉토리를 선택적으로 동기화 가능.

### Agent Fallback (claude --fallback)

`ai-env sync` 시 `shell_exports.sh`에 `claude()` 쉘 함수가 자동 생성됨.
원본 `claude` 바이너리를 shadow하며, `--fallback` 없이 사용하면 원본으로 passthrough.
`--fallback` 모드에서는 `config/settings.yaml`의 `agent_priority` 순서대로 에이전트를 시도하고, 앞 에이전트가 비정상 종료 시 다음으로 자동 전환.
전환은 Claude 프로세스 종료 후 세션 로그(rate-limit 문구 포함)를 분석해 트리거됨.

**모델 레벨 fallback**: `agent:model` 문법으로 동일 에이전트의 다른 모델을 우선순위에 추가 가능.
예: `claude:sonnet` → `claude --model sonnet`으로 실행. 각 엔트리는 독립적인 cooldown을 가짐.
Opus/Sonnet은 별도 API quota이므로, Opus 소진 → Sonnet 사용 → Sonnet도 소진 시 Codex 전환.

```bash
claude --fallback              # Claude(Opus) → Claude(Sonnet) → Codex 순서
claude --fallback "로그인 만들어줘"  # 프롬프트와 함께 시작
claude --fallback -2           # 2순위(claude:sonnet)부터 바로 시작
claude --fallback -3           # 3순위(codex)부터 바로 시작
claude --fallback --dangerously-skip-permissions "작업"  # wrapper가 --auto로 해석
claude --fallback -l           # 에이전트 우선순위 목록 확인
claude                         # 일반 claude 실행 (passthrough)
```

`--dangerously-skip-permissions` / `--allow-dangerously-skip-permissions`는 fallback wrapper에서 제어 플래그로 소비된다.
즉, Claude에는 `--dangerously-skip-permissions`, Codex에는 `--yolo`로 매핑되어 전달된다.

우선순위 변경: `config/settings.yaml`의 `agent_priority` 수정 후 `ai-env sync`.

**영속 cooldown**: Rate-limit 감지 시 cooldown 상태가 `$CLAUDE_FALLBACK_LOG_DIR/.fallback_cooldown`에 저장되어 셸 재시작 후에도 유지됨.
세션 로그에서 "resets Feb 23 at 9am" 등 리셋 시각을 파싱하여 정확한 cooldown 기간을 설정함.

**역방향 핸드오프**: Codex 등 non-Claude 에이전트 작업 완료 후 Claude cooldown이 해제되면 자동으로 Claude로 복귀하며, 핸드오프 컨텍스트를 전달함.

### Deep Research Dispatch (pipeline dispatch)

Track B(Gemini)/C(GPT) 심층리서치를 API로 자동 실행한다.
기존에는 프롬프트 파일만 생성하고 사용자가 웹에서 수동 실행했으나, Gemini Deep Research API와 OpenAI Deep Research API를 직접 호출하여 완전 자동화.

```bash
ai-env pipeline dispatch bitcoin-automation              # 전체 디스패치
ai-env pipeline dispatch bitcoin-automation --track gemini  # Gemini만
ai-env pipeline dispatch bitcoin-automation --track gpt     # GPT만
```

API 키 없으면 기존 프롬프트 파일 생성으로 graceful fallback.
API 키: `.env`의 `GOOGLE_API_KEY`, `OPENAI_API_KEY` 사용.

## 주요 규칙

- `.env`는 절대 커밋하지 않음
- 경로 확장은 `expand_path()` 사용
- CLI는 `console.print()` 사용 (`print()` 금지)
- SSE 서버는 Claude/ChatGPT Desktop에서 미지원 (stdio만). Codex Desktop은 SSE(url) 지원
- glocal = "global template for local" (MCP generator가 생성, git 추적)
- local = 프로젝트별 permissions (sync가 덮어쓰지 않음)
