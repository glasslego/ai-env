# fact_gift 테이블 가이드

## 개요

| 항목 | 내용 |
|------|------|
| 테이블 경로 | `kudu.dw.fact_gift` |
| 데이터 설명 | 선물하기 주문 팩트 테이블 (결제 완료 기준) |
| 기준 날짜 컬럼 | `order_paid_date` (timestamp) |
| 총 컬럼 수 | 약 160개 |

## 핵심 컬럼 그룹

### 기본 키 & 식별자
| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| order_id | long | 주문 아이디 |
| order_payment_id | long | 주문 결제 아이디 (동일 결제 내 복수 수신자 구분) |
| gift_order_id | long | 선물하기 주문 아이디 |
| gift_order_item_id | long | 선물하기 주문 아이템 아이디 |

### 사용자 정보
| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| order_account_id | long | 주문자(구매자) 계정 아이디 |
| order_commerce_user_id | long | 주문자 커머스 유저 아이디 |
| order_receiver_account_id | long | 수신자 계정 아이디 |
| order_receiver_commerce_user_id | long | 수신자 커머스 유저 아이디 |
| order_app_user_id | long | 주문자 앱 유저 아이디 |

### 금액 정보
| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| gmv_amt | decimal(18,3) | 거래액 (가장 많이 사용) |
| sales_amt | long | 매출액 |
| net_sales_amt | long | 순매출액 |
| order_pay_amt | long | 실제 결제 금액 |
| discount_amt | long | 할인 금액 |
| admin_discount_amt | long | 관리자 할인 금액 |

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
| gift_product_id | long | 선물하기 상품 아이디 |
| gift_item_id | long | 선물하기 아이템 아이디 |
| order_product_item_id | long | 주문 상품 아이템 아이디 |
| gift_brand_id | long | 브랜드 아이디 |
| gift_brand_nm | string | 브랜드명 |

### 카테고리 정보
| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| gift_cate1_id / gift_cate1_nm | long / string | 1차 카테고리 |
| gift_cate2_id / gift_cate2_nm | long / string | 2차 카테고리 |
| gift_product_cate1_id ~ cate4_id | string | 상품 카테고리 (1~4단계) |
| gift_cate_full_nm | string | 카테고리 전체 경로명 |

### 유입 채널 정보
| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| gift_input_channel_id | long | 유입 채널 아이디 |
| gift_input_channel_nm | string | 유입 채널명 |
| order_channel_id | long | 주문 채널 아이디 |
| order_product_referrer_area_cd | string | 유입 영역 코드 |

### 주문 유형 정보
| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| gift_order_type | string | 선물하기 주문 유형 (normal, random, fcfs, quiz 등) |
| order_tome_yn | string | 자기구매 여부 (Y/N) |
| item_type | string | 아이템 유형 |
| order_status_nm | string | 주문 상태명 |

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

### 2. 자기구매 제외

상황에 따라 분석에서 자기구매를 제외해야 하는 경유가 있습니다:

```sql
-- 방법 1: 계정 아이디 비교
WHERE order_account_id <> order_receiver_account_id

-- 방법 2: 플래그 사용
WHERE order_tome_yn = 'N'
```

### 3. 특수 주문 유형 제외

일반 선물 분석 시 특수 유형 제외:

```sql
-- 랜덤박스, 선착순, 퀴즈 등 제외
WHERE gift_order_type NOT IN ('random', 'fcfs', 'quiz')

-- 비지인 선물 제외 (코드, 오픈채팅, 다음카페)
AND gift_order_chat_type NOT IN ('code', 'open_chat', 'daum_cafe')
```

### 4. 유효 수신자 필터

수신자가 실제로 존재하는 건만 집계:

```sql
WHERE order_receiver_commerce_user_id IS NOT NULL
```

### 5. 복수 수신자 구분

동일 결제 내 여러 수신자가 있는 경우:

```sql
-- 복수 수신자 주문 식별
SELECT order_payment_id,
       COUNT(DISTINCT order_receiver_account_id) as receiver_cnt
FROM kudu.dw.fact_gift
WHERE order_paid_date >= timestamp '2025-01-01'
  AND order_paid_date < timestamp '2025-01-02'
GROUP BY order_payment_id
HAVING COUNT(DISTINCT order_receiver_account_id) > 1
```

