# tiara_shoptab 테이블 가이드

## 개요

| 항목 | 내용 |
|------|------|
| 테이블 경로 | `iceberg.log_iceberg.tiara_shoptab` |
| 레거시 경로 | `hive.log.tiara_shoptab` (이전 방식, 동일 데이터) |
| 데이터 설명 | 쇼핑탭 사용자 이벤트 로그 테이블 (행동 데이터) |
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
FROM iceberg.log_iceberg.tiara_shoptab
WHERE dt = '2025-01-01'

-- ⚠️ 레거시: element_at() 사용 (hive 테이블 호환용)
SELECT element_at(user, 'account_id') as account_id  -- string 타입, 변환 필요
FROM hive.log.tiara_shoptab
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
| action_type | varchar | 액션 타입 (Pageview, Click, Event) |
| action_name | varchar | 액션명 |
| action_kind | varchar | 액션 종류 (ClickContent, Search 등) |

### 공통 정보
| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| common_page | varchar | 페이지명 (search_entry, search_result 등) |
| common_section | varchar | 섹션명 (shopping 등) |
| common_service | varchar | 서비스명 |
| common_url | varchar | URL |
| common_access_timestamp | bigint | 접근 타임스탬프 |

### 클릭 정보 (쇼핑탭 특화)
| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| click_layer1 | varchar | 클릭 영역 1단계 (ho_talkdeal_box_2, ho_deallist 등) |
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
A/B 테스트, 검색, 스크롤 등 일부 필드는 map 컬럼 사용:

| Map 컬럼 | 주요 키 | 설명 |
|----------|---------|------|
| custom_props | custom_default_policy_id | A/B 테스트 정책 ID |
| custom_props | impression_id | 추천 슬롯 ID |
| search | search_term | 검색 키워드 |
| usage | scroll_height | 스크롤 높이 |

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

-- 클릭/이벤트만
WHERE action_type = 'Event'

-- 특정 액션 종류
WHERE action_kind = 'ClickContent'  -- 상품/콘텐츠 클릭
WHERE action_kind = 'Search'        -- 검색
```

### 3. 검색 분석

```sql
-- ✅ 검색 로그 조회 (flat 컬럼 + map 컬럼)
SELECT
    element_at(search, 'search_term') as keyword,
    COUNT(*) as search_cnt,
    COUNT(DISTINCT user_account_id) as searcher_cnt
FROM iceberg.log_iceberg.tiara_shoptab
WHERE dt = '2025-01-01'
  AND action_kind = 'Search'
  AND element_at(search, 'search_term') IS NOT NULL
GROUP BY element_at(search, 'search_term')
ORDER BY search_cnt DESC
```

### 4. A/B 테스트 분석 (중요!)

쇼핑탭에서 자주 사용되는 A/B 테스트 분석 패턴:

```sql
-- A/B 테스트 정책별 UV 분석
SELECT
    element_at(custom_props, 'custom_default_policy_id') as policy_id,
    COUNT(DISTINCT user_account_id) as uv,
    SUM(CASE WHEN action_type = 'Pageview' THEN 1 ELSE 0 END) as pv,
    COUNT(DISTINCT CASE WHEN action_kind = 'ClickContent'
                        THEN user_account_id END) as click_uv
FROM iceberg.log_iceberg.tiara_shoptab
WHERE dt >= '2025-04-14'
  AND dt <= '2025-05-04'
  AND element_at(custom_props, 'custom_default_policy_id') IN ('116', '117')
GROUP BY element_at(custom_props, 'custom_default_policy_id')
```

### 5. 클릭 영역별 분석 (click_layer1)

```sql
-- 영역별 클릭 분석
SELECT
    click_layer1 as click_area,
    COUNT(*) as click_cnt,
    COUNT(DISTINCT user_account_id) as click_uv
FROM iceberg.log_iceberg.tiara_shoptab
WHERE dt = '2025-01-01'
  AND action_type = 'Event'
  AND click_layer1 IS NOT NULL
GROUP BY click_layer1
ORDER BY click_cnt DESC

-- 주요 영역 코드:
-- ho_talkdeal_box_2 : 톡딜 박스
-- ho_deallist : 할인 리스트
-- ho_live_product : 라이브 상품
```

### 6. 스크롤 깊이 분석

```sql
-- 사용자별 평균 스크롤 깊이
SELECT
    element_at(custom_props, 'custom_default_policy_id') as policy_id,
    COUNT(DISTINCT user_account_id) as uv,
    SUM(try_cast(COALESCE(element_at(usage, 'scroll_height'), '0') as bigint)) as total_scroll,
    AVG(try_cast(COALESCE(element_at(usage, 'scroll_height'), '0') as double)) as avg_scroll
FROM iceberg.log_iceberg.tiara_shoptab
WHERE dt = '2025-01-01'
GROUP BY element_at(custom_props, 'custom_default_policy_id')
```

### 7. 팩트 테이블 JOIN (타입 변환 불필요!)

```sql
-- ✅ flat 컬럼 사용 시 타입 변환 불필요
SELECT ts.*, ft.gmv_amt
FROM iceberg.log_iceberg.tiara_shoptab ts
JOIN kudu.dw.fact_talkstore ft
  ON ts.user_account_id = ft.order_account_id  -- bigint = bigint
WHERE ts.dt = '2025-01-01'
  AND ft.order_paid_date >= timestamp '2025-01-01'
