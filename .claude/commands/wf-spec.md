# 3-Track 리서치 종합 → Plan/Spec 생성

토픽 ID: $ARGUMENTS

> 3개 Track의 리서치 결과를 교차 분석하여 plan-spec 문서를 생성한다.
> Phase 2는 단일 에이전트가 수행한다 (병렬 불필요).

## Step 1: 토픽 YAML 로드

- `~/work/glasslego/ai-env/config/topics/$ARGUMENTS.yaml` 파일을 Read로 읽는다
- 파일이 없으면 `config/topics/` 아래 토픽 목록을 보여주고 종료
- Obsidian 경로:
  - vault_root = `/Users/megan/Documents/Obsidian Vault`
  - base_path = `{vault_root}/{topic.obsidian_base}`
  - ref_dir = `{base_path}/07_참고`

## Step 2: 리서치 완료 여부 확인

`{ref_dir}/` 와 `{base_path}/10_Research/Clippings/` 두 디렉토리 아래에서
모든 `.md` 파일을 Glob으로 체크한다. YAML에 정의된 output 파일뿐 아니라
사용자가 직접 배치한 수동 리서치 파일도 포함한다.

Track별 현황을 테이블로 보여준다:
```
Track A (auto):       3/5 ✅
Track B (gemini):     1/1 ✅
Track C (gpt):        1/1 ✅
Manual:               2 files ✅
```

- **누락 파일이 있으면** 사용자에게 목록을 알리고 계속할지 확인
- **최소 2개 Track** 결과가 있어야 교차 분석 의미 있음 (1개만 있어도 진행 가능)
- **수동 리서치 파일만 있어도** 진행 가능 (사용자가 직접 자료를 수집한 경우)
- **결과가 0개면** Phase 1을 먼저 실행하거나 수동 리서치 파일을 배치하라고 안내하고 종료

## Step 3: 모든 리서치 파일 읽기

존재하는 모든 리서치 파일을 Read로 읽는다:
- Track A: `auto-*.md` 파일들
- Track B: `gemini-*.md` 파일들
- Track C: `gpt-*.md` 파일들
- Manual: 위 패턴에 해당하지 않는 모든 `.md` 파일들 (사용자가 직접 배치)
- `_`로 시작하는 메타 파일은 제외

검색 디렉토리: `{ref_dir}/` (07_참고) 와 `{base_path}/10_Research/Clippings/` 모두 확인.

각 파일을 읽을 때 **어떤 Track에서 온 것인지** 구분하여 기억한다.
수동 파일은 "Manual" 트랙으로 분류한다.
파일이 많으면 Task 도구로 병렬 읽기해도 된다.

## Step 4: 4-Way 교차 분석

리서치 결과를 종합할 때 **반드시** 다음 4가지 관점을 적용한다:

### 4-1. 공통 발견 (Consensus)

3개 소스가 모두 동의하거나 유사하게 언급하는 사항.
신뢰도가 가장 높으므로 spec의 **핵심 근거**로 활용한다.

> 예: "Track A/B/C 모두 ccxt 라이브러리를 비동기 거래에 추천"
> → spec에서 ccxt 채택의 핵심 근거

### 4-2. 상충 의견 (Divergence)

Gemini vs GPT 또는 Track 간에 **다르게 말하는 부분**을 명시적으로 기록한다.

> 예: "Gemini는 Freqtrade를 추천하지만 GPT는 Jesse를 추천.
>      Gemini 근거: 커뮤니티 규모. GPT 근거: 백테스트 정확도."
> → spec에서 어느 쪽을 채택했는지와 그 이유를 **반드시** 기술

### 4-3. 고유 인사이트 (Unique)

특정 소스에서만 나온 중요 정보:
- **Gemini 고유**: 최신 시장 데이터, 한국 규제, 거래소 특이사항
- **GPT 고유**: 학술 논문 근거, 수학적 모델, 리스크 공식
- **Claude(Track A) 고유**: 특정 라이브러리 API 상세, GitHub 이슈

