# fact_talkstore 테이블 가이드

## 개요

| 항목 | 내용 |
|------|------|
| 테이블 경로 | `kudu.dw.fact_talkstore` |
| 데이터 설명 | 톡스토어(톡딜) 주문 팩트 테이블 (결제 완료 기준) |
| 기준 날짜 컬럼 | `order_paid_date` (timestamp) |
| 총 컬럼 수 | 약 150개 |

## 핵심 컬럼 그룹

### 기본 키 & 식별자
| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| order_id | long | 주문 아이디 |
| order_payment_id | long | 주문 결제 아이디 |
| talkstore_order_product_id | long | 톡스토어 주문 상품 아이디 |

### 사용자 정보
| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| order_account_id | long | 주문자 계정 아이디 |
| order_commerce_user_id | long | 주문자 커머스 유저 아이디 |
| order_receiver_account_id | long | 수신자 계정 아이디 |
| order_receiver_commerce_user_id | long | 수신자 커머스 유저 아이디 |

### 금액 정보
| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| gmv_amt | decimal(18,3) | 거래액 (가장 많이 사용) |
| sales_amt | long | 매출액 |
| net_sales_amt | long | 순매출액 |
| discount_amt | long | 할인 금액 |
| admin_discount_amt | long | 관리자 할인 금액 |
| order_talkstore_payment_discount_price | decimal(10,1) | 톡스토어 결제 할인 가격 |

### 날짜/시간 정보
| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| order_paid_at | timestamp | 주문 결제 일시 |
| order_paid_date | timestamp | 주문 결제 일자 (기준 날짜로 주로 사용) |
| order_created_at | timestamp | 주문 생성 일시 |
| order_created_date | timestamp | 주문 생성 일자 |
| order_canceled_date | timestamp | 주문 취소 일자 |

### 상품 정보
| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| talkstore_product_id | long | 톡스토어 상품 아이디 |
| order_product_item_id | long | 주문 상품 아이템 아이디 |
| order_product_nm | string | 주문 상품명 |
| order_product_brand_nm | string | 주문 상품 브랜드명 |

### 스토어 정보
| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| talkstore_store_id | long | 스토어 아이디 |
| talkstore_store_nm | string | 스토어명 |
| talkstore_store_domain_nm | string | 스토어 도메인명 |
| talkstore_store_rep_cate_nm | string | 스토어 대표 카테고리명 |

### 카테고리 정보
| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| talkstore_product_cate1_id ~ cate4_id | string | 상품 카테고리 (1~4단계) |
| talkstore_product_cate1_nm ~ cate4_nm | string | 상품 카테고리명 (1~4단계) |
| talkstore_product_cate_full_nm | string | 카테고리 전체 경로명 |

### 유입 채널 정보
| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| talkstore_referrer_area_id | long | 유입 영역 아이디 |
| talkstore_referrer_area_nm | string | 유입 영역명 |
| talkstore_referrer_init_area_id | long | 최초 유입 영역 아이디 |
| talkstore_referrer_area_group_nm | string | 유입 영역 그룹명 |
| order_product_referrer_event_id | string | 기획전 ID |
| order_product_referrer_msg_id | string | 메시지 ID |

### 주문 유형 정보
| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| group_purchase_yn | string | 공동구매 주문 여부 (Y/N) |
| order_talkstore_group_discount_yn | string | 톡스토어 공동구매 할인 여부 |
| order_tome_yn | string | 자기구매 여부 (Y/N) |
| item_type | string | 아이템 유형 |
| order_status_nm | string | 주문 상태명 |

### 공동구매 관련 (톡스토어 고유)
| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| talkstore_group_discount_id | long | 공동구매 할인 아이디 |
| talkstore_group_discount_room_id | long | 공동구매 방 아이디 |
| talkstore_group_discount_group_size | long | 공동구매 그룹 크기 |
| talkstore_group_discount_price | long | 공동구매 할인 가격 |
| talkstore_group_discount_room_user_cnt | long | 공동구매 방 유저 수 |
| talkstore_group_discount_user_creator_yn | string | 공동구매 개설자 여부 |
| talkstore_group_discount_room_succeeded_at | timestamp | 공동구매 성공 시간 |
| talkstore_group_discount_user_kakao_point | long | 공동구매 카카오 포인트 |

