# ai-env Claude Code 설정

이 디렉토리는 모든 Claude Code 및 AI 에이전트 설정의 **단일 소스(Single Source of Truth)**입니다.

## 📁 디렉토리 구조

```
.claude/
├── global/                    # 글로벌 설정 (→ ~/.claude로 동기화)
│   ├── CLAUDE.md              # 시스템 와이드 규칙
│   ├── settings.json.template # Claude Code 설정 템플릿
│   ├── commands/              # 슬래시 명령어
│   │   ├── fix-github-issue.md
│   │   ├── commit.md
│   │   ├── review.md
│   │   └── ...
│   └── skills/                # 서브에이전트 스킬
│       ├── coding-standards/
│       ├── pyspark-best-practices/
│       ├── elasticsearch-query/
│       └── ...
├── commands/                  # ai-env 프로젝트 전용 명령어
│   ├── setup.md
│   ├── sync.md
│   └── ...
├── skills/                    # ai-env 프로젝트 전용 스킬
│   ├── mcp-config/
│   └── project-setup/
└── settings.local.json        # ai-env 로컬 설정
```

## 🔄 동기화

### 전체 동기화
```bash
cd /Users/megan/work/ai-env
uv run ai-env sync
```

### Claude 설정만 동기화
```bash
uv run ai-env sync --claude-only
```

### 상태 확인
```bash
uv run ai-env status
```

## 📝 설정 수정 워크플로우

1. **ai-env에서 수정**: `.claude/global/` 아래 파일 수정
2. **동기화 실행**: `uv run ai-env sync`
3. **Git 커밋**: 변경사항을 버전 관리

```bash
# 예: commands 추가
vi .claude/global/commands/new-command.md
uv run ai-env sync
git add .claude/global/commands/new-command.md
git commit -m "feat: add new-command"
```

## 🔐 환경변수 템플릿

`settings.json.template`은 환경변수 플레이스홀더를 사용합니다:

```json
{
  "env": {
    "GITHUB_GLASSLEGO_TOKEN": "${GITHUB_GLASSLEGO_TOKEN}"
  }
}
```

동기화 시 `.env` 파일의 값으로 자동 치환됩니다.

## 📦 동기화 대상

| 소스 (ai-env) | 대상 |
|---------------|------|
| `.claude/global/CLAUDE.md` | `~/.claude/CLAUDE.md` |
| `.claude/global/settings.json.template` | `~/.claude/settings.json` |
| `.claude/global/commands/` | `~/.claude/commands/` |
| `.claude/global/skills/` | `~/.claude/skills/` |

## ⚠️ 주의사항

- **`~/.claude`를 직접 수정하지 마세요** - 다음 동기화 시 덮어씌워집니다
- 모든 설정 변경은 ai-env에서 하고 `sync` 명령으로 배포하세요
- `.env` 파일은 절대 Git에 커밋하지 마세요
