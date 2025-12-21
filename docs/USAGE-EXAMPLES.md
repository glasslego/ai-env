# ai-env 효과적 사용 가이드

> ai-env가 해결하는 문제: Claude, Codex, Gemini, ChatGPT 등 여러 AI 도구의 API 키, MCP 서버, 코딩 가이드라인을 **한 곳에서 관리**하고 각 도구 형식으로 자동 변환.

---

## 시나리오 1: 처음 설정 (Day 0)

**상황**: 새 맥에서 AI 도구들을 세팅하려는데, Claude Desktop, Codex, Gemini CLI 각각 설정이 다르다.

```bash
# 1. 클론 & 환경 설정
git clone <repo> ~/work/ai-env && cd ~/work/ai-env
uv sync --all-extras && pre-commit install

# 2. API 키 등록 (.env에 한 번만)
cat > .env << 'EOF'
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=AIza...
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_...
EOF

# 3. 전체 동기화 — 이 한 줄이면 끝
uv run ai-env sync

# 4. 셸 함수 활성화 (.zshrc에 추가)
echo 'source ~/work/ai-env/generated/shell_exports.sh' >> ~/.zshrc
source ~/.zshrc
```

**결과**: 아래가 모두 자동 설정됨
- Claude Desktop: `claude_desktop_config.json` (MCP 서버 + API 키)
- ChatGPT Desktop: `config.json`
- Codex Desktop: `codex.config.json`
- Claude Code: `~/.claude/settings.json` + `CLAUDE.md` + `commands/` + `skills/`
- Codex CLI: `~/.codex/config.toml` + `AGENTS.md` + `skills/`
- Gemini CLI: `~/.gemini/settings.json` + `GEMINI.md`
- Shell: `claude --fallback` 함수

---

## 시나리오 2: 일상적인 코딩 (매일)

### 2a. Claude Code로 코딩하다가 rate-limit 걸렸을 때

```bash
# 그냥 claude 대신 --fallback으로 시작
claude --fallback

# Opus가 rate-limit되면 자동으로:
# 🚀 Starting claude...
# ⚠ claude rate-limit 감지 — cooldown 60분
# 🚀 Starting claude (sonnet)...    ← Sonnet으로 자동 전환
# (Sonnet도 소진되면)
# 🚀 Starting codex...               ← Codex로 자동 전환
```

**핵심**: 터미널을 닫을 필요 없이, 작업 컨텍스트(핸드오프 파일)가 다음 에이전트로 자동 전달됨.

### 2b. 프롬프트와 함께 자동 모드로 실행

```bash
# Claude → Codex 모두 자동 승인으로 실행
claude --fallback --auto "로그인 API에 2FA 지원 추가해줘"

# 2순위(Sonnet)부터 시작 (Opus quota 아끼고 싶을 때)
claude --fallback -2 "테스트 깨진 거 고쳐줘"

# 3순위(Codex)부터 바로 시작
claude --fallback -3 "리팩터링해줘"
```

### 2c. 현재 에이전트 우선순위 확인

```bash
claude --fallback -l
# 출력:
# Agent fallback priority:
#   1. claude
#   2. claude (sonnet)
#   3. codex
```

---

## 시나리오 3: 새 프로젝트에서 Claude + Codex 같이 쓰기

**상황**: 내 프로젝트에 CLAUDE.md와 .claude/skills/가 있는데, Codex에서도 같은 가이드라인과 스킬을 쓰고 싶다.

```bash
cd ~/work/my-project

# Claude 자산을 Codex 형식으로 동기화
ai-env project sync-codex

# 결과:
# ✅ CLAUDE.md → AGENTS.md (심볼릭 링크)
# ✅ .claude/skills/ → .codex/skills/ (Codex 호환 YAML로 정규화 복사)
```

이제 `codex`를 실행하면 CLAUDE.md의 가이드라인이 AGENTS.md로 읽히고,
`.claude/skills/`의 스킬이 Codex 호환 형태로 `.codex/skills/`에서 사용 가능.

```bash
# skills만 동기화 (AGENTS.md는 건드리지 않음)
ai-env project sync-codex --skills-only

# 복사 모드 (심볼릭 링크 대신 파일 복사)
ai-env project sync-codex --copy
```

---

## 시나리오 4: MCP 서버 추가/변경