### 라이브 관련
| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| live_content_id | long | 라이브 컨텐츠 아이디 |
| live_sale_yn | string | 라이브 판매 여부 |
| live_on_type | string | 라이브 방송중 유형 |

---

## 사용팁

### 1. 기본 필터 조건

```sql
-- 기본 기간 필터 (order_paid_date 사용)
WHERE order_paid_date >= timestamp '2025-01-01'
  AND order_paid_date < timestamp '2025-02-01'

-- 날짜 추출이 필요한 경우
WHERE date(order_paid_date) >= date '2025-01-01'
  AND date(order_paid_date) <= date '2025-01-31'
```

### 2. 공동구매 필터 (중요!)

공동구매 분석 시 두 가지 조건을 모두 확인:

```sql
-- 공동구매 주문만 추출
WHERE group_purchase_yn = 'Y'
  AND order_talkstore_group_discount_yn = 'Y'

-- 일반 톡딜만 추출 (공동구매 제외)
WHERE group_purchase_yn = 'N'
```

### 3. 주문 상태 필터

유효 주문만 집계할 때:

```sql
-- 취소/반품 제외
WHERE order_status_nm NOT IN ('취소', '반품', '환불')
```

### 4. 신규/기존 고객 구분

```sql
-- 사용자의 첫 구매일 확인
WITH first_purchase AS (
    SELECT order_account_id,
           MIN(order_paid_at) as first_paid_at
    FROM kudu.dw.fact_talkstore
    WHERE order_paid_date >= timestamp '2024-01-01'
    GROUP BY order_account_id
)
SELECT ft.*,
       CASE WHEN date(ft.order_paid_at) = date(fp.first_paid_at)
            THEN 'new' ELSE 'existing' END as customer_type
FROM kudu.dw.fact_talkstore ft
LEFT JOIN first_purchase fp
  ON ft.order_account_id = fp.order_account_id
```

### 5. 월별 집계

```sql
-- 월별 집계 패턴
SELECT date_format(order_paid_date, '%Y-%m') as month,
       COUNT(DISTINCT order_account_id) as buyer_cnt,
       SUM(gmv_amt) as total_gmv
FROM kudu.dw.fact_talkstore
WHERE order_paid_date >= timestamp '2025-01-01'
GROUP BY date_format(order_paid_date, '%Y-%m')
```

---

## JOIN 패턴

### 1. 쿠폰 정보 JOIN

```sql
-- 쿠폰 사용 분석
SELECT ft.*,
       ftc.coupon_type,
       ftc.discount_amt as coupon_discount
FROM kudu.dw.fact_talkstore ft
LEFT JOIN kudu.dw.fact_talkstore_coupon ftc
  ON ft.talkstore_coupon_id = ftc.coupon_id
```

### 2. 사용자 활동 순위 JOIN

```sql
-- 사용자별 구매 순위
SELECT ft.*,
       rank.purchase_rank
FROM kudu.dw.fact_talkstore ft
LEFT JOIN kudu.dw.fact_talkstore_order_paid_date_rank rank
  ON ft.order_account_id = rank.user_id
  AND ft.order_paid_date = rank.order_paid_date
```

### 3. 스토어 상세 정보 JOIN

```sql
-- 스토어 등급 정보
SELECT ft.*,
       ts.store_grade,
       ts.seller_type
FROM kudu.dw.fact_talkstore ft
LEFT JOIN kudu.dw.dim_talkstore_store ts
  ON ft.talkstore_store_id = ts.store_id
```

---

## 주의사항

