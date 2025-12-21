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

이 스킬은 Elasticsearch 인덱스에 대한 쿼리를 실행하고 결과를 포맷팅합니다.

## 사용 방법

### 1. 설정 파일 로드
```python
import json
with open('.claude/skills/elasticsearch-query/.config.json') as f:
    config = json.load(f)

# 환경 선택
env = "stage"  # or "prod"
host = config['environments'][env]['host']
index = config['environments'][env]['indices']['gift_ranking']  # or 'promotion_builder', 'epsilon_gift_product'
```

### 2. 쿼리 실행
```python
import requests

# 쿼리 생성 (references/query_patterns.md 참고)
query = {
    "size": 0,
    "aggs": {
        "batch_counts": {
            "terms": {"field": "batch_id", "size": 100}
        }
    }
}

# 실행
url = f"{host}/{index}/_search?pretty"
response = requests.get(url, json=query)
results = response.json()
```

### 3. 결과 포맷팅
```python
import sys
sys.path.append('.claude/skills/elasticsearch-query/scripts')
from format_results import format_batch_stats

format_batch_stats(results)
```

## 주요 환경 정보

### Production
- Host: `http://cdp-prod.es.onkakao.net:9200`
- Indices:
  - `gift_product_ranking` - 선물하기 랭킹 피처
  - `kcai_integrated_gift_product` - 프로모션 빌더
  - `epsilon_gift_product_v1` - 엡실론 선물 상품

### Stage
- Host: `http://cdpair-cbt.es.onkakao.net:9200`
- Indices: (동일)

## 인덱스별 주요 사용 패턴

### gift_product_ranking (선물 랭킹)

#### batch_id별 통계
```python
query = {
    "size": 0,
    "aggs": {
        "batch_counts": {
            "terms": {"field": "batch_id", "size": 100, "order": {"_key": "desc"}}
        }
    }
}
from format_results import format_batch_stats
format_batch_stats(response.json())
```

#### 상위 랭킹 상품
```python
query = {
    "query": {"term": {"batch_id": "20251118120000"}},
    "size": 30,
    "sort": [{"order_gift_total_score": {"order": "desc"}}]
}
from format_results import format_top_products
format_top_products(response.json(), "20251118120000", "order_gift_total_score")
```

#### product_id별 점수 조회
```python
query = {
    "query": {"term": {"product_id": "11062448"}},
    "size": 100,
    "sort": [
        {"batch_id": {"order": "desc"}},
        {"order_gift_total_score": {"order": "desc"}}
    ]
}
from format_results import format_product_scores
format_product_scores(response.json(), "11062448", "order_gift_total_score", verbose=True)
```

### kcai_integrated_gift_product (프로모션 빌더)

#### 카테고리/브랜드 필터링
```python
query = {
    "query": {
        "bool": {
            "filter": [
                {"term": {"large_display_category_code": "91"}},
                {"term": {"brand_id": "6"}}
            ]
        }
    },
    "sort": [{"service_score": {"order": "desc"}}],
    "size": 100
}
from format_results import format_product_list
format_product_list(response.json(), verbose=False)
```

#### 특정 상품 조회 (GET 방식)
```python
# GET /_doc/{id} 사용 (더 효율적)
url = f"{host}/{index}/_doc/{product_id}?pretty"
response = requests.get(url)
from format_results import format_product_detail
format_product_detail(response.json(), verbose=True)
```

### epsilon_gift_product_v1 (엡실론 선물 상품)

#### 최신 상품 조회
```python
query = {
    "query": {"match_all": {}},
    "sort": [{"gift_product_ranking_updated_at": {"order": "desc"}}],
    "size": 10
}
from format_results import format_product_list
format_product_list(response.json())
```

#### 특정 상품 조회 (GET 방식)
```python
url = f"{host}/{index}/_doc/{product_id}?pretty"
response = requests.get(url)
from format_results import format_product_detail
format_product_detail(response.json())
```

## 참고 문서

### references/query_patterns.md
- 자주 사용하는 쿼리 패턴
- 인덱스별 쿼리 예제
- 공통 쿼리 패턴

### references/field_mappings.md
- 각 인덱스의 필드 정보
- 필드 타입 및 설명
- 스코어 필드 목록

## 사용 가능한 포맷팅 함수

### scripts/format_results.py
- `format_batch_stats(results, pretty=False)` - batch 통계
- `format_score_stats(results, score_field)` - 스코어 통계
- `format_top_products(results, batch_id, score_field)` - 상위 상품
- `format_product_scores(results, product_id, score_field, verbose)` - 상품별 점수
- `format_product_list(results, verbose, pretty)` - 상품 목록
- `format_product_detail(result, verbose)` - 상품 상세
- `format_category_stats(results, pretty)` - 카테고리 통계
- `format_mapping(mapping, pretty)` - 매핑 정보

## 주의사항

1. **읽기 전용**: 이 스킬은 GET 요청만 수행합니다
2. **환경 구분**: prod 환경에서는 특히 신중하게 작업
3. **결과 크기**: size를 적절히 제한하여 과도한 데이터를 방지
4. **Pretty Print**: URL에 `?pretty`를 추가하면 읽기 쉬운 형태로 응답

## 트러블슈팅

### 연결 실패
- VPN 연결 확인 (회사 내부 네트워크 필요)
- 호스트 주소 및 포트 확인

### 쿼리 오류
- JSON 형식 확인
- 필드 이름 확인 (references/field_mappings.md 참고)
- 쿼리 문법 확인
