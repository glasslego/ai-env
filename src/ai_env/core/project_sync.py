"""Project-local Claude to Codex sync helpers."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .codex_skills import copy_skill_tree_for_codex


@dataclass
class ProjectSyncResult:
    """단일 프로젝트 동기화 결과."""

    name: str
    source: Path
    target: Path
    status: str
    mode: str
    backup_path: Path | None = None


def _timestamp() -> str:
    """백업 파일명용 타임스탬프 반환."""
    return datetime.now().strftime("%Y%m%d%H%M%S")


def _backup_target_path(target: Path) -> Path:
    """대상 경로의 백업 경로 반환."""
    return target.with_name(f"{target.name}.bak.{_timestamp()}")


def _is_same_symlink(target: Path, source: Path) -> bool:
    """대상이 동일한 소스를 가리키는 심볼릭 링크인지 확인."""
    if not target.is_symlink():
        return False

    try:
        return target.resolve() == source.resolve()
    except OSError:
        return False


def _prepare_target(target: Path, dry_run: bool) -> Path | None:
    """대상 경로를 교체 가능 상태로 준비 (기존 파일 백업/제거).

    - 심볼릭 링크면 제거
    - 일반 파일/디렉토리면 .bak 백업 후 제거

    Returns:
        백업 경로 (백업이 생성된 경우) 또는 None
    """
    backup_path: Path | None = None

    if target.is_symlink():
        if not dry_run:
            target.unlink()
    elif target.exists():
        backup_path = _backup_target_path(target)
        if not dry_run:
            shutil.move(str(target), str(backup_path))

    if not dry_run:
        target.parent.mkdir(parents=True, exist_ok=True)

    return backup_path


def _replace_with_symlink(source: Path, target: Path, dry_run: bool) -> tuple[str, Path | None]:
    """파일 또는 디렉토리를 심볼릭 링크로 교체."""
    if _is_same_symlink(target, source):
        return "unchanged", None

    backup_path = _prepare_target(target, dry_run)

    if not dry_run:
        rel_source = os.path.relpath(source, start=target.parent)
        target.symlink_to(rel_source)

    return "linked", backup_path


def _replace_with_copy(source: Path, target: Path, dry_run: bool) -> tuple[str, Path | None]:
    """파일 또는 디렉토리를 복사본으로 교체."""
    backup_path = _prepare_target(target, dry_run)

    if not dry_run:
        if source.is_dir():
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)

    return "copied", backup_path


def _sync_one(
    name: str,
    source: Path,
    target: Path,
    use_copy: bool,
    dry_run: bool,
) -> ProjectSyncResult:
    """단일 항목 동기화."""
    mode = "copy" if use_copy else "link"

    if not source.exists():
        return ProjectSyncResult(
            name=name,
            source=source,
            target=target,
            status="missing",
            mode=mode,
        )

    if use_copy:
        status, backup_path = _replace_with_copy(source, target, dry_run)
    else:
        status, backup_path = _replace_with_symlink(source, target, dry_run)

    return ProjectSyncResult(
        name=name,
        source=source,
        target=target,
        status=status,
        mode=mode,
        backup_path=backup_path,
    )


def _sync_codex_skills(
    source: Path,
    target: Path,
    dry_run: bool,
) -> ProjectSyncResult:
    """Codex skills 디렉토리를 정규화 복사한다."""
    if not source.exists():
        return ProjectSyncResult(
            name=".codex/skills",
            source=source,
            target=target,
            status="missing",
            mode="codex-copy",
        )

    backup_path = _prepare_target(target, dry_run)

    if not dry_run:
        copy_skill_tree_for_codex(source, target)

    return ProjectSyncResult(
        name=".codex/skills",
        source=source,
        target=target,
        status="copied",
        mode="codex-copy",
        backup_path=backup_path,
    )


def sync_project_claude_to_codex(
    project_dir: Path,
    *,
    use_copy: bool = False,
    dry_run: bool = False,
    sync_agents: bool = True,
    sync_skills: bool = True,
) -> list[ProjectSyncResult]:
    """프로젝트의 Claude 자산을 Codex가 사용할 수 있게 동기화.

    기본 정책:
    - `CLAUDE.md` → `AGENTS.md`
    - `.claude/skills/` → `.codex/skills/`
    - `AGENTS.md`는 기본 모드에서 심볼릭 링크이며, `use_copy=True`면 복사한다.
    - skills는 항상 Codex 호환 YAML frontmatter로 정규화된 복사본을 만든다.
    - 기존 일반 파일/디렉토리는 `.bak.<timestamp>`로 백업 후 교체한다.

    Args:
        project_dir: 프로젝트 루트 디렉토리.
        use_copy: True면 심볼릭 링크 대신 복사.
        dry_run: True면 실제 파일 변경 없이 결과만 계산.
        sync_agents: True면 `CLAUDE.md` → `AGENTS.md` 동기화.
        sync_skills: True면 `.claude/skills` → `.codex/skills` 동기화.

    Returns:
        동기화 결과 목록.
    """
    resolved_project_dir = project_dir.resolve()
    results: list[ProjectSyncResult] = []

    if sync_agents:
        results.append(
            _sync_one(
                "AGENTS.md",
                resolved_project_dir / "CLAUDE.md",
                resolved_project_dir / "AGENTS.md",
                use_copy,
                dry_run,
            )
        )

    if sync_skills:
        results.append(
            _sync_codex_skills(
                resolved_project_dir / ".claude" / "skills",
                resolved_project_dir / ".codex" / "skills",
                dry_run,
            )
        )

    return results
