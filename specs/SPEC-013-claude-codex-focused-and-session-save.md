---
id: SPEC-013
title: Claude+Codex 중심 정리 및 Obsidian 세션 저장 기능
status: implemented
created: 2026-04-29
updated: 2026-04-30
---

# SPEC-013: Claude+Codex 중심 정리 및 Obsidian 세션 저장 기능

## 1. 배경

ai-env는 현재 Claude Code, Codex, Gemini, Antigravity, ChatGPT Desktop 등 5개 이상의
AI 도구를 동시에 지원한다. 실제 활용은 **Claude Code + Codex** 조합으로 수렴하고
있으며, 미사용 타겟의 동기화가 매번 수행되어 다음 부작용이 있다.

- `ai-env sync` 시 비활성 타겟 설정도 매번 새로 생성 → 노이즈
- Gemini/Antigravity 관련 코드/테스트가 유지보수 부담
- Codex가 Claude의 SKILL.md, commands/, project-profile.yaml을 충분히 활용하지 못함
- 스킬 도중 컨텍스트(현재 작업 결정/요약)를 영구 저장할 수단이 부족함
  (handoff는 다음 세션 인계용일 뿐, Obsidian 노트로 내보내는 경로 부재)

## 2. 목표

1. **사용 범위 정리**: 기본 배포는 Claude Code + Codex만 활성화. Gemini/Antigravity/
   ChatGPT Desktop은 `enabled: false`로 비활성화하고 sync 파이프라인에서 가드.
2. **Codex의 Claude 자산 활용 극대화**: SKILL.md 정규화에 더해 commands/, hooks/ MD
   문서, project-profile.yaml을 Codex가 읽을 수 있도록 미러.
3. **Obsidian 세션 저장**: 스킬/대화 도중 호출되어 현재 세션의 핵심 컨텍스트를 사용자
   Obsidian vault의 지정 디렉토리에 마크다운으로 영구 저장. CLI(`ai-env session save`)
   + 스킬(`session-save`)로 양 에이전트에서 동작.

## 3. Acceptance Criteria

### AC-1 (정리)
- `config/settings.yaml`의 `providers.gemini.enabled`, `providers.antigravity.enabled`가
  `false`이고, `agent_priority`는 Claude+Codex만 포함한다.
- `MCPConfigGenerator.save_all()`은 `providers[name].enabled = false`인 타겟의
  config 파일을 생성하지 않는다 (단, `claude_*` / `codex_*` / `shell_exports`는 항상 생성).

### AC-2 (Codex 호환)
- `sync_codex_global_config()` 호출 시 다음이 함께 생성된다:
  - `~/.codex/AGENTS.md` (기존)
  - `~/.codex/skills/` (기존, frontmatter 정규화)
  - `~/.codex/commands/` (신규: `.claude/commands/*.md` + `.claude/commands/phases/*.md` 정규화 복사)
  - `~/.codex/project-profile.yaml` (신규: 프로젝트 루트의 `.claude/project-profile.yaml` 복사)
- 정규화는 SKILL.md와 동일하게 frontmatter가 strict YAML로 정렬됨.

### AC-3 (Obsidian 저장 — 코어)
- `ai_env.core.session_save.save_session(...)` 함수가 다음 입력을 받아 결과 경로를 반환:
  - `vault: Path` (Obsidian 루트, 미지정 시 `settings.yaml` → `obsidian.base` → `~/Documents/Obsidian/PARA-2025`)
  - `subdir: str` (기본 `00_session`)
  - `note: str | None` (사용자가 명시한 메모)
  - `title: str | None` (파일 제목, 미지정 시 시간+브랜치+세션 prefix)
  - `extras: dict[str, str] | None` (추가 섹션)
- 출력 파일은 `{vault}/{subdir}/{YYYY-MM-DD}-{slug}.md` 형식이며 같은 slug 충돌 시 `-2`, `-3` suffix.
- 파일은 다음 섹션을 포함한다:
  - frontmatter (`title`, `created`, `tags: [session, ai-env]`, `project`, `branch`)
  - `## Note` (사용자 노트, 있으면)
  - `## Git Snapshot` (`git status -s`, `git log --oneline -5`)
  - `## Recent Changes` (`git diff --stat`)
  - `## Extras` (옵셔널)

