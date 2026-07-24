---
name: grafana-board
description: Grafana 대시보드 목록/조회/엽기 (read-only browse + open). 사용자가 "/grafana", "그라파나", "대시보드", "grafana board", "monitoring 보드" 를 말하면 트리거. 실제 호출은 cde-skills `operations/grafana` 서브스킬에 위임. import/sync 등 mutating 은 차단.
---

# Grafana Board

> Origin: cde-skills/operations/grafana. **재구현 금지** — read-only wrapper.

## When to invoke

- "이 서비스 대시보드 어디?", "grafana 보드 검색"
- `/grafana list`, `/grafana open <slug>`, `/grafana export <uid>`

## 자주 쓰는 명령

```bash
~/.claude/skills/grafana-board/scripts/grafana.sh list                    # 대시보드 목록
~/.claude/skills/grafana-board/scripts/grafana.sh search "ranking"         # 키워드 검색
~/.claude/skills/grafana-board/scripts/grafana.sh open my-dash-slug        # 브라우저 열기
~/.claude/skills/grafana-board/scripts/grafana.sh export uid_xxx           # JSON 내보내기
# 환경 (prod/stage):
~/.claude/skills/grafana-board/scripts/grafana.sh --env stage list
```

## 위임 경로

1. `~/.claude/skills/operations/grafana/scripts/grafana_dashboard.py`
2. `~/work/glasslego/ai-env/cde-skills/skills/operations/grafana/scripts/grafana_dashboard.py`

## 의존성 (.env)

- `GRAFANA_PROD_URL`, `GRAFANA_STAGE_URL`
- `GRAFANA_USERNAME`, `GRAFANA_PASSWORD`

## 안전

- 본 wrapper 는 import / sync / delete 차단. 필요시 cde-skills 직접 호출.
