---
name: code-review
description: |
  프로젝트 코드베이스 전체 리뷰 + 스펙 정합성 검증. /simplify와 달리 지정 파일/디렉토리 전체를 리뷰한다.
  "리뷰해줘", "이 모듈 리뷰해줘", "src/ 리뷰", "spec review", "정합성 검증" 등에 반응.
---

# Code Review

코드 리뷰와 스펙 정합성 검증을 수행하는 통합 스킬.

## 모드 자동 판별

| 사용자 요청 | 모드 |
|------------|------|
| "리뷰" / "review" / "코드 리뷰" | Quick Review |
| "spec review" / "정합성" / "SPEC-NNN 리뷰" | Spec Conformance |
| "simplify" / "개선" / "리팩토링" | Simplify |

모호한 경우: SPEC 파일이 명시되었으면 Spec Conformance, 아니면 Quick Review.

---

## Quick Review 모드

변경된 코드를 빠르게 리뷰한다.

### Step 1: 변경사항 수집

```bash
git diff --stat
git diff
```

스테이지되지 않은 변경 + 스테이지된 변경 모두 포함.

### Step 2: 코드 리뷰

버그/보안/성능/가독성/테스트 관점으로 리뷰.

### Step 3: 결과 보고

Good / Issues (`[Must Fix]`, `[Nice to Have]`) / Suggestions 구분하여 `파일:라인` 형식으로 보고.

---

## Spec Conformance 모드

SPEC 파일의 AC(Acceptance Criteria) ↔ 구현 코드를 매핑 검증한다.

### Step 1: SPEC 파일 로드

- 프로젝트 컨텍스트에서 specs/ 디렉토리 확인
- 지정된 SPEC 파일을 Read
- Acceptance Criteria 섹션의 모든 AC 추출

### Step 2: 코드/테스트 매핑 (병렬)

Agent tool을 사용하여 병렬 분석:

**Agent 1 (코드 분석)**:
- 각 AC에 해당하는 코드 위치 식별
- 함수/클래스 시그니처, 주요 로직 요약

**Agent 2 (테스트 분석)**:
- 각 AC를 커버하는 테스트 식별
- 테스트 커버리지 현황

### Step 3: AC 매핑 검증

각 AC에 대해:
1. 코드 구현 확인 → 위치 기록
2. 테스트 검증 확인 → 테스트 파일 기록
3. 충족/미충족 판정

### Step 4: 리뷰 보고

```
📋 Spec Conformance Review — SPEC-NNN

| AC   | Description        | Code        | Test        | Status |
|------|--------------------|-------------|-------------|--------|
| AC-1 | 로그인 기능        | auth.py:45  | test_auth:12| ✅     |
| AC-2 | 권한 검증          | -           | -           | ❌     |

충족: X/Y (N%)

Must Fix:
  - AC-2: 구현 누락 — 권한 검증 코드 없음

Nice to Have:
  - 에러 로깅 추가 권장
```

### Step 5: 상태 환류

- Must Fix 있으면 → spec의 관련 task를 `review_required`로 변경
- _project-status.yaml에 리뷰 결과 기록:

```yaml
reviews:
  SPEC-NNN:
    date: "2026-03-08"
    must_fix: 1
    nice_to_have: 2
    resolved: false
```

- 모든 AC 충족 시 → spec status를 `done`으로 변경 가능 안내

---

## Simplify 모드

코드 품질 개선 + 리팩토링을 수행한다.

### Step 1: 대상 코드 분석

변경된 파일 또는 사용자가 지정한 파일을 Read.

### Step 2: 개선점 식별

`references/review-checklist.md`의 체크리스트 기준으로:

1. **중복 코드**: 동일/유사 로직이 2곳 이상
2. **복잡도**: 함수가 20줄 초과, 들여쓰기 3단 이상
3. **네이밍**: 의미 불명확한 변수/함수명
4. **패턴 위반**: 프로젝트 아키텍처 패턴 미준수
5. **불필요한 코드**: 사용하지 않는 import, 변수, 함수

### Step 3: 개선 적용

- 각 개선점을 Edit으로 적용
- 적용 후 테스트 실행하여 기능 보존 확인
- 테스트 실패 시 변경 롤백

### Step 4: 보고

적용된 개선 목록 + 테스트 결과 보고.

---

## 절대 금지

- Must Fix 항목을 무시하고 "완료"로 표시하지 마라
- Simplify에서 기능 변경을 하지 마라 (리팩토링만)
- 글로벌 CLAUDE.md "절대 금지 사항 > 테스트 코드 관련" 항목도 적용
