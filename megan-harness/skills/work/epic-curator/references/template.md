# Epic Curator 템플릿 조사·개인 작성 기준

- Spec/Task: `spec-document-authoring/task-personal-overrides`
- 조사 기준: 2026-10-14, cde-skills origin/develop와 라이브 CDETEAM-207 rubric
- 목표: **템플릿·검증은 유지, 본문 내용만 간소화**

## 모드별 원형

| 모드 | 유지할 템플릿 | 간소화할 부분 |
|---|---|---|
| 일반 Epic standard | ☑️ 배경 / 목적 / 기대효과 / 성공 기준 / 완료보고 / 관련 링크, 순서 유지 | 섹션의 반복 문장·상세 구현 목록 |
| 인바운드 describe | 배경 / 수집 범위 / 처리 조건 / 기대효과 / 성공 기준 / 요청 정보 / 완료보고 / 관련 링크의 8헤더 | 각 값·조건의 장문 설명. 일반 6섹션으로 변환하지 않음 |
| 섹션 patch | 대상 절 하나만 변경, 나머지 보존 | 요청된 절의 표현만 압축 |
| ledger | EPIC-CURATOR:AUTO 관리 마커 | 글별 요약. 사람 작성 영역 보존 |
| leader-report / person | MM/DD (상태) 제목·링크 + 본문 2~3줄 | 배경·목표·기대효과 또는 영향 중심 문장 |

## rubric 검증

- 정본: [CDETEAM-207](https://kakao.atlassian.net/browse/CDETEAM-207), 로컬 YAML은 폴백.
- 형태: `- [label] field: value`. 기호·태그·필드명을 바꾸거나 들여쓰기하지 않음.
- 실제 라벨의 필드를 모두 채움. allow_unknown=true인 미확인 값만 `미정` 사용.
- 필수 실제 값: ta-data 자산, ta-cost 대상비용, ta-productivity 대상작업, ta-security 대상, roadmap:약속 약속일정, roadmap:투자 투자대상.
- 길게 쓰라고 요구하는 validator는 없음. 헤더·순서·라벨 축·필수 값·금지어를 검증함.

## 일반 Epic 작성 예시

아래는 형식 검증용 예시다. 실제 Jira 생성·수정이나 성과·수치를 의미하지 않는다.
라벨 예시: roadmap:투자 / roadmap:플랫폼 / ta-productivity.

```text
☑️ 배경
* Epic 작성 시 장문·중복 설명이 반복됨

☑️ 목적
* 기존 Epic 템플릿에 개인 간결 작성 기준 적용

☑️ 기대효과
* 필요한 결과·조건을 항목별로 확인
- [roadmap:투자] 투자대상: ai-env 개인 문서 작성 규칙
- [roadmap:투자] 기대회수: 중복 설명·상세 절차의 반복 작성 감소
- [ta-productivity] 대상작업: Epic 본문 작성·현행화
- [ta-productivity] before_after: 미정
- [ta-productivity] 커버리지: 미정

☑️ 성공 기준
* 필수 헤더·rubric 검증 통과
* 개인 규칙·팀 원본 링크 동기화 확인

☑️ 완료보고
* 미완료 — 적용 후 검증 결과 기록

☑️ 관련 링크
* [개인 작성 규칙|https://github.com/glasslego/ai-env/blob/main/.claude/rules/wiki-jira-writing-style.md]
```

## 작성·읽기 범위

- 배경·목적은 각각 1~2개 핵심 항목부터 시작. 사실·결정에 필요한 경우만 확장.
- 목적은 직접 완료할 결과, 기대효과는 결과를 사용해서 생기는 변화로 구분.
- 성공 기준은 검수·데이터·운영 완료 조건. 구현 절차는 하위 Task/스펙으로 연결.
- 담당자·상태·일정은 Jira 필드 관리. rubric 필수 값은 예외로 유지.
- 일반 본문 수정에 원장·위클리·연관 후보·서빙 카탈로그 전체를 추가하지 않음.
- SKILL.md 전체를 상시 문서 컨텍스트에 복제하지 않음. 선택한 모드의 지침·CLI 도움말만 추가 확인.

## 조사 근거

- cde-skills `development/jira/references/epic-template.md`
- `development/epic-curator/scripts/epic_standard.py`: REQUIRED_SECTIONS, validate_structure, validate_description
- `scripts/ec_lint.py`: parse_rubric_bullets, coverage
- `scripts/epic_describe.py`: CANONICAL_HEADERS, render_description
- `references/share-item-format.md`: 공유 항목 2~3줄
- CDETEAM-207 라이브 rubric(source=jira)
