---
name: vault-lint
description: Obsidian vault 의 끊어진 wikilink, 고아 노트, frontmatter 누락을 점검하고 _meta/lint-report-{date}.md 에 결과를 작성. 사용자가 "vault 점검", "고아 노트", "/vault-lint", "vault lint" 를 말하면 트리거.
---

# Vault Lint

> Origin: jackie-skills/vault-lint. PARA layout 에 맞게 단순화.
>
> Vault: `$OBSIDIAN_BASE` (기본 `~/Documents/Obsidian Vault`).
> Output: `<vault>/_meta/lint-report-{YYYY-MM-DD}.md`.

## When to invoke

- 사용자가 "vault 점검", "고아 노트 찾아", "끊어진 wikilink", "/vault-lint"
- 매주 자동 (Phase 6 schedule 후보)

## 검사 항목

| Category | 정의 |
|---|---|
| broken wikilinks | `[[Note]]` 인데 vault 에 동명 노트 없음 |
| orphan notes | 어떤 노트도 가리키지 않는 노트 (exempt 폴더 제외) |
| missing frontmatter | `1X_업무카카오/` 하위 노트 중 frontmatter 누락 (업무 노트는 메타 필수) |

Exempt (orphan 검사 제외): `_meta/`, `90_journal/`, `99_archive/`, `attachments/`, `Excalidraw/`, `templates/`, `scripts/`.

## 실행

```bash
~/.claude/skills/vault-lint/scripts/lint.py
# 옵션
--vault PATH         # 기본 $OBSIDIAN_BASE
--report-only        # report 만 작성, 콘솔 요약 X
--max-orphans 50     # 보고서에 적을 최대 orphan 개수 (콘솔 요약은 모두 카운트)
```

## 출력 형식

```markdown
# Vault Lint — 2026-05-06

| Category | Count |
|---|---|
| broken wikilinks | 3 |
| orphan notes | 12 |
| missing frontmatter | 2 |

## Broken wikilinks
- `00_session/2026-05/foo.md` — `[[bar]]` 미발견

## Orphan notes
- `01_Inbox/idea.md`

## Missing frontmatter
- `02_Projects/x.md`
```
