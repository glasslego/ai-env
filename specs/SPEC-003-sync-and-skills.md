---
id: SPEC-003
title: Claude Global Sync & Skills Management
status: implemented
created: 2025-06-01
updated: 2026-02-13
---

# SPEC-003: Claude Global Sync & Skills Management

## 1. 개요

`ai-env sync` 명령은 ai-env 프로젝트의 `.claude/` 디렉토리에 있는 설정 소스를 `~/.claude/`로 동기화하여, 모든 프로젝트에서 일관된 Claude Code 글로벌 설정을 유지한다.

동기화 대상은 4가지이며, skills 동기화는 personal 스킬과 team 스킬을 병합하는 독립적인 정책을 갖는다.

### 핵심 설계 원칙

- **Single Source of Truth**: ai-env 저장소가 모든 Claude 글로벌 설정의 유일한 소스
- **Personal-first**: 기본 동기화는 개인 스킬만 포함 (팀 스킬은 opt-in)
- **안전한 기본값**: `--dry-run`으로 사전 확인 가능, 시크릿은 `${VAR}` 치환으로 분리 관리

## 2. 동기화 대상 4가지

| # | 항목 | 소스 (ai-env) | 타겟 (~/.claude) | 동기화 전략 |
|---|------|---------------|------------------|-------------|
| 1 | CLAUDE.md | `.claude/global/CLAUDE.md` | `~/.claude/CLAUDE.md` | 단일 파일 복사 |
| 2 | settings.json | `.claude/global/settings.json.template` | `~/.claude/settings.json` | 템플릿 치환 후 생성 |
| 3 | commands/ | `.claude/commands/*.md` | `~/.claude/commands/` | .md 파일만 복사 |
| 4 | skills/ | personal + team 병합 | `~/.claude/skills/` | 서브디렉토리 단위 복사 |

### 2.1 CLAUDE.md 동기화

```
ai-env/.claude/global/CLAUDE.md  -->  ~/.claude/CLAUDE.md
```

- 단순 파일 복사 (`shutil.copy2`)
- 시스템 전역 Claude Code 지시사항 (코딩 규칙, 금지 사항, 기술 스택 등)
- `.claude/global/` 하위에 위치하여 프로젝트 루트의 `CLAUDE.md`와 분리

### 2.2 settings.json 생성 (템플릿 치환)

```
ai-env/.claude/global/settings.json.template  -->  ~/.claude/settings.json
                                          (${VAR} 치환)
```

- `settings.json.template` 파일 내의 `${VAR}` 플레이스홀더를 SecretsManager가 실제 값으로 치환
- 치환 우선순위: `.env` 파일 > `os.environ` 환경변수
- 치환 대상 예시: `${GITHUB_GLASSLEGO_TOKEN}`, `${JIRA_URL}`, `${BRAVE_API_KEY}` 등
- 템플릿에는 permissions (allow/deny 규칙)와 mcpServers (MCP 서버 설정) 포함

### 2.3 commands/ 동기화

```
ai-env/.claude/commands/*.md  -->  ~/.claude/commands/
```

- `.md` 파일만 복사 (다른 확장자 무시)
- Claude Code의 슬래시 커맨드로 등록됨 (예: `/commit`, `/sync`, `/review` 등)
- 대상 디렉토리가 없으면 자동 생성

### 2.4 skills/ 동기화 (병합)

```
personal skills + team skills  -->  ~/.claude/skills/
```

- 가장 복잡한 동기화 로직으로, 별도 섹션(3장)에서 상세 설명
- personal 스킬은 항상 포함, team 스킬은 CLI 옵션에 따라 opt-in

## 3. Skills 동기화 정책

### 3.1 설계 결정: Personal-first

| 구분 | 설명 | 기본 포함 |
|------|------|-----------|
| Personal skills | 개인 전용 스킬 | 항상 포함 |
| Team skills | 팀 공유 스킬 (`cde-*skills/`) | 옵션 지정 시에만 포함 |

**근거**: 팀 스킬은 수가 많고 컨텍스트 윈도우를 소비하므로, 필요할 때만 선택적으로 포함한다.

### 3.2 Personal 스킬 소스 우선순위

```
우선순위 1 (primary):   ai-env/megan-skills/skills/
                               ↓ (없으면 fallback)
우선순위 2 (fallback):  ai-env/.claude/skills/
```

- `megan-skills/`는 별도 git 서브모듈 또는 심링크로 관리되는 개인 스킬 저장소
- 두 소스 중 하나만 사용 (병합하지 않음)
- 소스 디렉토리 내의 `.`으로 시작하는 서브디렉토리는 제외

