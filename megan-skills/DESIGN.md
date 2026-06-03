# megan-skills 설계 문서

> ai-env 산하의 **개인 스킬 묶음**. 외부 팀 스킬(`cde-skills`, `cde-ranking-skills`,
> `jackie-skills`)과 외부 레퍼런스(`kepano/obsidian-skills`,
> `AgriciDaniel/claude-obsidian`)에서 핵심만 골라 megan 스타일로 재구성.

## 1. 원칙 (Why)

1. **개인 워크플로우 최적화** — 남이 만든 스킬은 트리거/경로/언어가 맞지 않아 매번
   미스 트리거되거나 컨텍스트 낭비를 일으킨다. 직접 큐레이션해 적중률을 높인다.
2. **Obsidian 중심 통합** — Obsidian vault(`~/Documents/Obsidian Vault`, 공백 포함)를
   업무 정리·Jira·git·세션 기록의 단일 substrate로 사용. ai-env의
   `session-save`(SPEC-013)·`handoff-resume`(SPEC-014) 자산을 베이스로 확장.

   Vault 디렉토리 매핑 (megan vault 컨벤션, 숫자 prefix dewey-style):
   - sessions → `90_journal/04_sessions/`
   - daily → `90_journal/01_daily/`
   - jira → `1X_업무카카오/jira/`
   - hot/lint report → `_meta/` (top-level)
   - jsonl archive → `99_archive/sessions/`

   이 매핑은 각 스킬 script 상단의 `DIRS` 상수 한 곳에 모여있어, vault 컨벤션이
   바뀌면 한 줄씩만 수정하면 된다.
3. **에이전트 범위는 Claude Code + Codex만** — Gemini는 웹으로만 사용. CLI 자산은
   `claude` / `codex` 두 길에서만 동작하면 된다.
4. **Trino-only SQL** — 모든 SQL 스킬은 Trino 기반 (Hive/Spark SQL은 케이스별).
5. **Spark 최적화는 외부 코드베이스 reference로 처리** — `kamek-batch`,
   `cde-ranking-skills/spark-debug` 의 git 을 직접 참조해 스킬에 임베드하지 않음.
6. **토큰 효율** — SKILL.md는 description+routing만 짧게, 본문은 lazy load
   (`_SKILL.md` 또는 `references/`로 분리). Defuddle 스타일 외부 컨텐츠 정제 채용.
7. **ai-env 비파괴** — 기존 `.claude/skills/`, `core/`, `cli/`는 그대로 두고
   megan-skills를 **추가 sync 소스**로 통합한다.

## 2. 출처별 채용/거부 매핑 (What from where)

### 2-1. cde-ranking-skills — **그대로 포함 (reference)**

도메인 특화 (랭킹·CDE 운영). 이미 잘 동작하므로 megan-skills에서 **재구현하지
않는다**. 대신:
- `lib/trino_client.py`, `lib/es_client.py` 는 megan-skills 의 데이터 스킬에서
  **import 만** 한다 (path lookup 으로 자동 해결).
- 스킬은 `cde-ranking-skills/` 그대로 ai-env sync에 포함되어 있으므로 추가 작업 불필요.

| 유지 스킬 | 비고 |
|---|---|
| ranking-lookup, ranking-cs, ranking-batch-job, ranking-data-verify | 도메인 운영 |
| score-drilldown, es-gift-ranking | 도메인 진단 |
| service-onboard, feature-crud | repo 작업 가이드 |
| spark-debug | spark 일반 진단 (megan-skills 의 `spark-optimize` 가 보강) |

### 2-2. cde-skills — **공통 플랫폼 부분만 외부 참조**

`cde-skills/skills/{data, productivity, development, platform, operations,
orchestration}` 는 잘 만들어진 meta-skill 묶음이다. **재구현 금지** —
ai-env sync 가 이미 ~/.claude/skills/ 에 배포한다. megan-skills 에서는 그
스킬들을 트리거하기 좋은 명칭으로 commands/ 에서 wrap만 한다.

| 외부 스킬 (그대로 사용) | megan command wrapper (선택) |
|---|---|
| `data` (trino, elasticsearch) | `/trino`, `/es` |
| `productivity` (wiki, google) | `/wiki`, `/sheet` |
| `development` (github, jira, plan-and-build) | `/jira`, `/gh` |
| `platform` (k8s, vault) | 필요 시 |
| `orchestration` (airflow) | 필요 시 |

### 2-3. jackie-skills — **선별 채용 (Obsidian + 코드 리뷰 + 워크플로우)**

