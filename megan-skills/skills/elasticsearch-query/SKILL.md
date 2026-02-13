---
name: elasticsearch-query
description: Execute Elasticsearch queries against production(prod) or stage environments.
  - Supports three main indices:
   - gift_ranking: gift_product_ranking (선물하기 랭킹 피처 데이터)
   - promotion_builder: kcai_integrated_gift_product (프로모션 빌더 상품 데이터)
   - epsilon_gift_product: epsilon_gift_product_v1 (엡실론 선물 상품 데이터)

  Use this skill when user needs to:
  - Query or search Elasticsearch data
  - Analyze product rankings, scores, or statistics
  - Filter products by category, brand, or price
  - Retrieve batch statistics or latest product updates
  - Check index mappings or data structure
---

# Elasticsearch Query Skill

Elasticsearch 인덱스에 대한 쿼리를 실행하고 결과를 포맷팅합니다.

## 환경 정보

| 환경 | Host |
|------|------|
| prod | `http://cdp-prod.es.onkakao.net:9200` |
| stage | `http://cdpair-cbt.es.onkakao.net:9200` |

| 인덱스 키 | 인덱스명 | 설명 |
|-----------|----------|------|
| `gift_ranking` | `gift_product_ranking` | 선물하기 랭킹 피처 |
| `promotion_builder` | `kcai_integrated_gift_product` | 프로모션 빌더 |
| `epsilon_gift_product` | `epsilon_gift_product_v1` | 엡실론 선물 상품 |

## 사용 방법

### 1. 설정 + 쿼리 실행

```python
import json, requests, sys

with open('.claude/skills/elasticsearch-query/.config.json') as f:
    config = json.load(f)

env = "stage"  # or "prod"
host = config['environments'][env]['host']
index = config['environments'][env]['indices']['gift_ranking']

# 쿼리 실행
query = {"size": 0, "aggs": {"batch_counts": {"terms": {"field": "batch_id", "size": 100}}}}
response = requests.get(f"{host}/{index}/_search?pretty", json=query)
results = response.json()
```

### 2. 결과 포맷팅

```python
sys.path.append('.claude/skills/elasticsearch-query/scripts')
from format_results import (
    format_batch_stats, format_top_products, format_product_scores,
    format_product_list, format_product_detail, format_category_stats, format_mapping
)

format_batch_stats(results)
```

## 주요 쿼리 패턴

### batch_id별 통계 (gift_ranking)

```python
query = {"size": 0, "aggs": {"batch_counts": {"terms": {"field": "batch_id", "size": 100, "order": {"_key": "desc"}}}}}
```

### 상위 랭킹 상품

```python
query = {"query": {"term": {"batch_id": "20251118120000"}}, "size": 30, "sort": [{"order_gift_total_score": {"order": "desc"}}]}
```

### 특정 상품 조회

```python
# GET /_doc/{product_id} (더 효율적)
response = requests.get(f"{host}/{index}/_doc/{product_id}?pretty")
format_product_detail(response.json())
```

### 카테고리/브랜드 필터링 (promotion_builder)

```python
query = {"query": {"bool": {"filter": [{"term": {"large_display_category_code": "91"}}, {"term": {"brand_id": "6"}}]}}, "sort": [{"service_score": {"order": "desc"}}], "size": 100}
```

## 주의사항

1. **읽기 전용**: GET 요청만 수행
2. **환경 구분**: prod는 신중하게
3. **결과 크기**: size 적절히 제한
4. **VPN 필요**: 회사 내부 네트워크

## 참고 문서

- `references/query_patterns.md` - 쿼리 패턴
- `references/field_mappings.md` - 인덱스 필드 정보
- `scripts/format_results.py` - 포맷팅 함수
