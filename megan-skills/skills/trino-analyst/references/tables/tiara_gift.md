# tiara_gift 테이블 가이드

## 개요

| 항목 | 내용 |
|------|------|
| 테이블 경로 | `iceberg.log_iceberg.tiara_gift` |
| 레거시 경로 | `hive.log.tiara_gift` (이전 방식, 동일 데이터) |
| 데이터 설명 | 선물하기 사용자 이벤트 로그 테이블 (행동 데이터) |
| 파티션 키 | `dt` (날짜), `hr` (시간) |
| 특징 | **Flat 컬럼** + Map 컬럼 이중 구조 |

## 테이블 구조 특징

Iceberg 테이블은 **flat 컬럼**과 **map 컬럼** 두 가지 접근법을 모두 지원합니다.
**항상 flat 컬럼을 우선 사용**하세요. 더 효율적이고 타입 변환이 불필요합니다.

```sql
-- ✅ 권장: flat 컬럼 사용 (타입 변환 불필요)
SELECT user_account_id,     -- bigint 타입
       action_type,
       common_page
FROM iceberg.log_iceberg.tiara_gift

-- ⚠️ 레거시: element_at() 사용 (hive 테이블 호환용)
SELECT element_at(user, 'account_id') as account_id  -- string 타입, 변환 필요
FROM hive.log.tiara_gift
```

---

## 핵심 Flat 컬럼

### 사용자 정보
| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| user_account_id | bigint | 계정 아이디 (핵심!) |
| user_isuid | varchar | 고유 식별자 |

### 액션 정보
| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| action_type | varchar | 액션 타입 (Pageview, Click, Event, Purchase) |
| action_name | varchar | 액션명 |
| action_kind | varchar | 액션 종류 |

### 공통 정보
| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| common_page | varchar | 페이지명 |
| common_section | varchar | 섹션명 |
| common_service | varchar | 서비스명 |
| common_url | varchar | URL |
| common_access_timestamp | bigint | 접근 타임스탬프 |

### 커스텀 속성 (중요!)
| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| custom_props_input_channel_id | bigint | 유입 채널 ID |
| custom_props_tiara_purchase_entry | varchar | **구매 지면 코드** (전환 분석 핵심!) |
| custom_props_tiara_purchase_dkt | varchar | 시즌탭(DKT) 구매 지면 코드 |
| custom_props_impression_id | varchar | **추천 슬롯 ID** (일반 로그) |
| custom_props_tiara_purchase_impression_id | varchar | **추천 슬롯 ID** (구매 로그) |

### 클릭 정보
| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| click_layer1 | varchar | 클릭 영역 1단계 |
| click_layer2 | varchar | 클릭 영역 2단계 |
| click_layer3 | varchar | 클릭 영역 3단계 |
| click_click_url | varchar | 클릭 URL |

### 환경 정보
| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| env_browser | varchar | 브라우저 |
| env_ip | varchar | IP 주소 |

### 파티션
| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| dt | varchar | 날짜 (YYYY-MM-DD) |
| hr | varchar | 시간 (00-23) |

---

## 배열 필드

### viewimp_contents (노출 콘텐츠 배열)
여러 상품이 한 화면에 노출될 때 배열로 저장됩니다.

| 필드 경로 | 타입 | 설명 |
|-----------|------|------|
| viewimp_contents.element.id | string | 콘텐츠 ID |
| viewimp_contents.element.name | string | 콘텐츠명 |
| viewimp_contents.element.category | string | 카테고리 |
| viewimp_contents.element.imp_area | string | 노출 영역 |
| viewimp_contents.element.imp_ordnum | string | 노출 순서 |

### ecommerce_contents (구매 상품 배열)
구매 시 여러 상품 정보가 배열로 저장됩니다.

---

## 사용팁

### 1. 기본 필터 조건 (파티션 필수!)

```sql
-- 날짜 + 시간 파티션 활용
WHERE dt >= '2025-01-01'
  AND dt <= '2025-01-07'

-- 특정 시간대만
WHERE dt = '2025-01-01'
  AND hr BETWEEN '09' AND '18'
```

### 2. Flat 컬럼 접근 방법

```sql
-- ✅ flat 컬럼 사용 (권장)
SELECT
    user_account_id,      -- bigint, 타입 변환 불필요
    action_type,
    common_page
FROM iceberg.log_iceberg.tiara_gift
WHERE dt = '2025-01-01'
```

### 3. 액션 타입 필터

