# CLAUDE.md

## ai-env 브랜치 운영

- ai-env는 `main` 단일 브랜치에서 바로 작업·검증·커밋한다.
- 별도 작업 브랜치나 브랜치용 worktree를 만들지 않는다. 일반 스킬의 작업 브랜치 생성 권고보다 이 규칙이 우선한다.
- 머지하지 않는다. `git merge`, 머지 커밋을 만드는 `git pull`, PR 머지(`gh pr merge`, GitHub MCP merge)를 모두 금지한다.
  원격 반영은 `git pull --ff-only`만 쓰고, fast-forward가 안 되면 멈추고 사용자에게 보고한다.
- 이 정책은 ai-env에만 적용한다. 연결된 cde-skills·cde-ranking-skills의 develop 정책은 유지한다.
- 원격 push는 사용자가 요청한 범위에서 수행한다.


## 프로젝트 개요

ai-env는 **Claude Code + Codex CLI** 개발 환경의 설정과 MCP 서버를 **하나의 소스에서 통합 관리**하는 CLI 도구다. 설정 동기화와 공용 에이전트 규칙을 관리하며, 문서 작업에는 로컬 LLM Wiki 검색·출처 등록 CLI를 제공한다.

**핵심 가치**: 토큰·MCP 설정을 중앙화하고, 각 AI 도구 형식으로 자동 변환·배포한다.

## 공용 작업 원칙 (Spec-Task-Test-Commit)

- 공용 글로벌 원본: `.claude/global/CLAUDE.md`
- 구현 순서: `Spec 확인 -> Task 단위 구현 -> 테스트 통과 -> 커밋`
- 커밋 단위: `Spec의 Task 완료 단위`
- 커밋 메시지 권장 형식: `<type>(spec-<id>/task-<id>): <summary>`
- 공용 정책 변경 후 동기화: `uv run ai-env sync --claude-only`

### spec/task 식별자 운용 (이 repo 한정)

- ai-env는 개인 repo이므로 `spec-<id>`/`task-<id>`는 **반드시 `specs/`에 문서가 있어야 하는 건 아니다.** 작업 묶음을 가리키는 라벨로 느슨하게 쓴다.
- `specs/SPEC-0XX-*.md` 처럼 문서가 있으면 그 번호를 식별자로 쓰고(`spec-013`), 문서 없이 진행하는 작업 묶음은 의미 있는 라벨을 직접 만들어 쓴다(선례: `spec-claude-bedrock`).
- `task-<id>`는 그 묶음 안의 개별 구현 단계를 가리키는 자유 라벨이다(예: `task-sso-automation`, `task-mcp-permissions`).
- 핵심은 "어느 작업 묶음의 어느 단계인지" 추적 가능하게 만드는 것. 문서화 강제보다 라벨 일관성을 우선한다.

## 개발 명령어

```bash
uv sync --all-extras && pre-commit install  # 초기 설정
uv run ai-env status                        # 상태 확인
uv run ai-env sync --dry-run                # 동기화 미리보기
uv run ai-env sync                          # 전체 동기화
uv run pytest                               # 테스트 (커버리지 자동 측정, 최소 65%)
uv run ruff check . && uv run ruff format . # 린트·포맷
```

## 아키텍처

```
config/settings.yaml + config/mcp_servers.yaml  ← 설정 소스 (YAML)
.env                                      ← 시크릿 (gitignore)
         ↓ (ai-env sync)
├─ Claude Desktop  (claude_desktop_config.json)
├─ Claude Code Global (~/.claude/settings.json[권한/env/hooks], CLAUDE.md, commands/, skills/, hooks/)
├─ Claude MCP (user scope) (~/.claude.json top-level mcpServers — settings.json은 MCP를 읽지 않음)
├─ Claude Local    (.claude/settings.glocal.json)
├─ Codex Desktop   (~/.codex/codex.config.json)
├─ Codex Global    (~/.codex/config.toml, AGENTS.md, commands/, skills/, project-profile.yaml)
├─ Codex Local     (.codex/config.toml, .codex/skills, .codex/commands, .codex/project-profile.yaml)
└─ Shell exports   (shell_exports.sh)
```

