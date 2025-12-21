#!/usr/bin/env python3
"""Elasticsearch 결과 포맷팅 유틸리티.

이 모듈은 Elasticsearch 쿼리 결과를 사람이 읽기 쉬운 형태로 포맷팅합니다.
"""

import json
from typing import Any

# Constants
SEPARATOR_WIDTH = 80
SEPARATOR_LINE = "=" * SEPARATOR_WIDTH
DASH_LINE = "-" * SEPARATOR_WIDTH


def _print_header(title: str) -> None:
    """헤더를 출력합니다.

    Args:
        title: 헤더 제목
    """
    print(f"\n{SEPARATOR_LINE}")
    print(title)
    print(SEPARATOR_LINE)


def _print_aggregation_result(results: dict[str, Any]) -> None:
    """전체 aggregation 결과를 출력합니다.

    Args:
        results: Elasticsearch aggregation 응답
    """
    print(f"\n{SEPARATOR_LINE}")
    print("Full Aggregation Result:")
    print(SEPARATOR_LINE)
    print(json.dumps(results["aggregations"], indent=2, ensure_ascii=False))


def format_batch_stats(results: dict[str, Any], pretty: bool = False) -> None:
    """batch_id별 집계 결과를 포맷팅합니다.

    Args:
        results: Elasticsearch aggregation 응답
        pretty: 전체 aggregation 결과도 출력할지 여부

    Example:
        >>> results = {"aggregations": {"batch_counts": {"buckets": [...]}}}
        >>> format_batch_stats(results)
    """
    if "aggregations" not in results or "batch_counts" not in results["aggregations"]:
        print("No batch statistics found.")
        return

    buckets = results["aggregations"]["batch_counts"]["buckets"]

    _print_header("Batch ID Statistics")
    print(f"Total unique batch IDs: {len(buckets)}")
    print(f"\n{'Batch ID':<20} {'Document Count':>15}")
    print(f"{'-'*20} {'-'*15}")

    total_docs = sum(bucket["doc_count"] for bucket in buckets)

    for bucket in buckets:
        batch_id = bucket["key"]
        doc_count = bucket["doc_count"]
        print(f"{batch_id:<20} {doc_count:>15,}")

    print(f"{'-'*20} {'-'*15}")
    print(f"{'TOTAL':<20} {total_docs:>15,}")
    print(SEPARATOR_LINE)

    if pretty:
        _print_aggregation_result(results)


def format_score_stats(results: dict[str, Any], score_field: str = "total_score") -> None:
    """score 통계를 포맷팅합니다.

    Args:
        results: Elasticsearch stats aggregation 응답
        score_field: 통계를 낸 필드명

    Example:
        >>> results = {"aggregations": {"score_stats": {"count": 100, ...}}}
        >>> format_score_stats(results, "order_gift_total_score")
    """
    if "aggregations" not in results or "score_stats" not in results["aggregations"]:
        print("No score statistics found.")
        return

    stats = results["aggregations"]["score_stats"]

    _print_header(f"Score Statistics ({score_field})")
    print(f"Count:   {stats.get('count', 0):>10,}")
    print(f"Min:     {stats.get('min', 0):>10,.2f}")
    print(f"Max:     {stats.get('max', 0):>10,.2f}")
    print(f"Avg:     {stats.get('avg', 0):>10,.2f}")
    print(f"Sum:     {stats.get('sum', 0):>10,.2f}")
    print(SEPARATOR_LINE)


def format_top_products(
    results: dict[str, Any], batch_id: str, score_field: str = "total_score"
) -> None:
    """상위 상품 목록을 포맷팅합니다.

    Args:
        results: Elasticsearch search 응답
        batch_id: 배치 ID
        score_field: 정렬 기준 필드

    Example:
        >>> results = {"hits": {"hits": [...]}}
        >>> format_top_products(results, "20251118140000", "order_gift_total_score")
    """
    if "hits" not in results or not results["hits"]["hits"]:
        print(f"No products found for batch: {batch_id}")
        return

    hits = results["hits"]["hits"]

    _print_header(f"Top Products for Batch: {batch_id}")
    print(f"Total: {len(hits)} products")
    print(f"\n{'Rank':<6} {'Product ID':<20} {'Score':>15}")
    print(f"{'-'*6} {'-'*20} {'-'*15}")

    for idx, hit in enumerate(hits, 1):
        source = hit["_source"]
        product_id = source.get("product_id", "N/A")
        score = source.get(score_field, 0)
        print(f"{idx:<6} {product_id:<20} {score:>15,.4f}")

    print(SEPARATOR_LINE)


