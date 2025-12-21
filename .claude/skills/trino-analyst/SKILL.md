---
name: trino-analyst
description: |
  데이터 분석 쿼리 에이전트
  사용 시점: 유저가 데이터 조회/분석을 요청할 때 (거래액, UV, 전환율 등)
  기능: 테이블 탐색 → 쿼리 작성 → Trino 실행 → 결과 정리
---

# trino-analyst

데이터 분석 요청을 처리하는 쿼리 에이전트입니다.

## 워크플로우

### Step 0: 유사 분석 이력 확인 (권장)
1. `tmp/trino-analyst/` 디렉토리에서 유사한 분석 검색
2. 해당 summary.md의 쿼리 패턴 및 검증 로직 참조
3. 이전 분석에서 발견된 주의사항 확인

```bash
ls -la tmp/trino-analyst/
cat tmp/trino-analyst/request-{yyyymmdd-hhmm}/summary.md
```

### Step 1: 테이블 탐색
1. `references/tables/_catalog.yaml` 읽기
2. 유저 요청과 관련된 테이블 식별 (keywords 기반)
3. 해당 테이블의 상세 문서 (`.md`) 읽기
4. **문서에 없는 컬럼이 필요하면 DESCRIBE로 스키마 확인**
   ```sql
   DESCRIBE kudu.dw.fact_gift
   DESCRIBE iceberg.log_iceberg.tiara_gift
   ```

### Step 2: 쿼리 작성
1. 테이블 스키마와 예시 쿼리 참고하여 SQL 작성
2. **반드시 파티션 조건 포함** (date_id, dt 등)
3. 유저에게 쿼리 확인 요청

### Step 3: 샘플 쿼리로 검증 (중요!)
**전체 쿼리 실행 전, 반드시 샘플로 먼저 검증:**
```bash
uv run python .claude/skills/trino-analyst/scripts/run_query.py \
  --query "SELECT ... LIMIT 10" \
  --format markdown
```

- 컬럼명, 데이터 형식, 결과 구조 확인
- 예상대로 동작하는지 검증
- 문제 있으면 쿼리 수정

### Step 3-1: 거래액 검증 (조인 분석 시 필수!)
팩트 테이블과 로그 테이블을 조인하는 분석의 경우:

1. 팩트 테이블 단독 거래액 계산
2. 조인 결과 거래액 합계와 비교
3. 차이가 0.1% 이상이면:
   - INNER JOIN → LEFT JOIN 변경 검토
   - 1:N 조인으로 인한 중복 확인
   - GROUP BY 전 중복 제거 로직 추가

```sql
-- 검증 쿼리 예시
SELECT 'fact_gift 전체' as source, SUM(gmv_amt) as total_gmv
FROM kudu.dw.fact_gift WHERE ...

UNION ALL

SELECT '조인 결과' as source, SUM(gmv) as total_gmv
FROM (분석 쿼리)
```

### Step 4: 전체 쿼리 실행 (유저 동의 필요)
샘플 검증 후, **유저에게 전체 실행 동의를 받고** 실행:
```bash
uv run python .claude/skills/trino-analyst/scripts/run_query.py \
  --query "SELECT ..." \
  --format csv \
  --output tmp/trino-analyst/request-{yyyymmdd-hhmm}/result.csv
```

> ⚠️ 대용량 결과가 예상되면 LIMIT 옵션 사용 권장

### Step 5: 결과 저장 (기본 동작)
분석 완료 후 **반드시** 다음 구조로 결과를 저장:

```
tmp/trino-analyst/request-{yyyymmdd-hhmm}/
├── summary.md      # 요청 내용 + 결과 개요
└── result.csv      # 전체 쿼리 결과
```

**summary.md 형식:**
```markdown
# 데이터 분석 결과

## 요청 내용
{유저의 원본 요청 내용}

## 분석 기간
{분석 대상 기간}

## 실행 쿼리
```sql
{실행한 SQL 쿼리}
```

## 결과 개요
- 총 {N}개 행
- {주요 인사이트 요약}

## 주요 결과 (상위 10개)
{마크다운 테이블로 상위 결과}
```

**저장 명령어:**
```bash
# 1. 폴더 생성
mkdir -p tmp/trino-analyst/request-$(date +%Y%m%d-%H%M)

# 2. CSV 저장 (쿼리 실행 시 --output 옵션 사용)
uv run python .claude/skills/trino-analyst/scripts/run_query.py \
  --query "SELECT ..." \
  --format csv \
  --output tmp/trino-analyst/request-{yyyymmdd-hhmm}/result.csv

# 3. summary.md는 Write 도구로 직접 작성
```

## 주요 테이블

| 테이블 | 용도 |
|--------|------|
| `kudu.dw.fact_gift` | 선물하기 주문/거래액 |
| `kudu.dw.fact_talkstore` | 톡스토어 주문/거래액 |
| `iceberg.log_iceberg.tiara_gift` | 선물하기 UV/PV/전환 |
| `iceberg.log_iceberg.tiara_shoptab` | 쇼핑탭 트래픽/AB테스트 |
| `iceberg.log_iceberg.tiara_talkstore` | 톡스토어 트래픽/노출 |

## 주의사항

1. **파티션 필수**: 모든 쿼리에 날짜 파티션 조건 필수
2. **tiara 테이블**: flat 컬럼 우선 사용 (`user_account_id`, `action_type` 등)
3. **타입 변환**: flat 컬럼 사용 시 불필요 (user_account_id가 이미 bigint)
4. **결과 제한**: 대용량 결과는 LIMIT 사용
5. **구매/거래액/매출 분석**: tiara 로그만으로 불가, 반드시 fact_ 테이블과 조인 필요
   - tiara: UV, PV, 클릭 등 행동 데이터만 보유
   - fact_gift/fact_talkstore: 실제 주문/거래액 데이터 보유
   - 전환 분석 시 payment_id 또는 order_id 기준으로 조인

## 환경 설정

`.env` 파일에 다음 환경변수 필요:
```
TRINO_HOST=...
TRINO_PORT=...
TRINO_USER=...
TRINO_PASSWORD=...
```
