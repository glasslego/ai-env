# Phase 0: 워크플로우 초기화

토픽 ID: $ARGUMENTS

## 개요

토픽 YAML을 읽고, Obsidian 워크스페이스를 스캐폴딩하고,
Research Questions를 확장하고, Phase별 프롬프트를 생성한다.

## 실행 단계

### Step 1: 토픽 로드

```bash
uv run ai-env pipeline info $ARGUMENTS
```

토픽 YAML 경로: `config/topics/$ARGUMENTS.yaml`
이 파일을 Read 도구로 읽어서 토픽 정보를 확인한다.

### Step 2: Obsidian 워크스페이스 스캐폴딩

```bash
uv run ai-env pipeline scaffold $ARGUMENTS
```

이 명령은 다음을 생성한다:
- 폴더 구조 (10_Research, 20_Specs, 30_Tasks, 40_Reviews, 50_Logs)
- TASK-{topic_id}.md (초기 태스크 파일)
- SPEC-{topic_id}.md (빈 SPEC 템플릿)
- Phase별 프롬프트 파일 (_prompts/)
- 워크플로우 상태 파일 (_workflow-status.md)

### Step 3: Research Questions 확장

TASK 파일을 읽고, Research Questions 섹션을 확장한다.

**규칙:**
- 토픽 YAML의 research.auto 쿼리를 참고하여 8-12개 질문으로 확장
- 각 질문에 [자료 타입] 태그 부착: [논문], [블로그], [공식문서], [사례], [코드]
- TASK 파일의 Goal/Scope/AC를 반영하여 질문 생성
- TASK 파일에 Write 도구로 업데이트

**agent-teams 병렬 처리:**
Task 도구를 사용하여 질문 확장을 병렬로 수행한다.
반드시 하나의 응답에서 모든 Task 호출을 동시에 수행하라.

Task 1 (Research Questions 확장):
- subagent_type: "general-purpose"
- 토픽의 Goal, Scope, 기존 research queries를 분석
- 8-12개의 구체적 Research Questions 생성
- 결과를 TASK 파일의 Research Questions 섹션에 Write

Task 2 (AC 정제):
- subagent_type: "general-purpose"
- 토픽의 Goal, Scope를 분석
- Acceptance Criteria를 구체화 (측정 가능하게)
- 결과를 TASK 파일의 AC 섹션에 반영

### Step 4: 워크플로우 상태 확인

```bash
uv run ai-env pipeline workflow $ARGUMENTS
```

### Step 5: 다음 단계 안내

사용자에게 다음 워크플로우 단계를 안내한다:

```
📋 워크플로우 초기화 완료!

다음 단계:
  1. TASK 파일의 Research Questions 검토/수정
  2. 리서치 시작: claude "/wf-research {topic_id}"
  3. Gemini 심층리서치: _prompts/gemini-collect.md 참고
  4. Brief 작성: claude "/wf-spec {topic_id}" (리서치 완료 후)
  5. 전체 파이프라인 한번에: claude "/wf-run {topic_id}"
```
