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

Spark application 디버깅과 로그 모니터링을 지원합니다.

## 지원 클러스터

| 클러스터 | 설명 |
|----------|------|
| `hadoop-cdp` | CDP 프로덕션 (기본값) |
| `hadoop-dev` | 개발 클러스터 |
| `hadoop-doopey` | Doopey 클러스터 |

설정 상세: `.claude/skills/spark-debug/.config.json` 참조.

## 사용 방법

```python
import sys
sys.path.append('.claude/skills/spark-debug/scripts')
from spark_debugger import SparkDebugger
from format_logs import format_applications, format_error_logs
```

### 1. 초기화 + Kerberos 인증

```python
debugger = SparkDebugger(cluster='hadoop-cdp')  # 기본값
debugger.kinit()
debugger.check_auth()
```

### 2. Application 조회

```python
# 실행 중인 앱 목록
apps = debugger.list_applications(state='RUNNING')
format_applications(apps)

# 특정 앱 상태
status = debugger.get_application_status('application_xxx')
```

### 3. 로그 조회

```python
app_id = 'application_xxx'

# 전체 로그
logs = debugger.get_application_logs(app_id)

# stdout/stderr만
logs = debugger.get_application_logs(app_id, log_files=['stdout', 'stderr'])

# 에러만 필터링
errors = debugger.get_error_logs(app_id)
format_error_logs(errors)

# 실시간 모니터링
debugger.tail_logs(app_id, lines=100)
debugger.follow_logs(app_id)
```

### 4. Container 로그

```python
containers = debugger.list_containers(app_id)
logs = debugger.get_container_logs(app_id, container_id='container_xxx')
```

### 5. 로그 패턴 검색

```python
errors = debugger.search_logs(app_id, pattern='OutOfMemoryError|Exception')
from format_logs import summarize_errors
summarize_errors(errors)
```

## 환경 변수 (선택)

```bash
export HADOOP_KEYTAB_PATH="~/hadoop-cdp-write.keytab"    # 기본값
export HADOOP_PRINCIPAL="hadoop-cdp-write@KAKAO.HADOOP"   # 기본값
```

## 트러블슈팅

| 증상 | 해결 |
|------|------|
| Kerberos 인증 실패 | `klist -kt ~/hadoop-cdp-write.keytab`로 keytab 확인 |
| YARN 명령 실패 | `echo $HADOOP_CONF_DIR` 확인, VPN 연결 확인 |
| 로그 조회 실패 | 앱 종료 시 history server 조회, 오래된 로그는 삭제됨 |

## 참고 문서

- `references/yarn_commands.md` - YARN 명령어 레퍼런스
- `references/log_patterns.md` - 로그 패턴 및 에러 분석
- `scripts/spark_debugger.py` - 메인 디버거
- `scripts/format_logs.py` - 로그 포맷팅
