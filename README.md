# ai-env

**Claude Code + Codex CLI** 개발 환경의 MCP 서버와 설정을 한 곳에서 관리하는 CLI.
(Gemini / Antigravity / ChatGPT Desktop 지원은 SPEC-013 정리에서 제거됨.)

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
- `.claude/rules/*.md` (주제별·경로별 조건부 규칙)

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
- `~/.claude/CLAUDE.md`, `~/.claude/rules/` (Claude Code)
- `~/.codex/AGENTS.md`, `~/.codex/rules/`, `~/.codex/skills/`, `~/.codex/commands/`, `~/.codex/project-profile.yaml` (Codex CLI)

## 문서 작업의 LLM Wiki 연계

공용 에이전트 규칙은 재사용할 문서 작성 전 기존 지식을 검색하고, 저장 후 출처를 등록하도록 한다.
검색·등록은 아래 CLI가 수행하며, 종합 문장·인덱스·로그 갱신은 에이전트가 근거를 읽고 수행한다.
OS watcher나 백그라운드 LLM은 실행하지 않는다.

```bash
uv run ai-env wiki search "배치 성능 정합성" --limit 3
uv run ai-env wiki register /absolute/path/design.md --dry-run
uv run ai-env wiki register /absolute/path/design.md
uv run ai-env wiki --vault "/path/to/vault" search "지식 종합"
```

- Vault 경로: `--vault` → `OBSIDIAN_BASE` → `~/Documents/Obsidian Vault`.
- 검색 대상: `wiki/`의 `note_type: synthesis`와 등록한 출처. JSON에 경로·상태·근거 발췌를 반환한다.
- 외부 Markdown: `00_inbox/llm-wiki/<SHA-256>.md`에 불변 스냅샷 저장. 원본은 수정하지 않는다.
- Vault 내부 원본: 복사 없이 경로·해시 등록. 동일 내용 재등록은 무변경이다.
- 개인·투자 폴더: 기본 제외. 사용자가 지정한 문서만 `--allow-private` 등록 가능하며 기본 검색에서는 계속 제외된다.
- 저장소: `_meta/llm-wiki-registry.json`. 상세 계약: [SPEC-016](specs/SPEC-016-llm-wiki-document-workflow.md).
- 사용·종합 연결 절차: [LLM Wiki 가이드](docs/LLM-WIKI.md).
- 공용 규칙 배포: `uv run ai-env sync --claude-only` (Claude·Codex 포함). 지침·템플릿·단순 링크 수정은 자동 등록 대상이 아니다.

## 공용 작업·리뷰 기록

- Obsidian `00_session/<저장소명>/agent-logs/`에 Claude·Codex 기록을 프로젝트별 Markdown으로 남긴다.
- 지시 완료 보고는 work/review/fix, 응답 종료는 checkpoint, 세션 종료는 summary로 구분한다.
- `ai-env session record|list|show|compact`. 도구·kakao/personal·프로젝트·Jira/브랜치·시각·주제를 파일명으로 찾는다.
- 7일 지난 기록은 종료 시 요약·gzip 검증 후 긴 본문을 안내 노트로 교체한다. 원문 복원과 기존 링크를 유지한다.
- 설치·도구 전환·압축 절차: [공용 세션 기록](docs/SESSION-JOURNAL.md), [SPEC-017](specs/SPEC-017-shared-session-journal.md).

## 동작 원리

```
.env (토큰) + config/settings.yaml + config/mcp_servers.yaml
                         │
                   ai-env sync
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
  Claude Desktop    Codex CLI/Desktop  ~/.claude/
  Claude Local      ~/.codex/AGENTS.md  (commands, rules, skills, hooks)
                    ~/.codex/rules/
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
```

**스킬/에이전트 소스**

- 개인 스킬: `megan-harness/skills/{category}/{skill}/` (카테고리: ai-env, code, data, meta, obsidian, orchestration, platform, ranking, work)
- 개인 에이전트: `megan-harness/agents/`
- 팀 스킬: `cde-skills`, `cde-ranking-skills` 심링크 (동기화 시 git pull 후 병합)
- 활성 cde-skills 플러그인 카테고리와 cde-ranking-skills 정본은 개인 사본보다 우선하며 원본 디렉토리에 심링크한다. 다른 이름 충돌은 기존 개인 우선 정책을 따른다.
- 동기화 대상(destination): `~/.claude/skills`, `~/.codex/skills`, `~/.agents/skills` (스킬) / `~/.claude/agents`, `~/.codex/agents` (에이전트)

```bash
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
```

## megan.won 문서 작성 규칙

- 팀 스킬 코드·런타임: 최신 develop 원본 유지.
- Jira·Agit·위키·리뷰·PR·커밋 본문: [개인 작성 규칙](.claude/rules/wiki-jira-writing-style.md) 우선.
- Epic: **팀 템플릿 유지 + 내용 간소화**. 일반 6섹션·인바운드 8헤더·rubric 형식 유지.
- [개인 Epic 진입점](megan-harness/skills/work/epic-curator/SKILL.md) · [템플릿 조사·예시](megan-harness/skills/work/epic-curator/references/template.md).
- `sync --skills-only`는 스킬만 배포한다. 규칙·글로벌 지침은 글로벌 설정 sync에 포함된다.

## 동기화 대상

