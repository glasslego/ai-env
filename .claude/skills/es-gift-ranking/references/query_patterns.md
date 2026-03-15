# Elasticsearch Query Patterns

자주 사용하는 Elasticsearch 쿼리 패턴 모음입니다.

## Gift Ranking Feature (gift_product_ranking)

### batch_id별 문서 개수 집계
* batch_id 는 아래와 같습니다.
  * 패턴: yyyyMMddHH0000, 예시: 20251118120000
```json
{
  "size": 0,
  "aggs": {
    "batch_counts": {
      "terms": {
        "field": "batch_id",
        "size": 100,
        "order": {"_key": "desc"}
      }
    }
  }
}
```

### 특정 batch의 상위 랭킹 상품 조회
```json
{
  "query": {
    "term": {"batch_id": "20251118120000"}
  },
  "size": 30,
  "sort": [
    {"order_gift_total_score": {"order": "desc"}}
  ]
}
```

### product_id별 점수 조회 (batch별)
```json
{
  "query": {
    "term": {"product_id": "11062448"}
  },
  "size": 100,
  "sort": [
    {"batch_id": {"order": "desc"}}
  ]
}
```

## Promotion Builder (kcai_integrated_gift_product)

### 카테고리/브랜드 필터링 및 정렬
```json
{
  "query": {
    "bool": {
      "filter": [
        {"term": {"large_display_category_code": "91"}}
      ]
    }
  },
  "sort": [{"service_score": {"order": "desc"}}],
  "size": 100
}
```

### 상품 검색
```json
{
  "query": {
    "match": {"display_name": "커피"}
  },
  "size": 20
}
```

## Epsilon Gift Product (epsilon_gift_product_v1)

### 최신 상품 조회
```json
{
  "query": {"match_all": {}},
  "sort": [{"gift_product_ranking_updated_at": {"order": "desc"}}],
  "size": 10
}
```
