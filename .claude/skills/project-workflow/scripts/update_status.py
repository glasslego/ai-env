#!/usr/bin/env python3
"""_project-status.yaml를 갱신한다.

spec-manager의 parse_spec_status.py를 호출하고, 추가로 리뷰/도메인 ops 상태를 병합한다.

Usage:
    python update_status.py [project_root]
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml


def load_profile(root: Path) -> dict:
    """project-profile.yaml을 로드한다."""
    profile_path = root / ".claude" / "project-profile.yaml"
    if not profile_path.exists():
        return {}
    return yaml.safe_load(profile_path.read_text(encoding="utf-8")) or {}


def update_status(root: Path) -> None:
    """프로젝트 상태를 갱신한다."""
    profile = load_profile(root)

    specs_dir_name = profile.get("specs", {}).get("directory", "specs/")
    specs_dir = root / specs_dir_name
    status_file_name = profile.get("status", {}).get("file", "_project-status.yaml")
    status_file = root / status_file_name

    if not specs_dir.is_dir():
        print(f"⚠ Specs directory not found: {specs_dir}")
        print("  Creating empty status file")
        status = {
            "last_updated": str(__import__("datetime").date.today()),
            "current_phase": "intake",
            "specs": {},
        }
        status_file.write_text(
            yaml.dump(status, allow_unicode=True, default_flow_style=False, sort_keys=False),
            encoding="utf-8",
        )
        return

    # spec-manager의 parse_spec_status 모듈 사용
    # 직접 import가 안 되는 환경이면 동일 로직을 인라인 실행
    import re
    from datetime import date

    def parse_frontmatter(content: str) -> dict:
        match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
        if not match:
            return {}
        try:
            return yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError:
            return {}

    def count_tasks(content: str) -> tuple[int, int]:
        done = len(re.findall(r"- \[x\]", content, re.IGNORECASE))
        undone = len(re.findall(r"- \[ \]", content))
        return done + undone, done

    specs = {}
    for spec_file in sorted(specs_dir.glob("SPEC-*.md")):
        content = spec_file.read_text(encoding="utf-8")
        fm = parse_frontmatter(content)
        spec_id = fm.get("spec_id", spec_file.stem)
        tasks_total, tasks_done = count_tasks(content)
        specs[spec_id] = {
            "title": fm.get("title", spec_file.stem),
            "status": fm.get("status", "planned"),
            "tasks_total": tasks_total,
            "tasks_done": tasks_done,
        }

    # 기존 상태 보존
    existing = {}
    if status_file.exists():
        existing = yaml.safe_load(status_file.read_text(encoding="utf-8")) or {}

    # current_phase 추론
    statuses = [s["status"] for s in specs.values()] if specs else []
    if all(s == "done" for s in statuses) and statuses:
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

    if "reviews" in existing:
        status["reviews"] = existing["reviews"]

    status_file.write_text(
        yaml.dump(status, allow_unicode=True, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )

    print(f"✅ Updated {status_file}")
    print(f"   Phase: {current_phase}")
    print(f"   Specs: {len(specs)}")
    for sid, sdata in specs.items():
        progress = f"{sdata['tasks_done']}/{sdata['tasks_total']}"
        print(f"     {sid}: {sdata['status']} ({progress})")


if __name__ == "__main__":
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    update_status(root)