### 3.3 Team 스킬 디렉토리 탐지

team 스킬 디렉토리는 프로젝트 루트에서 `cde-*skills` 패턴의 이름을 가진 심링크(또는 디렉토리)다.

```
ai-env/
  cde-skills -> /Users/megan/work/cde/cde-skills          (심링크)
  cde-ranking-skills -> /Users/megan/work/cde/cde-ranking-skills  (심링크)
```

#### 탐지 조건

- 이름이 `cde-`로 시작하고 `skills`로 끝남
- 존재하는 경로 (broken symlink 제외)
- 심링크인 경우 `resolve()`로 실제 경로를 추적

#### 3가지 레이아웃 지원

team 스킬 디렉토리 내부는 다음 3가지 레이아웃 중 하나를 사용할 수 있다. 탐지 순서대로 우선 적용된다.

```
레이아웃 1 (nested):         cde-skills/.claude/skills/skill-name/SKILL.md
레이아웃 2 (skills subdir):  cde-skills/skills/skill-name/SKILL.md
레이아웃 3 (flat):           cde-skills/skill-name/SKILL.md
```

```
탐지 로직:
  cde-skills/ (resolve된 실제 경로)
    ├── .claude/skills/ 존재?  --> 레이아웃 1 (nested) 사용
    │     아니오 ↓
    ├── skills/ 존재?          --> 레이아웃 2 (skills subdir) 사용
    │     아니오 ↓
    └── 루트 자체를 스캔       --> 레이아웃 3 (flat) 사용
```

#### 유효한 스킬 판별

- 서브디렉토리 내에 `SKILL.md` 파일이 존재해야 유효한 스킬로 인정
- `.` 또는 `_`로 시작하는 서브디렉토리는 제외

### 3.4 Skills Include/Exclude 필터

CLI 옵션으로 team 스킬 포함 범위를 제어한다.

| 옵션 조합 | 동작 |
|-----------|------|
| (없음) | personal 스킬만 동기화 |
| `--skills-include cde-skills` | personal + cde-skills만 포함 |
| `--skills-include cde-skills --skills-include cde-ranking-skills` | personal + 지정된 2개 포함 |
| `--skills-exclude cde-ranking-skills` | personal + 모든 team 스킬 (cde-ranking-skills 제외) |
| `--skills-include`와 `--skills-exclude` 동시 사용 | include가 우선 (include 목록 내에서 exclude 필터 적용) |

### 3.5 병합 동기화 (_sync_skills_merged)

수집된 모든 스킬 디렉토리를 `~/.claude/skills/`에 복사한다.

- 동일 이름의 기존 디렉토리가 있으면 삭제 후 재복사 (`shutil.rmtree` + `shutil.copytree`)
- personal과 team 스킬의 이름이 겹치면, 수집 순서상 team 스킬이 나중에 복사되어 덮어씀

## 4. 동기화 플로우

### 4.1 전체 플로우차트

```
ai-env sync [옵션]
     |
     v
+---------------------------+
| 사전 검증                   |
| - .env 파일 존재 확인        |
| - 필수 환경변수 확인          |
|   (활성 MCP 서버 기준)       |
+---------------------------+
     |
     |  --mcp-only?  -----> MCP 설정 동기화만 실행
     |
     v
+---------------------------+
| Phase 1: Claude Global     |
| sync_claude_global_config()|
+---------------------------+
     |
     |--- 1. CLAUDE.md 복사
     |       .claude/global/CLAUDE.md -> ~/.claude/CLAUDE.md
     |
     |--- 2. settings.json 생성
     |       .claude/global/settings.json.template
     |         -> SecretsManager.substitute()
     |         -> ~/.claude/settings.json
     |
     |--- 3. commands/ 동기화
     |       .claude/commands/*.md -> ~/.claude/commands/
     |
     |--- 4. skills/ 병합 동기화
     |       _collect_skill_sources()
     |         -> personal: megan-skills/skills/ 또는 .claude/skills/
     |         -> team: cde-*skills/ (옵션에 따라)
     |       _sync_skills_merged()
     |         -> ~/.claude/skills/
     |
     |  --claude-only?  -----> 여기서 종료
     |
     v
+---------------------------+
| Phase 2: MCP Config        |
| MCPConfigGenerator         |
|   .save_all()              |
+---------------------------+
     |
     |--- Claude Desktop config
     |--- ChatGPT Desktop config
     |--- Antigravity config
     |--- Claude Code local (glocal)
     |--- Codex CLI config
     |--- Gemini CLI config
     |--- Shell exports
     |
     v
  동기화 완료
```

### 4.2 Skills 수집 플로우

