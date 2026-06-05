"""Claude Code on Bedrock setup helpers."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

BEDROCK_PROFILE_NAME = "bedrock-gateway"
BEDROCK_SSO_SESSION_NAME = "bedrock-gateway"
BEDROCK_SSO_START_URL = "https://d-9067b92cea.awsapps.com/start"
BEDROCK_SSO_REGION = "us-east-1"
BEDROCK_ACCOUNT_ID = "673981388588"
BEDROCK_ROLE_NAME = "BEDROCK"
BEDROCK_CLIENT_REGION = "us-east-1"
BEDROCK_OUTPUT_FORMAT = "json"

_AWS_SECTION_PATTERN = re.compile(r"^\s*\[([^\]]+)]\s*$")


@dataclass(frozen=True)
class BedrockSsoConfig:
    """AWS IAM Identity Center settings for Claude Code on Bedrock."""

    profile_name: str = BEDROCK_PROFILE_NAME
    sso_session_name: str = BEDROCK_SSO_SESSION_NAME
    sso_start_url: str = BEDROCK_SSO_START_URL
    sso_region: str = BEDROCK_SSO_REGION
    account_id: str = BEDROCK_ACCOUNT_ID
    role_name: str = BEDROCK_ROLE_NAME
    client_region: str = BEDROCK_CLIENT_REGION
    output_format: str = BEDROCK_OUTPUT_FORMAT

    @property
    def profile_section(self) -> str:
        """AWS config section name for the profile."""
        return f"profile {self.profile_name}"

    @property
    def sso_session_section(self) -> str:
        """AWS config section name for the SSO session."""
        return f"sso-session {self.sso_session_name}"


@dataclass(frozen=True)
class BedrockConfigResult:
    """Result of rendering or writing the AWS SSO config."""

    path: Path
    changed: bool
    content: str


@dataclass(frozen=True)
class BedrockCommandResult:
    """Subprocess result simplified for CLI rendering."""

    ok: bool
    stdout: str
    stderr: str
    returncode: int


def default_gateway_token_helper(home: Path | None = None) -> Path:
    """Return the expected Claude Code gateway token helper path."""
    root = home or Path.home()
    return root / "claude-code-gateway" / "scripts" / "get-gateway-token.sh"


def default_aws_config_path(home: Path | None = None) -> Path:
    """Return the AWS config file path for a home directory."""
    root = home or Path.home()
    return root / ".aws" / "config"


def bedrock_sso_sections(config: BedrockSsoConfig) -> dict[str, dict[str, str]]:
    """Return the AWS config sections required for Bedrock SSO."""
    return {
        config.sso_session_section: {
            "sso_start_url": config.sso_start_url,
            "sso_region": config.sso_region,
            "sso_registration_scopes": "sso:account:access",
        },
        config.profile_section: {
            "sso_session": config.sso_session_name,
            "sso_account_id": config.account_id,
            "sso_role_name": config.role_name,
            "region": config.client_region,
            "output": config.output_format,
        },
    }


def render_aws_section(section: str, values: dict[str, str]) -> str:
    """Render one AWS config section."""
    lines = [f"[{section}]"]
    lines.extend(f"{key} = {value}" for key, value in values.items())
    return "\n".join(lines)


def merge_aws_config(existing: str, sections: dict[str, dict[str, str]]) -> str:
    """Merge managed Bedrock SSO sections into an AWS config file.

    Only the managed section bodies are replaced. Unrelated profiles, comments,
    and ordering outside those sections are preserved.
    """
    lines = existing.splitlines()
    output: list[str] = []
    seen: set[str] = set()
    skipping_managed_section = False

    def append_managed_section(section: str) -> None:
        if output and output[-1] != "":
            output.append("")
        output.extend(render_aws_section(section, sections[section]).splitlines())
        seen.add(section)

    for line in lines:
        section_match = _AWS_SECTION_PATTERN.match(line)
        if section_match:
            section_name = section_match.group(1)
            skipping_managed_section = section_name in sections
            if skipping_managed_section:
                append_managed_section(section_name)
                continue

        if skipping_managed_section:
            continue
        output.append(line)

    for section in sections:
        if section in seen:
            continue
        append_managed_section(section)

    return "\n".join(output).rstrip() + "\n"


def configure_bedrock_sso(
    config: BedrockSsoConfig | None = None,
    *,
    aws_config_path: Path | None = None,
    dry_run: bool = False,
) -> BedrockConfigResult:
    """Create or update the AWS SSO profile used by Claude Code on Bedrock."""
    settings = config or BedrockSsoConfig()
    path = aws_config_path or default_aws_config_path()
    existing = path.read_text() if path.exists() else ""
    content = merge_aws_config(existing, bedrock_sso_sections(settings))
    changed = content != existing

    if not dry_run and changed:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    return BedrockConfigResult(path=path, changed=changed, content=content)


def is_bedrock_sso_configured(
    config: BedrockSsoConfig | None = None,
    *,
    aws_config_path: Path | None = None,
) -> bool:
    """Return whether the AWS config already contains the expected SSO settings."""
    settings = config or BedrockSsoConfig()
    path = aws_config_path or default_aws_config_path()
    if not path.exists():
        return False
    existing = path.read_text()
    expected = merge_aws_config(existing, bedrock_sso_sections(settings))
    return existing == expected


def check_tool(name: str) -> tuple[bool, str]:
    """Return whether a command exists and its resolved path."""
    resolved = shutil.which(name)
    return resolved is not None, resolved or ""


def run_bedrock_command(
    args: list[str],
    *,
    timeout: int = 60,
) -> BedrockCommandResult:
    """Run a Bedrock setup command and capture output."""
    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )
    return BedrockCommandResult(
        ok=result.returncode == 0,
        stdout=result.stdout.strip(),
        stderr=result.stderr.strip(),
        returncode=result.returncode,
    )


def aws_sso_login(profile_name: str = BEDROCK_PROFILE_NAME) -> BedrockCommandResult:
    """Run AWS SSO browser login for the Bedrock profile."""
    return run_bedrock_command(["aws", "sso", "login", "--profile", profile_name], timeout=600)


def aws_caller_identity(profile_name: str = BEDROCK_PROFILE_NAME) -> BedrockCommandResult:
    """Return the AWS STS caller identity for the Bedrock profile."""
    return run_bedrock_command(
        ["aws", "sts", "get-caller-identity", "--profile", profile_name, "--output", "json"]
    )


def gateway_token_status(
    helper: Path | None = None,
    *,
    profile_name: str = BEDROCK_PROFILE_NAME,
) -> BedrockCommandResult:
    """Call the gateway token helper and return a masked success/failure result."""
    helper_path = helper or default_gateway_token_helper()
    if not helper_path.exists():
        return BedrockCommandResult(False, "", f"token helper not found: {helper_path}", 127)

    env = os.environ.copy()
    env["AWS_PROFILE"] = profile_name
    result = subprocess.run(
        ["bash", str(helper_path)],
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    token = result.stdout.strip()
    if result.returncode == 0 and token.startswith("sk-"):
        return BedrockCommandResult(True, f"{token[:3]}*** (length={len(token)})", "", 0)
    if "AWS_ACCESS_KEY_ID" in result.stderr or "aws sso login" in result.stderr:
        return BedrockCommandResult(
            False,
            "",
            f"AWS SSO credentials unavailable; run `ai-env bedrock login --profile {profile_name}`",
            result.returncode,
        )
    return BedrockCommandResult(False, "", result.stderr.strip(), result.returncode)
