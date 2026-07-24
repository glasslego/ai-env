---
name: kdp-browse
description: KDP (카카오 데이터 플랫폼) 데이터셋 / 스키마 / 컬럼 / 권한 / 통계 조회 (read-only). 사용자가 "/kdp", "kdp 데이터셋", "스키마 보여줘", "row count", "컬럼 정보" 를 말하면 트리거. 실제 호출은 cde-skills `data/kdp` 서브스킬에 위임. create/update/delete 차단.
---

# KDP Browse

> Origin: cde-skills/data/kdp. **재구현 금지** — read-only wrapper.

## When to invoke

- "이 데이터셋 어디?", "kdp 스키마 보여줘"
- "row count", "EDA 통계"
- `/kdp datasets`, `/kdp schema <id>`, `/kdp stats <id>`

## 자주 쓰는 명령

```bash
~/.claude/skills/kdp-browse/scripts/kdp.sh datasets                  # 데이터셋 목록
~/.claude/skills/kdp-browse/scripts/kdp.sh dataset <id>              # 데이터셋 상세
~/.claude/skills/kdp-browse/scripts/kdp.sh schema <id>               # 스키마 (컬럼 목록)
~/.claude/skills/kdp-browse/scripts/kdp.sh columns <id>              # 컬럼 목록 (별칭)
~/.claude/skills/kdp-browse/scripts/kdp.sh stats <id>                # row count + EDA
~/.claude/skills/kdp-browse/scripts/kdp.sh permissions <id>          # 권한 (사용자 목록)
# 옵시디언 저장:
~/.claude/skills/kdp-browse/scripts/kdp.sh schema 12345 --save kdp-schema-12345
```

## 위임 경로

1. `~/.claude/skills/data/kdp/scripts/kdp_{dataset,schema,column,permission,statistics}.py`
2. `~/work/glasslego/ai-env/cde-skills/skills/data/kdp/scripts/kdp_{dataset,schema,column,permission,statistics}.py`

## 의존성 (.env)

- `KDP_TOKEN` — KDP API 토큰

## 안전

- 본 wrapper 는 create / update / delete 명령 차단 (read-only).
- 데이터셋 생성 등은 cde-skills 서브스킬 직접 호출 + 명시 confirm.
