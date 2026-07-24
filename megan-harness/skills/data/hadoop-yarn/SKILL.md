---
name: hadoop-yarn
description: Hadoop YARN apps / nodes / queues 조회 (read-only). 사용자가 "/yarn", "/hadoop", "yarn 앱", "리소스매니저", "RM 상태", "queue 상태" 를 말하면 트리거. 실제 호출은 cde-skills `data/hadoop` 서브스킬에 위임. kill 명령은 차단 (cde-skills 직접 호출 + --confirm 사용).
---

# Hadoop YARN

> Origin: cde-skills/data/hadoop. **재구현 금지** — read-only wrapper.

## When to invoke

- "이 application 이 왜 fail?", "yarn app 상태"
- "RM 노드 살아있나", "queue 사용량"
- `/yarn apps`, `/yarn app-detail <appid>`

## 자주 쓰는 명령

```bash
~/.claude/skills/hadoop-yarn/scripts/yarn.sh apps                       # 앱 목록 (RUNNING)
~/.claude/skills/hadoop-yarn/scripts/yarn.sh apps --state FAILED         # 실패만
~/.claude/skills/hadoop-yarn/scripts/yarn.sh app-detail application_xxx  # 앱 상세
~/.claude/skills/hadoop-yarn/scripts/yarn.sh nodes                       # RM 노드
~/.claude/skills/hadoop-yarn/scripts/yarn.sh queues                      # queue 사용량
~/.claude/skills/hadoop-yarn/scripts/yarn.sh apps --save yarn-fail-2026-05-06
```

## 위임 경로

1. `~/.claude/skills/data/hadoop/scripts/hadoop_{application,node,queue}.py`
2. `~/work/glasslego/ai-env/cde-skills/skills/data/hadoop/scripts/hadoop_{application,node,queue}.py`

## 의존성 (.env)

- `YARN_RM_URL` — Resource Manager 주소

## 안전

- 본 wrapper 는 `kill` 명령 차단. 필요시 cde-skills 서브스킬 직접 호출 + `--confirm`.