```

---

## JOIN 패턴

### 1. fact_talkstore와 연결 (방문 → 구매 전환)

```sql
-- 쇼핑탭 방문자 중 톡딜 구매자 확인
WITH shoptab_visitors AS (
    SELECT DISTINCT user_account_id
    FROM iceberg.log_iceberg.tiara_shoptab
    WHERE dt >= '2025-01-01'
      AND dt <= '2025-01-07'
      AND action_type = 'Pageview'
)
SELECT
    COUNT(DISTINCT sv.user_account_id) as visitor_cnt,
    COUNT(DISTINCT ft.order_account_id) as buyer_cnt
FROM shoptab_visitors sv
LEFT JOIN kudu.dw.fact_talkstore ft
  ON sv.user_account_id = ft.order_account_id
  AND ft.order_paid_date >= timestamp '2025-01-01'
  AND ft.order_paid_date < timestamp '2025-01-08'
```

### 2. A/B 테스트 모수와 연결

```sql
-- A/B 테스트 그룹별 구매 전환 분석
WITH ab_users AS (
    SELECT
        account_id,
        group_id
    FROM hive.dw_tmp.tmp_ted_shoptab_ab_test_group_2025
    WHERE date_id = '2025-04'
)
SELECT
    ab.group_id,
    COUNT(DISTINCT ab.account_id) as user_cnt,
    COUNT(DISTINCT ft.order_account_id) as buyer_cnt
FROM ab_users ab
LEFT JOIN kudu.dw.fact_talkstore ft
  ON ab.account_id = ft.order_account_id
  AND ft.order_paid_date >= timestamp '2025-04-14'
  AND ft.order_paid_date < timestamp '2025-05-05'
GROUP BY ab.group_id
```

---

## 주의사항

1. **파티션 필수**: `dt` 파티션 조건 필수 (데이터량이 매우 큼)
2. **Flat 컬럼 우선 사용**: `user_account_id`, `action_type`, `action_kind` 등 flat 컬럼 사용 권장
3. **타입 변환 불필요**: flat 컬럼 사용 시 `user_account_id`가 이미 bigint
4. **검색 분석**: `action_kind = 'Search'` 조건으로 검색 로그 필터링
5. **A/B 테스트**: `custom_default_policy_id`는 map 컬럼에서 element_at() 사용

---

## 예시 쿼리

### 일별 방문자 수 (UV/PV)

```sql
SELECT
    dt as date_id,
    COUNT(DISTINCT user_account_id) as uv,
    SUM(CASE WHEN action_type = 'Pageview' THEN 1 ELSE 0 END) as pv
FROM iceberg.log_iceberg.tiara_shoptab
WHERE dt >= '2025-01-01'
  AND dt <= '2025-01-31'
GROUP BY dt
ORDER BY dt
```

### 검색어 순위 분석

```sql
-- ✅ 검색어별 쿼리 카운트 TOP 100 (flat 컬럼)
SELECT
    element_at(search, 'search_term') as search_keyword,
    COUNT(*) as search_query_count
FROM iceberg.log_iceberg.tiara_shoptab
WHERE dt >= '2025-01-01'
  AND dt <= '2025-01-31'
  AND action_kind = 'Search'
  AND common_page IN ('search_entry', 'search_result')
  AND element_at(search, 'search_term') IS NOT NULL
GROUP BY element_at(search, 'search_term')
ORDER BY search_query_count DESC
LIMIT 100
```

### 쇼핑탭 vs 다른 서비스 검색 사용자 교차 분석

```sql
-- 쇼핑탭 검색 사용자 vs 선물하기 검색 사용자
WITH users AS (
    SELECT
        user_account_id as account_id,
        SUM(CASE WHEN source = 'shoptab' THEN 1 ELSE 0 END) as shoptab_cnt,
        SUM(CASE WHEN source = 'gift' THEN 1 ELSE 0 END) as gift_cnt
    FROM (
        -- 쇼핑탭 검색 사용자
        SELECT user_account_id, 'shoptab' as source
        FROM iceberg.log_iceberg.tiara_shoptab
        WHERE dt >= '2025-08-01' AND dt < '2025-09-01'
          AND common_page LIKE '%search%'

        UNION ALL

        -- 선물하기 검색 사용자
        SELECT user_account_id, 'gift' as source
        FROM iceberg.log_iceberg.tiara_gift
        WHERE dt >= '2025-08-01' AND dt < '2025-09-01'
          AND common_section = 'Search_v2'
    ) t
    GROUP BY user_account_id
)
SELECT
    COUNT(DISTINCT CASE WHEN shoptab_cnt > 0 AND gift_cnt > 0 THEN account_id END) as both_users,
    COUNT(DISTINCT CASE WHEN shoptab_cnt > 0 AND gift_cnt = 0 THEN account_id END) as shoptab_only,
    COUNT(DISTINCT CASE WHEN shoptab_cnt = 0 AND gift_cnt > 0 THEN account_id END) as gift_only
FROM users
```

### A/B 테스트 전체 지표 분석

```sql
SELECT
    element_at(custom_props, 'custom_default_policy_id') as policy_id,
    COUNT(DISTINCT user_account_id) as uv,
    SUM(CASE WHEN action_type = 'Pageview' THEN 1 ELSE 0 END) as pv,
    COUNT(DISTINCT CASE WHEN action_type = 'Event' THEN user_account_id END) as click_uv,
    SUM(CASE WHEN action_type = 'Event' THEN 1 ELSE 0 END) as clicks,
    COUNT(DISTINCT CASE WHEN action_kind = 'ClickContent' THEN user_account_id END) as content_click_uv
FROM iceberg.log_iceberg.tiara_shoptab
WHERE dt >= '2025-04-14'
  AND dt <= '2025-05-04'
  AND element_at(custom_props, 'custom_default_policy_id') IN ('116', '117')
GROUP BY element_at(custom_props, 'custom_default_policy_id')
ORDER BY policy_id
```
