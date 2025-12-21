"""ai-env CLI"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from .core import (
    get_secrets_manager,
    load_mcp_config,
    load_settings,
)
from .mcp import MCPConfigGenerator

console = Console()


def get_project_root() -> Path:
    """프로젝트 루트 디렉토리 반환"""
    return Path(__file__).parent.parent.parent


@click.group()
@click.version_option()
def main() -> None:
    """AI 개발 환경 통합 관리 도구"""
    pass


# === Setup 명령어 (초기 설정 가이드) ===
@main.command()
def setup() -> None:
    """초기 설정 가이드 (처음 사용자용)"""
    console.print("[bold cyan]🚀 ai-env 초기 설정 가이드[/bold cyan]\n")

    sm = get_secrets_manager()

    # 1. .env 파일 확인
    console.print("[bold]1. 환경변수 설정 파일 (.env)[/bold]")
    if sm.env_file.exists():
        env_count = len(sm.list())
        console.print(f"  [green]✓[/green] .env 파일 존재 ({env_count} 개 변수)")
    else:
        console.print("  [red]✗[/red] .env 파일이 없습니다")
        console.print("\n  [yellow]다음 단계를 따라 .env 파일을 생성하세요:[/yellow]")
        console.print("    1. [cyan]cp .env.example .env[/cyan]")
        console.print("    2. [cyan]vi .env[/cyan]  또는  [cyan]open -e .env[/cyan]")
        console.print("    3. 필요한 토큰 값을 입력하세요")
        console.print("\n  [dim]💡 .env.example 파일에 모든 필수 변수가 나열되어 있습니다[/dim]")
        return  # .env 파일이 없으면 여기서 종료

    # 2. 필수 환경변수 체크
    console.print("\n[bold]2. 필수 환경변수 체크[/bold]")
    required_vars = {
        "AI API Keys": ["ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GOOGLE_API_KEY"],
        "GitHub": ["GITHUB_GLASSLEGO_TOKEN"],
        "Atlassian": [
            "JIRA_URL",
            "JIRA_PERSONAL_TOKEN",
            "CONFLUENCE_URL",
            "CONFLUENCE_PERSONAL_TOKEN",
        ],
        "Notion": ["NOTION_API_TOKEN"],
    }

    for category, vars_list in required_vars.items():
        missing = [v for v in vars_list if not sm.get(v)]
        if not missing:
            console.print(f"  [green]✓[/green] {category}: 모두 설정됨")
        else:
            console.print(f"  [yellow]○[/yellow] {category}: {len(missing)}개 누락")
            for var in missing[:2]:
                console.print(f"    - {var}")
            if len(missing) > 2:
                console.print(f"    ... and {len(missing) - 2} more")

    # 3. MCP 서버 설정 확인
    console.print("\n[bold]3. MCP 서버 설정[/bold]")
    mcp_config = load_mcp_config()
    enabled_servers = [name for name, srv in mcp_config.mcp_servers.items() if srv.enabled]
    console.print(f"  [green]✓[/green] {len(enabled_servers)}개 MCP 서버 활성화됨")
    for name in enabled_servers[:3]:
        console.print(f"    - {name}")
    if len(enabled_servers) > 3:
        console.print(f"    ... and {len(enabled_servers) - 3} more")

    # 4. 다음 단계 안내
    console.print("\n[bold cyan]📋 다음 단계:[/bold cyan]")
    console.print("  1. 환경변수 확인: [cyan]ai-env secrets[/cyan]          (마스킹된 목록)")
    console.print("                   [cyan]ai-env secrets --show[/cyan]   (실제 값 표시)")
    console.print("  2. 설정 확인:    [cyan]ai-env status[/cyan]")
    console.print("  3. 동기화 실행:  [cyan]ai-env sync --dry-run[/cyan]  (미리보기)")
    console.print("                   [cyan]ai-env sync[/cyan]            (실제 동기화)")
    console.print("\n[dim]📖 상세 가이드: SETUP.md, SERVICES.md 참조[/dim]")
    console.print(f"[dim]💡 환경변수 수정: vi {sm.env_file}[/dim]")


# === Secrets 명령어 (읽기 전용) ===
@main.command("secrets")
@click.option("--show", is_flag=True, help="실제 값 표시 (마스킹 해제)")
def secrets(show: bool) -> None:
    """환경변수 목록 조회 (.env 파일에서)"""
    sm = get_secrets_manager()

    if not sm.env_file.exists():
        console.print(f"[red]✗ .env file not found: {sm.env_file}[/red]")
        console.print("\n[yellow]Create a .env file with your environment variables:[/yellow]")
        console.print("  [dim]$ cp .env.example .env[/dim]")
        console.print("  [dim]$ vi .env[/dim]")
        return

    table = Table(title=f"Environment Variables ({sm.env_file})")
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="green")

    data = sm.list() if show else sm.list_masked()
    for key, value in sorted(data.items()):
        if not key.startswith("#"):
            table.add_row(key, value)

    console.print(table)
    console.print(f"\n[dim]💡 Edit {sm.env_file} to modify environment variables[/dim]")


# === Config 명령어 그룹 ===
@main.group()
def config() -> None:
    """설정 관리"""
    pass


@config.command("show")
def config_show() -> None:
    """현재 설정 표시"""
    settings = load_settings()
    mcp_config = load_mcp_config()

    console.print("\n[bold cyan]Settings[/bold cyan]")
    console.print(f"  Version: {settings.version}")
    console.print(f"  Default Agent: {settings.default_agent}")
    console.print(f"  Env File: {settings.env_file}")

    console.print("\n[bold cyan]Providers[/bold cyan]")
    for name, provider in settings.providers.items():
        status = "[green]✓[/green]" if provider.enabled else "[red]✗[/red]"
        console.print(f"  {status} {name}: {provider.env_key}")

    console.print("\n[bold cyan]MCP Servers[/bold cyan]")
    for name, server in mcp_config.mcp_servers.items():
        status = "[green]✓[/green]" if server.enabled else "[red]✗[/red]"
        targets = ", ".join(server.targets)
        console.print(f"  {status} {name} ({server.type}): {targets}")


# === Generate 명령어 그룹 ===
@main.group()
def generate() -> None:
    """설정 파일 생성"""
    pass


@generate.command("all")
@click.option("--dry-run", is_flag=True, help="실제 저장하지 않고 미리보기")
def generate_all(dry_run: bool) -> None:
    """모든 설정 파일 생성"""
    sm = get_secrets_manager()
    generator = MCPConfigGenerator(sm)

    results = generator.save_all(dry_run=dry_run)

    action = "Would save" if dry_run else "Saved"
    for name, path in results.items():
        console.print(f"[green]✓ {action}[/green] {name}: {path}")


@generate.command("claude-desktop")
@click.option("--output", "-o", help="출력 경로")
def generate_claude_desktop(output: str | None) -> None:
    """Claude Desktop 설정 생성"""
    sm = get_secrets_manager()
    generator = MCPConfigGenerator(sm)
    config = generator.generate_claude_desktop()

    if output:
        with open(output, "w") as f:
            json.dump(config, f, indent=2)
        console.print(f"[green]✓ Saved to {output}[/green]")
    else:
        console.print_json(json.dumps(config))


@generate.command("antigravity")
@click.option("--output", "-o", help="출력 경로")
def generate_antigravity(output: str | None) -> None:
    """Antigravity 설정 생성"""
    sm = get_secrets_manager()
    generator = MCPConfigGenerator(sm)
    config = generator.generate_antigravity()

    if output:
        with open(output, "w") as f:
            json.dump(config, f, indent=2)
        console.print(f"[green]✓ Saved to {output}[/green]")
    else:
        console.print_json(json.dumps(config))


@generate.command("shell")
@click.option("--output", "-o", help="출력 경로")
def generate_shell(output: str | None) -> None:
    """Shell export 스크립트 생성"""
    sm = get_secrets_manager()
    content = sm.export_to_shell()

    if output:
        with open(output, "w") as f:
            f.write(content)
        console.print(f"[green]✓ Saved to {output}[/green]")
    else:
        console.print(content)


def _sync_file_or_dir(src: Path, dst: Path, dry_run: bool = False) -> tuple[str, int]:
    """
    파일이나 디렉토리 동기화 (공통 로직)

    Returns:
        (description, count) - 설명과 항목 수
    """
    if not src.exists():
        return "", 0

    if src.is_file():
        # 단일 파일 복사
        if not dry_run:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        return src.name, 1

    elif src.is_dir():
        # 디렉토리 복사
        if not dry_run:
            dst.mkdir(parents=True, exist_ok=True)

        # .md 파일만 복사 (commands/ 용)
        if src.name == "commands":
            md_files = list(src.glob("*.md"))
            if not dry_run:
                for md_file in md_files:
                    shutil.copy2(md_file, dst / md_file.name)
            return f"{src.name}/ ({len(md_files)} files)", len(md_files)

        # 디렉토리 전체 복사 (skills/ 용)
        else:
            subdirs = [d for d in src.iterdir() if d.is_dir() and not d.name.startswith(".")]
            if not dry_run:
                for subdir in subdirs:
                    dst_subdir = dst / subdir.name
                    if dst_subdir.exists():
                        shutil.rmtree(dst_subdir)
                    shutil.copytree(subdir, dst_subdir)
            return f"{src.name}/ ({len(subdirs)} items)", len(subdirs)

    return "", 0


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
        console.print(f"[yellow]Warning: Source directory not found: {source_dir}[/yellow]")
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


# === Sync 명령어 ===
@main.command()
@click.option("--dry-run", is_flag=True, help="실제 저장하지 않고 미리보기")
@click.option("--claude-only", is_flag=True, help="Claude 글로벌 설정만 동기화")
@click.option("--mcp-only", is_flag=True, help="MCP 설정만 동기화")
def sync(dry_run: bool, claude_only: bool, mcp_only: bool) -> None:
    """
    설정 파일 동기화 (ai-env → 각 대상)

    동기화 대상:
    - Claude Code: ~/.claude (CLAUDE.md, commands/, skills/, settings.json)
    - Claude Desktop: ~/Library/Application Support/Claude/
    - Antigravity: ~/.gemini/antigravity/
    - Shell exports: ./generated/shell_exports.sh
    """
    console.print("[bold]🔄 Syncing AI environment configurations...[/bold]\n")

    # === 사전 검증 ===
    sm = get_secrets_manager()
    project_root = get_project_root()

    # .env 파일 존재 확인
    if not sm.env_file.exists():
        console.print(f"[yellow]⚠ Warning: .env file not found at {sm.env_file}[/yellow]")
        console.print("[dim]💡 Tip: Create .env file - 'cp .env.example .env' then edit it[/dim]\n")

    # 필수 환경변수 확인 (MCP 동기화 시)
    if not claude_only:
        mcp_config = load_mcp_config()

        # 활성화된 MCP 서버의 필수 환경변수 체크
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
            for var in missing_vars[:5]:  # 최대 5개만 표시
                console.print(f"  - {var}")
            if len(missing_vars) > 5:
                console.print(f"  ... and {len(missing_vars) - 5} more")
            console.print(f"\n[dim]💡 Tip: Edit {sm.env_file} to add missing variables[/dim]\n")

    console.print(f"[dim]Source: {project_root}[/dim]\n")

    action = "Would sync" if dry_run else "Synced"

    if not mcp_only:
        # Claude 글로벌 설정 동기화
        console.print("[bold cyan]📁 Claude Code Global Config[/bold cyan]")
        console.print("[dim]   ai-env/.claude → ~/.claude[/dim]")
        claude_results = sync_claude_global_config(dry_run=dry_run)

        if not claude_results:
            console.print("  [yellow]○ No files to sync (source directory empty)[/yellow]")
        else:
            for name, file_path in claude_results.items():
                console.print(f"  [green]✓[/green] {action} {name}")
                console.print(f"    → {file_path}")

    if claude_only:
        if not dry_run:
            console.print("\n[bold green]✓ Claude global config sync complete![/bold green]")
        return

    # MCP 설정 동기화
    console.print("\n[bold cyan]🔌 MCP Configurations[/bold cyan]")
    generator = MCPConfigGenerator(sm)

    try:
        results: dict[str, Path] = generator.save_all(dry_run=dry_run)

        for name in results:
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


# === Status 명령어 ===
@main.command()
def status() -> None:
    """현재 상태 확인"""
    settings = load_settings()
    sm = get_secrets_manager()
    project_root = get_project_root()

    console.print("[bold]🌐 AI Environment Status[/bold]\n")
    console.print(f"[dim]Project root: {project_root}[/dim]\n")

    # Provider 상태
    table = Table(title="AI Providers")
    table.add_column("Provider", style="cyan")
    table.add_column("Env Key", style="yellow")
    table.add_column("Status", style="green")

    for name, provider in settings.providers.items():
        if provider.enabled:
            value = sm.get(provider.env_key)
            status = "[green]✓ Configured[/green]" if value else "[red]✗ Missing[/red]"
            table.add_row(name, provider.env_key, status)

    console.print(table)

    # MCP 서버 상태
    mcp_config = load_mcp_config()

    console.print()
    table2 = Table(title="MCP Servers")
    table2.add_column("Server", style="cyan")
    table2.add_column("Type", style="yellow")
    table2.add_column("Targets")

    for name, server in mcp_config.mcp_servers.items():
        if server.enabled:
            targets = ", ".join(server.targets[:3])
            if len(server.targets) > 3:
                targets += f" (+{len(server.targets) - 3})"
            table2.add_row(name, server.type, targets)

    console.print(table2)

    # 글로벌 Claude 설정 상태
    console.print()
    table3 = Table(title="Claude Global Config (ai-env → ~/.claude)")
    table3.add_column("Item", style="cyan")
    table3.add_column("Source (ai-env)", style="yellow")
    table3.add_column("Target (~/.claude)", style="green")

    source_dir = project_root / ".claude"
    global_dir = source_dir / "global"
    target_dir = Path.home() / ".claude"

    items = [
        ("CLAUDE.md", global_dir / "CLAUDE.md", target_dir / "CLAUDE.md"),
        ("settings.json", global_dir / "settings.json.template", target_dir / "settings.json"),
        ("commands/", source_dir / "commands", target_dir / "commands"),
        ("skills/", source_dir / "skills", target_dir / "skills"),
    ]

    for name, src, dst in items:
        src_exists = src.exists()
        dst_exists = dst.exists()

        # 소스 상태
        if src_exists:
            if src.is_dir():
                count = len([f for f in src.iterdir() if not f.name.startswith(".")])
                src_status = f"[green]✓ ({count})[/green]"
            else:
                src_status = "[green]✓[/green]"
        else:
            src_status = "[red]✗[/red]"

        # 타겟 상태
        if dst_exists:
            if dst.is_dir():
                count = len([f for f in dst.iterdir() if not f.name.startswith(".")])
                dst_status = f"[green]✓ ({count})[/green]"
            else:
                dst_status = "[green]✓[/green]"
        else:
            dst_status = "[yellow]○ (not synced)[/yellow]"

        table3.add_row(name, src_status, dst_status)

    console.print(table3)

    console.print("\n[dim]💡 Run 'ai-env sync' to synchronize all configurations[/dim]")


if __name__ == "__main__":
    main()