### 핵심 모듈

| 모듈 | 역할 |
|------|------|
| `core/config.py` | Pydantic 모델, YAML 설정 로드 |
| `core/secrets.py` | `.env` 환경변수 관리, `${VAR}` 치환 |
| `core/sync.py` | 글로벌 설정 동기화 (Claude, Codex) |
| `core/doctor.py` | 환경 건강 검사 (`ai-env doctor`) |
| `core/wiki_documents.py` | LLM Wiki 종합·출처 검색, Markdown 해시 등록과 불변 스냅샷 |
| `core/session_journal.py` | 공용 작업 기록 저장·조회·마스킹 |
| `core/session_storage.py` | 기록 경로·프로젝트 격리·Markdown 머리말·잠금 |
| `core/session_hooks.py` | 요청·응답·세션 종료 hook 처리 |
| `core/session_compaction.py` | 세션·날짜별 탐색 요약 |
| `core/session_archives.py` | 검증한 gzip 보관·원문 복원 |
| `core/project_sync.py` | 프로젝트 로컬 Claude↔Codex 동기화 |
| `mcp/generator.py` | 타겟별 MCP 설정 생성 (stdio/SSE/streamable-http) |
| `core/codex_skills.py` | Codex 호환 스킬 패키징 (SKILL.md frontmatter 정규화) |
| `mcp/vibe.py` | Agent Fallback 셸 함수 생성 (`claude()` wrapper) |
| `core/env_example.py` | `.env.example` 자동 생성 — MCP/provider 설정 + 팀 스킬 템플릿·코드의 변수 이름 수집 |
| `core/env_sync.py` | 팀 저장소 `.env`와 `~/.cde-skills.env`에 인증 배포, 백업·누락 방지·Cloud fallback 검증 |
| `core/bedrock.py` | Claude Code on Bedrock setup helpers. |
| `core/env_sync.py` | ai-env 원본에서 팀 저장소에 필요한 환경변수를 배포한다. |
| `cli/` | Click CLI + Rich UI (bedrock, doctor, generate, project, status, sync) |

### 환경변수 치환

`${VAR}` → SecretsManager가 `.env` → `os.environ` 순서로 조회하여 치환.
`ENV_KEY_MAPPING`으로 MCP별 키 이름 매핑 (예: `GITHUB_GLASSLEGO_TOKEN` → `GITHUB_PERSONAL_ACCESS_TOKEN`).

## 프로젝트 구조

```
config/           YAML 설정 (git 추적)
  github/         GitHub 토큰 관리
src/ai_env/       메인 패키지 (core/, mcp/)
.claude/
├── global/       글로벌 설정 소스 (CLAUDE.md, settings.json.template)
├── project-profile.yaml  프로젝트 메타 (스킬이 자동 로드)
├── commands/     슬래시 커맨드 (add-mcp, ai-env-sync, commit, handoff 등)
├── rules/        매 세션 로드하는 글로벌 규칙 원본 (→ ~/.claude/rules, ~/.codex/rules)
├── guides/       필요한 작업에서만 읽는 지침 원본 (→ ~/.claude/guides, ~/.codex/guides)
├── hooks/        세션 lifecycle 훅 (session_start, session_end, pre_compact)
├── handoff/      세션 간 컨텍스트 전달 (gitignore, /handoff로 생성)
├── logs/         fallback 세션 로그 (gitignore, 7일 후 자동 삭제)
├── worktrees/    agent worktree 작업 공간 (gitignore)
├── settings.glocal.json  로컬 Claude 템플릿 (MCP generator 생성, gitignore)
└── settings.local.json   프로젝트별 로컬 설정 (gitignore)
megan-harness/    개인 스킬·에이전트 단일 홈 (skills/{category}/, agents/, lib/, docs/)
scripts/          문서-코드 정합성 검증 스크립트 (pre-push hook)
cde-*skills/      팀 스킬 심링크 (cde-skills, cde-ranking-skills 등)
tests/            pytest 테스트
generated/        생성된 설정 (gitignore)
```

