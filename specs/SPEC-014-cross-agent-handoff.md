---
id: SPEC-014
title: Cross-Agent 핸드오프 — Claude 세션 종료 → Codex 이어작업 (cwd 격리)
status: implemented
created: 2026-04-30
updated: 2026-04-30
---

# SPEC-014: Cross-Agent 핸드오프 (cwd 격리)

## 1. 배경

Claude Code 세션이 rate-limit 또는 다른 사유로 끊기면 사용자가 같은 디렉토리에서
Codex CLI 를 띄워 이어 작업하고 싶다. 현재는 다음과 같은 한계가 있다.

- `claude --fallback` wrapper 안에서만 자동 핸드오프 (즉 사용자가 일반 `claude` 로
  실행한 경우에는 종료 시 컨텍스트가 휘발).
- Codex 가 cwd 의 `.claude/handoff/latest.md` 의 존재를 알 방법이 없음.
- 여러 프로젝트의 세션이 동시에 돌고 있을 때 (예: A 프로젝트 Claude + B 프로젝트
  Codex 가 동시 진행) 핸드오프가 섞일 위험이 있음.

## 2. 목표

1. **Claude 세션 종료 시 자동 핸드오프 작성** — `--fallback` 사용 여부와 무관하게,
   `SessionEnd` hook 이 cwd 메타데이터를 포함한 핸드오프 파일을 항상 남긴다.
2. **Codex 가 같은 cwd 에서 인계받아 이어작업** — Codex 가 자기 cwd 의
   `.claude/handoff/latest.md` 를 자동/수동으로 읽고 이어작업.
3. **Multi-project 격리** — 핸드오프 파일은 프로젝트 루트의 `.claude/handoff/`
   하위에만 저장. 다른 프로젝트 cwd 에서 시작한 Codex 가 잘못된 핸드오프를 잡지
   않도록 cwd 검증 필수.
4. **Global registry** — 사용자가 다른 머신/터미널에서 "최근 어디서 Claude 세션이
   끊겼나?" 를 빠르게 찾을 수 있도록 `~/.claude/handoffs/index.jsonl` 에 한 줄
   메타 append.

## 3. Acceptance Criteria

### AC-1 (cwd 메타데이터)
- `.claude/hooks/session_end.sh` 가 작성하는 `.claude/handoff/latest.md` 의 헤더에
  `cwd: <abs-path>` 라인이 포함된다.

### AC-2 (글로벌 인덱스)
- `SessionEnd` 마다 `~/.claude/handoffs/index.jsonl` 에 한 줄 JSON append:
  `{"ts": "...", "cwd": "...", "branch": "...", "session_id": "...", "handoff_path": "..."}`
- 이 파일이 100MB 를 넘지 않도록 직접 truncate 정책은 두지 않음 (jsonl 한 줄당
  ~200B → 약 50만 세션). 별도 cleanup 은 후속 SPEC.

### AC-3 (Codex 인계 스킬)
- `.claude/skills/handoff-resume/SKILL.md` 추가. 트리거: "이어서 해줘",
  "resume", "continue claude session", "이전 세션 이어".
- 동작: 현재 cwd 의 `.claude/handoff/latest.md` 존재 확인 → frontmatter 의 `cwd:`
  가 현재 cwd 와 일치하는지 검증 → 본문을 출력하고 작업 재개.
- cwd 불일치 시 경고 후 사용자 확인 후에만 진행.

### AC-4 (글로벌 안내)
- `.claude/global/CLAUDE.md` 에 "세션 시작 시 cwd 의 `.claude/handoff/latest.md`
  를 발견하면 항상 먼저 읽고 이어작업한다" 정책 추가.
- 이 파일은 ai-env sync 시 `~/.codex/AGENTS.md` 로도 동기화되어 Codex 도 규칙을
  인지한다.

### AC-5 (회귀)
- 기존 SessionEnd 동작 (ai-agent-log 요약, archive 이동) 보존.
- ai-env 테스트는 모두 통과.

## 4. Non-Goals

- 자동으로 Codex 를 띄우거나 명령을 실행하지 않음 (사용자가 직접 Codex 를 시작).
- 글로벌 인덱스의 자동 cleanup / TTL 은 별도 작업.
- transcript 전체를 핸드오프에 포함하지 않음 (요약 + git 상태 + 마지막 user
  메시지만).

## 5. Tasks

- [x] H-1: SPEC-014 작성 (본 문서)
- [x] H-2: `.claude/hooks/session_end.sh` 강화 — cwd 메타 + 글로벌 인덱스
- [x] H-3: `.claude/skills/handoff-resume/SKILL.md` 추가
- [x] H-4: 글로벌 CLAUDE.md 정책 + 검증 + 커밋

## 6. 검증

```bash
# session_end hook 직접 실행 (mock stdin)
echo '{"session_id":"test123","transcript_path":""}' | bash .claude/hooks/session_end.sh

# 결과 검증
head -5 .claude/handoff/latest.md           # cwd: <abs-path> 포함
tail -1 ~/.claude/handoffs/index.jsonl       # 한 줄 JSON

# Codex 에서 트리거 확인
# (수동) Codex CLI 시작 → "이어서 해줘" → handoff-resume 스킬 발동 확인
```