```sql
-- 페이지뷰만
WHERE action_type = 'Pageview'

-- 클릭만
WHERE action_type = 'Click'

-- 이벤트만
WHERE action_type = 'Event'

-- 구매 이벤트
WHERE action_type = 'Purchase'
```

### 4. 유입 채널 필터

```sql
-- 특정 유입 채널
WHERE custom_props_input_channel_id IN (11861, 11862)
```

### 5. 팩트 테이블 JOIN (타입 변환 불필요!)

```sql
-- ✅ flat 컬럼 사용 시 타입 변환 불필요
SELECT tg.*, fg.gmv_amt
FROM iceberg.log_iceberg.tiara_gift tg
JOIN kudu.dw.fact_gift fg
  ON tg.user_account_id = fg.order_account_id  -- bigint = bigint
WHERE tg.dt = '2025-01-01'
  AND fg.order_paid_date >= timestamp '2025-01-01'
```

### 6. 배열 처리 (UNNEST)

```sql
-- viewimp_contents 배열을 행으로 풀기
SELECT
    user_account_id,
    element_at(content, 'id') as content_id,
    element_at(content, 'name') as content_name
FROM iceberg.log_iceberg.tiara_gift
CROSS JOIN UNNEST(viewimp_contents) AS t(content)
WHERE dt = '2025-01-01'
  AND viewimp_contents IS NOT NULL
```

### 7. 구매 지면 코드 (tiara_purchase_entry) - 전환 분석 핵심!

`tiara_purchase_entry`는 유저의 구매가 발생할 수 있는 지면들을 별도의 코드로 관리하는 컬럼입니다.
전환 거래액 분석에 핵심적으로 사용됩니다.

```sql
-- ✅ flat 컬럼 사용 (우선순위: dkt > entry)
SELECT
    COALESCE(custom_props_tiara_purchase_dkt, custom_props_tiara_purchase_entry) as tiara_purchase_entry
FROM iceberg.log_iceberg.tiara_gift
WHERE dt = '2025-01-01'
  AND action_kind = 'Purchase'
```

**주요 entry code 유형:**
- `home_theme`, `home_ai`, `home_main_banner` - 홈 영역
- `home_story_gift`, `home_theme_birthday` - 스토리/생일 테마
- `home_reaction_ranking` - 반응 랭킹
- `home_friends_wish` - 친구 위시
- `giftbox_friends_wish_more` - 선물함 위시
- `시즌탭 DKT 코드` (예: christmas2022-14134) - 시즌 이벤트

**dim 테이블 JOIN으로 상세 정보 확인:**
```sql
-- entry_code 메타정보와 JOIN
SELECT
    entry.tiara_purchase_entry1_nm as "유입경로_1depth",
    entry.tiara_purchase_entry2_nm as "유입경로_2depth",
    entry.tiara_purchase_entry3_nm as "유입경로_3depth",
    entry.tiara_purchase_entry4_nm as "유입경로_4depth",
    entry.promotion_builder_id,
    entry.event_ad_yn  -- 광고 여부
FROM kudu.dw.dim_gift_tiara_purchase_entry entry
WHERE entry.tiara_purchase_entry4_cd = 'your_entry_code'
```

### 8. 추천 슬롯 ID (impression_id) - 추천팀 분석용

추천팀에서 만든 추천 슬롯에서 발생한 로그일 경우 남는 항목입니다.
이 ID를 기준으로 어떤 추천앱을 통해 유저 액션이 발생했는지 파악할 수 있습니다.

**컬럼 구분:**
- `custom_props.impression_id` - 일반 로그 (Pageview, Click, Event 등)
- `custom_props.tiara_purchase_impression_id` - 구매 로그 (Purchase)

```sql
-- ✅ 일반 로그에서 추천 슬롯별 노출/클릭 추적 (flat 컬럼)
SELECT
    custom_props_impression_id as impression_id,
    action_type,
    COUNT(*) as cnt,
    COUNT(DISTINCT user_account_id) as uv
FROM iceberg.log_iceberg.tiara_gift
WHERE dt >= '2025-01-01'
  AND dt <= '2025-01-07'
  AND custom_props_impression_id IS NOT NULL
GROUP BY 1, 2

-- ✅ 구매 로그에서 추천 슬롯별 전환 추적 (flat 컬럼)
SELECT
    custom_props_tiara_purchase_impression_id as impression_id,
    COUNT(DISTINCT try_cast(url_extract_parameter(
        replace(common_url, ' ', ''), 'paymentId') as bigint)) as payment_cnt
FROM iceberg.log_iceberg.tiara_gift
WHERE dt >= '2025-01-01'
  AND dt <= '2025-01-07'
  AND action_kind = 'Purchase'
  AND custom_props_tiara_purchase_impression_id IS NOT NULL
GROUP BY 1
```

