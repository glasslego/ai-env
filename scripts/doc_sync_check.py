#!/usr/bin/env python3
"""문서 ↔ 코드 정합성 검증 및 자동 수정.

pre-commit: --fix 모드로 자동 수정 가능한 불일치를 수정한다.
pre-push:   검증만 수행하고 불일치 시 push를 차단한다.

사용법:
    python scripts/doc_sync_check.py          # 검증만 (pre-push)
    python scripts/doc_sync_check.py --fix    # 자동 수정 (pre-commit)
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

# 프로젝트 루트 (이 스크립트는 scripts/ 하위)
ROOT = Path(__file__).resolve().parent.parent

# ────────────────────────────────────────────
# 유틸
# ────────────────────────────────────────────


def _read(path: Path) -> str:
    """파일 읽기. 없으면 빈 문자열."""
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _parse_yaml_servers(yaml_text: str) -> dict[str, bool]:
    """mcp_servers.yaml에서 서버 이름과 enabled 상태를 간이 파싱한다.

    정규식 기반이므로 PyYAML 의존성이 불필요.
    """
    servers: dict[str, bool] = {}
    current_server: str | None = None

    for line in yaml_text.splitlines():
        # 서버 이름: 2-space indent + name + ':'
        m = re.match(r"^  (\w[\w-]*):\s*$", line)
        if m:
            current_server = m.group(1)
            servers[current_server] = True  # 기본 enabled
            continue
        # enabled 속성
        if current_server and re.match(r"^\s+enabled:\s*false", line):
            servers[current_server] = False

    return servers


def _extract_module_docstring(py_path: Path) -> str:
    """Python 파일에서 모듈 docstring 첫 줄을 추출한다."""
    try:
        source = py_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        docstring = ast.get_docstring(tree)
        if docstring:
            return docstring.split("\n")[0].strip()
    except (SyntaxError, FileNotFoundError, UnicodeDecodeError):
        pass
    return ""


# ────────────────────────────────────────────
# 검증 함수들
# ────────────────────────────────────────────

Errors = list[str]


def check_services_md(mcp_servers: dict[str, bool]) -> Errors:
    """SERVICES.md에 활성화된 MCP 서버가 모두 언급되어 있는지 검증."""
    errors: Errors = []
    content = _read(ROOT / "SERVICES.md")
    if not content:
        errors.append("SERVICES.md: 파일이 없음")
        return errors

    enabled = {name for name, on in mcp_servers.items() if on}
    for name in sorted(enabled):
        if name not in content:
            errors.append(f"SERVICES.md: 활성 서버 '{name}' 미기재")

    return errors


def check_claude_md_modules() -> Errors:
    """CLAUDE.md의 '핵심 모듈' 테이블이 실제 모듈과 일치하는지 검증."""
    errors: Errors = []
    content = _read(ROOT / "CLAUDE.md")
    if not content:
        errors.append("CLAUDE.md: 파일이 없음")
        return errors

    # 실제 모듈 스캔 (core/, mcp/ 하위 .py, __init__ 제외)
    actual_modules: set[str] = set()
    for subdir in ["core", "mcp"]:
        module_dir = ROOT / "src" / "ai_env" / subdir
        if module_dir.is_dir():
            for py in module_dir.glob("*.py"):
                if py.name != "__init__.py":
                    actual_modules.add(f"{subdir}/{py.stem}")

    # CLAUDE.md에서 모듈 테이블 파싱 (| `core/config.py` | ... | 형식)
    documented: set[str] = set()
    for m in re.finditer(r"\|\s*`((?:core|mcp|cli)/[\w.]+)`\s*\|", content):
        name = m.group(1)
        # .py 확장자 제거
        documented.add(name.replace(".py", "").rstrip("/"))

    # cli/ 는 디렉토리로 기재되므로 제외
    missing = actual_modules - documented - {"cli"}
    for mod in sorted(missing):
        errors.append(f"CLAUDE.md: 모듈 '{mod}' 핵심 모듈 테이블에 미기재")

    return errors


def check_setup_md_env_keys(mcp_servers: dict[str, bool]) -> Errors:
    """SETUP.md에 MCP 서버가 요구하는 환경변수가 모두 언급되어 있는지 검증."""
    errors: Errors = []
    content = _read(ROOT / "SETUP.md")
    if not content:
        errors.append("SETUP.md: 파일이 없음")
        return errors

    # mcp_servers.yaml에서 env_keys 수집
    yaml_text = _read(ROOT / "config" / "mcp_servers.yaml")
    required_keys: set[str] = set()

    # 간이 파싱: env_keys 섹션의 - KEY 항목
    in_env_keys = False
    current_server: str | None = None
    for line in yaml_text.splitlines():
        server_m = re.match(r"^  (\w[\w-]*):\s*$", line)
        if server_m:
            current_server = server_m.group(1)
            in_env_keys = False
            continue
        if re.match(r"^\s+env_keys:\s*$", line):
            in_env_keys = True
            continue
        if in_env_keys:
            key_m = re.match(r"^\s+-\s+(\w+)", line)
            if key_m and current_server and mcp_servers.get(current_server, False):
                required_keys.add(key_m.group(1))
            elif not re.match(r"^\s+-", line):
                in_env_keys = False

    for key in sorted(required_keys):
        if key not in content:
            errors.append(f"SETUP.md: 환경변수 '{key}' 미기재")

    return errors


def check_project_structure() -> Errors:
    """CLAUDE.md의 프로젝트 구조 섹션에 주요 디렉토리가 언급되어 있는지 검증."""
    errors: Errors = []
    content = _read(ROOT / "CLAUDE.md")

    # 실제 존재하는 주요 디렉토리
    key_dirs = ["config/", "src/ai_env/", ".claude/", "tests/"]
    for d in key_dirs:
        if (ROOT / d.rstrip("/")).is_dir() and d not in content:
            errors.append(f"CLAUDE.md: 프로젝트 구조에 '{d}' 미기재")

    return errors


def check_skills_integrity() -> Errors:
    """스킬 디렉토리 무결성 검증: 디렉토리가 있으면 SKILL.md도 있어야 한다."""
    errors: Errors = []
    skills_dir = ROOT / ".claude" / "skills"
    if not skills_dir.is_dir():
        return errors

    for skill_dir in sorted(skills_dir.iterdir()):
        if skill_dir.is_dir() and not skill_dir.name.startswith("."):
            if not (skill_dir / "SKILL.md").exists():
                errors.append(f".claude/skills/{skill_dir.name}: SKILL.md 없음 (sync 대상 아님)")

    return errors


# ────────────────────────────────────────────
# 자동 수정 함수들
# ────────────────────────────────────────────


def fix_claude_md_modules() -> list[str]:
    """CLAUDE.md 핵심 모듈 테이블에 누락된 모듈을 자동 추가한다.

    Returns:
        수정된 항목 목록 (빈 리스트면 수정 없음)
    """
    claude_md = ROOT / "CLAUDE.md"
    content = _read(claude_md)
    if not content:
        return []

    # 실제 모듈 스캔
    actual_modules: dict[str, Path] = {}
    for subdir in ["core", "mcp"]:
        module_dir = ROOT / "src" / "ai_env" / subdir
        if module_dir.is_dir():
            for py in sorted(module_dir.glob("*.py")):
                if py.name != "__init__.py":
                    actual_modules[f"{subdir}/{py.stem}"] = py

    # 문서에 기재된 모듈
    documented: set[str] = set()
    for m in re.finditer(r"\|\s*`((?:core|mcp|cli)/[\w.]+)`\s*\|", content):
        name = m.group(1)
        documented.add(name.replace(".py", "").rstrip("/"))

    missing = set(actual_modules.keys()) - documented - {"cli"}
    if not missing:
        return []

    # 테이블 마지막 행 찾기 (| `cli/` | ... | 패턴 바로 앞에 삽입)
    # cli/ 행이 테이블의 마지막이므로 그 앞에 추가
    lines = content.splitlines()
    insert_idx = -1
    for i, line in enumerate(lines):
        if re.match(r"\|\s*`cli/`\s*\|", line):
            insert_idx = i
            break

    if insert_idx == -1:
        # cli/ 행이 없으면 테이블 마지막 행 뒤에 추가
        for i, line in enumerate(lines):
            if re.match(r"\|\s*`(core|mcp)/", line):
                insert_idx = i + 1
        if insert_idx == -1:
            return []

    # 누락 모듈 행 생성 (docstring에서 역할 추출)
    new_rows: list[str] = []
    fixed: list[str] = []
    for mod in sorted(missing):
        py_path = actual_modules[mod]
        desc = _extract_module_docstring(py_path)
        if not desc:
            desc = f"`{mod}` 모듈"
        new_rows.append(f"| `{mod}.py` | {desc} |")
        fixed.append(mod)

    # 삽입
    for row in reversed(new_rows):
        lines.insert(insert_idx, row)

    claude_md.write_text("\n".join(lines), encoding="utf-8")
    return fixed


# ────────────────────────────────────────────
# 메인
# ────────────────────────────────────────────


def main() -> int:
    fix_mode = "--fix" in sys.argv

    yaml_text = _read(ROOT / "config" / "mcp_servers.yaml")
    mcp_servers = _parse_yaml_servers(yaml_text)

    # --fix 모드: 자동 수정 가능한 항목 먼저 수정
    fixed_files: list[str] = []
    if fix_mode:
        fixed_modules = fix_claude_md_modules()
        if fixed_modules:
            fixed_files.append("CLAUDE.md")
            for mod in fixed_modules:
                print(f"  [fix] CLAUDE.md: 모듈 '{mod}' 테이블에 추가")

    # 수정 후 재검증
    all_errors: Errors = []
    all_errors.extend(check_services_md(mcp_servers))
    all_errors.extend(check_claude_md_modules())
    all_errors.extend(check_setup_md_env_keys(mcp_servers))
    all_errors.extend(check_project_structure())
    all_errors.extend(check_skills_integrity())

    if fixed_files and not all_errors:
        # 자동 수정으로 모든 문제 해결됨 → 파일이 수정되었으므로 exit 1
        # (pre-commit이 "files were modified" 감지 → 사용자가 re-stage)
        print(f"Doc Sync: {', '.join(fixed_files)} 자동 수정됨 (re-stage 필요)")
        return 1

    if all_errors:
        print("=" * 60)
        print("  Doc Sync Check: 문서 ↔ 코드 불일치 발견")
        print("=" * 60)
        for err in all_errors:
            print(f"  - {err}")
        print()
        if fix_mode:
            print("자동 수정할 수 없는 항목입니다. '/doc-sync'를 실행하세요.")
        else:
            print("'/doc-sync'를 실행하거나 문서를 직접 수정하세요.")
            print("긴급 시 --no-verify 로 우회 가능 (비권장).")
        print("=" * 60)
        return 1

    print("Doc Sync Check: OK (문서 ↔ 코드 정합성 통과)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
