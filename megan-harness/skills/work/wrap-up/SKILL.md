---
name: wrap-up
description: 오늘의 daily 노트(`90_journal/01_daily/{YYYY-MM-DD}.md`)에 진행한 세션·in-progress jira·미완 todo 를 자동 정리. 사용자가 "/wrap", "오늘 정리하자", "wrap up", "오늘 마무리" 를 말하면 트리거. 사용자 메모(`## 메모`)는 항상 보존.
---

# Wrap Up

> Origin: jackie-skills/wrap-up. PARA → megan vault layout 으로 단순화.
>
> Vault: `~/Documents/Obsidian Vault`. Output: `90_journal/01_daily/{YYYY-MM-DD}.md`.

## When to invoke

- 사용자가 "/wrap", "오늘 정리", "wrap up", "오늘 마무리"
- 일과 마감 시점 자동 (Phase 6 cron 후보)

## 동작

```
오늘 daily 노트 존재?
  ├─ 없음 → 새로 생성 (frontmatter + 섹션 skeleton)
  └─ 있음 → ## 자동 섹션 갱신, ## 메모 는 그대로 보존
```

## Daily 노트 구조

```markdown
---
date: 2026-05-06
type: daily
tags: [daily]
---

# 2026-05-06 (Wed)

## 오늘의 세션
- `2026-05-06 09:30` — [[2026-05-06-0930-megan-skills-phase-2|megan-skills phase 2]]
- `2026-05-06 14:10` — [[2026-05-06-1410-jira-CDE-1234]]

## 진행중 Jira (자동)
- **CDE-1234** — ranking quality fix (In Progress)

## 미완 todo
- [ ] vault-lint orphan 305건 가지치기
- [ ] phase 5 defuddle 적용

## 결정사항
-

## 메모
{사용자 자유 메모 — wrap-up 갱신 시 보존됨}

## 내일
- [ ] phase 3 trino-query 시작
```

## 실행

```bash
~/.claude/skills/wrap-up/scripts/wrap.py
# 옵션
--vault PATH         # 기본 $OBSIDIAN_BASE
--date YYYY-MM-DD    # 기본 오늘
--dry-run            # 본문만 stdout
```

## Source signals (자동 채움 영역)

| 섹션 | 소스 |
|---|---|
| 오늘의 세션 | `90_journal/04_sessions/{YYYY-MM}/{date}-*.md` |
| 진행중 Jira | `1X_업무카카오/jira/*.md` 중 frontmatter `status: In Progress` |
| 미완 todo | 어제 daily 의 unchecked todo 자동 carry-over |

## 보존 영역 (사용자 메모, 절대 덮어쓰지 않음)

- `## 메모`
- `## 결정사항` (사용자가 입력한 내용)
- `## 내일` (사용자가 입력한 todo)

## 트리거 시 in-conversation 흐름

1. 스크립트 실행 → daily 노트 갱신/생성
2. Claude 가 노트를 read 하고 사용자에게 요약 (오늘 한 일·내일 할 일)
3. 사용자가 "이거 추가/수정" 요청 시 Edit 으로 노트 수정
