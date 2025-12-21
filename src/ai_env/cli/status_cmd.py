"""status 명령어"""

from __future__ import annotations

from pathlib import Path

from ..core import get_project_root, get_secrets_manager, load_mcp_config, load_settings
from . import _create_table, console, main


@main.command()
def status() -> None:
    """현재 상태 확인"""
    settings = load_settings()
    sm = get_secrets_manager()
    project_root = get_project_root()

    console.print("[bold]🌐 AI Environment Status[/bold]\n")
    console.print(f"[dim]Project root: {project_root}[/dim]\n")

    # Provider 상태
    provider_rows = []
    for name, provider in settings.providers.items():
        if provider.enabled:
            value = sm.get(provider.env_key)
            status = "[green]✓ Configured[/green]" if value else "[red]✗ Missing[/red]"
            provider_rows.append((name, provider.env_key, status))

    table = _create_table(
        title="AI Providers",
        columns=[("Provider", "cyan"), ("Env Key", "yellow"), ("Status", "green")],
        rows=provider_rows,
    )
    console.print(table)

    # MCP 서버 상태
    mcp_config = load_mcp_config()
    enabled_mcp_servers = {
        name: server for name, server in mcp_config.mcp_servers.items() if server.enabled
    }
    mcp_rows = []
    for name, server in enabled_mcp_servers.items():
        targets = ", ".join(server.targets[:3])
        if len(server.targets) > 3:
            targets += f" (+{len(server.targets) - 3})"
        mcp_rows.append((name, server.type, targets))

    console.print()
    table2 = _create_table(
        title="MCP Servers",
        columns=[("Server", "cyan"), ("Type", "yellow"), ("Targets", "")],
        rows=mcp_rows,
    )
    console.print(table2)

    target_order = [
        "claude_desktop",
        "chatgpt_desktop",
        "codex_desktop",
        "antigravity",
        "claude_local",
        "codex",
        "gemini",
    ]
    target_rows = []
    for target in target_order:
        server_count = sum(1 for server in enabled_mcp_servers.values() if target in server.targets)
        target_rows.append((target, str(server_count)))

    console.print()
    table_target = _create_table(
        title="MCP Target Coverage",
        columns=[("Target", "cyan"), ("Enabled Servers", "green")],
        rows=target_rows,
    )
    console.print(table_target)

    full_coverage_servers = [
        name
        for name, server in enabled_mcp_servers.items()
        if all(target in server.targets for target in target_order)
    ]
    if full_coverage_servers:
        full_coverage_servers.sort()
        display_names = ", ".join(full_coverage_servers[:6])
        if len(full_coverage_servers) > 6:
            display_names += f", ... (+{len(full_coverage_servers) - 6})"
        console.print(
            f"[green]✓[/green] All-client MCP servers ({len(full_coverage_servers)}): "
            f"{display_names}"
        )

    # 글로벌 Claude 설정 상태
    source_dir = project_root / ".claude"
    global_dir = source_dir / "global"
    target_dir = Path.home() / ".claude"

    personal_skills_src = project_root / "megan-skills" / "skills"
    if not personal_skills_src.exists():
        personal_skills_src = source_dir / "skills"

    items = [
        ("CLAUDE.md", global_dir / "CLAUDE.md", target_dir / "CLAUDE.md"),
        ("settings.json", global_dir / "settings.json.template", target_dir / "settings.json"),
        ("commands/", source_dir / "commands", target_dir / "commands"),
        ("skills/", personal_skills_src, target_dir / "skills"),
    ]

    claude_rows = []
    for name, src, dst in items:
        if src.exists():
            if src.is_dir():
                count = len([f for f in src.iterdir() if not f.name.startswith(".")])
                src_status = f"[green]✓ ({count})[/green]"
            else:
                src_status = "[green]✓[/green]"
        else:
            src_status = "[red]✗[/red]"

        if dst.exists():
            if dst.is_dir():
                count = len([f for f in dst.iterdir() if not f.name.startswith(".")])
                dst_status = f"[green]✓ ({count})[/green]"
            else:
                dst_status = "[green]✓[/green]"
        else:
            dst_status = "[yellow]○ (not synced)[/yellow]"

        claude_rows.append((name, src_status, dst_status))

    console.print()
    table3 = _create_table(
        title="Claude Global Config (ai-env → ~/.claude)",
        columns=[("Item", "cyan"), ("Source (ai-env)", "yellow"), ("Target (~/.claude)", "green")],
        rows=claude_rows,
    )
    console.print(table3)

    console.print("\n[dim]💡 Run 'ai-env sync' to synchronize all configurations[/dim]")
