#!/usr/bin/env python3
"""Spark 로그 포맷팅 유틸리티.

이 모듈은 Spark/YARN 로그를 사람이 읽기 쉬운 형태로 포맷팅합니다.
"""

import re
from collections import Counter
from typing import Any

# Constants
SEPARATOR_WIDTH = 100
SEPARATOR_LINE = "=" * SEPARATOR_WIDTH
DASH_LINE = "-" * SEPARATOR_WIDTH


def _print_header(title: str) -> None:
    """헤더를 출력합니다.

    Args:
        title: 헤더 제목
    """
    print(f"\n{SEPARATOR_LINE}")
    print(title)
    print(SEPARATOR_LINE)


def format_applications(apps: list[dict[str, str]]) -> None:
    """Application 목록을 포맷팅합니다.

    Args:
        apps: Application 목록

    Example:
        >>> apps = debugger.list_applications()
        >>> format_applications(apps)
    """
    _print_header(f"YARN Applications ({len(apps)} items)")

    if not apps:
        print("No applications found.")
        print(SEPARATOR_LINE)
        return

    header = f"\n{'#':<4} {'Application ID':<30} {'Name':<30} " f"{'State':<12} {'User':<15}"
    print(header)
    divider = f"{'-'*4} {'-'*30} {'-'*30} {'-'*12} {'-'*15}"
    print(divider)

    for idx, app in enumerate(apps, 1):
        app_id = app.get("id", "N/A")[:30]
        name = app.get("name", "N/A")[:30]
        state = app.get("state", "N/A")[:12]
        user = app.get("user", "N/A")[:15]

        row = f"{idx:<4} {app_id:<30} {name:<30} {state:<12} {user:<15}"
        print(row)

    print(SEPARATOR_LINE)


def format_application_status(status: dict[str, Any]) -> None:
    """Application 상태를 포맷팅합니다.

    Args:
        status: Application 상태 정보
    """
    _print_header("Application Status")

    if not status:
        print("No status information available.")
        print(SEPARATOR_LINE)
        return

    for key, value in status.items():
        print(f"{key:<30}: {value}")

    print(SEPARATOR_LINE)


def format_error_logs(errors: list[str], max_lines: int = 50) -> None:
    """에러 로그를 포맷팅합니다.

    Args:
        errors: 에러 로그 라인 리스트
        max_lines: 최대 출력 줄 수
    """
    _print_header(f"Error Logs ({len(errors)} errors found)")

    if not errors:
        print("No errors found.")
        print(SEPARATOR_LINE)
        return

    displayed = min(len(errors), max_lines)
    for idx, error in enumerate(errors[:displayed], 1):
        print(f"{idx:4d}| {error}")

    if len(errors) > max_lines:
        print(f"\n... and {len(errors) - max_lines} more errors")

    print(SEPARATOR_LINE)


def summarize_errors(errors: list[str]) -> None:
    """에러 로그를 요약합니다.

    Args:
        errors: 에러 로그 라인 리스트
    """
    _print_header(f"Error Summary ({len(errors)} total errors)")

    if not errors:
        print("No errors to summarize.")
        print(SEPARATOR_LINE)
        return

    # 에러 타입별 카운트
    error_types = Counter()
    exception_pattern = re.compile(r"(\w+Exception|\w+Error)")

    for error in errors:
        match = exception_pattern.search(error)
        if match:
            error_types[match.group(1)] += 1
        else:
            error_types["Other"] += 1

    # 상위 10개 출력
    print("\nTop Error Types:")
    print(f"{'Error Type':<40} {'Count':>10}")
    print(f"{'-'*40} {'-'*10}")

    for error_type, count in error_types.most_common(10):
        print(f"{error_type:<40} {count:>10}")

    print(SEPARATOR_LINE)


def format_log_excerpt(logs: str, pattern: str, context_lines: int = 2) -> None:
    """패턴에 매칭되는 로그 부분을 컨텍스트와 함께 출력합니다.

    Args:
        logs: 전체 로그
        pattern: 검색 패턴
        context_lines: 전후 컨텍스트 줄 수
    """
    _print_header(f"Log Excerpts (pattern: {pattern})")

    lines = logs.split("\n")
    regex = re.compile(pattern, re.IGNORECASE)
    matches = []

    for idx, line in enumerate(lines):
        if regex.search(line):
            start = max(0, idx - context_lines)
            end = min(len(lines), idx + context_lines + 1)
            context = lines[start:end]
            matches.append((idx + 1, context))

    if not matches:
        print(f"No matches found for pattern: {pattern}")
        print(SEPARATOR_LINE)
        return

    for line_num, context in matches[:10]:  # 최대 10개만 표시
        print(f"\nLine {line_num}:")
        print(DASH_LINE)
        for line in context:
            print(line)
        print(DASH_LINE)

    if len(matches) > 10:
        print(f"\n... and {len(matches) - 10} more matches")

    print(SEPARATOR_LINE)


