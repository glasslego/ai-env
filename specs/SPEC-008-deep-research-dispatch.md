/---
id: SPEC-008
title: Deep Research API Dispatch (pipeline dispatch)
status: implemented
created: 2026-02-18
updated: 2026-02-18
---

# SPEC-008: Deep Research API Dispatch

## 개요

`ai-env pipeline dispatch {topic_id}`는 Track B(Gemini)와 Track C(GPT)의 심층리서치를 API로 자동 실행하는 CLI 커맨드다. 기존에는 프롬프트 파일만 생성하고 사용자가 웹에서 수동 실행해야 했으나, 이제 Gemini Deep Research API와 OpenAI Deep Research API를 직접 호출하여 완전 자동화한다.

API 키가 없는 트랙은 기존 프롬프트 파일 생성으로 graceful fallback.

## API 엔드포인트

### Gemini Deep Research (Track B)

- **API**: Google Interactions API
- **모델**: `deep-research-pro-preview-12-2025`
- **엔드포인트**: `POST https://generativelanguage.googleapis.com/v1beta/interactions`
- **인증**: `x-goog-api-key` 헤더 (GOOGLE_API_KEY)
- **방식**: 비동기 polling (POST → interaction_id → GET으로 상태 확인)
- **소요 시간**: 5~20분

### OpenAI Deep Research (Track C)

- **API**: Responses API
- **모델**: `o4-mini-deep-research`
- **엔드포인트**: `POST https://api.openai.com/v1/responses`
- **인증**: `Authorization: Bearer` 헤더 (OPENAI_API_KEY)
- **도구**: `web_search_preview`
- **방식**: 동기 또는 background polling

## 사용법

```bash
ai-env pipeline dispatch bitcoin-automation              # 전체 (Track B + C)
ai-env pipeline dispatch bitcoin-automation --track gemini  # Gemini만
ai-env pipeline dispatch bitcoin-automation --track gpt     # GPT만
ai-env pipeline dispatch bitcoin-automation --timeout 1800  # 타임아웃 30분
```

## 실행 흐름

```
ai-env pipeline dispatch {topic_id}
  │
  ├─ 토픽 YAML 로드
  ├─ .env에서 API 키 로드 (GOOGLE_API_KEY, OPENAI_API_KEY)
  │
  ├─ API 키 있는 트랙 → dispatch_deep_research() 병렬 호출
  │    ├─ Gemini: POST → interaction_id → 15초 간격 polling → 완료
  │    └─ OpenAI: POST → 응답 추출 (또는 background polling)
  │
  ├─ 결과를 Obsidian에 마크다운으로 저장
  │    └─ frontmatter: source, date, track, topic, elapsed
  │
  └─ API 키 없는 트랙 → 프롬프트 파일 생성 (fallback)
```

## 결과 파일 형식

```markdown
---
source: Gemini Deep Research (API)
date: 2026-02-18
track: B
topic: bitcoin-automation
elapsed: 320s
---

# 최신 트렌드, 시장 동향, 한국 거래소

(API 결과 내용)

---

## 참고 소스

- https://example.com/1
- https://example.com/2
```

## Fallback 전략

| 상황 | 동작 |
|------|------|
| API 키 있음 + API 성공 | 결과를 Obsidian에 저장 |
| API 키 있음 + API 에러 | 에러 표시, 해당 항목 실패 처리 |
| API 키 없음 | 프롬프트 파일 생성 (기존 동작) |
| 타임아웃 | 타임아웃 에러 표시 |

## 프롬프트 매핑 (Markdown frontmatter 방식)

토픽별 심층리서치 프롬프트는 `config/prompts/{topic_id}/` 디렉토리에 Markdown 파일로 관리한다.
YAML frontmatter에 메타데이터, 본문에 프롬프트 텍스트를 작성한다.

```
config/prompts/
  bitcoin-automation/
    gemini-trend-analysis.md    # Track B (Gemini)
    gpt-quant-strategy.md       # Track C (GPT)
  my-next-topic/
    gemini-xxx.md
    gpt-xxx.md
```

각 파일 형식:

```markdown
---
track: gemini          # gemini | gpt
output: "07_참고/gemini-deep-trend-analysis.md"   # Obsidian 저장 경로
focus: "최신 트렌드, 시장 동향"                     # 결과 제목용 (optional)
---

프롬프트 본문 (여러 줄 가능)
```