| jackie 스킬 | megan 처리 | 이유 |
|---|---|---|
| daily-hot-builder | **이식**: `obsidian/hot-context` | hot.md 패턴은 핵심. AgriciDaniel 의 hot-cache 와 맞물림. |
| vault-lint | **이식**: `obsidian/vault-lint` | 고아·끊긴 wikilink 점검. 가벼운 Python 스크립트. |
| distill | **이식**: `obsidian/distill` | 토큰 효율적 트랜스크립트 압축. 핵심. |
| auto-wikilink | **이식**: `obsidian/auto-wikilink` | 노트 작성 시 자동 링크 후보 제시. |
| session-saver | **흡수**: ai-env `session-save` 확장 (SPEC-013 베이스) | ai-env 자산 우선. |
| auto-session-archive | **이식**: `obsidian/auto-session-archive` | jsonl raw archive → distill 큐. |
| jira-create, jira-update | **이식**: `work/jira-task` (단일 스킬로 통합) | Obsidian vault `jira/{KEY}.md` ↔ Jira API. |
| wrap-up | **이식**: `work/wrap-up` | 일일/세션 마무리. |
| pr-evaluator | **이식**: `code/pr-evaluator` | PR 평가 체크리스트. |
| code-second-opinion | **이식**: `code/second-opinion` | Codex CLI wrapper로만 (gemini 제외). |
| branch-guard | **이식**: `code/branch-guard` | force-push, main 직접 push 차단. |
| memory-hygiene | **이식**: `meta/memory-hygiene` | auto-memory 노이즈 정리. |
| harness-engineering | **거부**: ai-env `harness` 가 이미 존재 | 중복. |
| auto-approve-readonly-ops | **거부**: ai-env `update-config` + settings.json 권장 | 메커니즘 불일치. |

### 2-4. ai-env 기존 자산 — **그대로 유지**

| 카테고리 | 스킬 |
|---|---|
| Workflow | research, spec-manager, task-implement, code-review, doc-sync |
| Session | session-save (Obsidian 저장), handoff-resume (cross-cwd) |
| Build | python-env, harness, skill-creator, spark-debug |
| Sync | ai-env-sync, add-mcp, token-rotate |
| Phases | wf-init, wf-research, wf-spec, wf-code, wf-review, wf-run |

`/handoff`, `/commit`, `/setup`, `/workflow` 등 commands 는 모두 유지.

### 2-5. 외부 레퍼런스 (kepano + AgriciDaniel) — **패턴 차용**

| 레퍼런스 | 차용 패턴 |
|---|---|
| kepano/obsidian-skills | (a) SKILL.md 명세 준수 → Codex/Claude 양쪽 호환. (b) **Defuddle** 류 토큰 절감 정제 — `obsidian/defuddle` 채용. (c) `obsidian-bases` 를 reference 로만 메모 (Bases 사용 시점에 추가). |
| AgriciDaniel/claude-obsidian | (a) `wiki/{index, log, hot, overview}` 메타 파일 구조. (b) hooks/ 의 SessionStart 에서 `hot.md` 자동 갱신. (c) `/save`, `/autoresearch` 컨셉 — ai-env 의 wf-research 와 통합. (d) Wiki 모드(Personal/Research/Business) 는 이번 단계에서는 **거부** (과한 추상화). |

## 3. 디렉토리 구조

```
megan-skills/
├── README.md                   설치/사용법
├── DESIGN.md                   본 문서
├── SKILLS.md                   스킬 인덱스 (자동 갱신 가능)
├── lib/                        공유 Python (필요 시점에 채움)
│   ├── obsidian.py             vault 경로 해석, hot.md helper, wikilink helper
│   └── trino_proxy.py          cde-ranking-skills/lib/trino_client 재사용 wrapper
├── skills/
│   ├── obsidian/
│   │   ├── hot-context/        SessionStart hot.md 갱신
│   │   ├── distill/            jsonl/긴 텍스트 → vault note 압축
│   │   ├── vault-lint/         vault 자가 점검
│   │   ├── auto-wikilink/      노트 작성 시 wikilink 후보 제시
│   │   ├── auto-session-archive/ raw jsonl → distill 큐
│   │   └── defuddle/           웹페이지 → 정제 markdown
│   ├── work/
│   │   ├── jira-task/          Jira ↔ vault/jira/{KEY}.md 양방향
│   │   └── wrap-up/            일일/세션 wrap-up → daily/{date}.md
│   ├── data/
│   │   ├── trino-query/        Trino SQL (cde-ranking-skills lib 재사용)
│   │   └── es-query/           Elasticsearch (cde-ranking-skills lib 재사용)
│   ├── code/
│   │   ├── second-opinion/     Codex CLI wrapper (gemini 제외)
│   │   ├── branch-guard/       force-push / main push 가드
│   │   ├── pr-evaluator/       PR 평가 체크리스트
│   │   └── spark-optimize/     kamek-batch / cde-ranking 의 spark 패턴 가이드
│   └── meta/
│       └── memory-hygiene/     ~/.claude/.../memory/ 정리
├── commands/                   슬래시 명령 (스킬 trigger wrapper)
│   ├── hot.md                  /hot — obsidian/hot-context 호출
│   ├── distill.md              /distill — obsidian/distill 호출
│   ├── vault-lint.md           /vault-lint
│   ├── jira.md                 /jira <KEY> — work/jira-task
│   ├── wrap.md                 /wrap — work/wrap-up
│   ├── trino.md                /trino "<SQL>" — data/trino-query
│   ├── 2nd.md                  /2nd — code/second-opinion
│   └── pr-eval.md              /pr-eval — code/pr-evaluator
├── hooks/
│   └── session_start_hot.sh    cwd 가 vault 와 무관해도 hot.md 가 12h+ 오래되면 갱신
└── docs/
    ├── INTEGRATION.md          ai-env sync 와의 결합 방식
    └── COMPARISON.md           kepano vs AgriciDaniel vs jackie vs megan 차이
```

