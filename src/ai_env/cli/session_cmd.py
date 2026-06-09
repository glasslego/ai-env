"""ai-env session — Obsidian 세션 노트 저장/조회 명령.

사용 예:
    ai-env session save --note "리뷰 1차 완료" --subdir 00_session
    ai-env session save --note "메모" --vault ~/Vaults/Other --dry-run
    ai-env session latest --cwd /path/to/project
"""

from __future__ import annotations

from pathlib import Path

import click

from ..core.session_save import (
    DEFAULT_CONTEXT_MAX_CHARS,
    DEFAULT_SUBDIR,
    build_latest_session_context,
    save_session,
)
from . import console, main


@main.group("session")
def session() -> None:
    """세션 컨텍스트를 Obsidian 등 외부 저장소에 보관."""


@session.command("save")
@click.option("--note", "-n", default=None, help="이번 세션의 메모 (필수 권장)")
@click.option("--title", "-t", default=None, help="노트 제목 (미지정 시 자동 생성)")
@click.option(
    "--vault",
    default=None,
    type=click.Path(),
    help="Obsidian vault 루트. 미지정 시 settings.yaml의 obsidian_base 사용",
)
@click.option(
    "--subdir",
    default=DEFAULT_SUBDIR,
    show_default=True,
    help="vault 내부 저장 디렉토리",
)
@click.option(
    "--cwd",
    default=None,
    type=click.Path(exists=True, file_okay=False),
    help="git 스냅샷을 수집할 디렉토리 (기본: 현재 디렉토리)",
)
@click.option(
    "--transcript-path",
    default=None,
    type=click.Path(exists=False, dir_okay=False),
    help="Claude/Codex transcript JSONL 경로. 있으면 압축 요약을 포함",
)
@click.option("--session-id", default=None, help="에이전트 세션 ID")
@click.option("--agent", default=None, help="에이전트 이름 (예: claude, codex)")
@click.option("--dry-run", is_flag=True, help="파일을 쓰지 않고 본문만 미리보기")
def session_save(
    note: str | None,
    title: str | None,
    vault: str | None,
    subdir: str,
    cwd: str | None,
    transcript_path: str | None,
    session_id: str | None,
    agent: str | None,
    dry_run: bool,
) -> None:
    """현재 세션 컨텍스트를 Obsidian vault에 마크다운으로 저장."""
    result = save_session(
        note=note,
        title=title,
        vault=vault,
        subdir=subdir,
        cwd=Path(cwd) if cwd else None,
        transcript_path=Path(transcript_path) if transcript_path else None,
        session_id=session_id,
        agent=agent,
        dry_run=dry_run,
    )

    if dry_run:
        console.print(f"[yellow]🔍 dry-run — would write to[/yellow] [cyan]{result.path}[/cyan]")
        console.print()
        # Rich markup 해석을 막기 위해 raw 출력
        console.print(result.body, markup=False, highlight=False)
        return

    console.print(f"[green]✓[/green] 세션 노트 저장 완료 — [cyan]{result.path}[/cyan]")


@session.command("latest")
@click.option(
    "--vault",
    default=None,
    type=click.Path(),
    help="Obsidian vault 루트. 미지정 시 settings.yaml의 obsidian_base 사용",
)
@click.option(
    "--subdir",
    default=DEFAULT_SUBDIR,
    show_default=True,
    help="vault 내부 저장 디렉토리",
)
@click.option(
    "--cwd",
    default=None,
    type=click.Path(exists=True, file_okay=False),
    help="프로젝트 식별에 사용할 디렉토리 (기본: 현재 디렉토리)",
)
@click.option("--project", default=None, help="프로젝트명 직접 지정")
@click.option(
    "--max-chars",
    default=DEFAULT_CONTEXT_MAX_CHARS,
    show_default=True,
    type=click.IntRange(min=1000),
    help="출력할 최대 문자 수",
)
@click.option("--path-only", is_flag=True, help="최신 세션 파일 경로만 출력")
def session_latest(
    vault: str | None,
    subdir: str,
    cwd: str | None,
    project: str | None,
    max_chars: int,
    path_only: bool,
) -> None:
    """현재 프로젝트의 최신 Obsidian 세션 컨텍스트를 출력."""
    result = build_latest_session_context(
        vault=vault,
        subdir=subdir,
        cwd=Path(cwd) if cwd else None,
        project_name=project,
        max_chars=max_chars,
    )

    if path_only:
        if result.path:
            console.print(str(result.path), markup=False, highlight=False)
        return

    if not result.found:
        console.print(f"[yellow]최신 세션 노트 없음[/yellow] — project={result.project_name}")
        return

    console.print(result.body, markup=False, highlight=False)
