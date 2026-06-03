---
name: kafka-browse
description: Kafka 토픽 / 클러스터 / 컨슈머 조회 (read-only). 사용자가 "/kafka", "kafka 토픽", "토픽 목록", "kafka describe", "consumer lag", "컨슈머 그룹" 을 말하면 트리거. 실제 호출은 cde-skills `data/kafka` 서브스킬에 위임. 본 wrapper 는 read-only — produce/delete 차단.
---

# Kafka Browse

> Origin: cde-skills/data/kafka. **재구현 금지** — read-only wrapper 만 제공.

## When to invoke

- "토픽 있나", "토픽 목록", "kafka describe my-topic"
- "컨슈머 lag", "consumer group 상태"
- `/kafka list`, `/kafka describe my-topic`

## 자주 쓰는 명령

```bash
~/.claude/skills/kafka-browse/scripts/kafka.sh clusters                          # 클러스터 목록
~/.claude/skills/kafka-browse/scripts/kafka.sh -c my-cluster topic-list           # 토픽 목록
~/.claude/skills/kafka-browse/scripts/kafka.sh -c my-cluster topic-list --internal  # 내부 토픽 포함
~/.claude/skills/kafka-browse/scripts/kafka.sh -c my-cluster topic-describe -t my-topic  # 토픽 상세
~/.claude/skills/kafka-browse/scripts/kafka.sh -c my-cluster consume -t my-topic --max 10  # 메시지 미리보기
# 결과를 옵시디언 노트로 저장:
~/.claude/skills/kafka-browse/scripts/kafka.sh -c c1 topic-describe -t t1 --save kafka-t1-2026-05-06
```

## 위임 경로

스크립트는 다음 후보에서 cde-skills kafka 모듈을 찾는다:

1. `~/.claude/skills/data/kafka/scripts/kafka_{cluster,topic,consume}.py`
2. `~/work/glasslego/ai-env/cde-skills/skills/data/kafka/scripts/kafka_{cluster,topic,consume}.py`

## 의존성 (.env)

- Kafka 클러스터 자격은 cde-skills 의 `_shared/auth` 또는 환경변수에서 자동 로드.
- megan 환경: ai-env `.env` 의 internal auth 가 cde-skills `common/auth` 로 전달됨.

## 안전

- 본 wrapper 는 produce/delete 명령 차단 (read-only).
- consumer reset 등 mutating 명령은 cde-skills 서브스킬 직접 호출 + 명시 confirm.
