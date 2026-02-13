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
config/settings.yaml + mcp_servers.yaml   ← 설정 소스 (YAML)
.env                                      ← 시크릿 (gitignore)
         ↓ (ai-env sync)
├─ Claude Desktop  (claude_desktop_config.json)
├─ ChatGPT Desktop (config.json)
├─ Antigravity     (mcp_config.json)
├─ Claude Code     (settings.json, glocal.json)
├─ Codex CLI       (config.toml)
├─ Gemini CLI      (settings.json)
└─ Shell exports   (shell_exports.sh)
```

### 핵심 모듈

| 모듈 | 역할 |
|------|------|
| `core/config.py` | Pydantic 모델, YAML 설정 로드 |
| `core/secrets.py` | `.env` 환경변수 관리, `${VAR}` 치환 |
| `core/sync.py` | Claude 글로벌 설정 동기화 (CLAUDE.md, commands/, skills/, settings.json) |
| `mcp/generator.py` | 타겟별 MCP 설정 생성 (stdio/SSE) |
| `cli.py` | Click CLI + Rich UI |

### 환경변수 치환

`${VAR}` → SecretsManager가 `.env` → `os.environ` 순서로 조회하여 치환.
`ENV_KEY_MAPPING`으로 MCP별 키 이름 매핑 (예: `GITHUB_GLASSLEGO_TOKEN` → `GITHUB_PERSONAL_ACCESS_TOKEN`).

## 프로젝트 구조

```
config/           YAML 설정 (git 추적)
src/ai_env/       메인 패키지 (core/, mcp/)
.claude/
├── global/       글로벌 설정 소스 (CLAUDE.md, settings.json.template)
├── commands/     슬래시 커맨드
├── skills/       개인 스킬 (personal)
├── settings.glocal.json  다른 프로젝트용 MCP 템플릿 (git 추적)
└── settings.local.json   이 프로젝트 전용 (gitignore)
cde-*skills/      팀 스킬 심링크 (cde-skills, cde-ranking-skills 등)
tests/            pytest 테스트
generated/        생성된 설정 (gitignore)
```

### Skills 동기화

`ai-env sync`는 personal + team 스킬을 합쳐서 `~/.claude/skills/`에 동기화:

```
personal: .claude/skills/*/
team:     cde-*skills/ (symlink) → SKILL.md를 가진 서브디렉토리만
                ↓ 병합
          ~/.claude/skills/
```

`--skills-include`/`--skills-exclude` 옵션으로 팀 스킬 디렉토리를 선택적으로 동기화 가능.

### Agent Fallback (vibe 함수)

`ai-env sync` 시 `shell_exports.sh`에 `vibe` 쉘 함수가 자동 생성됨.
`config/settings.yaml`의 `agent_priority` 순서대로 AI 에이전트를 시도하고, 앞 에이전트가 비정상 종료 시 다음으로 자동 전환.

```bash
vibe               # Claude Code 시작 → 한도 도달 시 Codex로 자동 전환
vibe "로그인 만들어줘"  # 프롬프트와 함께 시작
vibe -2            # 2순위(codex)부터 바로 시작
vibe -l            # 에이전트 우선순위 목록 확인
```

우선순위 변경: `config/settings.yaml`의 `agent_priority` 수정 후 `ai-env sync`.

## 주요 규칙

- `.env`는 절대 커밋하지 않음
- 경로 확장은 `expand_path()` 사용
- CLI는 `console.print()` 사용 (`print()` 금지)
- SSE 서버는 Desktop 앱에서 미지원 (stdio만)
- glocal = "global template for local" (sync가 생성, git 추적)
- local = 프로젝트별 permissions (sync가 덮어쓰지 않음)