### Skills 동기화

`ai-env sync`는 기본적으로 개인 스킬(`megan-harness/skills/`)만 `~/.claude/skills/`에 동기화한다.
team 스킬(`cde-*skills`)은 `--skills-include`/`--skills-exclude` 옵션을 줄 때만 합쳐서 동기화한다
(단, `ALWAYS_TEAM_SKILLS`의 cde-skills·cde-ranking-skills는 항상 포함).

```
개인:   megan-harness/skills/{category}/{skill}/   (카테고리 무관 재귀 스캔)
팀:     cde-*skills/ (symlink) → SKILL.md 가진 서브디렉토리만
                ↓ 병합 (활성 팀 정본 우선, 나머지는 개인 우선)
          ~/.claude/skills/  ·  ~/.codex/skills/  ·  ~/.agents/skills/
에이전트: megan-harness/agents/  →  ~/.claude/agents/  ·  ~/.codex/agents/
```

활성 cde-skills 플러그인 카테고리와 cde-ranking-skills 정본은 개인 사본보다 우선하며 원본 디렉토리에 심링크한다. 다른 이름 충돌은 기존 개인 우선 정책을 따른다.

`--skills-all`로 모든 팀 스킬을 포함하거나, `--skills-include`/`--skills-exclude`로 선택적 동기화 가능.
팀 스킬 포함 시(`--skills-all` 등) 동기화 전에 각 `cde-*skills` 레포의 `develop` 브랜치를 자동 `git pull`한다.

활성 팀 스킬은 원본을 링크하므로 `_shared`와 repo `lib`의 상대경로를 유지한다. 랭킹 helper는 cde-ranking-skills의 `.venv/bin/python`으로 실행한다. 통합 별칭 `spark-optimize`, `self-review`, `ranking-batch-task-execution`의 옛 개인 사본은 다시 배포하지 않는다.

팀 환경변수는 `.env.example`의 주석 placeholder로 기록한다. 필요한 기능만 주석을 해제하고 값을 설정한다. 모든 팀 변수가 필수는 아니며, 예시 토큰·비밀번호는 복사하지 않는다. 실제 `.env`의 값은 수정 시에도 출력하거나 커밋하지 않는다.

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
즉, Claude에는 `--dangerously-skip-permissions`가 적용되고, Codex는 프롬프트 실행 시 `codex exec -c "approval_policy='never'" -s workspace-write`로 one-shot 실행된다.
Codex 대화형 실행(프롬프트 없음)일 때만 `--yolo --no-alt-screen`을 사용한다.

우선순위 변경: `config/settings.yaml`의 `agent_priority` 수정 후 `ai-env sync`.

**세션 내 cooldown**: 같은 셸 세션 안에서 rate-limit 감지 시 해당 에이전트를 cooldown 처리하고 다음 에이전트로 전환.
새 세션 시작 시에는 항상 Claude(Opus)부터 시도한다 (이전 cooldown 상태를 무시).

**클린 종료**: Claude에서 `/exit`이나 `/quit`으로 종료하면 rate-limit 메시지가 로그에 있더라도 다음 에이전트로 전환하지 않고 깨끗하게 종료한다.

**역방향 핸드오프**: 같은 세션 내에서 Codex 등 non-Claude 에이전트 작업 완료 후 Claude cooldown이 해제되면 자동으로 Claude로 복귀하며, 핸드오프 컨텍스트를 전달함.

