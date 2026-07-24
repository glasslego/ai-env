# YARN Commands Reference

YARN 관련 명령어 레퍼런스입니다.

## Application 관리

### List Applications

```bash
# 모든 application 조회
yarn application -list

# 실행 중인 application만
yarn application -list -appStates RUNNING

# 완료된 application
yarn application -list -appStates FINISHED

# 실패한 application
yarn application -list -appStates FAILED

# 여러 상태 조회
yarn application -list -appStates RUNNING,SUBMITTED,ACCEPTED
```

### Application 상태 조회

```bash
# 상태 확인
yarn application -status application_1234567890123_0001

# JSON 형식으로 출력
yarn application -status application_1234567890123_0001 -output json
```

### Application 종료

```bash
# Application 종료
yarn application -kill application_1234567890123_0001
```

## 로그 조회

### 기본 로그 조회

```bash
# 전체 로그
yarn logs -applicationId application_1234567890123_0001

# 특정 로그 파일만
yarn logs -applicationId application_1234567890123_0001 -log_files stdout,stderr

# 로그 크기 제한
yarn logs -applicationId application_1234567890123_0001 -size 10485760  # 10MB
```

### Container 로그

```bash
# Container 목록 확인
yarn logs -applicationId application_1234567890123_0001 -show_container_log_info

# 특정 container 로그
yarn logs -applicationId application_1234567890123_0001 \
  -containerId container_1234567890123_0001_01_000001

# 특정 container의 특정 파일
yarn logs -applicationId application_1234567890123_0001 \
  -containerId container_1234567890123_0001_01_000001 \
  -log_files stderr
```

### 로그 필터링

```bash
# 정규식 패턴으로 필터링
yarn logs -applicationId application_1234567890123_0001 | grep -i error

# 특정 시간대 로그 (tail 사용)
yarn logs -applicationId application_1234567890123_0001 | tail -n 1000

# 에러 로그만 추출
yarn logs -applicationId application_1234567890123_0001 -log_files stderr
```

## Node 관리

### Node 목록

```bash
# 활성 노드 목록
yarn node -list

# 모든 노드 (비활성 포함)
yarn node -list -all

# 특정 상태의 노드
yarn node -list -states RUNNING,UNHEALTHY
```

### Node 상태 확인

```bash
# 특정 노드 상태
yarn node -status node-hostname:8042
```

## Queue 관리

### Queue 정보 조회

```bash
# 모든 queue 정보
yarn queue -status

# 특정 queue
yarn queue -status default
```

## Resource Manager

### RM Admin 명령어

```bash
# RM 상태 확인
yarn rmadmin -getServiceState rm1

# Configuration 리프레시
yarn rmadmin -refreshQueues

# 노드 리프레시
yarn rmadmin -refreshNodes
```

## Distributed Shell

### 간단한 분산 작업 실행

```bash
# Distributed shell 실행 예제
yarn jar $HADOOP_HOME/share/hadoop/yarn/hadoop-yarn-applications-distributedshell-*.jar \
  org.apache.hadoop.yarn.applications.distributedshell.Client \
  -jar $HADOOP_HOME/share/hadoop/yarn/hadoop-yarn-applications-distributedshell-*.jar \
  -shell_command "echo hello" \
  -num_containers 1
```

## Application Types

지원하는 application 타입:
- MAPREDUCE
- SPARK
- HIVE
- PIG
- TEZ
- FLINK

## 유용한 옵션

### Application List 옵션

```bash
-appStates <states>     # Application 상태 필터
-appTypes <types>       # Application 타입 필터
-queue <queue>          # Queue 필터
-user <user>            # 사용자 필터
```

### Logs 옵션

```bash
-applicationId <id>            # Application ID
-containerId <id>              # Container ID
-log_files <files>             # 로그 파일 필터 (comma-separated)
-size <bytes>                  # 로그 크기 제한
-show_container_log_info       # Container 로그 정보 표시
-show_application_log_info     # Application 로그 정보 표시
-out <path>                    # 출력 파일 경로
```

## 환경 변수

```bash
# Hadoop 설정 디렉토리
export HADOOP_CONF_DIR=/path/to/hadoop/conf

# YARN 로그 디렉토리
export YARN_LOG_DIR=/path/to/yarn/logs

# YARN Resource Manager 주소
export YARN_RESOURCEMANAGER_ADDRESS=rm-host:8032
```

## 자주 사용하는 조합

### 실행 중인 Spark 앱 찾기

```bash
yarn application -list -appStates RUNNING -appTypes SPARK
```

### 최근 실패한 앱 로그 확인

```bash
# 1. 실패한 앱 ID 찾기
yarn application -list -appStates FAILED | head -5

# 2. 에러 로그 확인
yarn logs -applicationId <app_id> -log_files stderr | grep -i error
```

### 특정 사용자의 실행 중인 앱

```bash
yarn application -list -appStates RUNNING | grep username
```

## YARN REST API

```bash
# Cluster info
curl http://resourcemanager:8088/ws/v1/cluster/info

# Applications
curl http://resourcemanager:8088/ws/v1/cluster/apps

# Specific application
curl http://resourcemanager:8088/ws/v1/cluster/apps/application_1234567890123_0001

# Application attempts
curl http://resourcemanager:8088/ws/v1/cluster/apps/application_1234567890123_0001/appattempts

# Nodes
curl http://resourcemanager:8088/ws/v1/cluster/nodes

# Queues
curl http://resourcemanager:8088/ws/v1/cluster/scheduler
```