**상황**: 새 MCP 서버를 Claude Desktop과 Codex에 동시에 추가하고 싶다.

```bash
# 1. config/mcp_servers.yaml에 서버 정의 추가
cat >> config/mcp_servers.yaml << 'EOF'

my-new-server:
  enabled: true
  type: stdio
  command: npx
  args: [-y, "@my-org/mcp-server"]
  env_keys: [MY_API_TOKEN]        # .env에서 자동으로 가져옴
  targets:
    - claude_desktop               # Claude Desktop에 배포
    - codex_desktop                # Codex Desktop에 배포
    - claude_local                 # 프로젝트 로컬 Claude에도
EOF

# 2. .env에 토큰 추가
echo 'MY_API_TOKEN=tok_...' >> .env

# 3. 동기화 — 모든 타겟에 자동 배포
ai-env sync

# 미리보기만 하고 싶으면
ai-env sync --dry-run
```

**포인트**: 서버를 한 번 정의하면 `targets`에 나열한 모든 AI 도구에 자동 배포. API 키는 `.env`에서 `${VAR}` 치환으로 주입되어 하드코딩 없음.

---

## 시나리오 5: 팀 코딩 가이드라인 통일

**상황**: 팀원들이 Claude, Codex, Gemini를 각자 다른 설정으로 쓰고 있다.

```bash
# 1. 가이드라인 수정 (단일 소스)
vi .claude/global/CLAUDE.md

# 2. Claude + Codex + Gemini 모두에 동기화
ai-env sync --claude-only

# 동기화 결과:
# ~/.claude/CLAUDE.md      ← Claude Code가 읽는 가이드라인
# ~/.codex/AGENTS.md       ← Codex CLI가 읽는 가이드라인
# ~/.gemini/GEMINI.md      ← Gemini CLI가 읽는 가이드라인
```

### 팀 스킬 공유

```bash
# 팀 스킬 레포를 심링크로 연결 (한 번만)
ln -s ~/work/cde/cde-skills ./cde-skills

# 팀 스킬 포함 동기화 (develop 브랜치 자동 pull)
ai-env sync --skills-all

# 특정 팀 스킬만 포함
ai-env sync --skills-include cde-ranking-skills

# 특정 팀 스킬 제외
ai-env sync --skills-exclude cde-skills
```

---

## 시나리오 6: 환경 건강 검사

**상황**: "Claude Desktop에서 MCP 서버가 안 되는데 뭐가 문제지?"

```bash
ai-env doctor

# 출력 예시:
# ✅ .env 파일 존재
# ✅ ANTHROPIC_API_KEY 설정됨
# ✅ OPENAI_API_KEY 설정됨
# ❌ GOOGLE_API_KEY 미설정 — Gemini 기능 사용 불가
# ✅ claude 설치됨 (v1.2.3)
# ✅ codex 설치됨 (v0.113.0)
# ❌ gemini 미설치

# JSON 형식으로 출력 (스크립트 연동용)
ai-env doctor --json
```

---

## 시나리오 7: 리서치 → 스펙 → 코드 자동화 워크플로우

**상황**: "비트코인 자동매매 시스템"을 리서치부터 코드까지 자동으로 진행하고 싶다.

```bash
# 1. 토픽 YAML 작성
cat > config/topics/bitcoin-automation.yaml << 'EOF'
id: bitcoin-automation
title: 비트코인 자동매매 시스템
research:
  gemini:
    - focus: 시장 분석 알고리즘
      prompt: "비트코인 자동매매에 사용되는 주요 기술적 분석 지표와 알고리즘을 조사해줘"
  gpt:
    - focus: 리스크 관리
      prompt: "암호화폐 자동매매 시스템의 리스크 관리 전략을 조사해줘"
plan:
  output_dir: ~/Documents/Obsidian/PARA-2025
  module_prefix: btc
EOF

# 2. Phase별 실행
claude "/wf-init bitcoin-automation"       # Obsidian 워크스페이스 생성
claude "/wf-research bitcoin-automation"   # 3-Track 자동 리서치
claude "/wf-spec bitcoin-automation"       # Brief 압축 → Spec/Plan 생성
claude "/wf-code bitcoin-automation"       # TDD 코드 생성
claude "/wf-review bitcoin-automation"     # 스펙 정합성 리뷰

# 또는 전체 자동 실행
claude "/wf-run bitcoin-automation"

# 3. Deep Research API 디스패치 (Gemini/GPT 동시)
ai-env pipeline dispatch bitcoin-automation
```

