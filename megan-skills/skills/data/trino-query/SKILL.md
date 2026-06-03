---
name: trino-query
description: Trino SQL 실행 + 결과를 markdown table 로 변환해 옵시디언 노트에 임베드 가능한 형태로 출력. 사용자가 "/trino", "trino 쿼리", "트리노로 조회", "Trino SQL" 을 말하면 트리거. 실제 Trino 호출은 cde-skills `data/trino` 서브스킬에 위임 (재구현 금지).
---

# Trino Query

> Origin: cde-skills/data/trino + cde-ranking-skills/lib/trino_client. megan 의 부가가치는
> ① Trino-only 정책 명시, ② 결과를 옵시디언 노트로 자동 저장 옵션,
> ③ 자주 쓰는 쿼리 템플릿 컨벤션.

## Trino-only 원칙

이 프로젝트의 SQL 은 모두 Trino 기반이다. Spark SQL/Hive SQL 직접 실행은 금지하고
Trino 의 catalog 를 통해 동일 데이터를 조회한다 (예: `hive.{db}.{table}`,
`iceberg.{db}.{table}`).

## When to invoke

- "/trino \"SELECT ...\"", "trino 로 조회", "iceberg 테이블 카운트"
- 사용자가 Hive/Spark SQL 작성 요청 시 Trino 로 변환 후 실행

## 동작

```
입력: SQL 문자열 또는 파일 경로
       ↓
cde-skills/data/trino/scripts/trino_query.py 호출
       ↓
결과 JSON / CSV / table
       ↓ (옵션)
옵시디언 노트에 markdown table 삽입
       ↓
~/Documents/Obsidian Vault/90_journal/04_sessions/{YYYY-MM}/{date}-{slug}-trino.md 저장
```

## 의존성 체크

스크립트는 다음 후보 경로에서 `trino_query.py` 를 찾아 호출한다:

1. `~/.claude/skills/data/trino/scripts/trino_query.py` (categorized layout)
2. `~/.claude/skills/cde-skills/skills/data/trino/scripts/trino_query.py` (legacy)
3. `~/work/cde/cde-skills/skills/data/trino/scripts/trino_query.py` (개발용)

찾지 못하면 안내 후 종료. ai-env sync 가 정상이면 1번이 항상 존재.

## 실행

```bash
~/.claude/skills/trino-query/scripts/trino_md.sh "SELECT 1"
~/.claude/skills/trino-query/scripts/trino_md.sh -f query.sql --save ranking-count
# 옵션
--save SLUG          # 결과를 vault session 노트로 저장 (slug = 파일명 일부)
--limit N            # 결과 row 수 제한 (기본 50)
--format md|json|csv # 출력 형식 (기본 md table)
```

## 자주 쓰는 쿼리 템플릿

`references/templates/` 에 공유 (TODO Phase 3.5):

- `iceberg_partition_count.sql` — 파티션별 row count
- `daily_metric.sql` — 일자별 핵심 지표
- `ranking_check.sql` — 랭킹 데이터 정합성 (cde-ranking-skills 의 verify 와 보완)
