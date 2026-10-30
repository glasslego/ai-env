# 커밋 메시지 규칙

이 규칙은 CDE 랭킹 저장소 또는 `CDETEAM-XXXX` Jira 작업에 적용한다. 다른 저장소에서는
해당 저장소의 커밋 규칙을 우선하고, 별도 규칙이 없을 때 글로벌 기본 형식을 사용한다.

## 형식

```
[CDETEAM-XXX] 변경 내용 요약 (한 줄)

- 변경 항목 1
- 변경 항목 2
- 입력 소스 / 출력 대상 / 검증 방법
- 요청: <agit 요청 링크>   (agit 요청 기반 작업일 때)

Co-Authored-By: {실제 에이전트명} {실제 모델명}
```

## 예시

```
[CDETEAM-364] 선물하기 랭킹 피처 추가

- gift_ranking_feature 테이블 신규 생성
- 입력: user_action_log (Kafka), 출력: Hive feature store
- 단위 테스트 pytest로 검증 완료

Co-Authored-By: Claude Sonnet 4.6

[CDETEAM-998] ES export 인덱스 매핑 수정

- gift_ranking_v2 인덱스 매핑 필드 타입 변경 (keyword → text)
- 기존 인덱스 alias 무중단 전환 확인

Co-Authored-By: Claude Sonnet 4.6

[CDETEAM-1075] 추천친구 원천 Mongo DB 변경 반영

- 원천 db giftassistant → giftrecommendpersonal 전환
- 요청: https://kakao.agit.in/g/300099141/wall/471772825

Co-Authored-By: Claude Sonnet 4.6

[CDETEAM-1127] Gift 검증 워크플로 추가

- 이미지 빌드 후 Airflow 3 검증 DAG 트리거
- 검증: workflow YAML 파싱 통과

Co-Authored-By: Codex gpt-5.6-sol
```

## 규칙

- 제목: `[CDETEAM-XXX] 한 줄 요약` (50자 이하 권장)
- 본문: `-` 로 변경 항목 나열
- 본문에 포함 권장: 입력 소스, 출력 대상, 검증 방법
- **agit 요청 기반 작업이면** 해당 Jira 티켓을 참조해 요청 아지트 링크를 본문에 넣는다.
  - Jira 티켓의 `☑️ 관련 링크 > 요청 아지트` (또는 description 상단 `출처`)에서 URL을 가져온다.
  - 본문에 `- 요청: <agit url>` 한 줄로 넣는다. 여러 건이면 각각 나열한다.
- 본문(`-` 목록)과 `Co-Authored-By:` 트레일러 사이에는 **빈 줄을 한 줄** 둔다. (본문에 바로 붙이지 않는다.)
- AI 작성 시 실제 사용한 에이전트와 모델명을 `Co-Authored-By: {에이전트명} {실제 모델명}`으로 명시한다. 모델명을 추정해서 쓰지 않는다.
  - Claude 예: `Co-Authored-By: Claude Sonnet 4.6`
  - Codex 예: `Co-Authored-By: Codex gpt-5.6-sol` (`{model 버전}`은 실제 사용 모델로)
