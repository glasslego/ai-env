#!/usr/bin/env python3
"""프로젝트 컨텍스트를 자동 감지하고 project-profile.yaml 초안을 생성한다.

Usage:
    python detect_project.py [project_root]

project_root: 프로젝트 루트 경로 (기본: 현재 디렉토리)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml


def detect_project_type(root: Path) -> str:
    """프로젝트 타입을 추론한다."""
    if (root / "pyproject.toml").exists():
        pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
        if "fastapi" in pyproject.lower() or "uvicorn" in pyproject.lower():
            return "api-server"
        if "click" in pyproject.lower() or "typer" in pyproject.lower():
            return "cli-tool"
        return "library"
    if (root / "package.json").exists():
        pkg = json.loads((root / "package.json").read_text(encoding="utf-8"))
        deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
        if "next" in deps or "react" in deps:
            return "web-app"
        if "express" in deps or "fastify" in deps:
            return "api-server"
        return "library"
    return "unknown"


def detect_architecture(root: Path) -> dict:
    """아키텍처 패턴을 추론한다."""
    layers = {}

    # 3-layer 탐지
    for api_dir in ("app/api", "src/api", "api"):
        if (root / api_dir).is_dir():
            layers["api"] = api_dir
    for svc_dir in ("app/services", "src/services", "services"):
        if (root / svc_dir).is_dir():
            layers["service"] = svc_dir
    for repo_dir in ("app/repositories", "src/repositories", "repositories"):
        if (root / repo_dir).is_dir():
            layers["repository"] = repo_dir

    if len(layers) >= 2:
        return {"pattern": "3-layer", "layers": layers}

    # src/ 패턴
    if (root / "src").is_dir():
        return {"pattern": "monolith", "layers": {"src": "src/"}}

    return {"pattern": "monolith", "layers": {}}


def detect_tests(root: Path) -> dict:
    """테스트 프레임워크를 감지한다."""
    if (root / "pyproject.toml").exists():
        pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
        if "pytest" in pyproject:
            test_dir = "tests/" if (root / "tests").is_dir() else "test/"
            return {
                "framework": "pytest",
                "command": f"pytest {test_dir} -x -q",
                "lint_command": "ruff check . && ruff format --check .",
            }
    if (root / "package.json").exists():
        pkg = json.loads((root / "package.json").read_text(encoding="utf-8"))
        deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
        if "jest" in deps:
            return {"framework": "jest", "command": "npm test"}
        if "vitest" in deps:
            return {"framework": "vitest", "command": "npx vitest run"}
    return {"framework": "unknown", "command": "echo 'No test framework detected'"}


def detect_specs(root: Path) -> dict:
    """스펙 디렉토리를 감지한다."""
    specs_dir = root / "specs"
    if specs_dir.is_dir():
        spec_files = list(specs_dir.glob("SPEC-*.md"))
        return {
            "directory": "specs/",
            "format": "SPEC-NNN",
            "count": len(spec_files),
        }
    return {"directory": "specs/", "format": "SPEC-NNN", "count": 0}


def generate_profile(root: Path) -> dict:
    """project-profile.yaml 초안을 생성한다."""
    project_type = detect_project_type(root)
    architecture = detect_architecture(root)
    tests = detect_tests(root)
    specs = detect_specs(root)

    profile = {
        "project": {
            "name": root.name,
            "type": project_type,
            "description": f"{root.name} project",
        },
        "architecture": architecture,
        "specs": {
            "directory": specs["directory"],
            "format": specs["format"],
        },
        "tests": tests,
        "status": {"file": "_project-status.yaml"},
    }

    return profile


def main() -> None:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    if not root.is_dir():
        print(f"Error: {root} is not a directory")
        sys.exit(1)

    profile = generate_profile(root)

    # 출력
    print("# Auto-detected project profile")
    print(yaml.dump(profile, allow_unicode=True, default_flow_style=False, sort_keys=False))

    # 기존 profile 확인
    profile_path = root / ".claude" / "project-profile.yaml"
    if profile_path.exists():
        print(f"\n⚠ Profile already exists: {profile_path}")
        print("  Use --force to overwrite")
    else:
        if "--save" in sys.argv:
            profile_path.parent.mkdir(parents=True, exist_ok=True)
            profile_path.write_text(
                yaml.dump(profile, allow_unicode=True, default_flow_style=False, sort_keys=False),
                encoding="utf-8",
            )
            print(f"\n✅ Saved to {profile_path}")
        else:
            print(f"\n💡 Run with --save to write to {profile_path}")


if __name__ == "__main__":
    main()
