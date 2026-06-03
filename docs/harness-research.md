# Harness 리서치 자료 모음

> 2026-04-12 작성. Claude Code Harness 관련 외부 리서치 자료.

---

## 1. 공식 Anthropic 문서

### Sub-Agents (서브에이전트)
- **URL**: https://code.claude.com/docs/en/sub-agents
- `.claude/agents/*.md` 에 YAML frontmatter로 정의
- 주요 frontmatter 필드:
  - `name`, `description` (필수)
  - `model`: sonnet / opus / haiku / 전체 모델 ID / inherit
  - `permissionMode`: default / acceptEdits / auto / dontAsk / bypassPermissions / plan
  - `isolation`: worktree (독립 git 워크트리)
  - `skills`: 사전 로드할 스킬 목록 (컨텍스트에 전문 주입)
  - `mcpServers`: 에이전트 전용 MCP 서버
  - `hooks`: 에이전트 스코프 훅
  - `maxTurns`, `effort`, `memory`, `background`, `color`, `initialPrompt`
- 제약: 서브에이전트는 다른 서브에이전트를 스폰할 수 없음 (무한 중첩 방지)
- 빌트인: `Explore` (Haiku, 읽기전용), `Plan` (읽기전용), `general-purpose`

### Hooks (훅)
- **URL**: https://code.claude.com/docs/en/hooks
- 23+ 훅 이벤트:
  - **세션**: `SessionStart`, `SessionEnd`, `PreCompact`, `PostCompact`
  - **사용자**: `UserPromptSubmit`
  - **도구**: `PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `PermissionRequest`, `PermissionDenied`
  - **턴**: `Stop`, `StopFailure`
  - **서브에이전트**: `SubagentStart`, `SubagentStop`
  - **파일**: `FileChanged`, `CwdChanged`
  - **태스크**: `TaskCreated`, `TaskCompleted`
  - **설정**: `InstructionsLoaded`, `ConfigChange`
  - **워크트리**: `WorktreeCreate`, `WorktreeRemove`
  - **MCP**: `Elicitation`, `ElicitationResult`
  - **알림**: `Notification`
- 핸들러 타입: `command` (쉘), `http` (POST), `prompt` (모델 평가), `agent` (서브에이전트 스폰)
- Exit code: 0=성공, 2=차단(stderr를 Claude에 표시), 1/3+=비차단
- JSON 출력: `permissionDecision`, `additionalContext`, `updatedInput`, `continue`

### Skills (스킬)
- **URL**: https://code.claude.com/docs/en/skills
- `SKILL.md` + YAML frontmatter → `/skill-name` 커맨드 자동 생성
- Agent Skills 오픈 스탠다드: https://agentskills.io
- 주요 frontmatter:
  - `name`, `description`, `argument-hint`
  - `allowed-tools`: 스킬 활성 시 사전 승인 도구
  - `model`, `effort`: 스킬 활성 시 오버라이드
  - `context: fork`: 독립 서브에이전트 컨텍스트에서 실행
  - `agent`: fork 시 사용할 서브에이전트 타입
  - `hooks`: 스킬 라이프사이클 훅
  - `paths`: 모노레포 지원 (glob 패턴)
- 문자열 치환: `$ARGUMENTS`, `$N`, `${CLAUDE_SESSION_ID}`, `${CLAUDE_SKILL_DIR}`
- 쉘 전처리: `` !`command` `` 구문으로 스킬 로드 전 쉘 실행
- 컨텍스트: 세션 동안 유지, compaction 시 상위 5개 스킬 재첨부 (각 5K, 합계 25K)

### Agent Teams (실험적)
- **URL**: https://code.claude.com/docs/en/agent-teams
- `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` 필요
- Team lead + teammates, 공유 태스크 리스트, 직접 메시징
- vs 서브에이전트: 서브에이전트는 메인에만 보고, 팀메이트는 P2P 통신
- 태스크 상태: pending → in progress → completed (의존성 추적)
- 디스플레이: in-process / tmux / iTerm2 분할

### Plugins (플러그인)
- **URL**: https://code.claude.com/docs/en/plugins
- Skills + Agents + Hooks + MCP + LSP를 하나의 배포 단위로 패키징
- 매니페스트: `.claude-plugin/plugin.json`
- 네임스페이스: `/plugin-name:skill-name`
- 보안: 플러그인 서브에이전트는 hooks/mcpServers/permissionMode 사용 불가
- 공식 마켓플레이스: https://github.com/anthropics/claude-plugins-official (101+ 플러그인)
- 테스트: `claude --plugin-dir ./my-plugin`, `/reload-plugins` 핫리로드

### Settings & Permissions
- **URL**: https://code.claude.com/docs/en/settings
- 계층: Managed (org) > CLI flags > Project `.claude/settings.json` > Local > User `~/.claude/settings.json`
- `allowedTools` / `disallowedTools`: 패턴 매칭 (`"Bash(git *)"`, `"mcp__memory__.*"`)
- `env`: 환경변수 주입
- `hooks`: 훅 설정

---

## 2. 멀티에이전트 조정 패턴 (공식)

- **URL**: https://claude.com/blog/multi-agent-coordination-patterns
- 5가지 정형 패턴:

| 패턴 | 구조 | 장점 | 약점 |
|------|------|------|------|
| Generator-Verifier | 생성 → 검증 | 명시적 테스트 기준에 강함 | 모호한 기준 시 환상 |
| Orchestrator-Subagent | 리드가 계획, 서브가 실행 | 가장 범용적 | 핸드오프 병목 |
| Agent Teams | 병렬 워커 + 공유 큐 | 도메인 전문성 축적 | 완료 감지 어려움 |
| Message Bus | 이벤트 기반 pub/sub | 예측 불가 워크플로우에 적합 | 장애 추적 어려움 |
| Shared State | 에이전트가 공유 저장소 직접 R/W | SPOF 제거 | 중복/토큰 낭비 |

> 시작점: Orchestrator-Subagent. 컨텍스트 필요에 따라 분해, 태스크 유형이 아니라.

---

## 3. 주요 오픈소스 하네스 구현

### Citadel — 가장 완성도 높은 프로덕션 하네스
- **URL**: https://github.com/SethGammon/Citadel
- 4-Tier 라우팅: regex(0토큰) → 세션상태(0토큰) → 키워드(0토큰) → LLM(~500토큰)
- 대부분의 요청이 1-3 티어에서 무료로 해결
- 캠페인 지속성: `/do continue`로 세션 간 작업 이어감
- 병렬 에이전트: 독립 git 워크트리
- 22 라이프사이클 훅 (14개 이벤트), 서킷 브레이커, 42 스킬
- **참고 가치**: 비용 최적화 라우팅, 세션 지속성, 안전 인프라

### claude-code-harness — 미니멀 규칙 기반
- **URL**: https://github.com/Chachamaru127/claude-code-harness
- TypeScript 가드레일 엔진: 13개 선언적 규칙 (R01-R13)
- 5개 동사 스킬: `/harness-plan`, `/harness-work`, `/harness-review`, `/harness-release`, `/harness-setup`
- 3개 에이전트: worker, reviewer, scaffolder
- 워크플로우: Plan → Work (병렬) → Review → Release
- **참고 가치**: 깔끔한 규칙 컴파일링, TDD 강제 워크플로우

### Everything Claude Code (affaan-m) — 최다 기능
- **URL**: https://github.com/affaan-m/everything-claude-code
- 47 서브에이전트, 181 스킬
- Instinct 학습: 패턴 + 신뢰도 점수 → 스킬로 자동 집계 (`/learn-eval`)
- AgentShield 보안: 1282 테스트, 102 규칙
- 크로스 플랫폼: Claude Code, Cursor, Codex, OpenCode, Gemini
- 3단계 훅 엄격도 프로파일
- **참고 가치**: Instinct/학습 레이어 개념, 대규모 스킬 체계

### awesome-claude-code — 디렉토리
- **URL**: https://github.com/hesreallyhim/awesome-claude-code
- Agent Skills (18 레포), Workflows (25+), Tooling (24+), Orchestrators (11)
- **참고 가치**: 하네스 컴포넌트 발견을 위한 최고 시작점

### Claude Swarm — 경량 멀티에이전트
- **URL**: https://github.com/parruda/claude-swarm
- Claude Code 인스턴스를 메시지 패싱으로 연결
- **참고 가치**: 경량 멀티에이전트 조정

### Ruflo — 엔터프라이즈 스웜
- **URL**: https://github.com/ruvnet/ruflo
- 멀티에이전트 스웜, 벡터 메모리, RAG 통합
- 분산 스웜 인텔리전스, Claude Code/Codex 네이티브 통합
- **참고 가치**: 엔터프라이즈 규모 오케스트레이션

### Claude Squad — 세션 관리 UI
- **URL**: https://github.com/smtg-ai/claude-squad
- 터미널 앱으로 복수 Claude Code 인스턴스 관리
- **참고 가치**: 수동 병렬 세션 관리

### Claude Task Master — 태스크 분해
- **URL**: https://github.com/eyaltoledano/claude-task-master
- AI 기반 개발용 태스크 관리, 구조화된 태스크 분해
- **참고 가치**: 태스크 큐 + 분해 레이어

### OpenHarness (HKUDS) — 연구용
- **URL**: https://github.com/HKUDS/OpenHarness
- 오픈소스 Python 에이전트 하네스, 빌트인 에이전트 "Ohmo"
- **참고 가치**: 연구 지향 참조 구현

### learn-claude-code — 교육용
- **URL**: https://github.com/shareAI-lab/learn-claude-code
- "Bash is all you need" — 0에서 nano claude-code 에이전트 하네스 구축
- **참고 가치**: 하네스 내부 구조를 빌드하며 이해

### claudekit — 실용 툴킷
- **URL**: https://github.com/carlrannaberg/claudekit
- 체크포인팅, 품질 훅, 20+ 서브에이전트
- **참고 가치**: 실용적 프로덕션 툴킷

### Container Use (Dagger) — 컨테이너 격리
- **URL**: https://github.com/dagger/container-use
- 컨테이너 기반 안전한 멀티에이전트 작업 환경
- **참고 가치**: 병렬 에이전트 안전을 위한 격리 레이어

### Harness meta-skill (revfactory)
- **URL**: https://github.com/revfactory/harness
- 도메인별 에이전트 팀을 설계하는 메타 스킬
- **참고 가치**: "하네스를 만드는 하네스" 자기참조 패턴

---

## 4. 블로그/가이드

### "2025 Was Agents. 2026 Is Agent Harnesses" — Aakash Gupta
- **URL**: https://aakashgupta.medium.com/2025-was-agents-2026-is-agent-harnesses-heres-why-that-changes-everything-073e9877655e
- 핵심: "모델은 범용재. 하네스가 해자."
- 6가지 필수 컴포넌트: human-in-loop, 파일시스템 접근 관리, 도구 오케스트레이션, 서브에이전트 조정, 프롬프트 프리셋 관리, 라이프사이클 훅
- **가장 많이 인용되는 하네스 정의 에세이**

### "Everything Claude Code: Agent Harness Guide" — Big Hat Group
- **URL**: https://www.bighatgroup.com/blog/everything-claude-code-ai-agent-harness-guide/
- 4-Layer 설계: User Interaction (57+ 커맨드) → Intelligence (25+ 에이전트, 108+ 스킬) → Automation (이벤트 기반 훅) → Learning (Instinct 신뢰도 점수)
- **실용적 아키텍처 워크스루**

### "Claude Code Agent Harness Architecture" — WaveSpeed AI
- **URL**: https://wavespeed.ai/blog/posts/claude-code-agent-harness-architecture/
- Deny-first 도구 디스패치 (3-Tier): 읽기전용 자동승인 → 백그라운드 분류기(상태변경) → 명시적 승인(고위험)
- 컨텍스트 관리: 세션 상태 지속, 25K MCP 출력 잘라내기, 98%에서 자동 compaction
- **권한 아키텍처와 컨텍스트 경계 설계 심화**

### "How to Configure Hooks" — Anthropic Blog
- **URL**: https://claude.com/blog/how-to-configure-hooks
- 공식 훅 설정 가이드 + 실용 예제
- **공식 기준 레퍼런스**

### Claude Code Hooks: Production CI/CD Patterns — Pixelmojo
- **URL**: https://www.pixelmojo.io/blogs/claude-code-hooks-production-quality-ci-cd-patterns
- 12+ 훅 이벤트 레퍼런스, CI/CD 통합 패턴
- **프로덕션 훅 구현 패턴**

### Automate Workflows with Claude Code Hooks — GitButler Blog
- **URL**: https://blog.gitbutler.com/automate-your-ai-workflows-with-claude-code-hooks
- git 워크플로우 자동화 실용 예제
- **실전 훅 자동화 예제**

### Claude Code Sub-Agents: Best Practices — ClaudeFast
- **URL**: https://claudefa.st/blog/guide/agents/sub-agent-best-practices
- 병렬 vs 순차 서브에이전트 패턴 비교
- **서브에이전트 오케스트레이션 설계 패턴**

### Multi-Agent Orchestration 2026 — Shipyard
- **URL**: https://shipyard.build/blog/claude-code-multi-agent/
- 3-Tier: (1) 빌트인 서브에이전트/팀 (2) 로컬 워크트리 3-10 에이전트 (3) 10+ 에이전트 플릿 관리
- **오케스트레이션 티어 선택 가이드**

### Building a Multi-Agent AI System — Mae Capozzi
- **URL**: https://maecapozzi.com/blog/building-a-multi-agent-orchestrator
- Claude로 오케스트레이터 구축하는 핸즈온 워크스루
- **구현 레벨 가이드**

### claude-code-hooks-mastery — disler
- **URL**: https://github.com/disler/claude-code-hooks-mastery
- 모든 이벤트에 대한 훅 마스터리 예제
- **훅 학습 전용 리소스**

---

## 5. 커뮤니티 리소스

| 이름 | URL | 설명 |
|------|-----|------|
| wshobson/commands | https://github.com/wshobson/commands | 프로덕션급 슬래시 커맨드 라이브러리 |
| wshobson/agents | https://github.com/wshobson/agents | 멀티에이전트 오케스트레이션 패턴 |
| Claude-Command-Suite | https://github.com/qdhenry/Claude-Command-Suite | 엔터프라이즈 커맨드 템플릿 |
| claude-code-best-practice | https://github.com/shanraisshan/claude-code-best-practice | settings.json 패턴 가이드 |
| subagents.app | https://subagents.app/ | 서브에이전트 디렉토리 |

---

## 6. 핵심 설계 원칙 (리서치 종합)

### Deny-first 권한
- 도구 호출 전에 차단 여부를 먼저 평가
- 3-Tier: 읽기전용 자동승인 → 상태변경 분류 → 고위험 명시승인

### 4-Tier 라우팅 (Citadel)
- regex → 세션상태 → 키워드 → LLM
- 대부분의 요청이 0토큰으로 해결되어야 함

### 컨텍스트 = 자본
- 스킬: 설명은 항상 컨텍스트에, 본문은 호출 시에만
- 서브에이전트: 탐색을 격리하여 메인 컨텍스트 보호

### 세션 지속성
- 캠페인/상태 파일이 컨텍스트 윈도우 리셋을 넘어 생존
- `.claude/logs/`, 태스크 리스트, `_code-status.yaml`

### Instinct 학습 (ECC)
- 패턴 축적 → 신뢰도 점수 → 스킬로 자동 집계
- "경험에서 배우는 하네스"

### Worktree 격리
- `isolation: worktree`가 병렬 에이전트 안전의 기본 단위
- 변경 없으면 자동 정리

---

## 7. 추천 학습 순서

1. **개념**: Aakash Gupta 에세이 → Anthropic 멀티에이전트 패턴 블로그
2. **공식 문서**: Sub-Agents → Skills → Hooks → Settings → Plugins → Agent Teams
3. **구현 참고**: Citadel (프로덕션), claude-code-harness (미니멀), ECC (풀스택)
4. **교육**: learn-claude-code (0에서 빌드), claude-code-hooks-mastery (훅 마스터)
5. **우리 레포**: cde-skills (로컬 하네스), kcai-claude (원격 하네스)
