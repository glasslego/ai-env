# Spark/YARN Log Patterns

Spark 및 YARN 로그에서 자주 발생하는 패턴 및 에러 분석 가이드입니다.

## 일반적인 에러 패턴

### OutOfMemoryError

**패턴:**
```
java.lang.OutOfMemoryError: Java heap space
java.lang.OutOfMemoryError: GC overhead limit exceeded
```

**원인:**
- Executor/Driver 메모리 부족
- 너무 큰 데이터를 메모리에 로드
- 메모리 누수

**해결:**
```python
# Executor 메모리 증가
spark.executor.memory = 8g
spark.driver.memory = 4g

# 메모리 오버헤드 조정
spark.executor.memoryOverhead = 2g
```

### Shuffle 관련 에러

**패턴:**
```
java.io.IOException: No space left on device
org.apache.spark.shuffle.FetchFailedException
org.apache.spark.shuffle.MetadataFetchFailedException
```

**원인:**
- Shuffle 데이터가 디스크 용량 초과
- Network timeout
- Executor 실패로 shuffle 데이터 손실

**해결:**
```python
# Shuffle partition 수 조정
spark.sql.shuffle.partitions = 200

# Network timeout 증가
spark.network.timeout = 600s
spark.shuffle.io.maxRetries = 5
```

### Executor Lost

**패턴:**
```
ExecutorLostFailure (executor X exited caused by one of the running tasks)
Killed by user
Container killed by YARN for exceeding memory limits
```

**원인:**
- 메모리 초과로 YARN이 Container 강제 종료
- 노드 장애
- Task timeout

**해결:**
```python
# 메모리 설정 조정
spark.executor.memory = 4g
spark.executor.memoryOverhead = 1g

# Task timeout 증가
spark.task.maxFailures = 8
```

### Connection Refused

**패턴:**
```
java.net.ConnectException: Connection refused
java.net.UnknownHostException
java.net.SocketTimeoutException: Read timed out
```

**원인:**
- Network 문제
- 방화벽
- DNS 해석 실패

**해결:**
- Network 연결 확인
- 방화벽 설정 확인
- DNS 설정 확인

## Spark 특화 에러

### Task Not Serializable

**패턴:**
```
org.apache.spark.SparkException: Task not serializable
java.io.NotSerializableException
```

**원인:**
- Closure에서 직렬화 불가능한 객체 참조
- RDD/DataFrame 연산 내부에서 Spark context 사용

**해결:**
```scala
// BAD: Spark context를 closure 안에서 사용
val sc = spark.sparkContext
rdd.map(x => sc.parallelize(...))  // Error!

// GOOD: Broadcast 사용
val broadcastVar = sc.broadcast(data)
rdd.map(x => use(broadcastVar.value))
```

### Stage Failure

**패턴:**
```
org.apache.spark.SparkException: Job aborted due to stage failure
org.apache.spark.rdd.PairRDDFunctions.combineByKeyWithClassTag
```

**원인:**
- Task 실패 반복
- Shuffle 실패
- 데이터 스큐

**해결:**
```python
# Speculative execution 활성화
spark.speculation = true
spark.speculation.multiplier = 3

# Data skew 해결
df.repartition(200, 'skewed_column')
```

## 로그 레벨별 패턴

### ERROR

```
ERROR: 치명적인 오류, 작업 실패 원인
```

주요 패턴:
- `ERROR Executor: Exception in task`
- `ERROR TaskSchedulerImpl: Lost executor`
- `ERROR YarnScheduler: Application failed`

### WARN

```
WARN: 경고, 작업은 계속되지만 주의 필요
```

주요 패턴:
- `WARN TaskSetManager: Lost task`
- `WARN MemoryStore: Not enough space to cache`
- `WARN NativeCodeLoader: Unable to load native-hadoop library`

### INFO

```
INFO: 일반 정보 로그
```

주요 패턴:
- `INFO DAGScheduler: Job X finished`
- `INFO TaskSetManager: Finished task`
- `INFO SparkContext: Successfully stopped`

## Performance 관련 패턴

### GC Overhead

```
WARN Executor: Managed memory leak detected; size = X bytes, TID = Y
WARN TaskMemoryManager: leak X bytes
GC time = XXXXX ms
```

**의미:**
- GC 시간이 과도하게 길어짐
- 메모리 누수 가능성

**해결:**
```python
# G1GC 사용
spark.executor.extraJavaOptions = -XX:+UseG1GC

# 메모리 증가
spark.executor.memory = 8g
```

### Skewed Data

```
WARN TaskSetManager: Stage X contains a task of very large size (X KB)
Task X in stage Y (TID X) is much larger than other tasks
```

**의미:**
- 데이터가 특정 파티션에 집중됨
- Task 간 불균형

**해결:**
```python
# Salting 기법 사용
df_with_salt = df.withColumn('salt', (rand() * 10).cast('int'))
result = df_with_salt.groupBy('key', 'salt').agg(...)

# AQE 활성화 (Spark 3.0+)
spark.sql.adaptive.enabled = true
spark.sql.adaptive.coalescePartitions.enabled = true
```

## 로그 검색 패턴

### 정규식 패턴

```regex
# Exception 찾기
(Exception|Error).*?at\s+

# 메모리 에러
(OutOfMemoryError|heap space|GC overhead)

# Network 에러
(Connection refused|timeout|UnknownHost)

# Executor 에러
(Executor.*lost|Container.*killed)

# Task 실패
(Task.*failed|Stage.*failed)
```

### Grep 명령어 예제

```bash
# 에러만 추출
yarn logs -applicationId <app_id> | grep -i error

# 예외 스택 트레이스
yarn logs -applicationId <app_id> | grep -A 20 "Exception"

# OOM 에러
yarn logs -applicationId <app_id> | grep -i "OutOfMemory"

# Executor lost
yarn logs -applicationId <app_id> | grep "ExecutorLostFailure"
```

## 디버깅 체크리스트

1. **먼저 확인할 것:**
   - Application 상태 (RUNNING/FAILED/KILLED)
   - Executor 로그의 ERROR/WARN 메시지
   - Driver 로그의 예외 스택

2. **메모리 문제 의심 시:**
   - OOM 에러 검색
   - GC 시간 확인
   - Container killed 메시지 확인

3. **Network 문제 의심 시:**
   - Connection refused 검색
   - Shuffle fetch 실패 확인
   - Timeout 메시지 확인

4. **성능 문제 의심 시:**
   - Stage/Task 실행 시간 확인
   - Shuffle read/write 크기 확인
   - Data skew 징후 확인

## 유용한 로그 분석 스크립트

```bash
#!/bin/bash
# analyze_spark_logs.sh

APP_ID=$1

echo "=== ERROR Analysis ==="
yarn logs -applicationId $APP_ID | grep -i "error" | sort | uniq -c | sort -rn | head -20

echo "=== Exception Types ==="
yarn logs -applicationId $APP_ID | grep -o "[A-Za-z]*Exception" | sort | uniq -c | sort -rn

echo "=== Task Failures ==="
yarn logs -applicationId $APP_ID | grep "Task.*failed" | wc -l

echo "=== GC Time ==="
yarn logs -applicationId $APP_ID | grep "GC time" | head -10
```
