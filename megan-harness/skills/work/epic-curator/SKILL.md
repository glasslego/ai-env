---
name: epic-curator
description: megan.won의 Jira Epic 작성·현행화. 짧은 6섹션 본문과 필요한 rubric만 작성하며 최신 cde-skills의 검증·API를 재사용한다. 트리거: 에픽 작성, 에픽 설명 수정, epic-curator.
---

# Epic Curator — megan.won

## 기준

- 개인 작성 규칙: `~/.codex/rules/wiki-jira-writing-style.md` 또는 `~/.claude/rules/wiki-jira-writing-style.md`.
- 이 진입점은 문서 표현과 읽는 범위를 줄인다. 팀의 API·필수 구조·rubric·검증을 대체하지 않는다.
- 팀 원본: `ai-env/cde-skills` 링크를 resolve한 저장소의 `plugins/cde-skills/skills/development/epic-curator/`.
- 프로젝트가 ai-env 밖이면 `~/work/cde/cde-skills`를 확인한다. 설치된 카테고리 링크는 `~/.codex/skills/development` 또는 `~/.claude/skills/development`다. 첫 유효 원본만 선택한다.
- 팀 CLI는 해당 저장소 `.venv/bin/python`으로 실행한다. 인증 로드는 팀 CLI에 맡기며 값은 출력하지 않는다.

## 일반 Epic 본문

1. 대상 Epic의 본문·필드·관련 근거를 읽는다. 사람 작성 내용과 인라인 근거를 보존한다.
2. 배경 / 목적 / 기대효과 / 성공 기준 / 완료보고 / 관련 링크의 6개 헤더를 유지한다.
3. 인바운드 describe는 8개 헤더를 유지한다. 기존 원장·공유 모드도 원래 구조를 유지하며 6섹션으로 바꾸지 않는다.
4. 핵심 사실은 짧은 항목, 조건은 하위 목록으로 쓴다. 구현 목록·상태·담당자·일정은 본문에 반복하지 않는다.
5. 실제 라벨의 rubric 필드는 모두 유지하고 값만 짧게 작성한다. `- [label] field: value`는 들여쓰기하지 않는다. 필수 값은 근거로 채우고 허용 필드만 미정으로 둔다.
6. `scripts/epic_standard.py --help`에서 선택한 명령을 확인한다. `apply --epic KEY --body-file FILE`로 dry-run 검증하고, fatal 판정이 없음을 확인한 뒤 팀 Jira CLI의 `update --description`으로 적용·재조회한다. 자동 원문 백업 댓글은 생성하지 않으며 필요한 백업은 로컬에 보관한다. 필수 구조·rubric 검증 실패는 고쳐서 다시 확인하며 우회하지 않는다.

## 작성 완료 기준: Epic 표준 검증

- Epic 문서를 작성·수정할 때는 최신 팀 기준으로 표준 검증을 통과하도록 작성한다. 간소화하더라도 필수 구조·라벨별 작성 기준·파서 표기를 유지한다.
- 일반 Epic은 6개 `☑️` 헤더와 순서, class·category 각 1개, 순위·관리 분기·Due date 정합성, 실제 라벨의 필수 값과 제목 규칙을 확인한다.
- `☑️ 관련 링크`에 실제 Agit 링크를 적는다. 공유 글이 없으면 `* 아지트: 없음 (과제 등록 단계, 공유 전)`처럼 표준 표기로 사실을 남긴다. `Agit: 미등록` 등 파서가 읽지 못하는 표현은 쓰지 않는다.
- 초안은 구조·필수 값 검증 후 적용하고, 저장 후 `epic_standard.py validate --epic KEY`로 재검증한다. fatal 오류는 수정하고 통과 전에는 표준 검증 완료로 보고하지 않는다.
- exit code만 보지 않고 제목·Agit·연관 후보 advisory도 확인한다. `declared_none`은 공유 전 사실 안내이며 형식 오류와 구분한다. 경고를 없애기 위해 근거·공유 완료를 만들지 않는다.
- 사용자 지정 상시 운영 Epic은 개인 예외 구조를 유지한다. 일반 Epic의 완료보고를 강제로 추가하지 않고, 예외 때문에 생기는 일반 검증 불일치는 명시한다.

## 완료보고·주간 보고 호환

- 일반 Epic의 완료보고 헤더는 정확히 `☑️ 완료보고`로 쓴다. Task는 `h2. 완료보고`로 쓴다. `완료 근거`·`구현 결과 및 검증`으로 이름을 바꾸지 않는다.
- 본문은 결과·영향 1항목 + 확인된 머지·운영 검증·공유 링크 + 필요한 미확인 범위만 짧게 쓴다. `TBD`·`미정`만 있는 완료보고는 완료 결과가 아니다.
- 적용 전후 팀 `epic_report._section(description, "완료보고")`가 의도한 절만 추출하는지 확인한다. 다음 헤더 전까지가 본문이며 코드·명령·전체 이력은 넣지 않는다.
- 형식 통과와 보고 대상 선정을 구분한다. `leader-report`는 Resolved Epic·원본 연결 이슈 반영일로 선별하고, `person`은 주간 상태전이를 Epic으로 롤업한다. Task 완료로 진행 중 Epic을 완료로 표시하지 않는다.
- 상시 운영 Epic(CDETEAM-160)은 완료보고를 생성하지 않는다. 하위 Task 결과는 개인 위클리의 진행 근거로 사용한다.
- 최종 위클리 항목은 팀 `share-item-format.md`의 헤더 + 2~3줄을 따른다. `label` 스타일은 배경·목표·기대효과 3줄이다. Jira 완료보고를 위클리 출력 양식으로 바꾸지 않는다.
- 예시·선별 조건: `references/completion-report.md`. 주간 수집 결과를 확인할 때만 팀 `epic_report.py person-collect` 또는 `collect`를 읽기 전용으로 실행한다.

## 조건부 상세

- 조사 결과·간결한 작성 예시: `references/template.md`. 예시는 실데이터로 바꾸며 적용 시 최신 팀 템플릿과 rubric을 확인한다.

- 6섹션·rubric 형식 확인: 팀 `../jira/references/epic-template.md`와 `references/label_rubric.md`만 읽는다.
- 기대효과/완료보고 한 절만 수정: `scripts/epic_effect.py --help`; 다른 절은 보존한다.
- 라벨·제목·원장·주간 보고 등 운영 요청: 팀 `_SKILL.md`의 해당 모드와 연결된 reference를 읽고 승인·적용·검증 규칙을 따른다.
- 일반 본문 수정에 ledger/describe/weekly/catalog 전수 실행을 붙이지 않는다.
