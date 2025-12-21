# tiara_talkstore 테이블 가이드

## 개요

| 항목 | 내용 |
|------|------|
| 테이블 경로 | `iceberg.log_iceberg.tiara_talkstore` |
| 레거시 경로 | `hive.log.tiara_talkstore` (이전 방식, 동일 데이터) |
| 데이터 설명 | 톡스토어(톡딜) 사용자 이벤트 로그 테이블 (행동 데이터) |
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
FROM iceberg.log_iceberg.tiara_talkstore
WHERE dt = '2025-01-01'

-- ⚠️ 레거시: element_at() 사용 (hive 테이블 호환용)
SELECT element_at(user, 'account_id') as account_id  -- string 타입, 변환 필요
FROM hive.log.tiara_talkstore
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

### 커스텀 속성
| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| custom_props_area | varchar | 영역 정보 |
| custom_props_query | varchar | 검색 쿼리 |
| custom_props_init_area | varchar | 최초 유입 영역 |

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

### Map 컬럼 (레거시 호환)
추천, 검색, 구매 지면 등 일부 필드는 map 컬럼 사용:

| Map 컬럼 | 주요 키 | 설명 |
|----------|---------|------|
| custom_props | impression_id | 추천 슬롯 ID |
| custom_props | tiara_purchase_entry | 구매 지면 코드 |
| search | search_term | 검색 키워드 |

---

## 배열 필드 (톡스토어 특화)

### viewimp_contents (노출 콘텐츠 배열) - 중요!

톡딜 상품 노출 분석에 핵심적으로 사용됩니다.

| 필드 경로 | 타입 | 설명 |
|-----------|------|------|
| viewimp_contents.element.id | string | 톡딜 상품 코드 |
| viewimp_contents.element.name | string | 상품명 |
| viewimp_contents.element.category | string | 카테고리 |
| viewimp_contents.element.imp_area | string | 노출 영역 |
| viewimp_contents.element.imp_ordnum | string | 노출 순서 |
| viewimp_contents.element.imp_type | string | 노출 타입 |

---

## 사용팁

### 1. 기본 필터 조건 (파티션 필수!)

```sql
-- 날짜 파티션 활용
WHERE dt >= '2025-01-01'
  AND dt <= '2025-01-31'

-- 특정 시간대만
WHERE dt = '2025-01-01'
  AND hr BETWEEN '09' AND '18'
```

### 2. 액션 타입 필터

```sql
-- 페이지뷰만
WHERE action_type = 'Pageview'

-- 클릭만
WHERE action_type = 'Click'

-- 이벤트만 (노출 등)
WHERE action_type = 'Event'
```

### 3. 노출 데이터 처리 (UNNEST 필수!)

톡딜 상품 노출 분석 시 배열을 행으로 풀어야 합니다:

```sql
-- viewimp_contents 배열을 행으로 변환
SELECT
    dt,
    user_account_id,
    element_at(talkstore_item, 'id') as talkstore_cd,
    element_at(talkstore_item, 'name') as product_name,
    element_at(talkstore_item, 'imp_ordnum') as imp_order
FROM iceberg.log_iceberg.tiara_talkstore
CROSS JOIN UNNEST(viewimp_contents) AS t(talkstore_item)
WHERE dt = '2025-01-01'
  AND action_type = 'Event'
  AND viewimp_contents IS NOT NULL
```

### 4. 유입 경로 분석

```sql
-- 일별 최초 유입 기준 UV
SELECT
    dt,
    element_at(common, 'ref_url') as referrer,
    COUNT(DISTINCT user_account_id) as uv
FROM iceberg.log_iceberg.tiara_talkstore
WHERE dt >= '2025-01-01'
  AND action_type = 'Pageview'
GROUP BY dt, element_at(common, 'ref_url')
```

### 5. 검색어 분석