```
_collect_skill_sources(project_root, skills_include, skills_exclude)
     |
     v
  [1] Personal 스킬 수집 (항상)
     |
     |  megan-skills/skills/ 존재?
     |    예 --> personal_dir = megan-skills/skills/
     |   아니오 --> personal_dir = .claude/skills/
     |
     |  personal_dir 내 서브디렉토리 수집
     |  (`.`으로 시작하는 디렉토리 제외)
     |
     v
  [2] Team 스킬 수집 (조건부)
     |
     |  skills_include도 skills_exclude도 없음?
     |    예 --> personal만 반환 (종료)
     |
     |  프로젝트 루트에서 cde-*skills 패턴 탐색
     |    |
     |    각 디렉토리에 대해:
     |      - broken symlink? --> 건너뜀
     |      - include 필터에 없음? --> 건너뜀
     |      - exclude 필터에 있음? --> 건너뜀
     |      |
     |      레이아웃 판별 (nested > skills subdir > flat)
     |      |
     |      scan_dir 내 서브디렉토리 중
     |      SKILL.md가 존재하는 것만 수집
     |
     v
  personal + team 스킬 리스트 반환
```

## 5. 동기화 헬퍼 함수

### 5.1 함수 계층 구조

```
sync_claude_global_config()           -- 진입점
  |
  +-- _sync_file_or_dir()             -- 라우터 (경로 이름으로 전략 결정)
  |     +-- _sync_file()              -- 단일 파일 복사 (CLAUDE.md)
  |     +-- _sync_md_files()          -- .md 파일만 복사 (commands/)
  |     +-- _sync_subdirectories()    -- 서브디렉토리 복사 (skills/)
  |     +-- _sync_directory()         -- 전체 디렉토리 복사 (기타)
  |
  +-- _sync_skills_merged()           -- skills 전용 (personal + team 병합)
  |     +-- _collect_skill_sources()  -- 스킬 소스 수집
  |
  +-- SecretsManager.substitute()     -- ${VAR} 치환 (settings.json)
```

### 5.2 각 헬퍼 함수 상세

| 함수 | 역할 | 대상 | 반환값 |
|------|------|------|--------|
| `_sync_file()` | 단일 파일 복사 (`shutil.copy2`) | CLAUDE.md 등 | `(파일명, 1)` |
| `_sync_md_files()` | 디렉토리 내 `*.md` 파일만 복사 | commands/ | `("commands/ (N files)", N)` |
| `_sync_subdirectories()` | 서브디렉토리 단위 복사, 기존 존재 시 삭제 후 복사 | skills/ | `("skills/ (N items)", N)` |
| `_sync_directory()` | 전체 디렉토리 복사, 기존 존재 시 삭제 후 복사 | 기타 | `("dirname/", 1)` |
| `_sync_file_or_dir()` | 경로 이름(`commands`, `skills`, 기타)으로 위 함수 중 적절한 것을 선택하는 라우터 | 모든 항목 | 선택된 함수의 반환값 |
| `_sync_skills_merged()` | `_collect_skill_sources()`로 수집 후 각 스킬 디렉토리를 타겟에 복사 | skills/ | `("skills/ (N items)", N)` |

### 5.3 에러 처리

- `_sync_file()`: `PermissionError`, `OSError`를 명시적으로 re-raise
- 존재하지 않는 소스 경로: `_sync_file_or_dir()`에서 `("", 0)` 반환 (무시)
- broken symlink: `_collect_skill_sources()`에서 `item.exists()` 체크로 건너뜀

## 6. CLI 인터페이스

### 6.1 sync 명령 옵션

```bash
ai-env sync [OPTIONS]
```

| 옵션 | 타입 | 설명 |
|------|------|------|
| `--dry-run` | flag | 실제 복사 없이 미리보기 |
| `--claude-only` | flag | Claude 글로벌 설정만 동기화 (Phase 1만) |
| `--mcp-only` | flag | MCP 설정만 동기화 (Phase 2만) |
| `--skills-include` | multiple | 포함할 team 스킬 디렉토리 (여러 번 지정 가능) |
| `--skills-exclude` | multiple | 제외할 team 스킬 디렉토리 (여러 번 지정 가능) |

### 6.2 사용 예시

```bash
# 전체 동기화 (personal 스킬만, MCP 포함)
ai-env sync

# 미리보기
ai-env sync --dry-run

# Claude 설정만 동기화 (MCP 제외)
ai-env sync --claude-only

# cde-skills 팀 스킬 포함
ai-env sync --skills-include cde-skills

# 모든 팀 스킬 포함하되, cde-ranking-skills 제외
ai-env sync --skills-exclude cde-ranking-skills

# 여러 팀 스킬 선택적 포함
ai-env sync --skills-include cde-skills --skills-include cde-ranking-skills
```

