# Project Setup Skill

새 프로젝트에 ai-env 표준 환경을 적용하는 skill입니다.

## 적용 항목

### 1. 디렉토리 구조
```
project/
├── .claude/
│   ├── settings.local.json  # MCP 서버 설정
│   └── commands/            # 프로젝트별 명령어
├── .codex/
│   └── config.toml
├── .gemini/
│   └── settings.local.json
├── .env                     # 프로젝트별 환경변수 (또는 symlink)
├── CLAUDE.md               # Claude Code 지시문
├── GEMINI.md               # Gemini CLI 지시문
└── AGENTS.md               # 공통 에이전트 가이드
```

### 2. 환경변수 연동 방식

**Option A: Symlink** (추천)
```bash
ln -s /Users/megan/work/ai-env/.env .env
```

**Option B: Source**
```bash
# .zshrc 또는 프로젝트 스크립트에 추가
source /Users/megan/work/ai-env/generated/shell_exports.sh
```

**Option C: 필요한 것만 복사**
필요한 토큰만 프로젝트 .env에 복사

### 3. MCP 설정 적용

ai-env의 mcp_servers.yaml을 기반으로 프로젝트별 설정 생성:

```bash
cd /Users/megan/work/ai-env
uv run ai-env generate claude-local > /path/to/project/.claude/settings.local.json
```

### 4. CLAUDE.md 생성

```bash
cd /path/to/project
claude /init  # 기본 CLAUDE.md 생성
```

이후 다음 내용 추가:
- 프로젝트별 규칙
- 사용 기술 스택
- 금지 사항

## 체크리스트

- [ ] .claude/settings.local.json 생성
- [ ] .codex/config.toml 생성
- [ ] .gemini/settings.local.json 생성
- [ ] .env 연동 (symlink 또는 복사)
- [ ] CLAUDE.md 생성 및 커스터마이즈
- [ ] .gitignore에 .env 추가
