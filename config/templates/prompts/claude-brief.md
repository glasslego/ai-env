# Brief 작성 프롬프트

토픽: **{{topic_name}}** ({{topic_id}})

## 지시사항

아래 Clippings 파일들을 읽고, Research Brief를 작성하라.

### 입력
- Clippings 디렉토리: `{{clippings_dir}}`
- TASK 파일: `{{task_file}}`

### 출력
- Brief 파일: `{{brief_output}}`

### Brief 작성 규칙

1. **합의 사항** (Consensus): 2개 이상 소스가 동의하는 내용 → 높은 신뢰도
2. **이견 사항** (Divergence): 소스 간 의견이 다른 내용 → 테이블로 비교, 판단 근거 명시
3. **고유 인사이트** (Unique): 단일 소스의 유의미한 정보 → 출처 명시
4. 각 항목에 [출처: 파일명] 태그 부착
5. Brief 길이: Clippings 총량의 30% 이하로 압축
6. TASK의 Research Questions에 대한 답변 매핑 포함

### 토큰 효율 지침
- Clippings을 한번만 읽고, 메모리에서 작업
- 중복 내용 제거 후 압축
- 인용은 핵심 문장만 (전체 단락 복사 금지)