```sql
-- ✅ 검색 로그 조회 (flat 컬럼 + map 컬럼)
SELECT
    element_at(search, 'search_term') as keyword,
    COUNT(*) as search_cnt,
    COUNT(DISTINCT user_account_id) as searcher_cnt
FROM iceberg.log_iceberg.tiara_talkstore
WHERE dt = '2025-01-01'
  AND action_kind = 'Search'
  AND element_at(search, 'search_term') IS NOT NULL
GROUP BY element_at(search, 'search_term')
ORDER BY search_cnt DESC
```

### 6. 팩트 테이블 JOIN (타입 변환 불필요!)

```sql
-- ✅ flat 컬럼 사용 시 타입 변환 불필요
SELECT tt.*, ft.gmv_amt
FROM iceberg.log_iceberg.tiara_talkstore tt
JOIN kudu.dw.fact_talkstore ft
  ON tt.user_account_id = ft.order_account_id  -- bigint = bigint
WHERE tt.dt = '2025-01-01'
  AND ft.order_paid_date >= timestamp '2025-01-01'
```

### 7. impression_id (추천 슬롯 ID) 추적

추천팀의 추천 결과 효과를 추적하는 데 사용됩니다.

> **참고**: tiara_talkstore는 tiara_gift와 다르게 **Purchase 로그에서도 `impression_id`**를 사용합니다.
> (tiara_gift는 구매 로그에서 `tiara_purchase_impression_id` 사용)

```sql
-- 일반 로그에서 추천 결과 추적 (페이지뷰, 클릭 등)
SELECT
    element_at(custom_props, 'impression_id') as impression_id,
    COUNT(*) as event_cnt
FROM iceberg.log_iceberg.tiara_talkstore
WHERE dt = '2025-01-01'
  AND element_at(custom_props, 'impression_id') IS NOT NULL
GROUP BY element_at(custom_props, 'impression_id')

-- 구매 로그에서 추천 슬롯별 전환 분석 (tiara_talkstore는 impression_id 사용)
SELECT
    element_at(custom_props, 'impression_id') as impression_id,
    COUNT(DISTINCT user_account_id) as buyer_cnt
FROM iceberg.log_iceberg.tiara_talkstore
WHERE dt = '2025-01-01'
  AND action_type = 'Purchase'
  AND element_at(custom_props, 'impression_id') IS NOT NULL
GROUP BY element_at(custom_props, 'impression_id')
```

---

## JOIN 패턴

### 1. fact_talkstore와 연결 (방문 → 구매 전환)

```sql
-- 방문자 중 구매자 확인
SELECT
    tt.dt,
    COUNT(DISTINCT tt.user_account_id) as visitor_cnt,
    COUNT(DISTINCT ft.order_account_id) as buyer_cnt
FROM iceberg.log_iceberg.tiara_talkstore tt
LEFT JOIN kudu.dw.fact_talkstore ft
  ON tt.user_account_id = ft.order_account_id
  AND ft.order_paid_date BETWEEN cast(tt.dt as timestamp) AND cast(tt.dt as timestamp) + interval '7' day
WHERE tt.dt >= '2025-01-01'
  AND tt.dt <= '2025-01-07'
  AND tt.action_type = 'Pageview'
GROUP BY tt.dt
```

### 2. 사용자 활동 유형 JOIN

```sql
-- 사용자 활동 유형별 분석
SELECT
    tt.*,
    action_cnt.purchase_cnt,
    action_cnt.visit_cnt
FROM iceberg.log_iceberg.tiara_talkstore tt
LEFT JOIN kudu.dw.fact_talkstore_user_action_type_cnt action_cnt
  ON tt.user_account_id = action_cnt.user_id
WHERE tt.dt = '2025-01-01'
```

---

## 주의사항

1. **파티션 필수**: `dt`와 `hr` 파티션 조건 필수 (데이터량이 매우 큼)
2. **Flat 컬럼 우선 사용**: `user_account_id`, `action_type`, `action_kind` 등 flat 컬럼 사용 권장
3. **타입 변환 불필요**: flat 컬럼 사용 시 `user_account_id`가 이미 bigint
4. **UNNEST 필수**: `viewimp_contents` 배열 처리 시 `CROSS JOIN UNNEST()` 사용
5. **검색 분석**: `action_kind = 'Search'` 조건으로 검색 로그 필터링

