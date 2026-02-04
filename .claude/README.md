# ~/.claude 디렉토리 구조 Best Practice

> ai-env에서 관리하고 `ai-env sync --claude-only`로 `~/.claude/`에 배포하는 구조.
> 이 문서 자체가 정답이자 레퍼런스.

## 디렉토리 맵

```
~/.claude/                          # Claude Code 글로벌 설정 루트
│
├── CLAUDE.md                       # [핵심] 글로벌 시스템 프롬프트
│                                   #   → 모든 프로젝트에 자동 적용
│                                   #   → 코딩 규칙, 금지사항, 기술 스택 정의
│
├── settings.json                   # [핵심] 글로벌 설정
│                                   #   → MCP 서버 연결 (jira, github, etc.)
│                                   #   → 권한 허용 목록 (Bash, MCP)
│                                   #   → ⚠️ 토큰 포함 — git에 올리지 않음
│                                   #   → ai-env에서는 .template로 관리
│
├── commands/                       # [사용자 정의] 슬래시 커맨드
│   ├── commit.md                   #   /commit — 커밋 + CLAUDE.md 연동
│   ├── review.md                   #   /review — 코드 리뷰
│   ├── setup.md                    #   /setup  — 프로젝트 초기 설정
│   ├── sync.md                     #   /sync   — ai-env 동기화
│   └── ...                         #   → 파일명 = 커맨드명 (확장자 제외)
│                                   #   → 프로젝트 .claude/commands/도 가능 (로컬 우선)
│
├── skills/                         # [사용자 정의] 도메인 지식 + 자동화 도구
│   ├── {skill-name}/               #   각 스킬 = 독립 디렉토리
│   │   ├── SKILL.md                #   [필수] 스킬 설명 + 사용법 (진입점)
│   │   ├── .config.json            #   [선택] 스킬별 설정값
│   │   ├── scripts/                #   [선택] 실행 스크립트 (Python, Bash)
│   │   └── references/             #   [선택] 참고 문서, 예제, 템플릿
│   │
│   ├── spark-debug/                #   예: Spark 디버깅 스킬
│   ├── elasticsearch-query/        #   예: ES 쿼리 빌더 스킬
│   ├── pyspark-best-practices/     #   예: PySpark 코딩 가이드
│   └── ...
│
├── projects/                       # [자동생성] 프로젝트별 메타데이터
│   └── -Users-megan-work-cde-*/    #   → Claude Code가 자동 관리
│                                   #   → 수동 편집 불필요
│
│── ─ ─ ─ 아래는 Claude Code 자동 관리 영역 ─ ─ ─
│
├── cache/                          # 임시 캐시 (changelog 등)
├── debug/                          # 세션 디버그 로그
├── file-history/                   # 파일 변경 이력 (세션별)
├── history.jsonl                   # 대화 히스토리
├── ide/                            # IDE 연동 락 파일
├── paste-cache/                    # 붙여넣기 캐시
├── plans/                          # 실행 계획 저장
├── plugins/                        # 플러그인 메타데이터
├── session-env/                    # 세션 환경변수
├── shell-snapshots/                # 셸 스냅샷
├── stats-cache.json                # 사용 통계
├── statsig/                        # Feature flag 캐시
├── tasks/                          # 태스크 상태
├── telemetry/                      # 원격 측정
└── todos/                          # 세션별 TODO 목록
```

## 핵심 원칙

### 1. 사용자가 관리하는 것 vs Claude가 관리하는 것

| 영역 | 관리 주체 | 파일 |
|------|----------|------|
| 글로벌 프롬프트 | **사용자** (ai-env) | `CLAUDE.md` |
| MCP/권한 설정 | **사용자** (ai-env) | `settings.json` |
| 슬래시 커맨드 | **사용자** (ai-env) | `commands/*.md` |
| 도메인 스킬 | **사용자** (ai-env + cde-skills) | `skills/*/` |
| 세션 데이터 | **Claude Code** 자동 | `debug/`, `todos/`, `history.jsonl` 등 |
| 프로젝트 메타 | **Claude Code** 자동 | `projects/` |

### 2. CLAUDE.md 작성 가이드

```markdown
# 좋은 CLAUDE.md 구조

## 절대 금지 (Never Do)          ← 가장 먼저, 명확하게
## 항상 해야 할 것 (Always Do)    ← 긍정적 지시
## 기술 스택 기본 설정            ← 구체적 도구/버전
## MCP 사용법                    ← 연동 서비스 안내
## 문제 해결 패턴                 ← 안티패턴 → 올바른 패턴
## 언어                          ← 사용자-코드-커밋 언어 정책
```