**주요 impression_id 예시:**
- `air_gift_search_product_search` - 검색 결과 추천
- 기타 추천팀에서 정의한 슬롯 ID들

---

## JOIN 패턴

### 1. fact_gift와 연결 (방문 → 구매 전환)

```sql
-- ✅ 방문자 중 구매자 확인 (flat 컬럼 - 타입 변환 불필요)
SELECT
    tg.dt,
    COUNT(DISTINCT tg.user_account_id) as visitor_cnt,
    COUNT(DISTINCT fg.order_account_id) as buyer_cnt
FROM iceberg.log_iceberg.tiara_gift tg
LEFT JOIN kudu.dw.fact_gift fg
  ON tg.user_account_id = fg.order_account_id  -- bigint = bigint
  AND fg.order_paid_date BETWEEN cast(tg.dt as timestamp) AND cast(tg.dt as timestamp) + interval '7' day
WHERE tg.dt >= '2025-01-01'
  AND tg.dt <= '2025-01-07'
  AND tg.action_type = 'Pageview'
GROUP BY tg.dt
```

### 2. 프로모션 기간 분석

방문과 구매 사이에 시간 버퍼를 두어야 합니다:

```sql
-- ✅ 프로모션 기간 방문 후 10일 이내 구매 (flat 컬럼)
SELECT
    fg.*
FROM iceberg.log_iceberg.tiara_gift tg
JOIN kudu.dw.fact_gift fg
  ON tg.user_account_id = fg.order_account_id  -- bigint = bigint
WHERE tg.dt BETWEEN '2025-04-30' AND '2025-05-06'  -- 프로모션 기간
  AND tg.action_type = 'Pageview'
  AND fg.order_paid_date >= timestamp '2025-04-30'
  AND fg.order_paid_date < timestamp '2025-05-17'  -- +10일
```

---

## 주의사항

1. **파티션 필수**: `dt`와 `hr` 파티션 조건 필수 (데이터량이 매우 큼)
2. **Flat 컬럼 우선 사용**: `user_account_id`, `action_type` 등 flat 컬럼 사용 권장
3. **타입 변환 불필요**: flat 컬럼 사용 시 `user_account_id`가 이미 bigint이므로 변환 불필요
4. **배열 필드 주의**: `viewimp_contents` 등 배열은 여전히 `element_at()` 필요
5. **테이블 마이그레이션**: `hive.log.tiara_gift` → `iceberg.log_iceberg.tiara_gift`로 이전됨

---

## 예시 쿼리

### 일별 방문자 수 (UV)

```sql
SELECT
    dt,
    COUNT(DISTINCT user_account_id) as uv
FROM iceberg.log_iceberg.tiara_gift
WHERE dt >= '2025-01-01'
  AND dt <= '2025-01-31'
  AND action_type = 'Pageview'
GROUP BY dt
ORDER BY dt
```

### 페이지별 방문 통계

```sql
SELECT
    common_page,
    COUNT(*) as pv,
    COUNT(DISTINCT user_account_id) as uv
FROM iceberg.log_iceberg.tiara_gift
WHERE dt = '2025-01-01'
  AND action_type = 'Pageview'
GROUP BY common_page
ORDER BY pv DESC
```

### 유입 채널별 분석

```sql
SELECT
    custom_props_input_channel_id as channel_id,
    COUNT(DISTINCT user_account_id) as uv,
    COUNT(*) as pv
FROM iceberg.log_iceberg.tiara_gift
WHERE dt >= '2025-01-01'
  AND dt <= '2025-01-07'
  AND action_type = 'Pageview'
  AND custom_props_input_channel_id IS NOT NULL
GROUP BY custom_props_input_channel_id
ORDER BY uv DESC
```

### 검색어 분석

```sql
SELECT
    element_at(search, 'search_term') as keyword,
    COUNT(*) as search_cnt,
    COUNT(DISTINCT user_account_id) as searcher_cnt
FROM iceberg.log_iceberg.tiara_gift
WHERE dt = '2025-01-01'
  AND action_type = 'Event'
  AND element_at(search, 'search_term') IS NOT NULL
GROUP BY element_at(search, 'search_term')
ORDER BY search_cnt DESC
LIMIT 100
```

