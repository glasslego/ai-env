---
name: airflow-ops
description: Airflow DAG/Task 운영 명령 (list/get/trigger/pause/runs). 사용자가 "/airflow", "에어플로우", "DAG 상태", "DAG 트리거", "airflow runs", "DAG 멈춰" 를 말하면 트리거. 실제 호출은 cde-skills `orchestration/airflow` 서브스킬에 위임. megan 부가가치: ① Korean 트리거, ② --env prod/stage shortcut, ③ 결과를 옵시디언 노트로 저장 옵션.
---

# Airflow Ops

> Origin: cde-skills/orchestration/airflow. **재구현 금지** — wrapper 만 제공.
> Airflow v2/v3 차이: v3 는 별도 메타-스킬 (`cde-skills/orchestration/airflow-v3`).

## When to invoke

- "DAG 상태", "DAG 목록", "DAG 트리거", "DAG 일시정지"
- `/airflow list`, `/airflow trigger my-dag`, `/airflow runs my-dag`
- task 단위 조회 ("이 task 가 왜 실패?")
- backfill 검토 (단, 실행은 v3 또는 별도 검토 후)

## 자주 쓰는 명령

```bash
~/.claude/skills/airflow-ops/scripts/airflow.sh list                    # DAG 전체 목록
~/.claude/skills/airflow-ops/scripts/airflow.sh details my-dag-id        # DAG 상세
~/.claude/skills/airflow-ops/scripts/airflow.sh runs my-dag-id           # 최근 실행
~/.claude/skills/airflow-ops/scripts/airflow.sh trigger my-dag-id        # 수동 트리거
~/.claude/skills/airflow-ops/scripts/airflow.sh pause my-dag-id          # 일시정지
~/.claude/skills/airflow-ops/scripts/airflow.sh task my-dag-id my-task-id  # task 상세
# 환경 (기본 prod):
~/.claude/skills/airflow-ops/scripts/airflow.sh --env stage runs my-dag-id
# 결과를 옵시디언 노트로 저장:
~/.claude/skills/airflow-ops/scripts/airflow.sh runs my-dag-id --save dag-failure-2026-05-06
```

## 위임 경로

스크립트는 다음 후보에서 cde-skills airflow 모듈을 찾는다:

1. `~/.claude/skills/orchestration/airflow/scripts/airflow_{dag,task}.py`
2. `~/work/glasslego/ai-env/cde-skills/skills/orchestration/airflow/scripts/airflow_{dag,task}.py`

찾지 못하면 안내 후 종료.

## 의존성 (.env)

- `AIRFLOW_USERNAME`, `AIRFLOW_PASSWORD` — Airflow 웹 UI 자격
- (선택) `AIRFLOW_DAGS_REPO_URL` — DAG 코드 위치

## 안전

- `delete`, `delete-run`, `update-state` 같은 파괴적 명령은 본 wrapper 가 자동 차단.
  필요시 cde-skills 서브스킬 직접 호출 + `--confirm` 플래그.
- 본 wrapper 는 read + trigger + pause 만 노출.