---

## 예시 쿼리

### 일별 방문자 수 (UV)

```sql
SELECT
    dt,
    COUNT(DISTINCT user_account_id) as uv
FROM iceberg.log_iceberg.tiara_talkstore
WHERE dt >= '2025-01-01'
  AND dt <= '2025-01-31'
  AND action_type = 'Pageview'
GROUP BY dt
ORDER BY dt
```

### 톡딜 상품 노출 분석

```sql
-- 상품별 노출 횟수
SELECT
    element_at(talkstore_item, 'id') as talkstore_cd,
    COUNT(*) as imp_cnt,
    COUNT(DISTINCT user_account_id) as imp_user_cnt
FROM iceberg.log_iceberg.tiara_talkstore
CROSS JOIN UNNEST(viewimp_contents) AS t(talkstore_item)
WHERE dt = '2025-01-01'
  AND action_type = 'Event'
  AND viewimp_contents IS NOT NULL
GROUP BY element_at(talkstore_item, 'id')
ORDER BY imp_cnt DESC
LIMIT 100
```

### 유입 유저 일별 최초 유입 기준 UV

```sql
-- 일별 유입 유저 (첫 방문 기준)
WITH first_visit AS (
    SELECT
        user_account_id,
        MIN(dt) as first_date
    FROM iceberg.log_iceberg.tiara_talkstore
    WHERE dt >= '2025-01-01'
      AND dt <= '2025-01-31'
      AND action_type = 'Pageview'
    GROUP BY user_account_id
)
SELECT
    first_date as dt,
    COUNT(DISTINCT user_account_id) as new_visitor_cnt
FROM first_visit
GROUP BY first_date
ORDER BY first_date
```

### 톡스토어 검색 지표

```sql
-- ✅ 톡스토어 검색어 분석 (flat 컬럼)
SELECT
    element_at(search, 'search_term') as keyword,
    COUNT(*) as search_cnt,
    COUNT(DISTINCT user_account_id) as searcher_cnt
FROM iceberg.log_iceberg.tiara_talkstore
WHERE dt = '2025-01-01'
  AND action_kind = 'Search'
  AND element_at(search, 'search_term') IS NOT NULL
  AND element_at(search, 'search_term') <> ''
GROUP BY element_at(search, 'search_term')
ORDER BY search_cnt DESC
LIMIT 100
```

### 톡딜 이탈 유저 분석

```sql
-- 최근 30일간 방문하지 않은 과거 구매자
WITH recent_visitors AS (
    SELECT DISTINCT user_account_id
    FROM iceberg.log_iceberg.tiara_talkstore
    WHERE dt >= date_format(current_date - interval '30' day, '%Y-%m-%d')
      AND action_type = 'Pageview'
),
past_buyers AS (
    SELECT DISTINCT order_account_id as account_id
    FROM kudu.dw.fact_talkstore
    WHERE order_paid_date >= current_date - interval '365' day
      AND order_paid_date < current_date - interval '30' day
)
SELECT pb.account_id
FROM past_buyers pb
LEFT JOIN recent_visitors rv ON pb.account_id = rv.user_account_id
WHERE rv.user_account_id IS NULL
```

### AB 테스트 분석

```sql
-- bucket 정보를 활용한 AB 테스트 분석
SELECT
    element_at(bucket, 'experiment_key') as experiment_key,
    element_at(bucket, 'variation_key') as variation,
    COUNT(DISTINCT user_account_id) as user_cnt,
    COUNT(*) as event_cnt
FROM iceberg.log_iceberg.tiara_talkstore
WHERE dt >= '2025-01-01'
  AND dt <= '2025-01-07'
  AND element_at(bucket, 'experiment_key') IS NOT NULL
GROUP BY element_at(bucket, 'experiment_key'), element_at(bucket, 'variation_key')
ORDER BY experiment_key, variation
```