### 4-4. 신뢰도 평가 (Confidence)

각 주장의 근거 충분성을 평가한다:
- 출처 URL/논문 인용 있는 주장 → **높음**
- 일반적 서술만 있는 주장 → **중간**
- 소스 간 상충하는 주장 → **낮음** (추가 검증 필요)

## Step 5: Plan/Spec 문서 생성

토픽 YAML의 `plan.synthesis_prompt`를 **주요 지시**로 삼아 spec을 작성한다.
synthesis_prompt에 명시된 항목 + 아래 교차 분석 섹션을 포함한다.

**저장 경로**: `{base_path}/{plan.output}`

### 문서 구조

```markdown
---
type: plan-spec
topic: {topic.id}
date: {오늘 YYYY-MM-DD}
sources:
  track_a: [파일명 목록]
  track_b: [파일명 목록]
  track_c: [파일명 목록]
  manual: [파일명 목록]
---

# {topic.name} — Plan/Spec

## Executive Summary
(전체 요약 5-10줄. 핵심 결정사항과 근거를 간결하게.)

## {synthesis_prompt가 지시하는 각 섹션}
(synthesis_prompt의 번호별 항목을 각각 섹션으로 작성)

## 소스 교차 분석

### 공통 발견 (Consensus)
(3개 Track이 동의하는 사항 — 신뢰도 높음)

### 상충 의견 (Divergence)
| 주제 | Gemini 의견 | GPT 의견 | 채택 | 근거 |
|------|------------|---------|------|------|
| ... | ... | ... | ... | ... |

### 고유 인사이트
- **Gemini에서만**: ...
- **GPT에서만**: ...
- **Claude에서만**: ...

### 신뢰도 평가
| 결정사항 | 근거 소스 | 신뢰도 | 비고 |
|---------|----------|:------:|------|
| ... | Track A,B,C | 높음 | 3개 소스 일치 |
| ... | Track B만 | 중간 | 추가 검증 권장 |

## 결정 로그
(주요 기술적 결정을 번호 매겨 기록. 각 결정마다 근거 Track 명시)
```

## Step 6: ADR 자동 생성

Step 4의 교차 분석에서 발견된 **주요 아키텍처/기술 결정**마다 ADR 파일을 생성한다.

워크플로우 스캐폴딩이 되어있으면 (`20_Specs/ADR/`이 존재하면):
- 각 Divergence 항목 중 채택 결정이 있는 것 → ADR 파일 생성
- 경로: `{base_path}/20_Specs/ADR/ADR-{NNN}-{slug}.md`
- ADR 템플릿: `config/templates/obsidian/ADR.md` 참고
- 최소 항목: Context, Decision, Alternatives, Consequences

## Step 7: 리서치 상태 업데이트

### 기존 상태 파일 업데이트
`{ref_dir}/_research-status.md` 파일 끝에 추가한다:

```markdown
---

## Phase 2: Plan/Spec 생성 완료 ✅
- [x] {plan.output} (생성일: {날짜})
- 사용된 소스: Track A {n}건, Track B {n}건, Track C {n}건

## 다음 단계
\```bash
claude --fallback "/wf-code {topic.id}"
\```
```

### 워크플로우 상태 업데이트

워크플로우 스캐폴딩이 되어있으면:
1. TASK 파일의 Phase Checklist에서 "Phase 3: Spec Freeze" 체크
2. `_workflow-status.md` 갱신 (Phase 3 완료)
3. SPEC 파일을 `20_Specs/SPEC-{topic.id}.md`에도 저장/링크

## Step 8: 완료 보고

사용자에게 보고:
- **spec 문서 경로** + Executive Summary 발췌
- **주요 아키텍처 결정** 3-5개 목록 + ADR 파일 경로
- **Gemini vs GPT 주요 상충점** 하이라이트 (있는 경우)
- **워크플로우 상태**: `ai-env pipeline workflow {topic.id}`
- **다음 단계**: `claude --fallback "/wf-code {topic.id}"`
