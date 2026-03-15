# 워크플로우: 리서치 → Spec → Code → Review 파이프라인
---
description: 6-Phase 워크플로우 통합 커맨드. 서브커맨드로 개별 Phase 또는 전체 실행.
---

## 사용법

```
/workflow <subcommand> <topic_id>
```

| 서브커맨드 | Phase | 설명 |
|-----------|-------|------|
| `init` | 0 | Obsidian 워크스페이스 스캐폴딩 |
| `research` | 2 | 3-Track 리서치 (A: 자동검색, B: Gemini, C: GPT) |
| `spec` | 3 | Brief 압축 → 교차 분석 → Plan/Spec + ADR |
| `code` | 4 | TDD 코드 생성 (체크포인트 재개 지원) |
| `review` | 5 | 스펙 정합성 리뷰 |
| `run` | 3→5 | 현재 Phase부터 끝까지 순차 실행 (1회) |
| `iterate` | 2→5 반복 | Review → 개선점 도출 → Research → Spec → Code → Review 반복 |
| `status` | — | 현재 Phase 상태 확인 |

예시:
- `/workflow run bitcoin` — 전체 파이프라인 1회 실행
- `/workflow iterate bitcoin` — 반복 개선 루프 (최대 3회)
- `/workflow iterate bitcoin 5` — 반복 개선 루프 (최대 5회)
- `/workflow spec bitcoin` — Spec 생성만
- `/workflow status bitcoin` — 상태 확인

## 인자 파싱

`$ARGUMENTS`를 파싱한다:
- 첫 번째 단어 = 서브커맨드 (init, research, spec, code, review, run, iterate, status)
- 두 번째 단어 = 토픽 ID
- 세 번째 단어 (iterate 전용) = 최대 반복 횟수 (기본값: 3)

서브커맨드 없이 토픽 ID만 주어지면 `run`으로 간주한다.
토픽 ID만 없으면 `status`로 간주하고 사용 가능한 토픽 목록을 보여준다.

## 실행 라우팅

### `status` — 상태 확인

```bash
uv run ai-env pipeline workflow {topic_id}
```

토픽이 없으면:
```bash
ls config/topics/*.yaml
```

### `init` — Phase 0: 워크스페이스 초기화

`.claude/commands/phases/wf-init.md` 파일을 Read로 읽고 그 안의 모든 단계를 수행한다.
토픽 ID를 해당 파일의 `$ARGUMENTS`로 전달한다.

### `research` — Phase 2: 3-Track 리서치

`.claude/commands/phases/wf-research.md` 파일을 Read로 읽고 그 안의 모든 단계를 수행한다.

### `spec` — Phase 3: Brief + Spec 생성

`.claude/commands/phases/wf-spec.md` 파일을 Read로 읽고 그 안의 모든 단계를 수행한다.

### `code` — Phase 4: TDD 코드 생성

`.claude/commands/phases/wf-code.md` 파일을 Read로 읽고 그 안의 모든 단계를 수행한다.

### `review` — Phase 5: 스펙 정합성 리뷰

`.claude/commands/phases/wf-review.md` 파일을 Read로 읽고 그 안의 모든 단계를 수행한다.

### `run` — 전체 자동 실행 (1회)

`.claude/commands/phases/wf-run.md` 파일을 Read로 읽고 그 안의 모든 단계를 수행한다.
이 파일이 내부적으로 wf-spec, wf-code, wf-review를 순차 호출한다.

### `iterate` — 반복 개선 루프

Review 결과를 기반으로 Research → Spec → Code → Review 사이클을 반복한다.
각 반복(iteration)은 이전 Review의 피드백을 다음 Research에 반영하여 점진적으로 개선한다.

**인자**: `iterate {topic_id} [max_iterations]` (기본 max: 3)

#### 루프 절차

