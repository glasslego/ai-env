"""project 명령어"""

from __future__ import annotations

from pathlib import Path

import click

from ..core import sync_project_claude_to_codex
from . import console, main


@main.group()
def project() -> None:
    """프로젝트 로컬 설정 관리"""
    pass


@project.command("sync-codex")
@click.option(
    "--project-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=Path.cwd(),
    show_default=True,
    help="대상 프로젝트 루트 경로",
)
@click.option("--copy", is_flag=True, help="AGENTS.md를 심볼릭 링크 대신 복사")
@click.option("--dry-run", is_flag=True, help="실제 변경 없이 미리보기")
@click.option("--agents-only", is_flag=True, help="CLAUDE.md → AGENTS.md만 동기화")
@click.option("--skills-only", is_flag=True, help=".claude/skills → .codex/skills만 동기화")
def project_sync_codex(
    project_dir: Path,
    copy: bool,
    dry_run: bool,
    agents_only: bool,
    skills_only: bool,
) -> None:
    """프로젝트의 Claude 지침/스킬을 Codex가 함께 쓰도록 연결"""
    sync_agents = not skills_only or agents_only
    sync_skills = not agents_only or skills_only

    agent_mode_label = "copy" if copy else "symlink"
    action = "Would sync" if dry_run else "Synced"

    console.print("[bold]🔗 Project Claude → Codex sync[/bold]")
    console.print(f"[dim]Project: {project_dir.resolve()}[/dim]")
    console.print(f"[dim]AGENTS mode: {agent_mode_label}[/dim]")
    console.print("[dim]Skills mode: codex-normalized copy[/dim]\n")

    results = sync_project_claude_to_codex(
        project_dir,
        use_copy=copy,
        dry_run=dry_run,
        sync_agents=sync_agents,
        sync_skills=sync_skills,
    )

    for result in results:
        if result.status == "missing":
            console.print(f"  [yellow]○[/yellow] Missing source: {result.source}")
            continue

        status_text = "unchanged" if result.status == "unchanged" else action
        console.print(f"  [green]✓[/green] {status_text} {result.name}")
        console.print(f"    {result.source} → {result.target}")
        if result.backup_path is not None:
            console.print(f"    [dim]backup: {result.backup_path}[/dim]")