### 친구탭 냉담자 분석 (특정 기간 미방문자)

```sql
-- 최근 30일간 방문하지 않은 사용자
WITH recent_visitors AS (
    SELECT DISTINCT user_account_id
    FROM iceberg.log_iceberg.tiara_gift
    WHERE dt >= date_format(current_date - interval '30' day, '%Y-%m-%d')
      AND action_type = 'Pageview'
      AND common_page = 'friends_tab'  -- 친구탭
)
SELECT fg.order_account_id
FROM kudu.dw.fact_gift fg
WHERE fg.order_paid_date >= current_date - interval '365' day
  AND fg.order_account_id NOT IN (SELECT user_account_id FROM recent_visitors WHERE user_account_id IS NOT NULL)
GROUP BY fg.order_account_id
```

### 구매 지면별 전환 거래액 분석 (entry_code 기반)

```sql
-- ✅ entry_code별 전환 거래액 집계 (flat 컬럼)
SELECT
    date(gift.order_paid_date) as dt,
    entry.tiara_purchase_entry1_nm as "유입경로_1depth",
    entry.tiara_purchase_entry2_nm as "유입경로_2depth",
    entry.tiara_purchase_entry3_nm as "유입경로_3depth",
    SUM(gift.gmv_amt) as "거래액",
    COUNT(DISTINCT gift.order_payment_id) as "결제건수",
    COUNT(DISTINCT gift.order_account_id) as "결제자수"
FROM (
    SELECT
        dt,
        try_cast(url_extract_parameter(
            replace(common_url, ' ', ''), 'paymentId') as bigint) as payment_id,
        COALESCE(custom_props_tiara_purchase_dkt, custom_props_tiara_purchase_entry) as tiara_purchase_entry
    FROM iceberg.log_iceberg.tiara_gift
    WHERE dt >= '2025-01-01'
      AND dt <= '2025-01-31'
      AND action_kind = 'Purchase'
    GROUP BY 1, 2, 3
) tiara
INNER JOIN kudu.dw.dim_gift_tiara_purchase_entry entry
    ON tiara.tiara_purchase_entry = entry.tiara_purchase_entry4_cd
INNER JOIN kudu.dw.fact_gift gift
    ON tiara.payment_id = gift.order_payment_id
WHERE gift.order_status_cd > 200
  AND gift.order_paid_date >= cast('2025-01-01' as timestamp)
  AND gift.order_paid_date <= cast('2025-01-31' as timestamp)
GROUP BY 1, 2, 3, 4
ORDER BY 1, 2, 3, 4
```

### 추천 슬롯별 검색 전환 거래액 분석 (impression_id 기반)

```sql
-- ✅ 추천팀 슬롯별 전환 거래액 (flat 컬럼)
SELECT
    date(gift.order_paid_date) as dt,
    tiara.tiara_purchase_impression_id,
    COUNT(DISTINCT gift.order_account_id) as "구매자수",
    COUNT(DISTINCT gift.order_id) as "구매건수",
    SUM(gift.gmv_amt) as "거래액(GMV)"
FROM (
    SELECT
        custom_props_tiara_purchase_impression_id as tiara_purchase_impression_id,
        try_cast(url_extract_parameter(
            replace(common_url, ' ', ''), 'paymentId') as bigint) as payment_id
    FROM iceberg.log_iceberg.tiara_gift
    WHERE dt >= '2025-01-01'
      AND dt <= '2025-01-07'
      AND action_kind = 'Purchase'
      AND custom_props_tiara_purchase_impression_id IS NOT NULL
    GROUP BY 1, 2
) tiara
INNER JOIN kudu.dw.fact_gift gift
    ON tiara.payment_id = gift.order_payment_id
WHERE gift.order_paid_date >= cast('2025-01-01' as timestamp)
  AND gift.order_paid_date <= cast('2025-01-07' as timestamp)
GROUP BY 1, 2
ORDER BY 1, 2
```

### 특정 추천 슬롯(검색) 전환 분석

