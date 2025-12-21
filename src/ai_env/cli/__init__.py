"""ai-env CLI"""

from __future__ import annotations

import json
import sys
from collections.abc import Sequence
from typing import Any

import click
from rich.console import Console
from rich.table import Table

from ..core import (
    get_secrets_manager,
    load_mcp_config,
    load_settings,
)


def _ensure_terminal_onlcr() -> None:
    """터미널 출력 모드 정상화: \\n → \\r\\n 변환(ONLCR) 보장.

    script/PTY 명령(claude --fallback 등) 사용 후 터미널 상태가 깨져
    줄바꿈 시 커서가 column 0으로 복귀하지 않는 문제를 자동 복구한다.
    """
    if not sys.stdout.isatty():
        return
    try:
        import termios

        fd = sys.stdout.fileno()
        attrs = termios.tcgetattr(fd)
        if not (attrs[1] & termios.ONLCR):
            attrs[1] |= termios.ONLCR
            termios.tcsetattr(fd, termios.TCSANOW, attrs)
    except (ImportError, termios.error, ValueError, OSError):
        pass


_ensure_terminal_onlcr()
console = Console()


def _create_table(
    title: str, columns: list[tuple[str, str]], rows: Sequence[tuple[str, ...]]
) -> Table:
    """테이블 생성 헬퍼 함수"""
    table = Table(title=title)
    for col_name, style in columns:
        table.add_column(col_name, style=style)
    for row in rows:
        table.add_row(*row)
    return table


def _output_content(content: dict[str, Any] | str, output: str | None) -> None:
    """생성된 설정을 출력하거나 파일로 저장하는 공통 함수"""
    if output:
        with open(output, "w") as f:
            if isinstance(content, dict):
                json.dump(content, f, indent=2)
            else:
                f.write(content)
        console.print(f"[green]✓ Saved to {output}[/green]")
    elif isinstance(content, dict):
        console.print_json(json.dumps(content))
    else:
        console.print(content)


@click.group()
@click.version_option()
def main() -> None:
    """AI 개발 환경 통합 관리 도구"""
    pass


# === Setup 명령어 ===
@main.command()
def setup() -> None:
    """초기 설정 가이드 (처음 사용자용)"""
    console.print("[bold cyan]🚀 ai-env 초기 설정 가이드[/bold cyan]\n")

    sm = get_secrets_manager()

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
        return

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

    console.print("\n[bold]3. MCP 서버 설정[/bold]")
    mcp_config = load_mcp_config()
    enabled_servers = [name for name, srv in mcp_config.mcp_servers.items() if srv.enabled]
    console.print(f"  [green]✓[/green] {len(enabled_servers)}개 MCP 서버 활성화됨")
    for name in enabled_servers[:3]:
        console.print(f"    - {name}")
    if len(enabled_servers) > 3:
        console.print(f"    ... and {len(enabled_servers) - 3} more")

    console.print("\n[bold cyan]📋 다음 단계:[/bold cyan]")
    console.print("  1. 환경변수 확인: [cyan]ai-env secrets[/cyan]          (마스킹된 목록)")
    console.print("                   [cyan]ai-env secrets --show[/cyan]   (실제 값 표시)")
    console.print("  2. 설정 확인:    [cyan]ai-env status[/cyan]")
    console.print("  3. 동기화 실행:  [cyan]ai-env sync --dry-run[/cyan]  (미리보기)")
    console.print("                   [cyan]ai-env sync[/cyan]            (실제 동기화)")
    console.print("\n[dim]📖 상세 가이드: SETUP.md, SERVICES.md 참조[/dim]")
    console.print(f"[dim]💡 환경변수 수정: vi {sm.env_file}[/dim]")


# === Secrets 명령어 ===
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

    data = sm.list() if show else sm.list_masked()
    rows = [(key, value) for key, value in sorted(data.items()) if not key.startswith("#")]

    table = _create_table(
        title=f"Environment Variables ({sm.env_file})",
        columns=[("Key", "cyan"), ("Value", "green")],
        rows=rows,
    )
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


# 서브 명령어 모듈 등록
from . import doctor_cmd, generate_cmd, pipeline_cmd, status_cmd, sync_cmd  # noqa: E402, F401