**세션 로그**: fallback 세션 로그는 현재 프로젝트의 `.claude/logs/`에 `{session_id}_{agent}.log` 형식으로 저장된다. 세션 시작 시 7일 이상 된 로그는 자동 삭제된다. `CLAUDE_FALLBACK_LOG_DIR` 환경변수로 저장 경로를 오버라이드할 수 있다.

## 주요 규칙

- 지시 완료 보고·교차 리뷰는 `.claude/rules/shared-session-journal.md`에 따라 `ai-env session record|list|show|compact`로 관리한다.
- Obsidian 작업 기록의 자동 hook·프로젝트 격리·검증 후 gzip 보관은 `docs/SESSION-JOURNAL.md`, `SPEC-017/TASK-01`을 따른다.

- 문서 작업은 `.claude/rules/llm-wiki-workflow.md`에 따라 작성 전 `ai-env wiki search`, 작성 후 `ai-env wiki register`를 실행한다. 종합은 에이전트가 근거를 읽고 갱신한다.
- Wiki CLI 계약과 테스트: `specs/SPEC-016-llm-wiki-document-workflow.md`. 검색은 종합·등록 출처 대상이며 전체 Vault 의미 검색은 아니다.

- `.env`는 절대 커밋하지 않음 (`.gitignore`에 `.env`, `*.pem`, `credentials*.json` 포함)
- 시크릿 하드코딩 절대 금지. 환경변수 또는 `.env` 파일 사용
- 경로 확장은 `expand_path()` 사용
- CLI는 `console.print()` 사용 (`print()` 금지)
- pre-commit 필수 (`.pre-commit-config.yaml` + `ruff check --fix` + `ruff format` + `gitleaks` + `mypy`)
- CI: GitHub Actions로 test + lint + type-check + doc-sync 자동 실행 (`.github/workflows/ci.yml`)
- 커버리지: `pytest --cov` 자동 측정, 최소 65% 미달 시 실패
- SSE 서버는 Claude Desktop에서 미지원 (stdio만). Codex Desktop은 SSE(url) 지원
- **MCP 서버 정의는 `~/.claude/settings.json`이 아니라 `~/.claude.json`(user scope) top-level `mcpServers`에 기록한다.** Claude Code는 settings.json의 mcpServers를 읽지 않는다 (MCP는 `~/.claude.json` 또는 `.mcp.json`에서만 로드). settings.json은 권한(`mcp__*` allow)/env/hooks 전용. sync는 `~/.claude.json`의 다른 키(projects 등)를 보존하며 mcpServers만 갱신한다.
- MCP `type`은 `stdio | sse | http`(streamable-http) 지원. url 기반(sse/http)은 `url_env`로 URL 주입.
- glocal = "global template for local" (MCP generator가 생성, git 추적)
- local = 프로젝트별 permissions (sync가 덮어쓰지 않음)
- `.claude/settings.json`의 `claudeMdExcludes`는 ai-env 세션에서 규칙 원본(`.claude/rules`)을 제외한다. 같은 내용의 `~/.claude/rules` 배포본만 로드된다. 규칙 수정 후 `ai-env sync --claude-only`로 배포해야 세션에 반영된다.

### Codex가 Claude 자산을 활용하는 범위

`ai-env sync` 1회 실행으로 Codex CLI도 Claude의 다음 자산을 사용한다:

- `~/.codex/AGENTS.md` — Claude 글로벌 지침 + 규칙 인덱스 (스킬 목록은 Codex가 `~/.agents/skills`에서 직접 읽음)
- `~/.codex/skills/` — 활성 팀 스킬은 정본 심링크, 개인 스킬은 YAML 정규화 사본
- `~/.codex/commands/` — `.claude/commands/*.md` 트리 미러 (참조용)
- `~/.codex/project-profile.yaml` — 프로젝트 프로파일 미러

프로젝트 로컬은 `ai-env project sync-codex`로 동일한 구조의 `.codex/`를 만든다.
