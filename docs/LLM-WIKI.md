# 문서 작업과 LLM Wiki

문서를 작성하기 전에 기존 이해를 검색하고, 완성한 Markdown을 출처로 등록한다.
등록된 근거가 결론을 바꾸면 에이전트가 관련 종합 페이지를 갱신한다.

## 사용

```bash
# 다른 프로젝트에서도 같은 CLI 사용
uv run --directory /Users/megan/work/glasslego/ai-env ai-env wiki search "배치 성능 정합성" --limit 3
uv run --directory /Users/megan/work/glasslego/ai-env ai-env wiki register /absolute/path/design.md --dry-run
uv run --directory /Users/megan/work/glasslego/ai-env ai-env wiki register /absolute/path/design.md
```

- Vault 선택: `wiki --vault "경로"` → `OBSIDIAN_BASE` → `~/Documents/Obsidian Vault`.
- 반환값은 JSON이다. 조회는 읽기 전용, dry-run은 파일을 생성하지 않는다.
- 한글·영문 키워드의 부분 일치를 사용한다. 여러 단어 중 일부만 일치한 후보도 나온다.
- 검색 결과는 경로·제목·종류·검토 상태·일치 점수·본문 발췌를 제공한다. 결과의 원문을 읽어 관련성과 근거를 확인한다.
- 전체 Vault 의미 검색은 아니다. `wiki/`의 `synthesis` 페이지와 명시적으로 등록한 출처만 검색한다.
- 결과가 부족하면 기존 MOC·원본 검색으로 보완한다.

## 문서 작업에서의 자동 실행

- 공용 규칙: `.claude/rules/llm-wiki-workflow.md`.
- 글로벌 CLAUDE·Codex AGENTS에서 규칙을 안내하고, 기존 sync가 양쪽 rules를 배포한다.
- distill·session-curator도 같은 절차를 따른다.
- 에이전트가 문서 작업 중 CLI를 실행하는 방식이다. 단순 파일 저장 이벤트를 감시하는 기능은 아니다.
- 등록 CLI가 요약·종합 문장을 자동 생성하지 않는다. 에이전트가 근거를 읽고 관련 종합 최대 3개에 반영한다.
- 지침·템플릿·단순 링크 수정은 등록하지 않는다. 검색·등록에 실패하면 실패 사실과 문서 저장 결과를 구분한다.

## 저장 계약

| 대상 | 등록 동작 |
|---|---|
| Vault 내부 원본 | 원본 경로·내용 해시 등록. 복사·수정 없음 |
| Vault 작업 기록 `00_session/agent-logs/` | gzip 보관으로 본문이 바뀌므로 외부 문서처럼 스냅샷 저장 |
| 외부 Markdown | `00_inbox/llm-wiki/<SHA-256>.md`에 내용별 스냅샷 저장 |
| 같은 경로·같은 내용 | `unchanged`. 레지스트리·스냅샷 갱신 없음 |
| 원본 내용 변경 | 새 해시 등록. 외부 문서의 이전 스냅샷 보존 |
| 종합·메타·스냅샷 자체 | `skipped`. 재등록에 따른 자기 증식 방지 |
| 개인·투자 폴더 원본 | 기본 차단. 사용자가 지정한 문서에 `--allow-private` 사용 가능. 기본 검색 제외 |

- 저장소: `_meta/llm-wiki-registry.json`. 원본 절대 경로별 최신 등록을 기록한다.
- macOS/Linux 파일 잠금과 원자적 교체로 동시 등록 손실을 방지한다.
- 경로 이탈·손상된 레지스트리·외부 스냅샷 변조는 오류로 처리한다.
- Vault 내부 원본이 등록 후 바뀌면 검색 상태가 `source_changed`다. 원본을 재확인하고 재등록한다.
- UTF-8 Markdown만 처리하며 파일당 최대 2 MiB다. PDF·원격 URL은 직접 등록하지 않는다.

## Vault 규칙과 작업 기록

- Vault 작업 전 Vault `AGENTS.md`, `wiki/index.md`, `wiki/운영 가이드.md`를 읽는다. 종합 절차·상태 전환의 정본은 운영 가이드다.
- 공용 작업 기록 중 work·review·fix 완료 보고만 ingest 후보다. checkpoint·summary는 자동 발췌라 출처로 등록하지 않는다.
- 작업 기록 frontmatter는 Vault 온톨로지(`note_type: log`, `entity_type: evidence`, `status: reference|archived`)를 따른다.

## 종합에 연결하기

1. 등록 응답의 `related_pages`에서 관련 종합을 읽는다. 후보는 제목 키워드 기반이므로 관련성을 직접 판단한다.
2. 사실과 AI 해석을 구분해 새 결론·반증·적용 범위 변화만 반영한다.
3. `source`에는 `snapshot`의 확장자를 뺀 Vault 상대 위키링크를 기록한다.
4. 해시는 코드가 등록부에 저장한다. 종합 노트에 수동 해시 필드를 추가하지 않는다.
5. 새 근거가 이전 스냅샷을 대체하면 현재 출처를 바꾸고 이전 근거는 로그에 남긴다.
6. 인덱스·로그·`synthesized_at`을 함께 갱신한다. 검토와 상태 전환은 Vault 운영 가이드의 최신 규칙을 따른다.

원본·직접 작성한 해석은 보존한다. `2026_경력관리/`는 종합 작업에서 수정하지 않는다.
등록 성공은 종합 완료와 다르다. 사용자 검토도 AI가 대신 완료 표시하지 않는다.

## 배포와 검증

- 일반 배포: `uv run ai-env sync --claude-only` (Claude·Codex 포함).
- 규칙을 수정할 때는 ai-env 정본을 수정하고 배포한다.
- 테스트: `uv run pytest tests/core/test_wiki_documents.py tests/cli/test_wiki_cmd.py --no-cov`.
- 계약: [SPEC-016](../specs/SPEC-016-llm-wiki-document-workflow.md).
