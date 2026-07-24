---
name: handoff-resume
description: |
  이전 Claude 세션이 rate-limit 등으로 끊겼을 때 cwd 의 .claude/handoff/latest.md
  를 읽어 작업을 이어가는 스킬. Codex 에서도 동일하게 동작.
  사용자가 "이어서 해줘", "이전 세션 이어", "resume", "continue claude session"
  등 인계 요청을 할 때 트리거.

  여러 프로젝트에서 동시에 다른 세션이 도는 환경을 가정하므로, 핸드오프 파일의
  `cwd:` 헤더가 현재 cwd 와 일치할 때만 컨텍스트를 적용한다.
---

# Handoff Resume

Claude Code 세션이 끊겼을 때 cwd(프로젝트 루트)의 핸드오프 파일을 읽어
작업을 이어가는 스킬. SPEC-014 (Cross-Agent 핸드오프) 의 Codex 측 진입점.

## 트리거 키워드

- "이어서 해줘", "이전 세션 이어", "이전 작업 이어"
- "resume claude", "continue claude session", "continue from handoff"
- "/handoff-resume"

## 사용 시점

- Claude Code 가 rate-limit / 네트워크 / 종료로 끊긴 직후 같은 cwd 에서
  Codex CLI 를 띄워 이어작업할 때.
- `claude --fallback` wrapper 가 자동 핸드오프를 만들지 않은 경우 (일반 `claude`
  실행이 종료되면서 SessionEnd hook 만 동작한 경우) 에도 동일하게 동작.

## 동작 단계

### Step 1: 핸드오프 파일 위치 확인

현재 cwd 의 `.claude/handoff/latest.md` 가 있는지 확인한다.

```bash
# 파일 존재 + cwd 헤더 확인
HANDOFF=".claude/handoff/latest.md"
test -f "$HANDOFF" || { echo "핸드오프 파일 없음"; exit 1; }
HANDOFF_CWD=$(grep -m1 '^- cwd:' "$HANDOFF" | sed 's/.*: //')
[ "$HANDOFF_CWD" = "$PWD" ] || echo "⚠ cwd 불일치: 핸드오프=$HANDOFF_CWD vs 현재=$PWD"
```

### Step 2: cwd 일치 검증

핸드오프 파일의 `- cwd:` 라인을 읽고 현재 작업 디렉토리와 비교한다.

- **일치**: Step 3 진행.
- **불일치**: 사용자에게 경고 후 명시적 확인을 받고서만 진행.
  - 예: "이 핸드오프는 `<other-cwd>` 에서 생성된 것입니다. 그래도 적용할까요?"
- **`- cwd:` 헤더 자체가 없음**: 구버전 핸드오프이므로 사용자에게 알림 후 확인.

### Step 3: 컨텍스트 로드 + 요약

`latest.md` 의 본문(진행 중이던 작업 / 다음 해야 할 것 / 변경된 파일 / Recent Commits)을
읽고 사용자에게 한 단락(8~12줄)으로 요약 보고한다.

```
[Handoff Resume]
  cwd: /Users/megan/work/foo
  날짜: 2026-04-30 18:33  (n분 전)
  브랜치: feature/abc
  진행 중이던 작업: ...
  다음 해야 할 것: ...
  변경된 파일: 12 files (3 staged, 9 unstaged)
```

### Step 4: 이어 작업

사용자에게 "위 컨텍스트로 이어작업할까요?" 짧게 확인 후 작업 재개.

### Step 5: (선택) 글로벌 인덱스 조회

같은 머신의 다른 cwd 에서 끊긴 세션을 찾고 싶다면:

```bash
# 최근 5개 세션 인덱스 확인
tail -5 ~/.claude/handoffs/index.jsonl
```

각 라인은 `{"ts":..., "cwd":..., "branch":..., "session_id":..., "handoff_path":...}`
형식. 사용자가 다른 cwd 의 핸드오프를 보길 원하면 해당 `handoff_path` 를 직접 읽어
정보만 출력 (cwd 가 다르므로 자동 적용은 하지 않음).

## 절대 금지

- 핸드오프의 `- cwd:` 가 현재 cwd 와 다른데 사용자 확인 없이 작업을 재개하지 않는다.
- 핸드오프 파일을 자동으로 삭제하지 않는다 (다음 SessionEnd 가 자동으로 archive 이동).
- 글로벌 인덱스(`~/.claude/handoffs/index.jsonl`)에 직접 쓰기 금지 — 그건 hook 의 역할.

## Claude / Codex 동작 차이

- **Claude Code**: `.claude/hooks/session_start.sh` 가 자동으로 latest.md 를
  로드해 표시한다. 따라서 본 스킬은 명시적 트리거(예: "다시 이어줘") 가 들어왔을
  때 보조 역할.
- **Codex CLI**: SessionStart hook 이 없으므로 사용자가 트리거 키워드로 명시 호출
  → 본 스킬이 핸드오프 파일을 읽어 컨텍스트 주입.
