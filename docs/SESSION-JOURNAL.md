# Claude·Codex 공용 작업 기록

작업과 교차 리뷰를 복사하지 않고 이어가면서, Obsidian에서 날짜·프로젝트별 이력을 찾는다.
코드·규칙은 ai-env가 관리하고, 실행 결과는 Vault의 Markdown에 저장한다.

## 저장 위치와 파일명

기본 경로:

```text
~/Documents/Obsidian Vault/00_session/<저장소명>/agent-logs/
```

- `OBSIDIAN_BASE`가 있으면 해당 Vault를 사용한다.
- Vault가 없으면 `~/.ai-env/session-logs/`. 다른 위치는 `AI_ENV_SESSION_LOG_DIR` 또는 `session --root`로 지정한다.
- 기존 세션 노트와 같은 저장소 폴더를 쓴다. Jira별 worktree도 메인 저장소 폴더에 모이며 브랜치·Jira는 파일명·frontmatter(`cwd`, `branch`)로 구분한다.
- 이름만 같은 다른 저장소는 `<저장소명>-<경로해시>/agent-logs/`로 분리한다. 폴더 소유는 숨김 파일 `.repository`에 기록한다.
- 분류는 `kakao / personal / unclassified`. 내용이나 경로로 업무·개인을 추측하지 않는다.
- 파일·압축본은 0600, 프로젝트 기록 폴더는 0700. Vault의 동기화·공유 정책은 그대로 적용된다.
- 현재 ai-env는 personal로 설정했다. 다른 프로젝트는 `.claude/project-profile.yaml`에 다음을 추가한다.

```yaml
project:
  session_scope: kakao
```

```text
도구__분류__프로젝트__유형__[work의 Jira/브랜치]__KST시각__ID__주제요약.md

codex__personal__ai-env__work__main__20261029T183000__a1b2c3d4e5f6a7b8__세션로그-자동기록.md
claude__kakao__kamek-batch__work__CDETEAM-1234__20261029T184000__b2c3d4e5f6a7b8c9__피처집계-개선.md
claude__kakao__kamek-batch__review__20261029T185000__c3d4e5f6a7b8c9d0__집계로직-검토.md
```

- Jira 키와 브랜치가 같으면 파일명에서 중복하지 않는다. 다르면 둘 다 표시한다.
- 본문 frontmatter에는 Jira·브랜치·HEAD·Spec/Task·도구·상태·세션/turn ID·원본 parent를 저장한다.
- Vault 온톨로지 필드: `note_type: log`, `entity_type: evidence`, `status: reference`(gzip 보관 후 `archived`).
  기록 상태(`--status`)는 `report_status`, parent는 원본 기록 위키링크(`[[파일명]]`)다.
- 주제는 `--title`로 명시한다. 자동 checkpoint는 요청 첫 유효 줄, 없으면 최종 답변 첫 줄을 사용한다.
- 경로 구분자와 위험한 문자는 정리하고 한글 UTF-8 바이트 길이를 제한한다.

## 기록 시점

| 시점 | 기록 | 의미 |
|---|---|---|
| 하나의 사용자 지시 완료 | work / review / fix | 에이전트가 변경·검증·TODO를 정리한 보고 |
| 응답 종료 Stop | checkpoint / stopped | 요청과 최종 답변의 자동 안전망. 성공 판정 아님 |
| 세션 종료 SessionEnd | summary | 해당 도구·세션의 작업 목록·짧은 발췌·원문 링크. 재개한 세션은 직전 요약 이후 기록만 묶는다 |
| 7일 지난 기록, 다음 SessionEnd | 날짜별 summary + gzip | 도구와 무관하게 날짜당 1개. 요약 후 원문 압축 검증, 긴 Markdown 본문 정리 |

- Stop은 질문·막힘·부분 완료 때도 실행될 수 있다. 이를 완료 이력과 구분한다.
- 의미 기반 요약은 에이전트가 지시 완료 보고를 작성할 때 한다. 자동 summary는 메타데이터와
  보고 앞부분 최대 400자의 발췌로 만들며 새로운 판단이나 테스트 결과를 생성하지 않는다.
- background timer나 별도 LLM은 없다. 7일 기준 정리는 현재 프로젝트의 다음 종료 이벤트에서 실행된다.
- 세션 종료 훅이 없거나 강제 종료되면 요약이 생기지 않을 수 있다. CLI로 다시 실행할 수 있다.
- 요약이 끝난 날짜는 원문을 다시 읽지 않는다. 기록 hook 제한 시간은 Claude·Codex 모두 30초다.
- 기록 디렉터리의 frontmatter가 없는 일반 Obsidian 노트는 조회·정리에서 건너뛴다.

## 완료 보고와 교차 리뷰

현재 셸이 프로젝트 루트라면:

```bash
uv run --directory /Users/megan/work/glasslego/ai-env ai-env session --project "$PWD" list
```

작업 보고를 임시 Markdown에 작성하고 저장한다. 보고에는 Spec/Task, 구현, 실행한 검증과 결과,
미해결/TODO, 다음 리뷰 포인트를 적는다. 환경변수·비밀키·내부 추론은 넣지 않는다.

```bash
uv run --directory /Users/megan/work/glasslego/ai-env ai-env session --project "$PWD" record \
  --agent codex --kind work --scope personal \
  --task SPEC-017/TASK-01 --title "공용 세션로그 자동기록" \
  --status needs-review --body-file /tmp/work-report.md
```