---

## JOIN 패턴

### 1. 사용자 개인정보 JOIN

```sql
-- 수신자 생년월일 정보 (생일선물 분석용)
SELECT fg.*,
       uop.birthday
FROM kudu.dw.fact_gift fg
LEFT JOIN kudu.ods.user_user_optional_personal_infos uop
  ON fg.order_receiver_commerce_user_id = uop.user_id
WHERE fg.order_paid_date >= timestamp '2025-01-01'
  AND fg.order_paid_date < timestamp '2025-01-02'
```

### 2. 채팅 정보 JOIN

```sql
-- 선물 채팅 상세 정보
SELECT fg.*,
       goc.chat_type,
       goc.message
FROM kudu.dw.fact_gift fg
LEFT JOIN kudu.ods.gift_order_chats goc
  ON fg.gift_order_id = goc.order_id
```

### 3. 이슈데이 기간 JOIN

```sql
-- 설날, 추석, 가정의달 등 이슈데이 분석
SELECT fg.*,
       mcd.issue_day_nm
FROM kudu.dw.fact_gift fg
LEFT JOIN kudu.dw.dim_manual_cd_date mcd
  ON fg.date_id = mcd.date_id
WHERE mcd.issue_day_nm IS NOT NULL
```

### 4. 상품 마스터 JOIN

```sql
-- 상품 상세 정보
SELECT fg.*,
       dgp.product_nm,
       dgp.brand_nm
FROM kudu.dw.fact_gift fg
LEFT JOIN kudu.dw.dim_gift_product dgp
  ON fg.order_product_item_id = dgp.gift_product_id
```

---

## 주의사항

1. **날짜 필터 필수**: `order_paid_date` 조건 없이 조회하면 전체 스캔 발생 (성능 저하)
2. **자기구매 구분**: 분석 목적에 따라 자기구매 포함/제외 결정 필요
3. **중복 주의**: `order_payment_id`와 `order_id`의 관계 이해 필요 (1:N)
4. **금액 단위**: `gmv_amt`는 decimal(18,3)으로 소수점 포함

---

## 예시 쿼리

### 일별 거래액 집계

```sql
SELECT date(order_paid_date) as dt,
       COUNT(DISTINCT order_account_id) as buyer_cnt,
       COUNT(DISTINCT order_id) as order_cnt,
       SUM(gmv_amt) as total_gmv
FROM kudu.dw.fact_gift
WHERE order_paid_date >= timestamp '2025-01-01'
  AND order_paid_date < timestamp '2025-02-01'
  AND order_account_id <> order_receiver_account_id  -- 자기구매 제외
GROUP BY date(order_paid_date)
ORDER BY dt
```

### 채널별 구매자 분석

```sql
SELECT gift_input_channel_nm,
       COUNT(DISTINCT order_account_id) as buyer_cnt,
       SUM(gmv_amt) as total_gmv,
       SUM(gmv_amt) / COUNT(DISTINCT order_account_id) as avg_gmv_per_buyer
FROM kudu.dw.fact_gift
WHERE order_paid_date >= timestamp '2025-01-01'
  AND order_paid_date < timestamp '2025-02-01'
GROUP BY gift_input_channel_nm
ORDER BY total_gmv DESC
```

### 생일선물 분석

```sql
-- 수신자 생일 주간에 받은 선물 분석
SELECT date(fg.order_paid_date) as dt,
       COUNT(DISTINCT fg.order_id) as birthday_gift_cnt,
       SUM(fg.gmv_amt) as birthday_gmv
FROM kudu.dw.fact_gift fg
JOIN kudu.ods.user_user_optional_personal_infos uop
  ON fg.order_receiver_commerce_user_id = uop.user_id
WHERE fg.order_paid_date >= timestamp '2025-01-01'
  AND fg.order_paid_date < timestamp '2025-02-01'
  AND fg.order_account_id <> fg.order_receiver_account_id
  -- 생일 ±3일 이내
  AND ABS(date_diff('day', fg.order_paid_date,
          cast(concat(cast(year(fg.order_paid_date) as varchar), '-',
                 substr(uop.birthday, 5, 5)) as date))) <= 3
GROUP BY date(fg.order_paid_date)
```