### AC-4 (CLI)
- `uv run ai-env session save [--note ...] [--vault ...] [--subdir ...] [--title ...] [--dry-run]`
  명령이 위 함수를 호출하고 결과 경로/미리보기를 출력한다.
- `--dry-run`은 실제 파일을 쓰지 않고 본문 미리보기를 stdout에 출력.

### AC-5 (스킬)
- `.claude/skills/session-save/SKILL.md`가 새로 생성되어 다음을 안내:
  - 트리거 키워드: "세션 저장", "옵시디언 저장", "session save", "obsidian 저장" 등
  - 단계: 사용자에게 note 확인 → `ai-env session save --note "<note>"` 실행 → 결과 경로 보고
- 스킬은 Codex에서도 동작 (CLI에 의존, frontmatter도 정규화됨).

### AC-6 (테스트)
- `tests/core/test_session_save.py`로 코어 동작 (vault 자동 생성, slug 충돌, frontmatter)
  검증.
- `tests/cli/test_session_cmd.py`로 CLI 동작 (dry-run, --note, --vault) 검증.
- 기존 277개 테스트 + 신규 테스트 모두 통과, 커버리지 65% 이상 유지.

### AC-7 (문서)
- `CLAUDE.md`, `AGENTS.md`(Codex), `README.md`에 다음 반영:
  - 지원 대상이 Claude Code + Codex 중심으로 정리됨
  - `ai-env session save` 사용 예시
  - `session-save` 스킬 트리거 안내

## 4. Out of Scope

- Gemini/Antigravity/ChatGPT 관련 코드 자체 삭제는 하지 않는다. 비활성 가드만 추가하여
  필요 시 settings.yaml에서 `enabled: true`로 다시 켤 수 있도록 둔다.
- 옵시디언에 저장된 노트의 자동 색인/링크 그래프 통합은 별도 SPEC.

## 5. Tasks

- [x] Task-01: `core/session_save.py` 코어 모듈 구현 (Iteration 1)
- [x] Task-02: `cli/session_cmd.py` + main 등록 (Iteration 2)
- [x] Task-03: `.claude/skills/session-save/SKILL.md` 작성 (Iteration 3)
- [x] Task-04: Codex sync 강화 (commands/profile 미러) (Iteration 4)
- [x] Task-05: providers 비활성화 + save_all 가드 (Iteration 5)
- [x] Task-06: session_save 단위 테스트 (21개 추가, Iteration 6)
- [x] Task-07: CLI session 단위 테스트 (4개 추가, Iteration 7)
- [x] Task-08: sync 회귀 테스트 보강 (provider 가드 + commands 미러, Iteration 8)
- [x] Task-09: CLAUDE.md/README 문서 동기화 (Iteration 9)
- [x] Task-10: 최종 lint/test/spec close (Iteration 10)

## 7. 결과

- 테스트: 277 → 309 (+32 신규), 모두 통과
- 커버리지: 67.47% → 70.07% (65% 임계 충족)
- 신규 모듈: `src/ai_env/core/session_save.py`, `src/ai_env/cli/session_cmd.py`
- 신규 스킬: `.claude/skills/session-save/SKILL.md`
- 갱신: `core/sync.py`(commands/profile 미러), `core/project_sync.py`(sync_assets), `mcp/generator.py`(provider enabled 가드), `cli/sync_cmd.py`(gemini 조건부)
- 설정: `config/settings.yaml`에서 gemini/antigravity/chatgpt providers 비활성, `obsidian_base` 추가
- 문서: `CLAUDE.md`, `README.md` 갱신

## 6. 검증 절차

```bash
uv run pytest tests/ -x -q
uv run ruff check . && uv run ruff format --check .
uv run ai-env sync --dry-run
uv run ai-env session save --note "test" --dry-run
```