Jira가 브랜치와 다르거나 추출되지 않으면 `--jira CDETEAM-1234`를 명시한다.
브랜치와 HEAD는 현재 프로젝트 Git에서 읽으며, Jira API 호출은 하지 않는다.

Claude에서 같은 task의 원문과 현재 diff를 확인하고 리뷰를 저장한다.

```bash
uv run --directory /Users/megan/work/glasslego/ai-env ai-env session --project "$PWD" list \
  --agent codex --task SPEC-017/TASK-01 --kind work

uv run --directory /Users/megan/work/glasslego/ai-env ai-env session --project "$PWD" record \
  --agent claude --kind review --task SPEC-017/TASK-01 \
  --title "공용 세션로그 검토" --status changes-requested \
  --parent "/absolute/path/to/codex-record.md" --body-file /tmp/review-report.md
```

- Codex가 지적을 반영하면 `--kind fix --parent "Claude 리뷰 경로"`로 연결한다.
- parent는 같은 프로젝트의 실제 기록만 허용한다. 확인하지 않은 “가장 최신 기록”을 자동 승인하지 않는다.
- recorded는 저장 완료, needs-review는 검토 대기, changes-requested는 수정 요청이다.
  approved는 실제 리뷰 결론으로만 명시하며 프로그램이 자동 부여하지 않는다.
- 사람의 복붙은 필요 없지만, 두 에이전트를 자동 실행하거나 무한히 교차 리뷰하지는 않는다.
- 동일 세션/turn/내용의 hook 재전달은 멱등하다. 별도 수동 보고는 새 기록이며 명시적 ID로 재전달을 구분할 수 있다.

## 압축과 원문 확인

```bash
# 미리보기: 기록 파일을 쓰거나 바꾸지 않는다.
uv run ai-env session compact --older-than-days 7 --archive --dry-run

# 현재 프로젝트의 오래된 기록을 날짜별 요약 + gzip으로 정리한다.
uv run ai-env session compact --older-than-days 7 --archive

# 특정 세션의 요약만 즉시 만든다. 최근 원문은 그대로 둔다.
uv run ai-env session compact --session-id SESSION_ID --agent codex

# 특정 세션을 7일 기다리지 않고 바로 요약·gzip 보관한다.
uv run ai-env session compact --session-id SESSION_ID --agent codex --archive

# 안내 노트 경로로 압축 전 원문도 볼 수 있다.
uv run ai-env session show "/absolute/path/to/record.md"
```

1. summary를 먼저 저장한다. summary 자체를 다시 요약 대상에 넣지 않는다.
2. `_archive/<원래파일명>.md.gz`에 원문 전체를 gzip으로 저장한다.
3. 디스크에서 다시 읽고 압축 해제 결과가 원문과 동일한지 검증한다.
4. 검증이 통과한 뒤에만 기존 Markdown 본문을 짧은 안내·압축본 링크로 교체한다.
5. 안내 노트는 같은 경로·ID·메타데이터를 유지하므로 기존 Obsidian 링크와 parent 참조가 유지된다.

압축본이 손상되거나 기존 압축본이 다르면 원문을 교체하지 않는다. 재실행은 같은 내용을 중복 보관하지 않는다.
`show`는 원문 SHA-256도 검증한다. 요약만 남기고 복구 불가능하게 원문을 버리는 방식은 사용하지 않는다.
압축본과 새 summary는 남으므로 저장 공간이 완전히 없어지는 것은 아니다.

## 자동 기록 설치·한계

- source: `.claude/hooks/session_journal.sh`, Claude settings 템플릿 두 개, Codex `_codex_hooks_json()`.
- Claude와 Codex 모두 SessionStart / UserPromptSubmit / Stop / SessionEnd에 recorder를 연결한다.
- hook은 안정적인 `prompt`·`last_assistant_message`를 사용한다. 비공개 transcript 포맷은 파싱하지 않는다.
- 요청 임시 상태는 `~/.ai-env/session-state/`에 두고, Vault에는 읽을 Markdown과 gzip만 남긴다.
  SessionEnd에서 해당 세션 상태와 7일 넘게 갱신되지 않은 상태 파일을 지운다.
- 기존 SessionEnd 핸드오프·cmux 알림·보안 훅을 유지한다.
- Codex는 새 hook 정의를 신뢰하기 전 실행하지 않는다. CLI의 `/hooks`에서 recorder 항목을 확인하고 신뢰한다.
  자동으로 trusted_hash를 쓰거나 보안 검사를 우회하지 않는다. 실행 중 채팅은 재시작해야 설정이 반영될 수 있다.
- hook 실행 실패·최종 답변 누락은 systemMessage로 알린다. 이 경우 완료 보고 CLI로 기록한다.
- 알려진 token/password/Bearer 표기는 마스킹하지만 모든 비밀·개인정보를 탐지하는 것은 아니다.
- 원문 transcript 전체, 도구 결과, 환경변수, 내부 추론은 수집하지 않는다. 장문은 24,000자에서 잘림 표시를 남긴다.
- 매 checkpoint를 LLM Wiki에 등록하지 않는다. 재사용할 설계·기술 문서는 기존 Wiki 워크플로우로 별도 등록한다.

공식 근거: [Codex Hooks](https://learn.chatgpt.com/docs/hooks), [Claude Code Hooks](https://code.claude.com/docs/en/hooks).
공식 문서 확인일: 2026-10-29. 설치된 Codex CLI: 0.162.1.
