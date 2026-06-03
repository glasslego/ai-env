---
name: flink-ops
description: Flink job / cluster 상태 조회 (read-only). 사용자가 "/flink", "flink job", "플링크", "flink cluster", "job 상태" 를 말하면 트리거. 실제 호출은 cde-skills `orchestration/flink` 서브스킬에 위임. 본 wrapper 는 read-only — cancel/savepoint 차단.
---

# Flink Ops

> Origin: cde-skills/orchestration/flink. **재구현 금지** — read-only wrapper.

## When to invoke

- "flink job 돌고 있나", "running job 목록", "이 job 실패 사유"
- `/flink jobs`, `/flink cluster`, `/flink job-detail <jid>`

## 자주 쓰는 명령

```bash
~/.claude/skills/flink-ops/scripts/flink.sh cluster                  # 클러스터 정보
~/.claude/skills/flink-ops/scripts/flink.sh jobs                     # job 목록
~/.claude/skills/flink-ops/scripts/flink.sh job-detail <jid>          # job 상세
~/.claude/skills/flink-ops/scripts/flink.sh job-exceptions <jid>      # job 예외
# 환경 (prod/stage/dev):
~/.claude/skills/flink-ops/scripts/flink.sh --env stage jobs
# 옵시디언 저장:
~/.claude/skills/flink-ops/scripts/flink.sh job-detail abc123 --save flink-fail-debug
```

## 위임 경로

1. `~/.claude/skills/orchestration/flink/scripts/flink_{cluster,job}.py`
2. `~/work/glasslego/ai-env/cde-skills/skills/orchestration/flink/scripts/flink_{cluster,job}.py`

## 의존성 (.env)

- `FLINK_PROD_URL`, `FLINK_STAGE_URL`, `FLINK_DEV_URL`

## 안전

- 본 wrapper 는 cancel / savepoint / restart 명령을 차단 (read-only).