def _print_product_scores_verbose(hits: list[dict[str, Any]], score_field: str) -> None:
    """상세 모드로 상품 점수를 출력합니다.

    Args:
        hits: Elasticsearch hits 리스트
        score_field: 주요 점수 필드명
    """
    header = (
        f"\n{'#':<4} {'Batch ID':<20} {score_field:>15} "
        f"{'Ranking':>15} {'Self Purchase':>15} {'Service':>15}"
    )
    print(header)
    print(f"{'-'*4} {'-'*20} {'-'*15} {'-'*15} {'-'*15} {'-'*15}")

    for idx, hit in enumerate(hits, 1):
        source = hit["_source"]
        batch_id = source.get("batch_id", "N/A")
        main_score = source.get(score_field, 0)
        ranking_score = source.get("ranking_score", 0)
        self_purchase = source.get("self_purchase_score", 0)
        service = source.get("service_score", 0)
        print(
            f"{idx:<4} {batch_id:<20} {main_score:>15,.4f} "
            f"{ranking_score:>15,.4f} {self_purchase:>15,.4f} {service:>15,.4f}"
        )


def _print_product_scores_simple(hits: list[dict[str, Any]], score_field: str) -> None:
    """간단 모드로 상품 점수를 출력합니다.

    Args:
        hits: Elasticsearch hits 리스트
        score_field: 점수 필드명
    """
    print(f"\n{'#':<4} {'Batch ID':<20} {score_field:>15}")
    print(f"{'-'*4} {'-'*20} {'-'*15}")

    for idx, hit in enumerate(hits, 1):
        source = hit["_source"]
        batch_id = source.get("batch_id", "N/A")
        score = source.get(score_field, 0)
        print(f"{idx:<4} {batch_id:<20} {score:>15,.4f}")


def format_product_scores(
    results: dict[str, Any],
    product_id: str,
    score_field: str = "total_score",
    verbose: bool = False,
) -> None:
    """특정 product_id의 batch별 점수를 포맷팅합니다.

    Args:
        results: Elasticsearch search 응답
        product_id: 상품 ID
        score_field: 표시할 주요 점수 필드
        verbose: 상세 모드 (모든 스코어 필드 표시)

    Example:
        >>> results = {"hits": {"hits": [...]}}
        >>> format_product_scores(
        ...     results, "11062448", "order_gift_total_score", verbose=True
        ... )
    """
    if "hits" not in results or not results["hits"]["hits"]:
        print(f"No data found for product: {product_id}")
        return

    hits = results["hits"]["hits"]

    _print_header(f"Product Scores by Batch: {product_id}")
    print(f"Total batches: {len(hits)}")

    if verbose:
        _print_product_scores_verbose(hits, score_field)
    else:
        _print_product_scores_simple(hits, score_field)

    print(SEPARATOR_LINE)


def _get_product_name(source: dict[str, Any]) -> str:
    """상품명을 조회합니다.

    Args:
        source: Elasticsearch document source

    Returns:
        상품명 (없으면 'N/A')
    """
    return source.get("product_name", source.get("display_name", "N/A"))


def _get_product_price(source: dict[str, Any]) -> Any:
    """상품 가격을 조회합니다.

    Args:
        source: Elasticsearch document source

    Returns:
        상품 가격 (없으면 'N/A')
    """
    return source.get("selling_price", source.get("price", "N/A"))


def _print_product_detailed(hits: list[dict[str, Any]], pretty: bool = False) -> None:
    """상품 목록을 상세 모드로 출력합니다.

    Args:
        hits: Elasticsearch hits 리스트
        pretty: 전체 데이터 출력 여부
    """
    print("\nProducts (Detailed):")
    for i, hit in enumerate(hits, 1):
        source = hit["_source"]
        print(f"\n{DASH_LINE}")
        print(f"Product {i}")
        print(DASH_LINE)
        print(f"ID:    {source.get('product_id', 'N/A')}")
        print(f"Name:  {_get_product_name(source)}")

        price = _get_product_price(source)
        print(f"Price: {price if price == 'N/A' else f'{price:,}'}")
        print(f"Score: {hit.get('_score', 'N/A')}")

        if pretty:
            print("\nFull Data:")
            print(json.dumps(source, indent=2, ensure_ascii=False))


def _print_product_list_simple(hits: list[dict[str, Any]]) -> None:
    """상품 목록을 간단 모드로 출력합니다.

    Args:
        hits: Elasticsearch hits 리스트
    """
    print(f"\n{'#':<4} {'Product ID':<20} {'Product Name':<40} {'Price':>12}")
    print(f"{'-'*4} {'-'*20} {'-'*40} {'-'*12}")

    for i, hit in enumerate(hits, 1):
        source = hit["_source"]
        product_id = str(source.get("product_id", "N/A"))[:20]
        product_name = str(_get_product_name(source))[:40]
        price = source.get("selling_price", source.get("price", 0))
        print(f"{i:<4} {product_id:<20} {product_name:<40} {price:>12,}")


def format_product_list(
    results: dict[str, Any], verbose: bool = False, pretty: bool = False
) -> None:
    """상품 목록을 포맷팅합니다.

    Args:
        results: Elasticsearch search 응답
        verbose: 상세 모드
        pretty: Pretty print 모드

    Example:
        >>> results = {"hits": {"total": {"value": 100}, "hits": [...]}}
        >>> format_product_list(results, verbose=False)
    """
    if "hits" not in results:
        return

    total = results["hits"].get("total", {})
    total_hits = total.get("value", 0) if isinstance(total, dict) else total

    _print_header(f"Total products: {total_hits}")
    print(f"Returned: {len(results['hits']['hits'])}")
    print(SEPARATOR_LINE)

    hits = results["hits"]["hits"]
    if not hits:
        print("\nNo products found.")
        return

    if verbose:
        _print_product_detailed(hits, pretty)
    else:
        _print_product_list_simple(hits)


