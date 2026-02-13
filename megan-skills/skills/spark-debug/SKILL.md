---
name: spark-debug
description: Spark application 디버깅 및 로그 모니터링 도구입니다.
  - Kerberos 인증 (kinit) 자동화
  - YARN application 상태 조회
  - Spark application 로그 실시간 모니터링
  - 에러 로그 분석 및 필터링

  Use this skill when user needs to:
  - Debug Spark applications
  - Monitor application logs
  - Check application status
  - Analyze Spark errors
  - Troubleshoot YARN issues
---

# Spark Debug Skill

이 스킬은 Spark application의 디버깅과 로그 모니터링을 지원합니다.

## 지원 클러스터

이 스킬은 세 가지 Hadoop 클러스터를 지원합니다:

- **hadoop-cdp** (기본값): CDP 프로덕션 클러스터
- **hadoop-dev**: 개발 클러스터
- **hadoop-doopey**: Doopey 클러스터

## 사용 방법

### 0. 클러스터 선택

```python
import sys
sys.path.append('.claude/skills/spark-debug/scripts')
from spark_debugger import SparkDebugger

# 기본 클러스터 (hadoop-cdp)
debugger = SparkDebugger()

# 특정 클러스터 지정
debugger = SparkDebugger(cluster='hadoop-dev')
debugger = SparkDebugger(cluster='hadoop-doopey')

# 클러스터 정보 확인
info = debugger.get_cluster_info()
print(info)
```

### 1. Kerberos 인증

```python
import sys
sys.path.append('.claude/skills/spark-debug/scripts')
from spark_debugger import SparkDebugger

# Initialize debugger (클러스터 선택)
debugger = SparkDebugger(cluster='hadoop-cdp')

# Kerberos 인증
debugger.kinit()
```

또는 수동으로:

```python
# Manual kinit
debugger.kinit()

# Check authentication
debugger.check_auth()
```

### 2. Application 목록 조회

```python
# List running applications
apps = debugger.list_applications(state='RUNNING')

# List all applications
all_apps = debugger.list_applications()

# Format output
from format_logs import format_applications
format_applications(apps)
```

### 3. Application 상태 조회

```python
# Get application status
status = debugger.get_application_status('application_1234567890123_0001')

from format_logs import format_application_status
format_application_status(status)
```

### 4. 로그 조회

#### 전체 로그
```python
logs = debugger.get_application_logs('application_1234567890123_0001')
print(logs)
```

#### 특정 파일만 (stdout/stderr)
```python
logs = debugger.get_application_logs(
    'application_1234567890123_0001',
    log_files=['stdout', 'stderr']
)
```

#### 에러 로그만 필터링
```python
errors = debugger.get_error_logs('application_1234567890123_0001')

from format_logs import format_error_logs
format_error_logs(errors)
```

### 5. 로그 실시간 모니터링

```python
# Tail logs (마지막 100줄)
debugger.tail_logs('application_1234567890123_0001', lines=100)

# Follow logs (실시간)
debugger.follow_logs('application_1234567890123_0001')
```

### 6. Container 로그

```python
# List containers
containers = debugger.list_containers('application_1234567890123_0001')

# Get specific container log
logs = debugger.get_container_logs(
    'application_1234567890123_0001',
    container_id='container_1234567890123_0001_01_000001'
)
```

## 주요 기능

### Kerberos 인증
- 자동 kinit (keytab 사용)
- 인증 상태 확인
- 자동 재인증 (만료 시)

### Application 관리
- 실행 중인 application 목록
- Application 상태 조회
- Application 종료

### 로그 조회
- 전체 로그 조회
- stdout/stderr 필터링
- 에러 로그 추출
- 실시간 로그 모니터링

### 로그 분석
- 에러 패턴 감지
- 예외 스택 추출
- 성능 메트릭 파싱
- 경고 메시지 필터링

## 설정

### 환경 변수 (선택)

```bash
# Keytab 경로 (기본값: ~/hadoop-cdp-write.keytab)
export HADOOP_KEYTAB_PATH="/path/to/your.keytab"

# Principal (기본값: hadoop-cdp-write@KAKAO.HADOOP)
export HADOOP_PRINCIPAL="your-principal@REALM"

# Hadoop config 경로
export HADOOP_CONF_DIR="/Users/megan/work/hadoop/hadoop-client-env-v2/target/hadoop-cdp/config/spark3"
```

### 설정 파일

`.claude/skills/spark-debug/.config.json`:

