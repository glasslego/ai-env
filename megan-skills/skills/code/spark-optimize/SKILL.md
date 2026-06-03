---
name: spark-optimize
description: PySpark 코드 최적화 가이드 — kamek-batch, cde-ranking-skills/spark-debug 의 패턴을 참조해 일반적인 안티패턴 검출 + 권장 수정 제안. 사용자가 "spark 최적화", "/spark-opt", "pyspark 튜닝", "셔플 줄이기" 를 말하면 트리거.
---

# Spark Optimize

> Origin: kamek-batch (외부 git 참조) + cde-ranking-skills/spark-debug 보완.
> 이 스킬은 **코드 자동수정 X** — 안티패턴 검출 + 인용 가이드만 제공한다.

## When to invoke

- 사용자가 spark 코드 최적화 / 셔플 / 메모리 / OOM 관련 도움 요청
- `/spark-opt path/to/spark_job.py`

## 검사 항목 (정적 sniff)

| Anti-pattern | Sniff |
|---|---|
| UDF 남용 | `udf(`, `@udf` 검출 → 네이티브 `F.<func>` 변환 가능성 묻기 |
| import * | `from pyspark.sql.functions import *` → `as F` 권장 |
| collect() 무경계 | `.collect()` 호출 → 사이즈 한계 검토 |
| cache() 미해제 | `.cache()` 또는 `.persist()` 있는데 `.unpersist()` 없음 |
| repartition 의심 | `.repartition(<숫자>)` → 데이터 규모 대비 합리적인지 |
| broadcast 미사용 | join 직전 작은 테이블에 `broadcast()` 미사용 단서 |
| toPandas 호출 | `.toPandas()` → 분산 collect 의 변형, 큰 DF 위험 |

## 외부 참조 (코드 임베드 X)

```bash
~/.claude/skills/spark-optimize/scripts/refs.sh
# 출력:
#   kamek-batch repo 경로 (있으면)
#   cde-ranking-skills/spark-debug 경로
#   각 위치의 README/CLAUDE.md 발췌 (skill 본문에 임베드 X)
```

## 실행

```bash
~/.claude/skills/spark-optimize/scripts/sniff.sh path/to/spark_job.py
~/.claude/skills/spark-optimize/scripts/sniff.sh src/  # 디렉토리 재귀
```

## 출력 형식

```
file:line — pattern — 권장
```

검출 후 in-conversation 에서 Claude/Codex 가 각 라인에 대한 구체 수정안을 제시.
이 스킬은 자동 적용 X (사용자 검토 필수).