### 6.3 사전 검증 (Pre-sync Validation)

sync 명령 실행 시 다음 사항을 사전 검증한다:

1. **`.env` 파일 존재 확인**: 없으면 경고 메시지 출력 (동기화는 계속 진행)
2. **필수 환경변수 확인** (MCP 동기화 시, `--claude-only`가 아닌 경우):
   - 활성화된(`enabled=True`) MCP 서버 순회
   - SSE 서버: `url_env`에 해당하는 환경변수 확인
   - stdio 서버: `env_keys`에 해당하는 환경변수 확인
   - 누락된 변수가 있으면 경고 메시지 출력 (최대 5개 표시)

### 6.4 실행 결과 출력

```
Syncing AI environment configurations...

Claude Code Global Config
   ai-env/.claude -> ~/.claude
  Synced CLAUDE.md
    -> /Users/megan/.claude/CLAUDE.md
  Synced settings.json
    -> /Users/megan/.claude/settings.json
  Synced commands/ (12 files)
    -> /Users/megan/.claude/commands
  Synced skills/ (9 items)
    -> /Users/megan/.claude/skills

AI Tools Configuration
  Synced claude_desktop
    -> ~/Library/Application Support/Claude/claude_desktop_config.json
  ...

Sync complete!
```

## 7. 파일 시스템 구조

### 7.1 소스 구조 (ai-env 프로젝트)

```
ai-env/
  .claude/
    global/
      CLAUDE.md                    # 글로벌 CLAUDE.md 소스
      settings.json.template       # settings.json 템플릿 (${VAR} 포함)
    commands/
      commit.md                    # 슬래시 커맨드 정의 파일들
      sync.md
      review.md
      ...
    skills/                        # personal 스킬 (fallback)
      jira-weekly-update/
        SKILL.md
      trino-analyst/
        SKILL.md
      ...
    settings.glocal.json           # 다른 프로젝트용 MCP 템플릿 (sync 대상 아님)
    settings.local.json            # 이 프로젝트 전용 (sync 대상 아님)
  megan-skills/                    # personal 스킬 (primary)
    skills/
      agit-search/
        SKILL.md
      elasticsearch-query/
        SKILL.md
      ...
  cde-skills -> /path/to/cde-skills       # team 스킬 심링크
  cde-ranking-skills -> /path/to/...       # team 스킬 심링크
```

### 7.2 타겟 구조 (~/.claude)

```
~/.claude/
  CLAUDE.md                        # 글로벌 지시사항
  settings.json                    # 권한 + MCP 서버 (치환 완료)
  commands/
    commit.md
    sync.md
    ...
  skills/
    agit-search/                   # personal 스킬
      SKILL.md
    elasticsearch-query/
      SKILL.md
    team-skill-name/               # team 스킬 (옵션 지정 시)
      SKILL.md
    ...
```

## 8. 구현 위치

| 파일 | 주요 함수/클래스 |
|------|-----------------|
| `src/ai_env/core/sync.py` | `sync_claude_global_config()`, `_collect_skill_sources()`, `_sync_skills_merged()`, 헬퍼 함수들 |
| `src/ai_env/core/secrets.py` | `SecretsManager.substitute()` (${VAR} 치환) |
| `src/ai_env/cli.py` | `sync()` CLI 명령 (Click) |
| `.claude/global/CLAUDE.md` | 글로벌 CLAUDE.md 소스 |
| `.claude/global/settings.json.template` | settings.json 템플릿 |
| `.claude/commands/` | 슬래시 커맨드 소스 |

## 9. 제약 사항 및 알려진 한계

1. **personal 스킬 소스는 하나만 사용**: `megan-skills/skills/`와 `.claude/skills/` 중 하나만 선택 (병합하지 않음)
2. **skills 이름 충돌**: personal과 team 스킬의 서브디렉토리 이름이 같으면, 나중에 복사되는 team 스킬이 덮어씀
3. **settings.json 완전 덮어쓰기**: sync 실행 시 기존 `~/.claude/settings.json`이 통째로 교체됨 (부분 병합 미지원)
4. **commands/ 누적**: 기존 `~/.claude/commands/`에 있던 파일 중 소스에 없는 것은 삭제되지 않음 (누적됨)
5. **skills/ 누적**: 마찬가지로 소스에 없는 스킬 디렉토리는 타겟에 남아 있음 (명시적 삭제 필요)
6. **macOS 전용 경로**: outputs 설정의 Desktop 앱 경로가 `~/Library/Application Support/`로 macOS 기준