핵심 팁:
- **금지사항이 허용사항보다 중요** — LLM은 "하지 마라"를 놓치기 쉬움
- **구체적 예시 포함** — "KISS principle" 보다 "❌ 이렇게 → ✅ 이렇게"
- **프로젝트 CLAUDE.md와 역할 분리** — 글로벌은 팀 공통, 프로젝트는 해당 repo 전용

### 3. commands/ 작성 가이드

```markdown
# 커맨드 파일 구조 (예: review.md)
---
description: 한 줄 설명 (커맨드 목록에 표시됨)
---

## 수행 단계
1. 첫 번째 단계
2. 두 번째 단계
...
```

네이밍 규칙:
- 파일명 = 커맨드명: `review.md` → `/review`
- 동사형: `commit`, `setup`, `sync`, `review`
- 복합어는 하이픈: `fix-github-issue`, `cleanup-branches`
- 프로젝트 로컬 `.claude/commands/`가 글로벌보다 우선

### 4. skills/ 작성 가이드

```
skills/{skill-name}/
├── SKILL.md              # [필수] 진입점 — 이것만 있으면 스킬로 인식
│                         #   frontmatter: name, description
│                         #   본문: 사용법, 예제 코드, 주의사항
│
├── .config.json          # [선택] 런타임 설정값
│                         #   클러스터 주소, 기본값, 패턴 등
│
├── scripts/              # [선택] 실행 가능한 코드
│   ├── main.py           #   메인 로직
│   └── utils.py          #   헬퍼 함수
│
└── references/           # [선택] 참고 자료
    ├── examples.md       #   사용 예제 모음
    └── patterns.md       #   자주 쓰는 패턴
```

SKILL.md frontmatter 예시:
```yaml
---
name: spark-debug
description: |
  Spark application 디버깅 및 로그 모니터링.
  Use this skill when user needs to:
  - Debug Spark applications
  - Monitor application logs
---
```

**description 작성이 핵심** — Claude Code가 어떤 스킬을 쓸지 description으로 판단함.

### 5. settings.json 보안

```
ai-env repo 구조:
  .claude/global/settings.json.template   ← git 추적 (토큰 = 플레이스홀더)

동기화 후:
  ~/.claude/settings.json                 ← git 미추적 (실제 토큰)
```

- 토큰은 `config/secrets.yaml` (gitignore) 또는 환경변수로 주입
- `.template`에는 `"${GITHUB_TOKEN}"` 같은 플레이스홀더 사용
- `ai-env sync`가 secrets 치환하여 최종 settings.json 생성

## 소스 관리 흐름 (ai-env)

```
ai-env repo (git)                    ~/.claude/ (로컬, git 미추적)
─────────────────                    ──────────────────────────────
.claude/global/CLAUDE.md        →    CLAUDE.md
.claude/global/settings.json    →    settings.json (토큰 치환)
.claude/commands/               →    commands/
.claude/skills/ (개인)          ─┐
cde-skills/ (팀 symlink)       ─┤→  skills/ (머지 결과)
                                 │
                                 └   SKILL.md가 있는 디렉토리만 인식
```

## 프로젝트 레벨 (.claude/)

각 프로젝트 루트에도 `.claude/` 디렉토리를 둘 수 있음:

```
my-project/
├── .claude/
│   ├── commands/           # 프로젝트 전용 커맨드 (글로벌보다 우선)
│   └── settings.local.json # 프로젝트 전용 설정 (Bash 권한 등)
├── CLAUDE.md               # 프로젝트 전용 프롬프트 (글로벌에 추가)
├── .mcp.json               # 프로젝트 전용 MCP (보통 비워둠 → 글로벌 상속)
└── ...
```

설정 우선순위 (높은 것이 이김):
1. 프로젝트 `CLAUDE.md` + `.claude/settings.local.json`
2. 글로벌 `~/.claude/CLAUDE.md` + `~/.claude/settings.json`

**팁**: 프로젝트 `.mcp.json`은 `{"mcpServers": {}}`로 비워두면 글로벌 MCP를 자동 상속.

## 자주 하는 실수

| 실수 | 해결 |
|------|------|
| settings.json에 토큰 하드코딩 후 git push | `.template` + secrets 분리 |
| 프로젝트 .mcp.json에 글로벌과 동일한 MCP 복사 | 비워두고 글로벌 상속 |
| skills/ 안에 SKILL.md 없는 디렉토리 | sync가 무시함 — 반드시 SKILL.md 생성 |
| commands/ 파일에 frontmatter 누락 | `description:` 없으면 /help에 설명 안 뜸 |
| CLAUDE.md에 허용사항만 나열 | 금지사항을 먼저, 구체적으로 |
| 자동생성 디렉토리 (debug/, todos/) 수동 편집 | 건드리지 않음 — Claude Code 전용 |