```sql
-- ✅ 검색 추천 슬롯 전환 거래액 (flat 컬럼)
SELECT
    date(gift.order_paid_date) as dt,
    COUNT(DISTINCT gift.order_account_id) as "구매자수",
    COUNT(DISTINCT gift.order_id) as "구매건수",
    SUM(gift.gmv_amt) as "거래액(GMV)"
FROM (
    SELECT
        try_cast(url_extract_parameter(
            replace(common_url, ' ', ''), 'paymentId') as bigint) as payment_id
    FROM iceberg.log_iceberg.tiara_gift
    WHERE dt >= '2025-01-01'
      AND dt <= '2025-01-07'
      AND action_kind = 'Purchase'
      AND custom_props_tiara_purchase_impression_id = 'air_gift_search_product_search'
    GROUP BY 1
) tiara
INNER JOIN kudu.dw.fact_gift gift
    ON tiara.payment_id = gift.order_payment_id
WHERE gift.order_paid_date >= cast('2025-01-01' as timestamp)
  AND gift.order_paid_date <= cast('2025-01-07' as timestamp)
GROUP BY 1
ORDER BY 1
```

---

## Entry 기반 거래액 분석 (Best Practice)

### 1. entry 컬럼 구분 (중요!)

| 컬럼 | 테이블 | 의미 | 분석 용도 |
|------|--------|------|----------|
| `gift_input_channel_nm` | fact_gift | **앱 진입점** (어디서 선물하기에 들어왔는지) | 유입 채널 분석 |
| `tiara_purchase_entry` | tiara_gift | **구매 경로** (선물하기 내 어떤 페이지에서 구매했는지) | 전환 경로 분석 |

**예시**: 사용자가 채팅방 +버튼(`kt_android_chatroom_plusbtn`)으로 진입 → 검색에서 구매 → tiara_entry는 `search_recent_keyword`

### 2. 표준 쿼리 패턴 (거래액 100% 일치 보장)

**핵심 원칙**:
1. `fact_gift` 기준 LEFT JOIN (tiara 로그 누락분 포함)
2. `payment_id`당 `MAX(entry)`로 중복 제거
3. 실행 전 거래액 총합 검증

**검증된 쿼리 템플릿**:
```sql
SELECT
    COALESCE(entry.tiara_purchase_entry4_cd, 'null') as entry_code,
    COALESCE(entry.tiara_purchase_entry1_nm, 'null') as depth1,
    COALESCE(entry.tiara_purchase_entry2_nm, 'null') as depth2,
    COALESCE(entry.tiara_purchase_entry3_nm, 'null') as depth3,
    COALESCE(entry.tiara_purchase_entry4_nm, 'null') as depth4,
    SUM(gift.gmv_amt) as gmv
FROM kudu.dw.fact_gift gift
LEFT JOIN (
    -- payment_id당 하나의 entry만 선택 (중복 방지)
    SELECT payment_id, MAX(tiara_purchase_entry) as tiara_purchase_entry
    FROM (
        SELECT
            try_cast(url_extract_parameter(
                replace(common_url, ' ', ''), 'paymentId') as bigint) as payment_id,
            COALESCE(custom_props_tiara_purchase_dkt, custom_props_tiara_purchase_entry) as tiara_purchase_entry
        FROM iceberg.log_iceberg.tiara_gift
        WHERE dt >= '2025-11-01'
          AND dt <= '2025-11-30'
          AND action_kind = 'Purchase'
        GROUP BY 1, 2
    )
    GROUP BY payment_id
) tiara ON gift.order_payment_id = tiara.payment_id
LEFT JOIN kudu.dw.dim_gift_tiara_purchase_entry entry
    ON tiara.tiara_purchase_entry = entry.tiara_purchase_entry4_cd
WHERE gift.order_status_cd > 200
  AND gift.order_paid_date >= timestamp '2025-11-01'
  AND gift.order_paid_date < timestamp '2025-12-01'
GROUP BY 1, 2, 3, 4, 5
ORDER BY gmv DESC
```

### 3. 거래액 검증 쿼리

조인 분석 후 반드시 총합 비교:
```sql
-- 1) fact_gift 단독 거래액
SELECT SUM(gmv_amt) FROM kudu.dw.fact_gift
WHERE order_status_cd > 200
  AND order_paid_date >= timestamp '2025-11-01'
  AND order_paid_date < timestamp '2025-12-01'

-- 2) entry 분석 결과 합계와 비교
-- 차이가 0이면 정상, 차이 발생 시 조인 조건 재검토
```

### 4. 주의사항

| 이슈 | 원인 | 해결책 |
|------|------|--------|
| 거래액 누락 | INNER JOIN 사용 | fact_gift 기준 LEFT JOIN |
| 거래액 중복 | payment_id당 여러 entry | MAX(entry)로 하나만 선택 |
| entry null 비율 높음 | tiara 로그 누락 or 매핑 안됨 | 정상 (약 15-20%) |
