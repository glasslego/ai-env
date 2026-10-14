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
6. `scripts/epic_standard.py --help`에서 선택한 명령을 확인한다. `apply --epic KEY --body-file FILE`로 dry-run 검증하고, 사용자가 요청한 쓰기 범위에서 `--apply` 후 본문을 재조회한다. 필수 구조·rubric 검증 실패는 고쳐서 다시 확인하며 우회하지 않는다.

## 조건부 상세

- 조사 결과·간결한 작성 예시: `references/template.md`. 예시는 실데이터로 바꾸며 적용 시 최신 팀 템플릿과 rubric을 확인한다.

- 6섹션·rubric 형식 확인: 팀 `../jira/references/epic-template.md`와 `references/label_rubric.md`만 읽는다.
- 기대효과/완료보고 한 절만 수정: `scripts/epic_effect.py --help`; 다른 절은 보존한다.
- 라벨·제목·원장·주간 보고 등 운영 요청: 팀 `_SKILL.md`의 해당 모드와 연결된 reference를 읽고 승인·적용·검증 규칙을 따른다.
- 일반 본문 수정에 ledger/describe/weekly/catalog 전수 실행을 붙이지 않는다.
