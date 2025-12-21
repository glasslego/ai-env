#!/usr/bin/env python3
"""specs/ 디렉토리를 파싱하여 _project-status.yaml을 생성/갱신한다.

Usage:
    python parse_spec_status.py <specs_dir> [status_file]

specs_dir: specs/ 디렉토리 경로
status_file: _project-status.yaml 경로 (기본: specs_dir/../_project-status.yaml)
"""

from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

import yaml


def parse_frontmatter(content: str) -> dict:
    """YAML frontmatter를 파싱한다."""
    match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return {}
    try:
        return yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return {}


def count_tasks(content: str) -> tuple[int, int]:
    """체크박스 기반으로 전체/완료 task 수를 카운트한다."""
    done = len(re.findall(r"- \[x\]", content, re.IGNORECASE))
    undone = len(re.findall(r"- \[ \]", content))
    return done + undone, done


def scan_specs(specs_dir: Path) -> dict:
    """specs/ 디렉토리를 스캔하여 스펙 상태 딕셔너리를 반환한다."""
    specs = {}
    for spec_file in sorted(specs_dir.glob("SPEC-*.md")):
        content = spec_file.read_text(encoding="utf-8")
        fm = parse_frontmatter(content)
        spec_id = fm.get(
            "spec_id", spec_file.stem.split("-")[0] + "-" + spec_file.stem.split("-")[1]
        )
        tasks_total, tasks_done = count_tasks(content)
        specs[spec_id] = {
            "title": fm.get("title", spec_file.stem),
            "status": fm.get("status", "planned"),
            "tasks_total": tasks_total,
            "tasks_done": tasks_done,
        }
    return specs


def update_status_file(specs_dir: Path, status_file: Path) -> None:
    """_project-status.yaml를 생성/갱신한다."""
    specs = scan_specs(specs_dir)

    # 기존 파일이 있으면 로드하여 병합
    existing = {}
    if status_file.exists():
        try:
            existing = yaml.safe_load(status_file.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            existing = {}

    # 기존 상태에서 추가 필드(current_task 등) 보존
    existing_specs = existing.get("specs", {})
    for spec_id, spec_data in specs.items():
        if spec_id in existing_specs:
            # 기존의 current_task 등 보존
            for key in ("current_task",):
                if key in existing_specs[spec_id]:
                    spec_data[key] = existing_specs[spec_id][key]

    # current_phase 추론
    statuses = [s["status"] for s in specs.values()]
    if all(s == "done" for s in statuses):
        current_phase = "done"
    elif any(s == "review_required" for s in statuses):
        current_phase = "review"
    elif any(s == "in_progress" for s in statuses):
        current_phase = "implementing"
    elif any(s == "planned" for s in statuses):
        current_phase = "spec"
    else:
        current_phase = "intake"

    status = {
        "last_updated": str(date.today()),
        "current_phase": current_phase,
        "specs": specs,
    }

    # reviews 섹션 보존
    if "reviews" in existing:
        status["reviews"] = existing["reviews"]

    status_file.write_text(
        yaml.dump(status, allow_unicode=True, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )
    print(f"Updated {status_file}")
    print(f"  Phase: {current_phase}")
    print(f"  Specs: {len(specs)}")
    for sid, sdata in specs.items():
        print(f"    {sid}: {sdata['status']} ({sdata['tasks_done']}/{sdata['tasks_total']})")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <specs_dir> [status_file]")
        sys.exit(1)

    specs_dir = Path(sys.argv[1])
    if not specs_dir.is_dir():
        print(f"Error: {specs_dir} is not a directory")
        sys.exit(1)

    if len(sys.argv) >= 3:
        status_file = Path(sys.argv[2])
    else:
        status_file = specs_dir.parent / "_project-status.yaml"

    update_status_file(specs_dir, status_file)
