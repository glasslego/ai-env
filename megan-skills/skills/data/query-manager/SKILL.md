---
name: query-manager
description: QueryManager (Flink/Trino 쿼리 관리 시스템) productions / queries 검색 + source/sink 추적 + 분석. 사용자가 "/qm", "querymanager", "쿼리 매니저", "production 검색", "쿼리 분석" 을 말하면 트리거. 실제 호출은 cde-skills `data/query-manager` 서브스킬에 위임. upload 차단.
---

# Query Manager

> Origin: cde-skills/data/query-manager. **재구현 금지** — read-only wrapper.

## When to invoke

- "이 production 어디 있나", "쿼리 검색"
- "이 테이블 source/sink 추적", "lineage"
- `/qm productions`, `/qm queries`, `/qm search-sink my-table`

## 자주 쓰는 명령

```bash
~/.claude/skills/query-manager/scripts/qm.sh productions                # production 목록
~/.claude/skills/query-manager/scripts/qm.sh discover                    # production 자동 탐색
~/.claude/skills/query-manager/scripts/qm.sh queries                     # 쿼리 목록
~/.claude/skills/query-manager/scripts/qm.sh query <id>                  # 쿼리 상세
~/.claude/skills/query-manager/scripts/qm.sh search-source <table>       # source 검색
~/.claude/skills/query-manager/scripts/qm.sh search-sink <table>         # sink 검색
~/.claude/skills/query-manager/scripts/qm.sh analyze <query-id>          # 쿼리 분석
# 옵시디언 저장:
~/.claude/skills/query-manager/scripts/qm.sh search-sink iceberg.db.t1 --save qm-sink-t1
```

## 위임 경로

1. `~/.claude/skills/data/query-manager/scripts/query_manager_query.py`
2. `~/work/glasslego/ai-env/cde-skills/skills/data/query-manager/scripts/query_manager_query.py`

## 안전

- 본 wrapper 는 `upload` 명령 차단 (mutating). 필요시 cde-skills 서브스킬 직접 호출.
