"""sync 명령어"""

from __future__ import annotations

from pathlib import Path

import click

from ..core import get_project_root, get_secrets_manager, load_mcp_config
from ..core.sync import (
    sync_claude_global_config,
    sync_codex_global_config,
    sync_gemini_global_config,
)
from ..mcp import MCPConfigGenerator
from . import console, main


@main.command()
@click.option("--dry-run", is_flag=True, help="실제 저장하지 않고 미리보기")
@click.option("--claude-only", is_flag=True, help="Claude 글로벌 설정만 동기화")
@click.option("--mcp-only", is_flag=True, help="MCP 설정만 동기화")
@click.option(
    "--skills-include",
    multiple=True,
    help="추가할 팀 스킬 디렉토리 (기본은 megan-skills만 동기화, 예: --skills-include cde-skills). 여러 번 사용 가능.",
)
@click.option(
    "--skills-exclude",
    multiple=True,
    help="제외할 팀 스킬 디렉토리 (예: --skills-exclude cde-ranking-skills). 여러 번 사용 가능.",
)
def sync(
    dry_run: bool,
    claude_only: bool,
    mcp_only: bool,
    skills_include: tuple[str, ...],
    skills_exclude: tuple[str, ...],
) -> None:
    """설정 파일 동기화 (ai-env → 각 대상)"""
    console.print("[bold]🔄 Syncing AI environment configurations...[/bold]\n")

    sm = get_secrets_manager()
    project_root = get_project_root()

    # .env 파일 존재 확인
    if not sm.env_file.exists():
        console.print(f"[yellow]⚠ Warning: .env file not found at {sm.env_file}[/yellow]")
        console.print("[dim]💡 Tip: Create .env file - 'cp .env.example .env' then edit it[/dim]\n")

    # 필수 환경변수 확인 (MCP 동기화 시)
    if not claude_only:
        mcp_config = load_mcp_config()
        missing_vars = []
        for name, server in mcp_config.mcp_servers.items():
            if server.enabled:
                if server.type == "sse" and server.url_env:
                    if not sm.get(server.url_env):
                        missing_vars.append(f"{name}: {server.url_env}")
                elif server.env_keys:
                    for key in server.env_keys:
                        if not sm.get(key):
                            missing_vars.append(f"{name}: {key}")

        if missing_vars:
            console.print("[yellow]⚠ Warning: Missing environment variables:[/yellow]")
            for var in missing_vars[:5]:
                console.print(f"  - {var}")
            if len(missing_vars) > 5:
                console.print(f"  ... and {len(missing_vars) - 5} more")
            console.print(f"\n[dim]💡 Tip: Edit {sm.env_file} to add missing variables[/dim]\n")

    console.print(f"[dim]Source: {project_root}[/dim]\n")

    action = "Would sync" if dry_run else "Synced"

    if not mcp_only:
        console.print("[bold cyan]📁 Claude Code Global Config[/bold cyan]")
        console.print("[dim]   ai-env/.claude → ~/.claude[/dim]")
        claude_results = sync_claude_global_config(
            dry_run=dry_run,
            skills_include=list(skills_include) or None,
            skills_exclude=list(skills_exclude) or None,
        )

        if not claude_results:
            console.print("  [yellow]○ No files to sync (source directory empty)[/yellow]")
        else:
            for name, file_path in claude_results.items():
                console.print(f"  [green]✓[/green] {action} {name}")
                console.print(f"    → {file_path}")

        # Codex CLI 글로벌 설정 동기화
        console.print("\n[bold cyan]📁 Codex CLI Global Config[/bold cyan]")
        console.print("[dim]   ai-env/.claude/global/CLAUDE.md → ~/.codex/AGENTS.md[/dim]")
        codex_results = sync_codex_global_config(dry_run=dry_run)
        if not codex_results:
            console.print("  [yellow]○ No files to sync (source not found)[/yellow]")
        else:
            for name, file_path in codex_results.items():
                console.print(f"  [green]✓[/green] {action} {name}")
                console.print(f"    → {file_path}")

        # Gemini CLI 글로벌 설정 동기화
        console.print("\n[bold cyan]📁 Gemini CLI Global Config[/bold cyan]")
        console.print("[dim]   ai-env/.claude/global/CLAUDE.md → ~/.gemini/GEMINI.md[/dim]")
        gemini_results = sync_gemini_global_config(dry_run=dry_run)
        if not gemini_results:
            console.print("  [yellow]○ No files to sync (source not found)[/yellow]")
        else:
            for name, file_path in gemini_results.items():
                console.print(f"  [green]✓[/green] {action} {name}")
                console.print(f"    → {file_path}")

    if claude_only:
        if not dry_run:
            console.print("\n[bold green]✓ Claude global config sync complete![/bold green]")
        return

    # MCP 설정 동기화
    console.print("\n[bold cyan]🔌 AI Tools Configuration[/bold cyan]")
    generator = MCPConfigGenerator(sm)

    try:
        results: dict[str, Path] = generator.save_all(dry_run=dry_run)

        for name in sorted(results.keys()):
            path: Path = results[name]
            console.print(f"  [green]✓[/green] {action} {name}")
            console.print(f"    → {str(path)}")

        if not dry_run:
            console.print("\n[bold green]✓ Sync complete![/bold green]")
            console.print(
                "\n[dim]💡 Tip: Run 'source ./generated/shell_exports.sh' to load env vars[/dim]"
            )
    except Exception as e:
        console.print(f"\n[red]✗ Error during sync: {e}[/red]")
        if dry_run:
            console.print("[dim]Re-run without --dry-run to see detailed errors[/dim]")
        raise
