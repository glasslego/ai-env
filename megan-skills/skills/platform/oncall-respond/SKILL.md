---
name: oncall-respond
description: CDE 팀 온콜 장애 대응 가이드. 사용자가 "/oncall", "온콜", "장애 대응", "DAG 실패", "장애났어", "incident", "서비스 다운" 을 말하면 트리거. cde-skills `operations/oncall/references/guide.md` (80+ 플레이북, 722줄) 을 정합 참조 + megan 의 airflow-ops/k8s-ops/grafana-board wrapper 들로 진단 흐름 가이드.
---

# Oncall Respond

> Origin: cde-skills/operations/oncall (CDE-613 에픽 80+ 사례 + 20개 위키 문서 정리).
> **본 스킬은 지식 가이드** — 실제 진단 명령은 megan 의 다른 wrapper 로 위임.

## When to invoke

- "장애났어", "DAG fail", "이 서비스 다운"
- `/oncall`, `/oncall airflow`, `/oncall k8s`
- 알림이 슬랙/카카오워크/Watchtower 로 들어왔을 때

## 진단 흐름 (megan 표준)

```
1) 증상 수집 (사용자 메시지 + 알림 캡쳐)
        ↓
2) 영향 범위 파악
   - DAG/task    → /airflow runs my-dag-id
   - K8s pod     → /k8s pods -n my-ns
   - Flink job   → /flink jobs
   - Kafka lag   → /kafka topic-describe -t my-topic
   - YARN app    → /yarn apps --state FAILED
        ↓
3) 플레이북 검색
   - 가이드 위치: ~/.claude/skills/operations/oncall/references/guide.md
   - 카테고리: Airflow / Flink / K8s / 데이터 정합성 / 외부 의존
        ↓
4) 조치
   - 재실행 (idempotent 한지 검토 후)
   - hotfix 브랜치 → /branch + /pr
   - jira 이슈 자동 생성/업데이트 → /jira
        ↓
5) 사후 처리
   - jira 댓글에 RCA 정리
   - guide.md 에 신규 사례 추가 검토
```

## 빠른 액션 셀프 매뉴얼

| 증상 | megan 명령 |
|---|---|
| DAG task 가 fail | `/airflow runs <dag>` → `/airflow task <dag> <task>` (로그) |
| pod CrashLoop | `/k8s observe -n <ns> <pod>` (events + describe) |
| Flink job exceptions | `/flink job-exceptions <jid>` |
| Kafka lag | `/kafka topic-describe -t <topic>` (consumer offsets) |
| YARN app failed | `/yarn app-detail <appid>` |
| 모니터 보드 확인 | `/grafana search "<service>"` → `/grafana open <slug>` |

## 가이드 검색 (직접)

```bash
# 키워드로 플레이북 검색
~/.claude/skills/oncall-respond/scripts/playbook.sh "Iceberg 컬럼 삭제"
~/.claude/skills/oncall-respond/scripts/playbook.sh DELTA
# 카테고리만 보기
~/.claude/skills/oncall-respond/scripts/playbook.sh --list
```

## 의존성

- megan wrappers: airflow-ops, flink-ops, kafka-browse, hadoop-yarn, k8s-ops, grafana-board
- cde-skills/operations/oncall/references/guide.md (80+ 플레이북)
- jira-task (이슈 생성/업데이트), branch-guard/git-branch/github-pr (hotfix flow)
- (선택) prometheus, watchtower, kakaowork — cde-skills 서브스킬 직접 호출

## 안전

- 본 wrapper 는 자동 조치를 수행하지 않음 — 진단 + 가이드 제시만.
- 재실행 / 데이터 backfill 등 mutating 조치는 사용자 명시 confirm 후 megan 의 다른 스킬로 진행.
- 운영 reset (DELETE/TRUNCATE 등) 은 cde-skills 서브스킬 직접 호출 + --confirm 으로만.
