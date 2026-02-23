# 토픽 기반 3-Track 리서치 파이프라인

토픽 ID: $ARGUMENTS

> **Agent-Teams 병렬 패턴**: Track A의 각 검색 쿼리를 별도 Task 에이전트로 병렬 실행한다.

## Step 1: 토픽 YAML 로드

- `~/work/glasslego/ai-env/config/topics/$ARGUMENTS.yaml` 파일을 Read 도구로 읽는다
- 파일이 없으면 `config/topics/` 아래 YAML 파일 목록을 Glob으로 보여주고 종료
- Obsidian vault 경로 결정:
  - vault_root = `/Users/megan/Documents/Obsidian Vault`
  - base_path = `{vault_root}/{topic.obsidian_base}`
  - **신규 파일 저장**: `clip_dir = {base_path}/10_Research/Clippings` (표준 경로)
  - **레거시 읽기 전용**: `{base_path}/07_참고` (기존 파일 참조만, 신규 저장 금지)
- `clip_dir`이 없으면 Bash로 `mkdir -p "{clip_dir}"` 실행

## Step 2: Track A — 병렬 자동검색 (Agent-Teams)

**CRITICAL: 아래 패턴을 정확히 따르라.**

`research.auto` 배열의 **모든 항목**에 대해 Task 도구를 호출한다.
**반드시 하나의 응답에서 모든 Task 호출을 동시에 수행하라** — 이것이 병렬 실행의 핵심이다.

### 각 Task 설정

```
Task 도구 호출:
  description: "Track A 검색: {query 처음 40자}"
  subagent_type: "general-purpose"
  prompt: 아래 템플릿에 값을 채워서 전달
```

### 서브에이전트 프롬프트 템플릿

각 Task의 `prompt` 파라미터에 다음 내용을 채워서 전달한다:

```
너는 리서치 파이프라인의 Track A 검색 에이전트다.

**임무**: 웹검색을 수행하고 결과를 마크다운 파일로 저장하라.

**쿼리**: {query}
**저장 경로**: {vault_root}/{topic.obsidian_base}/10_Research/Clippings/{output 파일명}
**토픽 ID**: {topic.id}
**날짜**: {오늘 YYYY-MM-DD}

**수행 절차**:
1. WebSearch 도구로 "{query}"를 검색한다
2. 검색 결과에서 가장 유용한 URL 2-3개를 WebFetch로 상세 내용을 가져온다
3. 수집한 정보를 종합하여 아래 형식의 마크다운을 Write 도구로 저장한다
4. 저장 전 디렉토리가 없으면 Bash로 mkdir -p 실행

**출력 형식** (이 형식을 정확히 따르라):

---
source: auto-search (Claude Code)
query: "{query}"
date: {날짜}
track: A
topic: {topic.id}
---

# {쿼리 주제를 반영한 제목}

## 핵심 요약
(3-5줄 핵심 내용)

## 상세 내용
(검색 결과를 주제별로 정리, 구체적인 수치/버전/코드 예시 포함)

## 참고 소스
- [제목](URL) — 핵심 내용 한 줄 요약

**에러 처리**: WebSearch가 실패하면 검색 쿼리와 에러 내용을 반환하라.
```

### 실행 예시 (auto가 5개인 경우)

**하나의 응답에서** 5개 Task를 동시에 호출한다:

1. Task: "Track A: ccxt python async trading bot..."
2. Task: "Track A: bitcoin automated trading system..."
3. Task: "Track A: binance upbit futures API..."
4. Task: "Track A: freqtrade vs jesse vs hummingbot..."
5. Task: "Track A: cryptocurrency trading backtesting..."

## Step 3: Track B/C — Deep Research API 디스패치

**Step 2의 Task들과 동시에** 메인 에이전트(나)가 직접 수행한다.

### API 자동 디스패치 (권장)

Bash 도구로 `ai-env pipeline dispatch {topic.id}` 실행:

```bash
cd ~/work/glasslego/ai-env && uv run ai-env pipeline dispatch {topic.id}
```

이 커맨드가:
1. `.env`에서 `GOOGLE_API_KEY`, `OPENAI_API_KEY` 확인
2. API 키가 있으면 Gemini/OpenAI Deep Research API 자동 호출
3. 결과를 Obsidian에 마크다운으로 저장
4. API 키 없는 트랙은 프롬프트 파일 생성으로 fallback

### Fallback: 수동 프롬프트 파일 (API 키 없을 때)

`dispatch` 커맨드에서 자동 처리됨. API 키가 없으면 아래 프롬프트 파일이 생성된다:

- Track B: `{clip_dir}/_gemini-prompts.md` — Gemini 웹에 복붙
- Track C: `{clip_dir}/_gpt-prompts.md` — GPT 웹에 복붙

## Step 4: 서브에이전트 완료 대기

Step 2에서 스폰한 Task들의 결과를 확인한다.
- 각 Task의 결과에서 성공/실패 여부를 파악
- 실패한 검색이 있으면 기록

## Step 5: 진행 상황 체크리스트 생성

`{clip_dir}/_research-status.md` 파일을 Write로 생성한다:

```markdown
# 리서치 진행 상황: {topic.name}

토픽 ID: `{topic.id}`
생성일: {날짜}

## Track A: 자동검색 (Claude Code)

- [x/실패] `{각 auto 항목의 output}`

## Track B: Gemini 심층리서치 (수동)

- [ ] `{각 gemini_deep 항목의 output}` — {focus}
  → 프롬프트: `_gemini-prompts.md` 참고

## Track C: GPT 심층리서치 (수동)

- [ ] `{각 gpt_deep 항목의 output}` — {focus}
  → 프롬프트: `_gpt-prompts.md` 참고

---

## 다음 단계

Track B, C 완료 후:
\```bash
claude "/wf-spec {topic.id}"
\```
```

## Step 6: 워크플로우 상태 업데이트

워크플로우 스캐폴딩이 되어있으면 (30_Tasks/, 20_Specs/ 등이 존재하면):

1. Track A 결과를 `10_Research/Clippings/` 폴더에도 복사/링크한다
2. `_workflow-status.md` 파일을 갱신한다 (Phase 2: Research 진행중)
3. Brief 작성 프롬프트를 안내한다:
   - `_prompts/claude-brief.md` 참고
   - 또는 리서치 완료 후 `/wf-spec`이 Brief 통합 작성

## Step 7: 완료 보고

사용자에게 다음을 보고한다:
- **Track A 결과**: 성공 N건 / 실패 N건, 각 파일별 핵심 발견 1줄 요약
- **프롬프트 파일**: `_gemini-prompts.md`, `_gpt-prompts.md` 경로
- **Track B/C 결과**: API 디스패치 성공 여부 (성공 N건 / 실패 N건 / fallback N건)
- **Brief 작성**: 리서치 완료 후 Clippings → Brief 압축 (선택사항)
- **상태 확인**: `ai-env pipeline status {topic.id}` 또는 `ai-env pipeline workflow {topic.id}`
- **Phase 3**: `claude "/wf-spec {topic.id}"`