```json
{
  "default_cluster": "hadoop-cdp",
  "hadoop_client_base": "/Users/megan/work/hadoop/hadoop-client-env-v2",
  "clusters": {
    "hadoop-cdp": {
      "name": "hadoop-cdp",
      "env_script": "/Users/megan/work/hadoop/hadoop-client-env-v2/bin/hadoop-cdp-env",
      "target_dir": "/Users/megan/work/hadoop/hadoop-client-env-v2/target/hadoop-cdp",
      "config_dir": "/Users/megan/work/hadoop/hadoop-client-env-v2/target/hadoop-cdp/config/spark3",
      "kerberos": {
        "keytab": "~/hadoop-cdp-write.keytab",
        "principal": "hadoop-cdp-write@KAKAO.HADOOP",
        "realm": "KAKAO.HADOOP"
      }
    },
    "hadoop-dev": {
      "name": "hadoop-dev",
      "env_script": "/Users/megan/work/hadoop/hadoop-client-env-v2/bin/hadoop-dev-env",
      "target_dir": "/Users/megan/work/hadoop/hadoop-client-env-v2/target/hadoop-dev",
      "config_dir": "/Users/megan/work/hadoop/hadoop-client-env-v2/target/hadoop-dev/config/spark3",
      "kerberos": {
        "keytab": "~/hadoop-cdp-write.keytab",
        "principal": "hadoop-cdp-write@KAKAO.HADOOP",
        "realm": "KAKAO.HADOOP"
      }
    },
    "hadoop-doopey": {
      "name": "hadoop-doopey",
      "env_script": "/Users/megan/work/hadoop/hadoop-client-env-v2/bin/hadoop-doopey-env",
      "target_dir": "/Users/megan/work/hadoop/hadoop-client-env-v2/target/hadoop-doopey",
      "config_dir": "/Users/megan/work/hadoop/hadoop-client-env-v2/target/hadoop-doopey/config/spark3",
      "kerberos": {
        "keytab": "~/hadoop-cdp-write.keytab",
        "principal": "hadoop-cdp-write@KAKAO.HADOOP",
        "realm": "KAKAO.HADOOP"
      }
    }
  },
  "yarn": {
    "log_lines_default": 100,
    "follow_interval": 2,
    "max_log_size": 10485760,
    "app_states": ["RUNNING", "ACCEPTED", "SUBMITTED", "FINISHED", "FAILED", "KILLED"]
  },
  "log_patterns": {
    "error": ["ERROR", "Exception", "FATAL", "Failed"],
    "warn": ["WARN", "WARNING"],
    "oom": ["OutOfMemoryError", "Java heap space", "GC overhead"],
    "network": ["Connection refused", "timeout", "UnknownHostException"]
  },
  "defaults": {
    "log_files": ["stdout", "stderr"],
    "container_log_files": ["stdout", "stderr", "syslog"]
  }
}
```

## 사용 예제

### 예제 1: 실행 중인 앱 디버깅

```python
from spark_debugger import SparkDebugger
from format_logs import format_applications, format_error_logs

debugger = SparkDebugger()

# 1. 실행 중인 앱 목록
apps = debugger.list_applications(state='RUNNING')
format_applications(apps)

# 2. 특정 앱 에러 확인
app_id = 'application_1234567890123_0001'
errors = debugger.get_error_logs(app_id)
format_error_logs(errors)

# 3. 전체 로그 확인
logs = debugger.get_application_logs(app_id)
print(logs[:5000])  # 처음 5000자만
```

### 예제 2: 로그 실시간 모니터링

```python
debugger = SparkDebugger()

# Application ID
app_id = 'application_1234567890123_0001'

# 실시간 로그 추적
debugger.follow_logs(app_id, filter_pattern='ERROR|WARN')
```

### 예제 3: 에러 분석

```python
debugger = SparkDebugger()

# 에러 패턴 검색
errors = debugger.search_logs(
    app_id='application_1234567890123_0001',
    pattern='OutOfMemoryError|StackOverflowError|Exception'
)

# 에러 요약
from format_logs import summarize_errors
summarize_errors(errors)
```

## 명령어 참조

### YARN 명령어

```bash
# Application 목록
yarn application -list

# 특정 상태의 application
yarn application -list -appStates RUNNING

# Application 상태
yarn application -status {application_id}

# Application 종료
yarn application -kill {application_id}

# 로그 조회
yarn logs -applicationId {application_id}

# 특정 로그 파일만
yarn logs -applicationId {application_id} -log_files stdout,stderr

# Container 목록
yarn logs -applicationId {application_id} -show_container_log_info
```

### Kerberos 명령어

```bash
# kinit
kinit -kt ~/hadoop-cdp-write.keytab hadoop-cdp-write@KAKAO.HADOOP

# 인증 확인
klist

# 티켓 갱신
kinit -R
```

## 참고 문서

- `references/yarn_commands.md` - YARN 명령어 레퍼런스
- `references/log_patterns.md` - 로그 패턴 및 에러 분석
- `references/hadoop_config.md` - Hadoop 설정 파일 가이드
- `scripts/spark_debugger.py` - 메인 디버거 구현
- `scripts/format_logs.py` - 로그 포맷팅 유틸리티

## 주의사항

1. **Kerberos 인증**: 처음 사용 시 kinit 필요
2. **네트워크**: Hadoop 클러스터 접근 가능해야 함 (VPN 등)
3. **권한**: 로그 조회 권한 필요
4. **로그 크기**: 대용량 로그는 필터링하여 조회

## 트러블슈팅

### Kerberos 인증 실패
```bash
# Keytab 파일 확인
ls -l ~/hadoop-cdp-write.keytab

# Principal 확인
klist -kt ~/hadoop-cdp-write.keytab

# 수동 kinit 시도
kinit -kt ~/hadoop-cdp-write.keytab hadoop-cdp-write@KAKAO.HADOOP
klist
```

### YARN 명령어 실패
```bash
# Hadoop 설정 확인
echo $HADOOP_CONF_DIR

# YARN 연결 테스트
yarn application -list

# 네트워크 확인
ping namenode-host
```

### 로그 조회 실패
- Application이 종료된 경우: YARN history server에서 조회
- 권한 없음: 관리자에게 권한 요청
- 로그 보관 기간: 오래된 로그는 삭제되었을 수 있음