def extract_stack_traces(logs: str) -> list[str]:
    """로그에서 스택 트레이스를 추출합니다.

    Args:
        logs: 전체 로그

    Returns:
        스택 트레이스 목록
    """
    stack_traces = []
    lines = logs.split("\n")
    current_trace = []
    in_trace = False

    for line in lines:
        # 스택 트레이스 시작 감지
        if re.search(r"Exception|Error", line) and ":" in line:
            in_trace = True
            current_trace = [line]
        # 스택 트레이스 라인 감지
        elif in_trace and (line.strip().startswith("at ") or line.strip().startswith("...")):
            current_trace.append(line)
        # 스택 트레이스 종료
        elif in_trace and current_trace:
            stack_traces.append("\n".join(current_trace))
            current_trace = []
            in_trace = False

    return stack_traces


def format_stack_traces(traces: list[str], max_traces: int = 5) -> None:
    """스택 트레이스를 포맷팅합니다.

    Args:
        traces: 스택 트레이스 목록
        max_traces: 최대 출력 개수
    """
    _print_header(f"Stack Traces ({len(traces)} found)")

    if not traces:
        print("No stack traces found.")
        print(SEPARATOR_LINE)
        return

    for idx, trace in enumerate(traces[:max_traces], 1):
        print(f"\nStack Trace #{idx}:")
        print(DASH_LINE)
        print(trace)
        print(DASH_LINE)

    if len(traces) > max_traces:
        print(f"\n... and {len(traces) - max_traces} more stack traces")

    print(SEPARATOR_LINE)


def analyze_performance_metrics(logs: str) -> dict[str, Any]:
    """로그에서 성능 메트릭을 추출합니다.

    Args:
        logs: 전체 로그

    Returns:
        성능 메트릭 딕셔너리
    """
    metrics = {
        "task_count": 0,
        "failed_tasks": 0,
        "stages": 0,
        "jobs": 0,
        "gc_time_ms": [],
        "shuffle_read_mb": [],
        "shuffle_write_mb": [],
    }

    for line in logs.split("\n"):
        # Task 카운트
        if "Finished task" in line:
            metrics["task_count"] += 1
        if "FAILED" in line and "task" in line.lower():
            metrics["failed_tasks"] += 1

        # Stage/Job 카운트
        if "Stage" in line and "finished" in line:
            metrics["stages"] += 1
        if "Job" in line and "finished" in line:
            metrics["jobs"] += 1

        # GC time
        gc_match = re.search(r"GC time = (\d+) ms", line)
        if gc_match:
            metrics["gc_time_ms"].append(int(gc_match.group(1)))

        # Shuffle metrics
        shuffle_read = re.search(r"shuffle read.*?(\d+\.?\d*)\s*MB", line, re.IGNORECASE)
        if shuffle_read:
            metrics["shuffle_read_mb"].append(float(shuffle_read.group(1)))

        shuffle_write = re.search(r"shuffle write.*?(\d+\.?\d*)\s*MB", line, re.IGNORECASE)
        if shuffle_write:
            metrics["shuffle_write_mb"].append(float(shuffle_write.group(1)))

    return metrics


def format_performance_metrics(metrics: dict[str, Any]) -> None:
    """성능 메트릭을 포맷팅합니다.

    Args:
        metrics: 성능 메트릭 딕셔너리
    """
    _print_header("Performance Metrics")

    print(f"Total Tasks:          {metrics['task_count']}")
    print(f"Failed Tasks:         {metrics['failed_tasks']}")
    print(f"Stages Completed:     {metrics['stages']}")
    print(f"Jobs Completed:       {metrics['jobs']}")

    if metrics["gc_time_ms"]:
        avg_gc = sum(metrics["gc_time_ms"]) / len(metrics["gc_time_ms"])
        total_gc = sum(metrics["gc_time_ms"])
        print(f"\nGC Time (avg):        {avg_gc:.2f} ms")
        print(f"GC Time (total):      {total_gc:.2f} ms")

    if metrics["shuffle_read_mb"]:
        total_read = sum(metrics["shuffle_read_mb"])
        print(f"\nShuffle Read (total): {total_read:.2f} MB")

    if metrics["shuffle_write_mb"]:
        total_write = sum(metrics["shuffle_write_mb"])
        print(f"Shuffle Write (total):{total_write:.2f} MB")

    print(SEPARATOR_LINE)


if __name__ == "__main__":
    print("This module provides formatting utilities for Spark logs.")
    print("\nAvailable functions:")
    print("  - format_applications(apps)")
    print("  - format_application_status(status)")
    print("  - format_error_logs(errors, max_lines)")
    print("  - summarize_errors(errors)")
    print("  - format_log_excerpt(logs, pattern, context_lines)")
    print("  - extract_stack_traces(logs)")
    print("  - format_stack_traces(traces, max_traces)")
    print("  - analyze_performance_metrics(logs)")
    print("  - format_performance_metrics(metrics)")
