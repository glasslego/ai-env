---
name: es-query
description: Elasticsearch 인덱스 조회 (ID/자연어/필터/kNN) — 결과를 JSON 또는 markdown 으로 출력하고 옵션으로 옵시디언 노트에 저장. 사용자가 "/es", "elasticsearch 조회", "ES 검색", "es-query" 를 말하면 트리거. 실제 ES 호출은 cde-skills `data/elasticsearch` 서브스킬에 위임.
---

# ES Query

> Origin: cde-skills/data/elasticsearch + cde-ranking-skills/lib/es_client.
> megan 의 부가가치는 read-only 강제와 vault 노트 저장 옵션.

## When to invoke

- "/es \"index_name\" \"query\"", "엘라스틱 조회", "ES kNN"
- 자연어 질의 → ES query DSL 변환 후 실행

## 의존성

`~/.claude/skills/data/elasticsearch/scripts/es_query.py` (cde-skills 가 제공).
ai-env sync 정상이면 자동 위치.

## 안전 정책

이 스킬은 read-only. 인덱스 생성/삭제·매핑 변경은 거부한다 (`HEAD/GET/_search` 만).
write API 가 필요한 경우 cde-skills `/elasticsearch` 직접 호출 + `--confirm`.

## 실행

```bash
~/.claude/skills/es-query/scripts/es.sh INDEX "QUERY"
# 옵션
--by-id ID           # ID 단건 조회
--knn FIELD          # kNN 검색 (vector 필드명)
--save SLUG          # vault 세션 노트 저장
--size N             # 기본 10
```

## 출력 형식

기본은 hit 별로 `_id`, `_score`, 핵심 필드 markdown table. `--format json` 시 raw.
