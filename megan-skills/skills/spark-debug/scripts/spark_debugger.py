#!/usr/bin/env python3
"""Spark Application 디버거.

이 모듈은 Spark application의 디버깅 및 로그 모니터링을 지원합니다.
"""

import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any

# Config
DEFAULT_CONFIG_PATH = ".claude/skills/spark-debug/.config.json"


class SparkDebugger:
    """Spark application 디버깅 클래스."""

    def __init__(self, config_path: str | None = None, cluster: str | None = None) -> None:
        """SparkDebugger를 초기화합니다.

        Args:
            config_path: 설정 파일 경로 (선택)
            cluster: 클러스터 이름 (hadoop-cdp, hadoop-dev, hadoop-doopey)

        Example:
            >>> debugger = SparkDebugger(cluster='hadoop-cdp')
            >>> apps = debugger.list_applications(state='RUNNING')
        """
        self.config = self._load_config(config_path or DEFAULT_CONFIG_PATH)
        self.cluster_name = cluster or self.config.get("default_cluster", "hadoop-cdp")
        self.cluster_config = self.config["clusters"][self.cluster_name]
        self._setup_environment()

    def _load_config(self, path: str) -> dict[str, Any]:
        """설정 파일을 로드합니다.

        Args:
            path: 설정 파일 경로

        Returns:
            설정 딕셔너리
        """
        config_file = Path(path)
        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        with open(config_file) as f:
            return json.load(f)

    def _setup_environment(self) -> None:
        """Hadoop 환경 변수를 설정합니다."""
        hadoop_conf = self.cluster_config["config_dir"]
        expanded_path = os.path.expanduser(hadoop_conf)

        if os.path.exists(expanded_path):
            os.environ["HADOOP_CONF_DIR"] = expanded_path
        else:
            print(f"Warning: Hadoop config directory not found: {expanded_path}")

    def get_cluster_info(self) -> dict[str, str]:
        """현재 설정된 클러스터 정보를 반환합니다.

        Returns:
            클러스터 정보 딕셔너리
        """
        return {
            "cluster": self.cluster_name,
            "env_script": self.cluster_config["env_script"],
            "config_dir": self.cluster_config["config_dir"],
            "principal": self.cluster_config["kerberos"]["principal"],
        }

    def _run_command(
        self, cmd: list[str], capture_output: bool = True, timeout: int | None = None
    ) -> subprocess.CompletedProcess:
        """명령어를 실행합니다.

        Args:
            cmd: 실행할 명령어 리스트
            capture_output: 출력 캡처 여부
            timeout: 타임아웃 (초)

        Returns:
            subprocess.CompletedProcess 객체

        Raises:
            subprocess.CalledProcessError: 명령 실행 실패 시
            subprocess.TimeoutExpired: 타임아웃 발생 시
        """
        return subprocess.run(
            cmd, capture_output=capture_output, text=True, timeout=timeout, check=True
        )

    def kinit(self) -> bool:
        """Kerberos 인증을 수행합니다.

        Returns:
            인증 성공 여부

        Example:
            >>> debugger = SparkDebugger()
            >>> success = debugger.kinit()
        """
        keytab = os.path.expanduser(self.cluster_config["kerberos"]["keytab"])
        principal = self.cluster_config["kerberos"]["principal"]

        if not os.path.exists(keytab):
            print(f"Error: Keytab file not found: {keytab}")
            return False

        try:
            cmd = ["kinit", "-kt", keytab, principal]
            self._run_command(cmd)
            print(f"Successfully authenticated as {principal} on {self.cluster_name}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"kinit failed: {e}")
            return False

    def check_auth(self) -> bool:
        """Kerberos 인증 상태를 확인합니다.

        Returns:
            인증 여부
        """
        try:
            result = self._run_command(["klist", "-s"])
            return result.returncode == 0
        except subprocess.CalledProcessError:
            return False

    def list_applications(
        self, state: str | None = None, user: str | None = None
    ) -> list[dict[str, str]]:
        """YARN application 목록을 조회합니다.

        Args:
            state: Application 상태 (RUNNING, FINISHED 등)
            user: 사용자 필터

        Returns:
            Application 정보 리스트

        Example:
            >>> apps = debugger.list_applications(state='RUNNING')
            >>> for app in apps:
            ...     print(app['id'], app['name'])
        """
        cmd = ["yarn", "application", "-list"]

        if state:
            cmd.extend(["-appStates", state])

        try:
            result = self._run_command(cmd)
            return self._parse_app_list(result.stdout, user)
        except subprocess.CalledProcessError as e:
            print(f"Failed to list applications: {e}")
            return []

    def _parse_app_list(self, output: str, user_filter: str | None) -> list[dict[str, str]]:
        """Application 목록 파싱합니다.

        Args:
            output: yarn application -list 출력
            user_filter: 사용자 필터

        Returns:
            파싱된 application 목록
        """
        apps = []
        lines = output.strip().split("\n")

        for line in lines:
            if line.startswith("application_"):
                parts = line.split()
                if len(parts) >= 6:
                    app = {
                        "id": parts[0],
                        "name": parts[1],
                        "type": parts[2],
                        "user": parts[3],
                        "queue": parts[4],
                        "state": parts[5],
                    }

                    if user_filter and app["user"] != user_filter:
                        continue

                    apps.append(app)

        return apps

    def get_application_status(self, app_id: str) -> dict[str, Any]:
        """Application 상태를 조회합니다.

        Args:
            app_id: Application ID

        Returns:
            Application 상태 정보

        Example:
            >>> status = debugger.get_application_status('application_123_0001')
        """
        cmd = ["yarn", "application", "-status", app_id]

        try:
            result = self._run_command(cmd)
            return self._parse_app_status(result.stdout)
        except subprocess.CalledProcessError as e:
            print(f"Failed to get application status: {e}")
            return {}

    def _parse_app_status(self, output: str) -> dict[str, Any]:
        """Application 상태 출력을 파싱합니다.

        Args:
            output: yarn application -status 출력

        Returns:
            파싱된 상태 정보
        """
        status = {}
        for line in output.strip().split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                status[key.strip()] = value.strip()
        return status

    def get_application_logs(
        self,
        app_id: str,
        log_files: list[str] | None = None,
        size: int | None = None,
    ) -> str:
        """Application 로그를 조회합니다.

        Args:
            app_id: Application ID
            log_files: 조회할 로그 파일 목록 (stdout, stderr 등)
            size: 조회할 로그 크기 (바이트)

        Returns:
            로그 내용

        Example:
            >>> logs = debugger.get_application_logs(
            ...     'application_123_0001',
            ...     log_files=['stdout', 'stderr']
            ... )
        """
        cmd = ["yarn", "logs", "-applicationId", app_id]

        if log_files:
            cmd.extend(["-log_files", ",".join(log_files)])

        if size:
            cmd.extend(["-size", str(size)])

        try:
            result = self._run_command(cmd, timeout=60)
            return result.stdout
        except subprocess.CalledProcessError as e:
            print(f"Failed to get logs: {e}")
            return ""
        except subprocess.TimeoutExpired:
            print("Log retrieval timed out")
            return ""

    def get_error_logs(self, app_id: str) -> list[str]:
        """에러 로그만 추출합니다.

        Args:
            app_id: Application ID

        Returns:
            에러 로그 라인 리스트
        """
        logs = self.get_application_logs(app_id, log_files=["stderr"])
        return self._filter_errors(logs)

    def _filter_errors(self, logs: str) -> list[str]:
        """로그에서 에러 라인만 필터링합니다.

        Args:
            logs: 전체 로그

        Returns:
            에러 라인 리스트
        """
        error_patterns = self.config["log_patterns"]["error"]
        pattern = "|".join(error_patterns)
        regex = re.compile(pattern, re.IGNORECASE)

        error_lines = []
        for line in logs.split("\n"):
            if regex.search(line):
                error_lines.append(line)

        return error_lines

    def tail_logs(self, app_id: str, lines: int = 100) -> str:
        """로그의 마지막 N줄을 조회합니다.

        Args:
            app_id: Application ID
            lines: 조회할 줄 수

        Returns:
            로그 마지막 N줄
        """
        logs = self.get_application_logs(app_id)
        log_lines = logs.split("\n")
        return "\n".join(log_lines[-lines:])

    def search_logs(self, app_id: str, pattern: str) -> list[str]:
        """로그에서 패턴을 검색합니다.

        Args:
            app_id: Application ID
            pattern: 검색 패턴 (정규식)

        Returns:
            매칭되는 로그 라인 리스트

        Example:
            >>> errors = debugger.search_logs(
            ...     'application_123_0001',
            ...     'OutOfMemoryError|Exception'
            ... )
        """
        logs = self.get_application_logs(app_id)
        regex = re.compile(pattern, re.IGNORECASE)

        matching_lines = []
        for line in logs.split("\n"):
            if regex.search(line):
                matching_lines.append(line)

        return matching_lines

    def kill_application(self, app_id: str) -> bool:
        """Application을 종료합니다.

        Args:
            app_id: Application ID

        Returns:
            종료 성공 여부
        """
        cmd = ["yarn", "application", "-kill", app_id]

        try:
            self._run_command(cmd)
            print(f"Successfully killed application: {app_id}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Failed to kill application: {e}")
            return False

    def follow_logs(
        self, app_id: str, interval: int = 2, filter_pattern: str | None = None
    ) -> None:
        """로그를 실시간으로 추적합니다.

        Args:
            app_id: Application ID
            interval: 갱신 주기 (초)
            filter_pattern: 필터링 패턴

        Note:
            Ctrl+C로 중단할 수 있습니다.
        """
        print(f"Following logs for {app_id}... (Ctrl+C to stop)")
        last_line_count = 0

        try:
            while True:
                logs = self.get_application_logs(app_id)
                lines = logs.split("\n")

                new_lines = lines[last_line_count:]
                last_line_count = len(lines)

                for line in new_lines:
                    if filter_pattern:
                        if re.search(filter_pattern, line, re.IGNORECASE):
                            print(line)
                    else:
                        print(line)

                time.sleep(interval)

        except KeyboardInterrupt:
            print("\nStopped following logs")


if __name__ == "__main__":
    print("Spark Debugger - Usage Examples")
    print("\n1. Initialize:")
    print("   debugger = SparkDebugger()")
    print("\n2. Authenticate:")
    print("   debugger.kinit()")
    print("\n3. List applications:")
    print("   apps = debugger.list_applications(state='RUNNING')")
    print("\n4. Get logs:")
    print("   logs = debugger.get_application_logs('application_id')")