## 4. ai-env 통합 전략

### 4-1. sync 소스로 등록

ai-env 의 `core/sync.py` 는 personal(`.claude/skills/*`) + team(`cde-*skills/*`)
두 카테고리만 안다. megan-skills 는 **third 카테고리("own")** 로 별도 추가 대신,
간단히 personal 로 취급한다:

- 옵션 A (권장, 빠름): `megan-skills/skills/<name>` → `.claude/skills/<name>` 심링크
  - `cde-*skills` 가 git submodule 인 점과 대칭. ai-env sync 변경 거의 없음.
- 옵션 B: ai-env `core/sync.py` 에 `megan_skills_root` 설정 추가하고 personal과
  병합. (다음 spec 으로 분리)

이번 단계는 **옵션 A** 로 진행하고, 잘 굳어지면 옵션 B 로 승격.

### 4-2. project-profile.yaml 노출

`.claude/project-profile.yaml` 의 skills 인덱스에 megan-skills/SKILLS.md 를
추가하여 다른 프로젝트에서 ai-env 를 참조할 때도 megan 스킬을 자동 인식.

### 4-3. SPEC 추적

megan-skills 도입은 ai-env 입장에서 **SPEC-015** (가칭) 후보. 현재는 docs/
플레이스홀더로만 두고, 안정화 후 specs/ 로 승격.

## 5. Phase 작업 순서

| Phase | 산출물 | 차단 의존성 |
|---|---|---|
| 0 — 계획 | DESIGN.md, README.md, SKILLS.md, 빈 디렉토리 | 없음 |
| 1 — Obsidian core | hot-context, vault-lint, distill | Phase 0 |
| 2 — Work | jira-task, wrap-up | Phase 1 (vault helper lib) |
| 3 — Data | trino-query, es-query (lib import) | Phase 0 (lib/ 위치만 결정) |
| 4 — Code | second-opinion, branch-guard, pr-evaluator | Phase 0 |
| 4.5 — Workflow | git-branch, github-pr, run-tests | Phase 4 |
| 5 — Defuddle / autoresearch | obsidian/defuddle, autoresearch | Phase 1 |
| 6 — ai-env sync 통합 | ALWAYS_TEAM_SKILLS + own skills 자동 수집 + 3타겟 배포 | Phase 1~5 일부 |
| 7 — Repo 운영 (확정) | **ai-env 모노레포 유지** — 별도 repo 분리 안 함 | — |

**Phase 7 결정 (2026-05-06)**: megan-skills 는 ai-env 안에서 함께 운영. 이유: (1) 잦은 수정 사이클 — 분리 시 두 repo 동기화 부담, (2) cde-* lib 참조가 ai-env 경로에 자연스럽게 묶임, (3) 카카오 내부 vault/jira 컨벤션이 스킬에 묻어있어 sanitize 비용. 향후 안정화되면 `git subtree split` 으로 언제든 분리 가능 (현재 비용 0).

각 Phase 는 독립 커밋. spec-task 컨벤션을 따름:
`feat(megan-skills/<phase>): <summary>`.

## 6. 토큰 효율 정책

- SKILL.md 본문은 100줄 이내. 상세는 `references/<topic>.md` 로 분리.
- 외부 페이지 인용은 `obsidian/defuddle` 로 정제 후 vault 저장 → 이후 vault 만 참조.
- SessionStart 시 hot.md 자동 갱신은 **Claude Code 만 적용** (Codex 는 hook 미지원이므로 수동 `/hot` 권장).
- `claude -p` headless 모드를 distill 등에서 활용해 메인 컨텍스트 오염 방지.

## 7. 명시적 비채택 (Out of scope)

- Gemini CLI 통합 (웹으로만 사용)
- AgriciDaniel 의 6 wiki modes 추상화
- jackie 의 harness-engineering / auto-approve-readonly-ops
- Spark 최적화 스킬 안에 코드 임베드 (외부 git 참조만)
- megan-skills 자체 git push (이번 단계는 ai-env 안 로컬만)

## 8. 다음 액션

1. README.md, SKILLS.md 작성 (Phase 0 마무리)
2. Phase 1 시작: `obsidian/hot-context` 부터 — hot.md 가 모든 후속 스킬의 입력
3. ai-env sync 심링크 (옵션 A) 는 Phase 1 직후
