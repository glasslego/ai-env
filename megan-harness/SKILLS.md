# megan-harness 인덱스

> 각 스킬은 `skills/<category>/<name>/SKILL.md` 에 정의. 본 문서는 빠른 조회용.

## obsidian/ — vault 운영

| 스킬 | 트리거 | 상태 | 출처 |
|---|---|---|---|
| hot-context | `/hot`, "오늘 뭐 했지", "이어서 작업" | **shipped (P1)** | jackie/daily-hot-builder + AgriciDaniel/hot |
| distill | `/distill`, "이 세션 정리해줘" | **shipped (P1)** | jackie/distill |
| vault-lint | `/vault-lint`, "vault 점검" | **shipped (P1)** | jackie/vault-lint |
| auto-wikilink | "wikilink 후보 알려줘" | planned (post-P6) | jackie/auto-wikilink |
| auto-session-archive | `/archive` | planned (post-P6) | jackie/auto-session-archive |
| defuddle | "이 URL 정제해줘", "/defuddle" | **shipped (P5)** — pandoc fallback OK | kepano/defuddle |

## work/ — 업무 통합

| 스킬 | 트리거 | 상태 | 출처 |
|---|---|---|---|
| jira-task | `/jira <KEY>`, "지라 만들어/업데이트" | **shipped skeleton (P2)** — pull/push wiring P2.5 | jackie/jira-create + jira-update 통합 |
| wrap-up | `/wrap`, "오늘 정리하자" | **shipped (P2)** | jackie/wrap-up |

## data/ — 쿼리

| 스킬 | 트리거 | 상태 | 출처 |
|---|---|---|---|
| trino-query | `/trino`, "trino 쿼리" | **shipped (P3)** — cde-skills/data/trino 위임 | cde-skills 위임 |
| es-query | `/es`, "elasticsearch 조회" | **shipped (P3)** — cde-skills/data/elasticsearch 위임 | cde-skills 위임 |
| kafka-browse | `/kafka`, "토픽 목록", "consumer lag" | **shipped (P5.5)** — read-only | cde-skills/data/kafka 위임 |
| hadoop-yarn | `/yarn`, "yarn 앱", "RM 상태" | **shipped (P5.5)** — kill 차단 | cde-skills/data/hadoop 위임 |
| kdp-browse | `/kdp`, "데이터셋", "스키마", "row count" | **shipped (P5.6)** — read-only | cde-skills/data/kdp 위임 |
| query-manager | `/qm`, "production 검색", "lineage" | **shipped (P5.6)** — upload 차단 | cde-skills/data/query-manager 위임 |

## orchestration/ — 워크플로우

| 스킬 | 트리거 | 상태 | 출처 |
|---|---|---|---|
| airflow-ops | `/airflow`, "DAG 상태/트리거" | **shipped (P5.5)** — delete 차단 | cde-skills/orchestration/airflow 위임 |
| flink-ops | `/flink`, "flink job", "job 상태" | **shipped (P5.5)** — cancel 차단 | cde-skills/orchestration/flink 위임 |

## platform/ — 인프라

| 스킬 | 트리거 | 상태 | 출처 |
|---|---|---|---|
| grafana-board | `/grafana`, "대시보드", "monitoring" | **shipped (P5.5)** — import/sync 차단 | cde-skills/operations/grafana 위임 |
| k8s-ops | `/k8s`, "쿠버네티스", "pod 상태" | **shipped (P5.5)** — delete/exec 차단 | cde-skills/platform/kubernetes 위임 |
| oncall-respond | `/oncall`, "장애났어", "DAG fail" | **shipped (P5.6)** — 지식 가이드 + 진단 흐름 | cde-skills/operations/oncall (80+ 플레이북) |

## code/ — 코드 검증

| 스킬 | 트리거 | 상태 | 출처 |
|---|---|---|---|
| second-opinion | `/2nd`, "교차 검증" | **shipped (P4)** — codex CLI only | jackie/code-second-opinion |
| branch-guard | git push 직전 자동 + `/branch-guard` | **shipped (P4)** | jackie/branch-guard |
| pr-evaluator | `/pr-eval` | **shipped (P4)** — 7카테고리 sniff | jackie/pr-evaluator |
| spark-optimize | `/spark-opt`, "spark 최적화" | **shipped (P4)** — 정적 sniff | kamek-batch + cde-ranking-skills/spark-debug 가이드 |
| git-branch | `/branch CDE-XXXX`, "브랜치 만들어" | **shipped (P4.5)** — CDE/spec 컨벤션 | new (megan) |
| github-pr | `/pr`, "PR 만들어" | **shipped (P4.5)** — gh wrapper + 자동 본문 | new (megan) |
| run-tests | `/test`, "테스트 돌려" | **shipped (P4.5)** — profile/추론 기반 | new (megan) |

## meta/

| 스킬 | 트리거 | 상태 | 출처 |
|---|---|---|---|
| memory-hygiene | `/memory-clean` | planned (post-P6) | jackie/memory-hygiene |

## ai-env 자산 (개인 스킬 소스, megan-harness/skills/ai-env/)

| 스킬 | 위치 | 비고 |
|---|---|---|
| handoff-resume | `megan-harness/skills/ai-env/handoff-resume/` | cross-cwd 핸드오프 (SPEC-014) |
| spec-manager, task-implement, code-review, doc-sync | `megan-harness/skills/ai-env/<name>/` | workflow 핵심 |
| skill-creator, harness, python-env, spark-debug | `megan-harness/skills/ai-env/<name>/` | 메타/도메인 |

## cde-* 자산 (외부 참조, 재구현 금지)

| 묶음 | 스킬 |
|---|---|
| cde-skills | data, productivity, development, platform, operations, orchestration (각 meta-skill) |
| cde-ranking-skills | ranking-{lookup,cs,batch-job,data-verify}, score-drilldown, es-gift-ranking, service-onboard, feature-crud, spark-debug |