**진행 상황 확인**:
```bash
ai-env pipeline workflow bitcoin-automation
# 현재 Phase, 완료된 리서치 파일, 남은 작업 등 표시
```

---

## 시나리오 8: 일상 개발 슬래시 커맨드

Claude Code 세션 내에서 바로 사용하는 커맨드들:

```
/commit                    # Spec-Task 기반 커밋 메시지 자동 생성
# 코드 리뷰는 code-review 스킬이 자동 트리거 ("리뷰해줘", "review" 등)
/sync                      # ai-env sync 실행
/handoff                   # 세션 컨텍스트를 다음 세션에 전달
/setup                     # 프로젝트 초기 설정 가이드
/upgrade-ai-tools          # Claude, Codex, Gemini CLI 일괄 업그레이드
/cleanup-branches          # 머지된 브랜치 정리
/git-summary               # Git 히스토리 요약
```

---

## 시나리오 9: 세션 간 컨텍스트 이어받기

**상황**: 어제 작업하다가 세션이 끊겼는데, 오늘 이어서 하고 싶다.

ai-env의 세션 lifecycle hooks가 자동으로 처리:

1. **세션 종료 시** (`session_end.sh`): 현재 작업 상태를 `.claude/handoff/latest.md`에 저장
2. **세션 시작 시** (`session_start.sh`): `latest.md`를 자동으로 로드하여 이전 컨텍스트 복원
3. **컨텍스트 압축 시** (`pre_compact.sh`): 트랜스크립트를 백업하고 핸드오프 갱신

```bash
# 수동으로 핸드오프 생성 (중요한 작업 중간에)
claude "/handoff"

# 핸드오프 확인
cat .claude/handoff/latest.md
```

---

## 시나리오 10: 다른 프로젝트에 ai-env 적용

**상황**: 새 프로젝트에서 ai-env의 혜택을 받고 싶다.

```bash
cd ~/work/new-project

# 1. ai-env의 글로벌 설정이 이미 동기화되어 있으므로
#    Claude Code를 열면 자동으로:
#    - ~/.claude/CLAUDE.md (팀 가이드라인) 적용
#    - ~/.claude/skills/ (공유 스킬) 사용 가능
#    - ~/.claude/commands/ (슬래시 커맨드) 사용 가능

# 2. 프로젝트별 MCP 서버가 필요하면
#    ai-env가 생성한 .claude/settings.glocal.json을 복사
cp ~/work/ai-env/.claude/settings.glocal.json .claude/settings.local.json

# 3. 프로젝트별 프로파일 설정 (스킬이 프로젝트 컨텍스트 자동 로드)
cat > .claude/project-profile.yaml << 'EOF'
project:
  name: my-api-server
  type: api-server
  description: 사용자 인증 마이크로서비스

architecture:
  pattern: 3-layer
  layers:
    api: "app/api/"
    service: "app/services/"
    repository: "app/repositories/"

specs:
  directory: "specs/"
  format: "SPEC-NNN"

tests:
  framework: pytest
  command: "uv run pytest tests/ -x -q"
  lint_command: "uv run ruff check . && uv run ruff format --check ."
EOF

# 4. Claude + Codex 동시 사용 설정
ai-env project sync-codex
```

---

## 핵심 팁 정리

| 상황 | 명령어 |
|------|--------|
| 처음 세팅 | `uv sync && ai-env sync` |
| API 키 변경 후 | `ai-env sync` |
| MCP 서버 추가 후 | `ai-env sync` (또는 `--mcp-only`) |
| 가이드라인 수정 후 | `ai-env sync --claude-only` |
| 스킬만 빠르게 갱신 | `ai-env sync --skills-only` |
| 팀 스킬 전체 포함 | `ai-env sync --skills-all` |
| 뭐가 문제인지 모를 때 | `ai-env doctor` |
| Rate-limit 걱정 없이 | `claude --fallback` |
| 프로젝트에 Codex 추가 | `ai-env project sync-codex` |
| 리서치 자동화 | `claude "/wf-run topic_id"` |
