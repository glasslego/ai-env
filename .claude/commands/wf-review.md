# Phase 5: 스펙 정합성 리뷰

토픽 ID: $ARGUMENTS

## 개요

SPEC 파일과 구현 코드를 비교하여 정합성 리뷰를 수행한다.
AC별 충족 여부를 검증하고, 리뷰 노트를 생성한다.

## 실행 단계

### Step 1: 토픽 로드 및 파일 확인

토픽 YAML 경로: `config/topics/$ARGUMENTS.yaml`
이 파일을 Read 도구로 읽어서 토픽 정보를 확인한다.

Obsidian vault에서 SPEC 파일을 찾는다:
- `20_Specs/SPEC-$ARGUMENTS.md`

SPEC 파일이 없으면 에러를 출력하고 종료한다.

### Step 2: SPEC의 AC 추출

SPEC 파일을 Read 도구로 읽고, Acceptance Criteria 섹션의 모든 AC를 추출한다.
각 AC에 대해 검증할 코드/테스트 위치를 식별한다.

### Step 3: 코드 변경사항 수집 (agent-teams 병렬)

반드시 하나의 응답에서 모든 Task 호출을 동시에 수행하라.

**Task 1 (코드 분석):**
- subagent_type: "Explore"
- target_repo 디렉토리에서 구현 코드 탐색
- 각 AC에 해당하는 코드 위치 식별
- 함수/클래스 시그니처, 주요 로직 요약

**Task 2 (테스트 분석):**
- subagent_type: "Explore"
- 테스트 디렉토리에서 각 AC를 커버하는 테스트 식별
- 테스트 커버리지 현황 파악

**Task 3 (git diff 분석):**
- subagent_type: "Bash"
- target_repo에서 `git diff main...HEAD` 또는 최근 커밋 diff 수집
- 변경된 파일 목록과 주요 변경사항 요약

### Step 4: AC 매핑 검증

각 AC에 대해:
1. 코드에서 구현 확인 → 코드 위치 기록
2. 테스트에서 검증 확인 → 테스트 파일 기록
3. 충족/미충족 판정

### Step 5: 리뷰 노트 생성

REVIEW 템플릿(`config/templates/obsidian/REVIEW.md`)을 참고하여
리뷰 노트를 작성한다.

**Must Fix**: 스펙 위반, 버그, 보안 이슈
**Nice to Have**: 개선 제안, 리팩토링, 성능

**운영 관점 체크:**
- 에러 처리: 예외 경로 커버리지
- 로깅: 디버깅에 충분한 로그
- 엣지 케이스: 경계값, 빈 입력 등

Write 도구로 `40_Reviews/REV-$ARGUMENTS.md`에 저장한다.

### Step 6: Follow-up 태스크 + 워크플로우 상태 갱신

Must Fix 항목이 있으면:
- TASK 파일에 Follow-up 항목 추가
- 워크플로우 상태를 "review"로 유지

모든 AC가 충족되면:
- 워크플로우 상태를 "done"으로 업데이트

워크플로우 상태 갱신:
```bash
uv run ai-env pipeline workflow $ARGUMENTS
```

### Step 7: 결과 보고

```
📋 스펙 정합성 리뷰 완료!

  AC 충족: X/Y
  Must Fix: N건
  Nice to Have: M건

  리뷰 노트: 40_Reviews/REV-{topic_id}.md
```

워크플로우 상태 확인:
```bash
uv run ai-env pipeline workflow $ARGUMENTS
```
