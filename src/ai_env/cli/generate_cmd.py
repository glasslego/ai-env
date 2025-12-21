"""generate 명령어 그룹"""

from __future__ import annotations

import click

from ..core import get_secrets_manager
from ..mcp import MCPConfigGenerator
from . import _output_content, console, main


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
    generator = MCPConfigGenerator(get_secrets_manager())
    _output_content(generator.generate_claude_desktop(), output)


@generate.command("chatgpt-desktop")
@click.option("--output", "-o", help="출력 경로")
def generate_chatgpt_desktop(output: str | None) -> None:
    """ChatGPT Desktop 설정 생성"""
    generator = MCPConfigGenerator(get_secrets_manager())
    _output_content(generator.generate_chatgpt_desktop(), output)


@generate.command("codex-desktop")
@click.option("--output", "-o", help="출력 경로")
def generate_codex_desktop(output: str | None) -> None:
    """Codex Desktop 설정 생성"""
    generator = MCPConfigGenerator(get_secrets_manager())
    _output_content(generator.generate_codex_desktop(), output)


@generate.command("antigravity")
@click.option("--output", "-o", help="출력 경로")
def generate_antigravity(output: str | None) -> None:
    """Antigravity 설정 생성"""
    generator = MCPConfigGenerator(get_secrets_manager())
    _output_content(generator.generate_antigravity(), output)


@generate.command("shell")
@click.option("--output", "-o", help="출력 경로")
def generate_shell(output: str | None) -> None:
    """Shell export 스크립트 생성"""
    _output_content(get_secrets_manager().export_to_shell(), output)
