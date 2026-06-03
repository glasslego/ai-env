---
name: jira-task
description: Jira 이슈 ↔ Obsidian vault `1X_업무카카오/jira/{KEY}.md` 양방향 노트 동기화. 사용자가 "/jira <KEY>", "지라 만들어줘", "지라 업데이트", "JIRA-123 노트로 만들어" 를 말하면 트리거. Jira API 직접 호출은 하지 않고 이미 설치된 jira-wiki-mcp 또는 cde-skills `development/jira` 서브스킬을 wrap.
---

# Jira Task

> Origin: jackie-skills/jira-create + jira-update 통합. 단순화 + vault 컨벤션 통일.
>
> Vault note: `~/Documents/Obsidian Vault/1X_업무카카오/jira/{KEY}.md`
> Jira 접근: jira-wiki-mcp (글로벌 MCP) 또는 cde-skills `/jira` (development 서브스킬).

## When to invoke

- 사용자가 `/jira <KEY>` (예: `/jira CDE-1234`)
- "지라 만들어줘 CDE-1234", "JIRA 업데이트", "이 이슈 노트로 정리"
- daily wrap-up 중 "in progress 이슈 다시 동기화"

## 동작 분기

```
입력: KEY (e.g. CDE-1234)
vault note 존재?
  ├─ 없음 → Jira fetch → vault note 생성 (frontmatter + body)
  └─ 있음 → 사용자에게 "pull (Jira→vault) / push (vault→Jira) / both" 확인
              ├─ pull: Jira fetch → 본문 갱신 (사용자 메모 보존)
              ├─ push: vault frontmatter status/assignee/labels → Jira 업데이트
              └─ both: pull 먼저 (Jira 가 truth), 그 후 push
```

## Vault note 구조 (regex 안전한 단순 형식)

```markdown
---
key: CDE-1234
title: ranking quality fix
status: In Progress
assignee: megan.won
priority: P2
labels: [ranking, quality]
sprint: "2026-W18"
created: 2026-04-22
updated: 2026-05-06
url: https://jira.kakaocorp.com/browse/CDE-1234
---

# CDE-1234 — ranking quality fix

## 설명
{Jira description (markdown 변환)}

## 진행 상황
{Jira comments 최신 5개. 사용자가 직접 추가한 메모는 ## 메모 섹션 사용.}

## 메모
{사용자 자유 메모 — sync 시 보존되는 영역}

## 관련 링크
- [[2026-05-04-spec-014]]
- {git PR / 슬랙 등}
```

`## 메모` 섹션은 sync 시 항상 보존.

## 실행 (셸 스크립트는 cde-skills 의 jira 서브스킬을 호출)

```bash
~/.claude/skills/jira-task/scripts/jira_note.py CDE-1234
# 옵션
--mode pull|push|both    # 기본 pull
--vault PATH             # 기본 $OBSIDIAN_BASE
--dry-run                # 변경 사항만 출력
```

## 구현 의존성

- `cde-skills` 의 `data/development/jira/scripts/jira_*.py` (이미 글로벌 sync 됨)
- 또는 글로벌 MCP `jira-wiki-mcp` (settings.json `mcpServers` 등록)
- 위 둘 다 없으면 SKILL 이 안내 후 종료 (megan-skills 자체는 Jira API 안 가짐)

## 트리거 우선순위

1. 사용자가 KEY 명시 → 단일 노트 처리
2. "in progress 모두 sync" → `1X_업무카카오/jira/*.md` 중 frontmatter `status: In Progress` 만 pull
3. wrap-up 스킬이 호출 시 항상 mode=pull 로 호출 (사용자 메모 보존)