```
┌─────────────────────────────────────────────────┐
│  Iteration 1: 초기 실행                          │
│  Research → Spec → Code → Review                │
│         ↓                                        │
│  Review 결과 분석                                │
│    ├─ Must Fix 0건 + Nice to Have ≤ 2건 → 종료  │
│    └─ 개선 필요 → Iteration 2                    │
│         ↓                                        │
│  Iteration 2: 개선 사이클                        │
│  Review 피드백 → 타겟 Research → Spec 수정       │
│  → Code 수정 → Review                           │
│    ├─ 통과 → 종료                                │
│    └─ 개선 필요 → Iteration 3 ...               │
│         ↓                                        │
│  max_iterations 도달 → 강제 종료 + 잔여 이슈 보고│
└─────────────────────────────────────────────────┘
```

#### Step 1: 초기 사이클 (Iteration 1)

1. 현재 Phase 확인: `uv run ai-env pipeline workflow {topic_id}`
2. Phase에 따라 분기:
   - research 이전 → `wf-research.md` 부터 시작
   - research 완료 → `wf-spec.md` 부터 시작
   - spec 완료 → `wf-code.md` 부터 시작
   - code 완료 → `wf-review.md` 부터 시작
3. `wf-run.md`의 절차를 따라 Review까지 실행

#### Step 2: Review 결과 분석

Review 완료 후 리뷰 파일(`40_Reviews/REV-{topic_id}.md`)을 읽고 분석한다:

| 조건 | 판정 |
|------|------|
| Must Fix = 0 AND Nice to Have ≤ 2 | **PASS** → 루프 종료 |
| Must Fix > 0 | **FAIL** → 다음 Iteration |
| Must Fix = 0 AND Nice to Have > 2 | **IMPROVE** → 다음 Iteration |

**PASS이면**: 최종 보고 후 종료.

#### Step 3: 개선 피드백 추출 (Iteration 2+)

Review에서 발견된 이슈를 **개선 리서치 쿼리**로 변환한다:

1. Must Fix 항목 각각에서 핵심 키워드/기술적 질문 추출
2. Nice to Have 중 영향도 높은 것 선별 (최대 3개)
3. 이를 추가 Research 쿼리로 구성:
   ```
   iteration_{N}_queries:
     - "Must Fix: {이슈 요약} 해결 방법"
     - "개선: {Nice to Have 요약} 모범 사례"
   ```

#### Step 4: 타겟 Research (Iteration 2+)

**전체 리서치가 아닌 타겟 리서치**만 수행한다:
- Step 3에서 추출한 쿼리만 WebSearch로 검색
- 결과를 `10_Research/Clippings/iter-{N}-*.md`로 저장
- 기존 리서치 자료는 보존 (덮어쓰지 않음)

#### Step 5: Spec/Code 수정 (Iteration 2+)

- **Spec**: 기존 Spec에서 Review 피드백 해당 섹션만 수정 (전체 재작성 금지)
- **Code**: 기존 코드에서 Must Fix 항목만 수정
- **테스트**: 수정 후 전체 테스트 실행하여 기존 기능 미파손 확인

#### Step 6: 재Review

`wf-review.md` 절차를 다시 수행한다.
리뷰 파일에 iteration 번호를 기록:
```markdown
## Iteration {N} Review
- 이전 Must Fix 해소: {M}/{Total}건
- 신규 이슈: {K}건
```

→ Step 2로 돌아가 판정.

#### Step 7: 최종 보고

루프 종료 시 (PASS 또는 max_iterations 도달) 전체 결과를 보고한다:

```
🔄 워크플로우 반복 개선 완료!

📊 Iteration 요약:
  Iteration 1: Must Fix 3건, Nice to Have 5건
  Iteration 2: Must Fix 1건, Nice to Have 2건 (2건 해소)
  Iteration 3: Must Fix 0건, Nice to Have 1건 ✅ PASS

총 반복: 3회
해소된 이슈: Must Fix 3/3, Nice to Have 4/5
잔여: Nice to Have 1건 (영향도 낮음)
```

**max_iterations 도달 시**:
```
⚠ 최대 반복 횟수({max})에 도달했습니다.
잔여 Must Fix: {N}건 — 수동 검토 필요
리뷰 파일: 40_Reviews/REV-{topic_id}.md
```

## 절대 금지

- 테스트를 통과시키기 위해 테스트 코드를 수정/삭제하지 마라
- 각 Phase의 절차를 임의로 생략하지 마라
- Gate Check 실패 시 강제로 다음 Phase로 넘어가지 마라