프롬프트 우선순위:
1. `config/prompts/{topic_id}/*.md` (매핑 파일)
2. `config/topics/{topic_id}.yaml`의 `gemini_deep`/`gpt_deep` (fallback)

## 모듈 구조

| 파일 | 역할 |
|------|------|
| `src/ai_env/core/research.py` | API 래퍼 (Gemini/OpenAI), 결과 포맷팅, 통합 디스패치 |
| `src/ai_env/cli/pipeline_cmd.py` | `dispatch` CLI 커맨드 |
| `src/ai_env/core/pipeline.py` | 토픽 YAML 모델, 프롬프트 MD 로더, 기존 프롬프트 생성 (fallback) |
| `config/prompts/{topic_id}/*.md` | 토픽별 심층리서치 프롬프트 (frontmatter + 본문) |
| `tests/core/test_research.py` | httpx mock 기반 테스트 |
| `tests/core/test_pipeline.py` | 프롬프트 로더 테스트 포함 |

## 테스트 커버리지

### `TestDeepResearchResult` (Pydantic 모델)

| 테스트 | 검증 내용 |
|--------|-----------|
| `test_success_result` | 성공 결과 모델 검증 |
| `test_error_result` | 에러 결과 모델 검증 |
| `test_sources_field` | 참고 URL 리스트 검증 |

### `TestGeminiExtract` (콘텐츠 추출)

| 테스트 | 검증 내용 |
|--------|-----------|
| `test_extract_content_from_output` | output.content.parts 경로 |
| `test_extract_content_from_candidates` | candidates 경로 |
| `test_extract_content_from_response` | response.text 경로 |
| `test_extract_content_fallback` | 알 수 없는 형식 fallback |
| `test_extract_sources_from_grounding` | groundingMetadata 소스 추출 |
| `test_extract_sources_from_output` | output.sources 소스 추출 |
| `test_extract_sources_empty` | 빈 데이터 처리 |

### `TestOpenAIExtract` (콘텐츠 추출)

| 테스트 | 검증 내용 |
|--------|-----------|
| `test_extract_content_from_output_message` | output[].message.content 경로 |
| `test_extract_content_from_text` | 직접 text 필드 |
| `test_extract_content_empty` | 빈 데이터 처리 |
| `test_extract_sources_from_web_search` | web_search_call URL 추출 |
| `test_extract_sources_empty` | 빈 데이터 처리 |

### `TestFormatResultMarkdown` (결과 포맷)

| 테스트 | 검증 내용 |
|--------|-----------|
| `test_success_format` | frontmatter + 본문 + 소스 |
| `test_error_format` | 에러 메시지 포맷 |
| `test_no_focus` | focus 없을 때 기본 제목 |

### `TestGeminiDispatch` (API 호출)

| 테스트 | 검증 내용 |
|--------|-----------|
| `test_gemini_start_research` | POST → polling → 완료 전체 흐름 |
| `test_gemini_api_error` | HTTP 에러 처리 |
| `test_gemini_timeout` | 폴링 타임아웃 |
| `test_gemini_failed_state` | FAILED 상태 처리 |

### `TestOpenAIDispatch` (API 호출)

| 테스트 | 검증 내용 |
|--------|-----------|
| `test_openai_dispatch_success` | 성공 응답 처리 |
| `test_openai_api_error` | HTTP 에러 처리 |
| `test_openai_empty_content` | 빈 콘텐츠 처리 |

### `TestDispatchIntegration` (통합)

| 테스트 | 검증 내용 |
|--------|-----------|
| `test_dispatch_with_both_keys` | 양쪽 API 동시 호출 + 파일 저장 |
| `test_dispatch_gemini_only` | Gemini만 사용 |
| `test_dispatch_no_keys_returns_empty` | 키 없으면 빈 리스트 |
| `test_result_saved_with_frontmatter` | frontmatter 포함 파일 저장 |

## 제약사항

- httpx만 사용 (google-genai, openai 라이브러리 미사용)
- Gemini Deep Research는 5~20분 소요 (긴 타임아웃 필요)
- API 응답 형식은 프리뷰 모델이므로 변경될 수 있음
- 병렬 호출 시 두 API가 동시에 실행됨 (asyncio.gather)
