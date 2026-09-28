# Jira Task 진행 워크플로우

CDETEAM-XXXX Jira 티켓 기반의 `kamek-batch` 개발 작업 시 아래 프로세스를 순서대로 따른다.

## Phase 1: 환경 준비

1. **브랜치 생성**: `CDETEAM-XXXX` 형태로 worktree 분리
   ```bash
   git worktree add ../kamek-batch-CDETEAM-XXXX -b CDETEAM-XXXX develop
   ```
2. **Jira 확인**: `/jira CDETEAM-XXXX` 로 티켓 상세 확인, 요구사항 파악

## Phase 2: Spec 작성

1. `/spec-generate CDETEAM-XXXX <제목>` 으로 스펙 문서 생성
2. Jira 요구사항과 스펙 정합성 확인
3. Task 분해: 스펙 내 체크리스트로 구현 단위 정의

## Phase 3: TDD 구현

1. Task 단위로 **테스트 먼저 작성** → 구현 → 테스트 통과 순서
2. 한 번에 하나의 Task만 구현
3. Task 완료마다 커밋: `[CDETEAM-XXXX] <변경 요약>`
4. 테스트 실패 상태에서는 절대 커밋하지 않음

## Phase 4: 리뷰 & 개선 (최소 3회)

1. `/code-review` 로 전체 변경사항 리뷰
2. 리뷰 지적사항 수정 → 재리뷰
3. **최소 3회 반복** — 개선사항이 더 나오지 않을 때까지 계속
4. 리뷰 완료 후 `/simplify` 로 코드 간소화

## Phase 5: 회귀 검증 (dev phase — 코드 변경이 기존 결과를 깨뜨리지 않는지 확인)

**목적**: 변경된 코드로 gift ranking 배치를 dev에서 실행하고, 현재 prod에 배포된 결과와 비교하여 의도하지 않은 변경이 없는지 검증한다.

### 5-1. prod 기준 데이터 수집 (비교 대상)

변경 전 상태의 prod 최신 데이터를 먼저 수집한다:

```bash
# prod ES에서 최신 batch_id의 건수 + Top N 조회
/es-verify gift_product prod
```

기록할 항목:

- prod 최신 batch_id, 문서 수
- Top 20 상품 (total_score 기준)
- 주요 점수 분포 (min/max/avg)

### 5-2. dev phase 배치 실행

변경된 코드로 **prod와 동일한 시각** 기준으로 dev 배치를 실행한다:

```bash
# prod 최신 batch_id의 시각과 동일하게 맞춤
/ranking-pipeline gift batch --from dev --batch-date-time <prod_batch_id에_해당하는_시각>
```

> 동일 시각으로 실행해야 입력 데이터가 같아져 결과 비교가 의미 있다.

### 5-3. dev vs prod 데이터 비교

**Step 1 (필수)**: 리팩토링 검증 스크립트로 Hive 점수 동일성 검증

```bash
# Hadoop 환경에서 실행 (before=prod, after=dev)
bash src/app/feature_store/script/ranking_v2/run_refactoring_validation.sh \
  --domain gift --dt <DT> --hr <HR> \
  --before-phase prod --after-phase dev
```

> 이 스크립트는 prod와 dev의 동일 dt/hr 파티션을 Spark로 로드하여
> 점수 컬럼별 차이를 부동소수점 허용 오차(기본 1e-10) 내에서 비교한다.
> **이 검증을 통과해야** 다음 Step으로 진행한다.

**Step 2**: ES 적재 결과 확인

```bash
/es-verify gift_product dev
```

**Step 3**: Hive/Iceberg 정합성 확인

```bash
/data-verify --batch gift_ranking_feature --phase dev
```

**비교 항목 및 허용 기준:**

| 비교 항목 | 허용 기준 | 위반 시 조치 |
|-----------|----------|-------------|
| 전체 문서 수 | dev/prod 차이 ±1% 이내 | Phase 3으로 복귀 |
| Top 20 순위 | 상위 20개 상품 ID 90% 이상 일치 | 변경 의도 확인, 스펙에 명시 |
| 점수 분포 (avg) | ±5% 이내 | 가중치/로직 변경 원인 분석 |
| 신규/삭제 필드 | 스펙에 명시된 변경만 허용 | 의도하지 않은 스키마 변경 롤백 |

### 5-4. 결과 판정

- **PASS**: 모든 비교 항목이 허용 기준 이내 → Phase 6 진행
- **EXPECTED_DIFF**: 스펙에 명시된 의도적 차이 → 차이 사유를 PR 본문에 기록 후 Phase 6 진행
- **FAIL**: 의도하지 않은 차이 → 원인 분석 후 Phase 3(TDD 구현)으로 복귀

## Phase 6: PR 생성

1. 검증 통과 후 `develop` 브랜치로 PR 생성
   ```bash
   gh pr create --base develop --title "[CDETEAM-XXXX] <제목>"
   ```
2. PR 본문에 포함:
   - 스펙 문서 링크 (`docs/specs/CDETEAM-XXXX.md`)
   - 리뷰 라운드 수 및 주요 개선사항
   - dev 검증 결과 요약
3. worktree 정리는 PR 머지 후

> PR 문서 강제 게이트는 폐지되었습니다 — `bin/run_pr_docs_enforcer.bash` 실행은 더 이상
> 필수가 아니며, 랭킹 문서 현행화는 리뷰어 재량의 권장 사항입니다.

## 체크리스트 (Phase 전환 전 확인)

- [ ] Phase 2→3: 스펙 문서 존재, Task 분해 완료
- [ ] Phase 3→4: 모든 테스트 통과, Task별 커밋 완료
- [ ] Phase 4→5: 리뷰 3회 이상, simplify 완료
- [ ] Phase 5→6: prod 기준 데이터 수집 완료, dev 배치 실행 완료, dev vs prod 비교 PASS 또는 EXPECTED_DIFF
- [ ] Phase 6: PR 생성, 스펙/검증 결과 첨부