def _print_product_common_fields(source: dict[str, Any]) -> None:
    """상품 공통 필드를 출력합니다.

    Args:
        source: Elasticsearch document source
    """
    if "product_name" in source or "display_name" in source:
        name = _get_product_name(source)
        print(f"Name:  {name}")

    if "selling_price" in source or "price" in source:
        price = _get_product_price(source)
        print(f"Price: {price if price == 'N/A' else f'{price:,}'}")

    if "brand_name" in source:
        print(f"Brand: {source.get('brand_name', 'N/A')}")


def format_product_detail(result: dict[str, Any], verbose: bool = False) -> None:
    """단일 상품 상세 정보를 포맷팅합니다 (_id로 조회한 결과).

    Args:
        result: Elasticsearch GET /_doc/{id} 응답
        verbose: 상세 모드 (전체 데이터 출력)

    Example:
        >>> result = {"found": True, "_source": {...}, "_id": "123"}
        >>> format_product_detail(result, verbose=True)
    """
    if not result.get("found"):
        _print_header("Product NOT Found")
        print(f"ID: {result.get('_id', 'N/A')}")
        return

    source = result.get("_source", {})

    _print_header("Product Found")
    print(f"ID:    {result.get('_id', 'N/A')}")
    print(f"Index: {result.get('_index', 'N/A')}")

    _print_product_common_fields(source)

    if verbose:
        print(f"\n{DASH_LINE}")
        print("Full Data:")
        print(DASH_LINE)
        print(json.dumps(source, indent=2, ensure_ascii=False))


def format_category_stats(results: dict[str, Any], pretty: bool = False) -> None:
    """카테고리별 통계를 포맷팅합니다.

    Args:
        results: Elasticsearch aggregation 응답
        pretty: 전체 aggregation 결과도 출력할지 여부

    Example:
        >>> results = {"aggregations": {"categories": {"buckets": [...]}}}
        >>> format_category_stats(results)
    """
    if "aggregations" not in results or "categories" not in results["aggregations"]:
        print("No category statistics found.")
        return

    buckets = results["aggregations"]["categories"]["buckets"]

    _print_header("Category Statistics")
    print(f"Total unique categories: {len(buckets)}")
    print(f"\n{'Category':<30} {'Product Count':>15}")
    print(f"{'-'*30} {'-'*15}")

    total_products = sum(bucket["doc_count"] for bucket in buckets)

    for bucket in buckets:
        category = bucket["key"]
        doc_count = bucket["doc_count"]
        print(f"{category:<30} {doc_count:>15,}")

    print(f"{'-'*30} {'-'*15}")
    print(f"{'TOTAL':<30} {total_products:>15,}")
    print(SEPARATOR_LINE)

    if pretty:
        _print_aggregation_result(results)


def _print_mapping_fields(mappings: dict[str, Any]) -> None:
    """매핑 필드 정보를 출력합니다.

    Args:
        mappings: Elasticsearch mappings 정보
    """
    if "properties" not in mappings:
        return

    print(f"\nFields ({len(mappings['properties'])} total):")
    for field_name, field_info in sorted(mappings["properties"].items()):
        field_type = field_info.get("type", "object")
        print(f"  - {field_name}: {field_type}")

        if "properties" in field_info:
            for nested_field, nested_info in sorted(field_info["properties"].items()):
                nested_type = nested_info.get("type", "object")
                print(f"      - {nested_field}: {nested_type}")


def format_mapping(mapping: dict[str, Any], pretty: bool = False) -> None:
    """인덱스 매핑을 포맷팅합니다.

    Args:
        mapping: Elasticsearch _mapping 응답
        pretty: 전체 매핑도 출력할지 여부

    Example:
        >>> mapping = {"index_name": {"mappings": {"properties": {...}}}}
        >>> format_mapping(mapping, pretty=False)
    """
    _print_header("Index Mapping:")

    for index_name, index_data in mapping.items():
        print(f"\nIndex: {index_name}")

        if "mappings" not in index_data:
            continue

        mappings = index_data["mappings"]
        _print_mapping_fields(mappings)

        if pretty:
            print(f"\n{SEPARATOR_LINE}")
            print("Full Mapping:")
            print(SEPARATOR_LINE)
            print(json.dumps(mappings, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    print("This module provides formatting utilities for Elasticsearch results.")
    print("\nAvailable functions:")
    print("  - format_batch_stats()")
    print("  - format_score_stats()")
    print("  - format_top_products()")
    print("  - format_product_scores()")
    print("  - format_product_list()")
    print("  - format_product_detail()")
    print("  - format_category_stats()")
    print("  - format_mapping()")
