# 전체 워크플로우 자동 실행

토픽 ID: $ARGUMENTS

## 개요

리서치 자료가 이미 있다는 전제 하에, 현재 Phase부터 끝(Review)까지
Spec → Code → Review 파이프라인을 자동으로 순차 실행한다.

`claude --fallback` 모드에서 사용 권장 (토큰 소진 시 자동 에이전트 전환).

## 실행 단계

### Step 1: 토픽 로드 + 현재 Phase 확인

```bash
uv run ai-env pipeline workflow $ARGUMENTS
```

토픽 YAML 경로: `config/topics/$ARGUMENTS.yaml`
이 파일을 Read 도구로 읽어서 토픽 정보를 확인한다.

현재 Phase를 확인하고 아래 Phase 맵에 따라 시작 지점을 결정:

| Phase | 의미 | 시작 Step |
|-------|------|-----------|
| intake | 초기화만 완료 | Step 2 (리서치 필요 → 안내 후 중단) |
| research | 리서치 진행중/완료 | Step 3 |
| spec | Spec 완료 | Step 4 |
| implementing | 구현 진행중 | Step 4 (이어서) |
| review | 리뷰 완료 | 종료 안내 |
| done | 전체 완료 | 종료 안내 |

**Phase가 intake이면:**
리서치 자료가 없다. 사용자에게 안내하고 중단:
```
⚠ 리서치 자료가 없습니다.
먼저 리서치를 수행하세요:
  - 수동: PDF/MD 파일을 Obsidian vault의 10_Research/Clippings/ 또는 07_참고/ 에 배치
  - 자동: claude "/wf-research {topic_id}"
```

**Phase가 review 또는 done이면:**
```
✅ 이미 완료된 워크플로우입니다.
  리뷰 결과: 40_Reviews/REV-{topic_id}.md
```

### Step 2: 리서치 충분성 검증

리서치 파일이 최소 1개 이상 있는지 확인한다.

```bash
uv run ai-env pipeline status $ARGUMENTS
```

리서치 파일이 0건이면 Step 1의 intake 안내와 동일하게 중단.
1건 이상이면 다음 Step으로 진행.

### Step 3: Phase 3 — Brief + Spec 생성

**이 단계의 상세 절차는 `.claude/commands/wf-spec.md`에 정의되어 있다.**
해당 파일을 Read 도구로 읽고, 그 안의 모든 단계를 빠짐없이 실행하라.
(Brief 생성 → 교차 분석 → Spec 작성 → ADR 생성 순서)

#### Gate Check (Spec 완료 확인)

Spec 생성 후 다음을 확인:
1. Plan/Spec 파일이 존재하는가?
2. 파일 내용이 500자를 초과하는가?
3. "한 문단 요약" (빈 템플릿 플레이스홀더)을 포함하지 않는가?

**Gate 실패 시**: 사용자에게 Spec이 불완전함을 알리고 중단한다.

```bash
uv run ai-env pipeline workflow $ARGUMENTS
```

Phase가 "spec" 또는 "implementing"으로 변경되었는지 확인.

### Step 4: Phase 4 — TDD 코드 생성

**이 단계의 상세 절차는 `.claude/commands/wf-code.md`에 정의되어 있다.**
해당 파일을 Read 도구로 읽고, 그 안의 모든 단계를 빠짐없이 실행하라.

토픽 YAML에 `code` 섹션이 없으면 이 Step을 건너뛰고 사용자에게 안내:
```
ℹ 토픽에 code 섹션이 없어 구현 단계를 건너뜁니다.
  필요하면 config/topics/{topic_id}.yaml에 code 섹션을 추가하세요.
```

#### Gate Check (코드 완료 확인)

코드 생성 후 통합 테스트:
```bash
cd {code.target_repo} && uv run pytest -v --tb=short
```

**Gate 실패 시 (테스트 실패)**:
- 실패한 테스트를 분석하고 구현 코드만 수정 (테스트 코드 수정 금지)
- 최대 3회 재시도
- 3회 후에도 실패하면 중단하고 실패 현황 보고

```bash
uv run ai-env pipeline workflow $ARGUMENTS
```

### Step 5: Phase 5 — 스펙 정합성 리뷰

**이 단계의 상세 절차는 `.claude/commands/wf-review.md`에 정의되어 있다.**
해당 파일을 Read 도구로 읽고, 그 안의 모든 단계를 빠짐없이 실행하라.

### Step 6: 최종 보고

```bash
uv run ai-env pipeline workflow $ARGUMENTS
```

사용자에게 전체 파이프라인 결과를 보고:

```
🏁 워크플로우 완료!

📊 실행 결과:
  Phase 3 (Spec):   ✅ {spec 파일 경로}
  Phase 4 (Code):   ✅ {target_repo} — 테스트 {pass}/{total} 통과
  Phase 5 (Review): ✅/⚠ {리뷰 파일 경로}
    - Must Fix: {N}건
    - Nice to Have: {N}건

{Must Fix가 있으면}
⚠ Must Fix 항목이 있습니다. 리뷰 파일을 확인하고 수정 후
  다시 실행하세요: claude "/wf-review {topic_id}"

{Must Fix가 없으면}
✅ 모든 AC 충족! 워크플로우가 완료되었습니다.
```

## 오류 격리 원칙

- 각 Phase는 **독립적으로 재실행 가능**해야 한다
- Phase 실패 시 해당 Phase만 다시 실행한다 (이전 Phase 결과는 보존):
  - Spec 실패: `claude "/wf-spec {topic_id}"`
  - Code 실패: `claude "/wf-code {topic_id}"` (체크포인트에서 재개)
  - Review 실패: `claude "/wf-review {topic_id}"`
- Phase 간 전환 시 반드시 `ai-env pipeline workflow`로 상태를 갱신하고 확인한다
- 이전 Phase의 산출물이 손상된 경우에만 이전 Phase를 재실행한다

## Phase 실행 체크리스트

각 Phase 실행 전후로 확인:

- [ ] Phase 시작 전: `ai-env pipeline workflow {topic_id}` → 현재 Phase 확인
- [ ] Phase 실행: 해당 wf-* 커맨드의 모든 Step 수행
- [ ] Phase 완료 후: `ai-env pipeline workflow {topic_id}` → Phase 진행 확인
- [ ] Gate Check 통과 확인 후 다음 Phase로 진행

## 절대 금지

- 테스트를 통과시키기 위해 테스트 코드를 수정/삭제하지 마라
- 각 Phase의 절차를 임의로 생략하지 마라 — wf-spec/wf-code/wf-review 파일의 모든 단계를 따르라
- Gate Check 실패 시 강제로 다음 Phase로 넘어가지 마라
