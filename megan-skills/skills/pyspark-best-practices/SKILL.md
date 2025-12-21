# PySpark Best Practices Skill
---
name: pyspark-best-practices
description: |
  PySpark 코드 작성 시 자동 적용되는 베스트 프랙티스.
  Auto-apply when writing PySpark code.
---

# PySpark 코딩 표준

## 기본 Import 패턴
```python
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F  # 항상 F로 alias
from pyspark.sql import types as T
from pyspark.sql.window import Window
```

## DataFrame 체이닝 스타일
```python
# ✅ GOOD
result = (
    df
    .filter(F.col("is_active") == True)
    .withColumn("score_normalized", F.col("score") / 100)
    .groupBy("category")
    .agg(F.count("*").alias("count"))
    .orderBy(F.desc("count"))
)
```

## Window Functions
```python
window_spec = Window.partitionBy("category").orderBy(F.desc("score"))
df_ranked = df.withColumn("rank", F.row_number().over(window_spec))
```

## 성능 최적화

### Broadcast Join
```python
from pyspark.sql.functions import broadcast
result = large_df.join(broadcast(small_df), on="key", how="left")
```

### Repartition vs Coalesce
```python
df.repartition(100, "key_column")  # 파티션 늘리기 (shuffle)
df.coalesce(10)  # 파티션 줄이기 (no shuffle)
```

### Cache
```python
df_cached = df.cache()
# 작업 완료 후
df_cached.unpersist()
```

## 타입 안전성
```python
schema = StructType([
    StructField("id", StringType(), nullable=False),
    StructField("score", IntegerType(), nullable=True)
])
df = spark.read.schema(schema).parquet("path")
```
