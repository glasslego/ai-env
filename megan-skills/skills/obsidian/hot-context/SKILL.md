---
name: hot-context
description: Obsidian vault 의 _meta/hot.md 를 갱신하거나 읽어 현재 작업 컨텍스트를 한 화면에 요약. 사용자가 "오늘 뭐 했지", "이어서 작업하자", "what was I working on", "/hot" 을 말하면 트리거. 새 세션 시작 시 hot.md 의 mtime 이 12 시간을 넘으면 자동 갱신 후보.
---

# Hot Context

> Origin: jackie-skills/daily-hot-builder + AgriciDaniel/claude-obsidian hot cache pattern.
>
> Vault: `$OBSIDIAN_BASE` (기본 `~/Documents/Obsidian Vault`, 공백 포함).
> Output: `<vault>/_meta/hot.md`.

## When to invoke

- 새 Claude/Codex 세션 시작 시 `hot.md` mtime 이 12 시간 이상 오래됨
- 사용자가 "오늘 뭐 했지", "이어서 작업하자", "어제 어디까지", "what was I working on"
- `/hot` 슬래시 커맨드

## Source signals (읽는 순서)

> 디렉토리 매핑은 script 의 `DIRS` 상수에 모여 있음 — vault 컨벤션이 바뀌면 거기만 수정.

1. `<vault>/90_journal/04_sessions/**/*.md` 최근 7일 — mtime 정렬, 최신 5건의 TL;DR
2. `<vault>/1X_업무카카오/jira/*.md` 중 frontmatter `status: "In Progress"`
3. `<vault>/90_journal/01_daily/{today}.md` 의 미체크 todo (없으면 skip)
4. `~/.claude/projects/*/memory/MEMORY.md` 의 7일 이내 추가/수정 항목

## Output

```markdown
# Hot — {today KST}

> 자동 갱신: {timestamp}. 직접 메모는 ## 직접 메모 섹션에 — 다음 빌드가 보존.

## 진행중
- **CDE-XXXX** — 한 줄 요약 (status, 다음 액션)

## 최근 세션 (7일)
- `2026-05-04` — [[2026-05-04-spec-014|spec-014]] — TL;DR 한 줄

## 미완 todo
- [ ] daily/{today}.md 의 미체크 항목

## 최근 메모리 변경 (7일)
- `feedback_xxx.md` — 추가

## 직접 메모
{사용자가 자유롭게 적은 메모. 빌드가 이 섹션은 보존하고 위쪽만 갱신.}
```

## 실행

```bash
# 갱신
~/.claude/skills/hot-context/scripts/build_hot.py

# 읽기만
~/.claude/skills/hot-context/scripts/build_hot.py --read

# 옵션
--vault PATH         # 기본 $OBSIDIAN_BASE 또는 ~/Documents/Obsidian Vault
--max-age-hours 12   # 이 시간보다 새로우면 갱신 skip
--force              # mtime 무시 강제 갱신
```

## 트리거 우선순위

1. 사용자가 "/hot" → 강제 갱신 후 출력
2. 사용자가 "오늘 뭐 했지" → 우선 read, 12h 이상이면 갱신 후 read
3. SessionStart 자동 호출 (Phase 6 hook 등록 후) → mtime 검사 후 조건부 갱신