| 대상 | 출력 경로 |
|------|----------|
| Claude Desktop | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Claude Code (글로벌) | `~/.claude/settings.json`, `CLAUDE.md`, `commands/`, `rules/`, `skills/`, `hooks/` |
| Claude Local | `.claude/settings.glocal.json` |
| Codex Desktop | `~/.codex/codex.config.json` |
| Codex CLI (글로벌) | `~/.codex/config.toml`, `AGENTS.md`, `rules/`, `skills/`, `commands/`, `project-profile.yaml` |
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

## claude --fallback

`ai-env sync`가 생성하는 `claude()` 쉘 함수. `config/settings.yaml`의 `agent_priority` 순서대로 에이전트를 시도하고, rate-limit 시 자동 전환.

```bash
claude --fallback              # claude → claude:sonnet → codex 자동 전환
claude --fallback -2           # 2순위부터 시작
claude --fallback --auto       # 모든 에이전트 자동 승인 모드
claude --fallback -l           # 우선순위 목록 출력
claude                         # 팀 플랜 Claude Code 프로필로 일반 실행 (~/.claude)
claude team                    # 팀 플랜 프로필 명시 실행
claude personal                # 개인 Anthropic 로그인 프로필로 실행 (~/.claude-personal)
claude enterprise              # legacy alias: 팀 플랜 프로필로 실행
```

| 옵션 | 설명 |
|------|------|
| `--auto` | Claude에 `--dangerously-skip-permissions` 주입. Codex는 프롬프트 실행 시 `codex exec -c "approval_policy='never'" -s workspace-write`로 동작 |
| `--dangerously-skip-permissions` | `--auto`와 동일 (wrapper가 소비) |
| `-N` | N순위부터 시작 (예: `-2`) |

**프로필 전환 (team / personal)**

`--settings`는 User 계층(`~/.claude/settings.json`)을 *대체*하지 못한다. 그래서
프로필 격리는 `CLAUDE_CONFIG_DIR`로 user-level config 디렉토리 자체를 바꾸는
방식으로 동작한다.

- team(기본): `~/.claude`를 그대로 사용 — Claude Code 팀 플랜 OAuth 로그인
- personal: `CLAUDE_CONFIG_DIR=~/.claude-personal` — 별도 `settings.json`과 개인
  Anthropic 로그인(OAuth 토큰은 이 디렉토리에 별도 저장)
- 권한(`permissions`)·`skipDangerousModePermissionPrompt`·hooks·MCP는 두 프로필 모두 동일
  (오직 **로그인 저장 위치만 분리**)
- 모델 ID는 둘 다 direct Claude Code 형식을 사용한다.
- 공용 자산(CLAUDE.md/commands/rules/skills/agents/hooks)은 `~/.claude`를 가리키는 심링크로 재사용
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
- 공용 자산(AGENTS.md/rules/skills/commands/agents/config.toml/hooks)은 `~/.codex` 심링크로 재사용
- `ai-env sync`가 `~/.codex-personal/` 심링크를 생성한다 (auth.json은 절대 심링크 안 함)
- 첫 personal 실행 시 `codex personal login`으로 개인 계정 로그인 필요
- `CODEX_CODE_PROFILE=personal codex ...`로도 개인 프로필을 기본 선택 가능

## Optional Claude Code on Bedrock

Bedrock AWS SSO profile helper는 필요할 때만 `ai-env bedrock` 명령으로 사용합니다.
기본 `claude`/`claude team` 설정에는 Bedrock env, AWS profile, `apiKeyHelper`를 넣지 않습니다.

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

## 중앙 환경변수 배포

- 원본: ai-env 루트 `.env` (Git 제외, 권한 600).
- 대상: 연결된 cde-skills·cde-ranking-skills의 `.env`와 `~/.cde-skills.env`.
- 각 저장소의 코드·템플릿이 참조하는 key만 복사한다.
- 홈 fallback에는 Jira·Wiki 인증과 cde-skills 원본 경로만 배포한다. 플러그인 cache에서도 저장소·다른 에이전트의 설정 없이 읽을 수 있다. 기존 파일의 다른 서비스 key는 보존한다.
- 기존 파일은 `.env-backups/`에 백업한다. 비밀값은 출력하지 않는다.
- 필요한 기존 값이 원본에 없거나 비어 있으면 배포를 중단한다.

```bash
uv run ai-env sync-env --dry-run
uv run ai-env sync-env
```

일반 `ai-env sync`에도 포함된다. `--skills-only`는 환경변수를 배포하지 않는다.
대상 파일을 직접 수정하지 않고 ai-env `.env`를 수정한 뒤 다시 배포한다.

Wiki Cloud에서 Jira 인증을 재사용하려면 같은 사이트의 `JIRA_URL`, `JIRA_EMAIL`, `JIRA_TOKEN`을 설정하고 `WIKI_TOKEN=''`로 별도 토큰을 명시적으로 비운다. 별도 `WIKI_TOKEN`이 있으면 Jira 토큰보다 먼저 사용된다. 명시적인 빈 값은 같은 Cloud 사이트·계정의 Jira 인증이 있는 경우에만 기존 Wiki 토큰을 대체할 수 있다.

`ai-env doctor`는 Jira·Wiki 필수 변수와 배포 누락·차이·파일 권한을 검사한다. 값이 있는 것과 실제 인증 성공은 구분하며, doctor는 네트워크 요청을 보내지 않는다. 실제 조회는 cde-skills 클라이언트로 확인한다. 셸에서 인증 변수를 사용한다면 `ai-env sync` 후 `source ./generated/shell_exports.sh`로 갱신한다. 빈 Wiki override도 export하므로 기존 셸의 오래된 토큰을 비울 수 있다.