1. **날짜 필터 필수**: `order_paid_date` 조건 없이 조회하면 전체 스캔 발생 (성능 저하)
2. **공동구매 구분**: `group_purchase_yn`과 `order_talkstore_group_discount_yn` 모두 확인 필요
3. **유입 영역**: `talkstore_referrer_area_id`와 `talkstore_referrer_init_area_id` 구분 (현재 vs 최초)
4. **금액 단위**: `gmv_amt`는 decimal(18,3)으로 소수점 포함

---

## 예시 쿼리

### 일별 거래액 집계

```sql
SELECT date(order_paid_date) as dt,
       COUNT(DISTINCT order_account_id) as buyer_cnt,
       COUNT(DISTINCT order_id) as order_cnt,
       SUM(gmv_amt) as total_gmv
FROM kudu.dw.fact_talkstore
WHERE order_paid_date >= timestamp '2025-01-01'
  AND order_paid_date < timestamp '2025-02-01'
GROUP BY date(order_paid_date)
ORDER BY dt
```

### 공동구매 vs 일반 톡딜 비교

```sql
SELECT date(order_paid_date) as dt,
       group_purchase_yn,
       COUNT(DISTINCT order_account_id) as buyer_cnt,
       COUNT(DISTINCT order_id) as order_cnt,
       SUM(gmv_amt) as total_gmv
FROM kudu.dw.fact_talkstore
WHERE order_paid_date >= timestamp '2025-01-01'
  AND order_paid_date < timestamp '2025-02-01'
GROUP BY date(order_paid_date), group_purchase_yn
ORDER BY dt, group_purchase_yn
```

### 유입 영역별 분석

```sql
SELECT talkstore_referrer_area_group_nm,
       talkstore_referrer_area_nm,
       COUNT(DISTINCT order_account_id) as buyer_cnt,
       SUM(gmv_amt) as total_gmv,
       SUM(gmv_amt) / COUNT(DISTINCT order_account_id) as avg_gmv_per_buyer
FROM kudu.dw.fact_talkstore
WHERE order_paid_date >= timestamp '2025-01-01'
  AND order_paid_date < timestamp '2025-02-01'
GROUP BY talkstore_referrer_area_group_nm, talkstore_referrer_area_nm
ORDER BY total_gmv DESC
```

### 신규 구매자 잔존율 분석

```sql
-- 특정 월 신규 구매자의 다음 달 재구매율
WITH new_buyers AS (
    SELECT order_account_id,
           MIN(date_format(order_paid_date, '%Y-%m')) as first_month
    FROM kudu.dw.fact_talkstore
    WHERE order_paid_date >= timestamp '2024-01-01'
    GROUP BY order_account_id
),
jan_new AS (
    SELECT order_account_id
    FROM new_buyers
    WHERE first_month = '2025-01'
)
SELECT
    '2025-01' as cohort_month,
    COUNT(DISTINCT jn.order_account_id) as new_buyer_cnt,
    COUNT(DISTINCT CASE WHEN ft.order_paid_date >= timestamp '2025-02-01'
                        AND ft.order_paid_date < timestamp '2025-03-01'
                        THEN ft.order_account_id END) as feb_repurchase_cnt
FROM jan_new jn
LEFT JOIN kudu.dw.fact_talkstore ft
  ON jn.order_account_id = ft.order_account_id
```

### 스토어별 실적

```sql
SELECT talkstore_store_id,
       talkstore_store_nm,
       talkstore_store_rep_cate_nm,
       COUNT(DISTINCT order_account_id) as buyer_cnt,
       COUNT(DISTINCT order_id) as order_cnt,
       SUM(gmv_amt) as total_gmv
FROM kudu.dw.fact_talkstore
WHERE order_paid_date >= timestamp '2025-01-01'
  AND order_paid_date < timestamp '2025-02-01'
GROUP BY talkstore_store_id, talkstore_store_nm, talkstore_store_rep_cate_nm
ORDER BY total_gmv DESC
LIMIT 100
```
