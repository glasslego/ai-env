"""Claude Code on Bedrock setup commands."""

from __future__ import annotations

import json
from pathlib import Path

import click

from ..core.bedrock import (
    BEDROCK_PROFILE_NAME,
    BEDROCK_SSO_SESSION_NAME,
    BedrockCommandResult,
    BedrockSsoConfig,
    aws_caller_identity,
    aws_sso_login,
    check_tool,
    configure_bedrock_sso,
    default_aws_config_path,
    default_gateway_token_helper,
    gateway_token_status,
    is_bedrock_sso_configured,
)
from . import console, main


@main.group("bedrock")
def bedrock() -> None:
    """Claude Code on Bedrock 설정 자동화."""


def _bedrock_config(profile: str, session_name: str | None) -> BedrockSsoConfig:
    """Build Bedrock SSO config from CLI options."""
    return BedrockSsoConfig(
        profile_name=profile,
        sso_session_name=session_name or BEDROCK_SSO_SESSION_NAME,
    )


def _aws_config_path(path: Path | None) -> Path:
    """Resolve AWS config path from CLI option."""
    return path or default_aws_config_path()


def _print_tool_status(name: str) -> None:
    """Print whether a required command is installed."""
    ok, resolved = check_tool(name)
    if ok:
        console.print(f"  [green]✓[/green] {name}: {resolved}")
    else:
        console.print(f"  [yellow]○[/yellow] {name}: not found")


def _print_identity(result: BedrockCommandResult) -> None:
    """Print masked AWS identity verification result."""
    if not result.ok:
        detail = result.stderr or result.stdout or f"exit {result.returncode}"
        console.print(f"  [red]✗[/red] AWS SSO auth: {detail}")
        return

    try:
        identity = json.loads(result.stdout)
    except json.JSONDecodeError:
        console.print("  [green]✓[/green] AWS SSO auth: ok")
        return

    account = identity.get("Account", "")
    arn = identity.get("Arn", "")
    console.print(f"  [green]✓[/green] AWS SSO auth: account={account}")
    if arn:
        console.print(f"    [dim]{arn}[/dim]")


def _print_gateway_token(result: BedrockCommandResult) -> None:
    """Print masked gateway token helper status."""
    if result.ok:
        console.print(f"  [green]✓[/green] Gateway token: {result.stdout}")
        return
    detail = result.stderr or result.stdout or f"exit {result.returncode}"
    console.print(f"  [red]✗[/red] Gateway token: {detail}")


@bedrock.command("setup")
@click.option("--dry-run", is_flag=True, help="~/.aws/config를 쓰지 않고 결과만 표시")
@click.option("--login", is_flag=True, help="설정 후 aws sso login 실행")
@click.option("--verify", is_flag=True, help="설정 후 aws sts get-caller-identity 실행")
@click.option("--verify-token", is_flag=True, help="Gateway token helper까지 검증")
@click.option("--profile", default=BEDROCK_PROFILE_NAME, show_default=True, help="AWS profile 이름")
@click.option(
    "--session-name",
    default=BEDROCK_SSO_SESSION_NAME,
    show_default=True,
    help="AWS SSO session 이름",
)
@click.option(
    "--aws-config",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="AWS config 파일 경로 (테스트/고급 옵션)",
)
def bedrock_setup(
    dry_run: bool,
    login: bool,
    verify: bool,
    verify_token: bool,
    profile: str,
    session_name: str,
    aws_config: Path | None,
) -> None:
    """Bedrock용 AWS SSO 프로필을 비대화형으로 생성/갱신."""
    config = _bedrock_config(profile, session_name)
    path = _aws_config_path(aws_config)

    console.print("[bold cyan]Claude Code on Bedrock SSO setup[/bold cyan]\n")
    console.print("[bold]Tools[/bold]")
    _print_tool_status("brew")
    _print_tool_status("aws")

    result = configure_bedrock_sso(config, aws_config_path=path, dry_run=dry_run)
    action = "Would update" if dry_run and result.changed else "Would keep"
    if not dry_run:
        action = "Updated" if result.changed else "Already configured"
    console.print(f"\n[green]✓[/green] {action}: {result.path}")
    console.print(f"  profile: {config.profile_name}")
    console.print(f"  sso session: {config.sso_session_name}")
    console.print(f"  account/role: {config.account_id}/{config.role_name}")

    if dry_run:
        return

    if login:
        console.print("\n[bold]AWS SSO login[/bold]")
        login_result = aws_sso_login(config.profile_name)
        if login_result.ok:
            console.print("  [green]✓[/green] aws sso login complete")
        else:
            detail = login_result.stderr or login_result.stdout or f"exit {login_result.returncode}"
            console.print(f"  [red]✗[/red] aws sso login failed: {detail}")
            raise SystemExit(login_result.returncode)

    if verify:
        console.print("\n[bold]Verification[/bold]")
        _print_identity(aws_caller_identity(config.profile_name))

    if verify_token:
        _print_gateway_token(gateway_token_status(profile_name=config.profile_name))


@bedrock.command("status")
@click.option("--verify-auth", is_flag=True, help="aws sts get-caller-identity 실행")
@click.option("--verify-token", is_flag=True, help="Gateway token helper 실행")
@click.option("--profile", default=BEDROCK_PROFILE_NAME, show_default=True, help="AWS profile 이름")
@click.option(
    "--session-name",
    default=BEDROCK_SSO_SESSION_NAME,
    show_default=True,
    help="AWS SSO session 이름",
)
@click.option(
    "--aws-config",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="AWS config 파일 경로 (테스트/고급 옵션)",
)
def bedrock_status(
    verify_auth: bool,
    verify_token: bool,
    profile: str,
    session_name: str,
    aws_config: Path | None,
) -> None:
    """Bedrock SSO 설정과 인증 상태를 확인."""
    config = _bedrock_config(profile, session_name)
    path = _aws_config_path(aws_config)

    console.print("[bold cyan]Claude Code on Bedrock status[/bold cyan]\n")
    console.print("[bold]Tools[/bold]")
    _print_tool_status("brew")
    _print_tool_status("aws")

    configured = is_bedrock_sso_configured(config, aws_config_path=path)
    if configured:
        console.print(f"\n[green]✓[/green] AWS config: {path}")
    else:
        console.print(f"\n[yellow]○[/yellow] AWS config needs setup: {path}")
        console.print("  [dim]run: ai-env bedrock setup[/dim]")

    helper = default_gateway_token_helper()
    if helper.exists():
        executable = "executable" if helper.stat().st_mode & 0o111 else "not executable"
        console.print(f"[green]✓[/green] Gateway token helper: {helper} ({executable})")
    else:
        console.print(f"[yellow]○[/yellow] Gateway token helper not found: {helper}")

    if verify_auth:
        console.print("\n[bold]Verification[/bold]")
        _print_identity(aws_caller_identity(config.profile_name))

    if verify_token:
        _print_gateway_token(gateway_token_status(profile_name=config.profile_name))


@bedrock.command("login")
@click.option("--profile", default=BEDROCK_PROFILE_NAME, show_default=True, help="AWS profile 이름")
def bedrock_login(profile: str) -> None:
    """Bedrock AWS SSO 브라우저 로그인을 실행."""
    console.print(f"[bold cyan]AWS SSO login[/bold cyan] [dim]profile={profile}[/dim]\n")
    result = aws_sso_login(profile)
    if result.ok:
        console.print("[green]✓[/green] aws sso login complete")
        return

    detail = result.stderr or result.stdout or f"exit {result.returncode}"
    console.print(f"[red]✗[/red] aws sso login failed: {detail}")
    raise SystemExit(result.returncode)
