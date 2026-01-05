"""Synchronization logic for ai-env."""

from __future__ import annotations

import shutil
from pathlib import Path

from .config import get_project_root
from .secrets import get_secrets_manager


def _sync_file(src: Path, dst: Path, dry_run: bool) -> tuple[str, int]:
    """단일 파일 동기화

    Args:
        src: 소스 파일 경로
        dst: 목적지 파일 경로
        dry_run: True면 실제 복사하지 않음

    Returns:
        (파일 이름, 복사된 파일 수)

    Raises:
        OSError: 파일 복사 실패 시
        PermissionError: 권한 오류 시
    """
    if not dry_run:
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        except PermissionError as e:
            raise PermissionError(f"Permission denied copying {src} to {dst}") from e
        except OSError as e:
            raise OSError(f"Failed to copy {src} to {dst}: {e}") from e
    return src.name, 1


def _sync_md_files(src: Path, dst: Path, dry_run: bool) -> tuple[str, int]:
    """디렉토리 내 .md 파일만 동기화 (commands/ 디렉토리용)

    Args:
        src: 소스 디렉토리
        dst: 목적지 디렉토리
        dry_run: True면 실제 복사하지 않음

    Returns:
        (설명, 복사된 파일 수)
    """
    md_files = list(src.glob("*.md"))

    if not dry_run:
        dst.mkdir(parents=True, exist_ok=True)
        for md_file in md_files:
            shutil.copy2(md_file, dst / md_file.name)

    return f"{src.name}/ ({len(md_files)} files)", len(md_files)


def _sync_subdirectories(src: Path, dst: Path, dry_run: bool) -> tuple[str, int]:
    """서브디렉토리들 동기화 (skills/ 디렉토리용)

    Args:
        src: 소스 디렉토리
        dst: 목적지 디렉토리
        dry_run: True면 실제 복사하지 않음

    Returns:
        (설명, 복사된 디렉토리 수)
    """
    subdirs = [d for d in src.iterdir() if d.is_dir() and not d.name.startswith(".")]

    if not dry_run:
        dst.mkdir(parents=True, exist_ok=True)
        for subdir in subdirs:
            dst_subdir = dst / subdir.name
            if dst_subdir.exists():
                shutil.rmtree(dst_subdir)
            shutil.copytree(subdir, dst_subdir)

    return f"{src.name}/ ({len(subdirs)} items)", len(subdirs)


def _sync_directory(src: Path, dst: Path, dry_run: bool) -> tuple[str, int]:
    """일반 디렉토리 동기화 (전체 복사)

    Args:
        src: 소스 디렉토리
        dst: 목적지 디렉토리
        dry_run: True면 실제 복사하지 않음

    Returns:
        (설명, 복사된 항목 수)
    """
    if not dry_run:
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)

    return f"{src.name}/", 1


def _sync_file_or_dir(src: Path, dst: Path, dry_run: bool = False) -> tuple[str, int]:
    """파일이나 디렉토리 동기화 (공통 로직)

    동기화 전략:
    - 파일: 단순 복사
    - commands/ 디렉토리: .md 파일만 복사
    - skills/ 디렉토리: 서브디렉토리 전체 복사
    - 기타 디렉토리: 전체 복사

    Args:
        src: 소스 경로
        dst: 목적지 경로
        dry_run: True면 실제 복사하지 않음

    Returns:
        (설명, 복사된 항목 수)
    """
    if not src.exists():
        return "", 0

    if src.is_file():
        return _sync_file(src, dst, dry_run)

    # 디렉토리 처리
    if src.name == "commands":
        return _sync_md_files(src, dst, dry_run)
    elif src.name == "skills":
        return _sync_subdirectories(src, dst, dry_run)
    else:
        return _sync_directory(src, dst, dry_run)


def sync_claude_global_config(dry_run: bool = False) -> dict[str, str]:
    """
    글로벌 Claude Code 설정 동기화
    ai-env/.claude → ~/.claude
    (CLAUDE.md, commands/, skills/, settings.json)
    """
    project_root = get_project_root()
    source_dir = project_root / ".claude"
    global_dir = source_dir / "global"  # CLAUDE.md와 settings.json.template 위치
    target_dir = Path.home() / ".claude"

    results: dict[str, str] = {}

    if not source_dir.exists():
        return results

    # 1. CLAUDE.md 동기화 (global/에서)
    desc, _ = _sync_file_or_dir(global_dir / "CLAUDE.md", target_dir / "CLAUDE.md", dry_run)
    if desc:
        results[desc] = str(target_dir / "CLAUDE.md")

    # 2. settings.json 생성 (환경변수 치환, global/에서)
    settings_template = global_dir / "settings.json.template"
    settings_dst = target_dir / "settings.json"
    if settings_template.exists():
        sm = get_secrets_manager()
        with open(settings_template) as f:
            content = f.read()

        # 환경변수 치환
        env_vars = sm.list()
        for key, value in env_vars.items():
            if value:  # 빈 값은 치환하지 않음
                content = content.replace(f"${{{key}}}", value)

        if not dry_run:
            settings_dst.parent.mkdir(parents=True, exist_ok=True)
            with open(settings_dst, "w") as f:
                f.write(content)
        results["settings.json"] = str(settings_dst)

    # 3. commands/ 동기화 (.claude/commands → ~/.claude/commands)
    desc, _ = _sync_file_or_dir(source_dir / "commands", target_dir / "commands", dry_run)
    if desc:
        results[desc] = str(target_dir / "commands")

    # 4. skills/ 동기화 (.claude/skills → ~/.claude/skills)
    desc, _ = _sync_file_or_dir(source_dir / "skills", target_dir / "skills", dry_run)
    if desc:
        results[desc] = str(target_dir / "skills")

    return results
