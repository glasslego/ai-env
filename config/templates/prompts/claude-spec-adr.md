# Spec/ADR 작성 프롬프트

토픽: **{{topic_name}}** ({{topic_id}})

## 지시사항

Brief와 TASK를 읽고, SPEC과 ADR을 작성하라.

### 입력
- Brief 파일: `{{brief_file}}`
- TASK 파일: `{{task_file}}`
- SPEC 템플릿: `{{spec_template}}`

### 출력
- SPEC 파일: `{{spec_output}}`
- ADR 디렉토리: `{{adr_dir}}`

### SPEC 작성 규칙

1. Brief의 합의 사항 → Architecture/Data Model 반영
2. Brief의 이견 사항 → 각각 ADR로 분리 (결정 근거 포함)
3. TASK의 AC → SPEC의 Acceptance Criteria로 정제
4. Implementation Plan은 Phase 단위로 작성
5. 모든 기술 선택에 대해 Alternatives Considered 포함

### ADR 작성 규칙

1. 중요한 아키텍처/기술 결정마다 ADR 파일 생성
2. ADR 번호는 순차 (ADR-001, ADR-002, ...)
3. 각 ADR은 Context → Decision → Alternatives → Consequences 구조
4. SPEC에서 해당 ADR 참조 링크 추가

### 토큰 효율 지침
- Brief만 읽으면 됨 (원본 Clippings 다시 읽지 말것)
- SPEC은 실행 가능한 수준의 구체성 (코드 작성에 충분할 정도)
- ADR은 간결하게 (각 500자 이내)
