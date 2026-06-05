"""Bedrock SSO setup helper tests."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from ai_env.core.bedrock import (
    BEDROCK_ACCOUNT_ID,
    BEDROCK_PROFILE_NAME,
    BEDROCK_ROLE_NAME,
    BEDROCK_SSO_SESSION_NAME,
    BEDROCK_SSO_START_URL,
    BedrockSsoConfig,
    configure_bedrock_sso,
    default_gateway_token_helper,
    gateway_token_status,
    is_bedrock_sso_configured,
    merge_aws_config,
)


def test_merge_aws_config_adds_bedrock_sections_and_preserves_other_profiles() -> None:
    """Bedrock section 추가 시 기존 profile/comment를 보존."""
    existing = """# user config
[default]
region = ap-northeast-2
"""

    merged = merge_aws_config(
        existing,
        {
            "sso-session bedrock-gateway": {
                "sso_start_url": BEDROCK_SSO_START_URL,
            },
            "profile bedrock-gateway": {
                "sso_session": BEDROCK_SSO_SESSION_NAME,
            },
        },
    )

    assert "# user config" in merged
    assert "[default]" in merged
    assert "[sso-session bedrock-gateway]" in merged
    assert "sso_start_url = https://d-9067b92cea.awsapps.com/start" in merged
    assert "[profile bedrock-gateway]" in merged
    assert "sso_session = bedrock-gateway" in merged


def test_merge_aws_config_replaces_existing_bedrock_sections() -> None:
    """기존 Bedrock section이 있으면 관리 값으로 교체."""
    existing = """[profile bedrock-gateway]
sso_session = old
region = old

[profile unrelated]
region = us-west-2

[sso-session bedrock-gateway]
sso_start_url = old
"""

    merged = merge_aws_config(
        existing,
        {
            "sso-session bedrock-gateway": {
                "sso_start_url": BEDROCK_SSO_START_URL,
                "sso_region": "us-east-1",
            },
            "profile bedrock-gateway": {
                "sso_session": BEDROCK_SSO_SESSION_NAME,
                "sso_account_id": BEDROCK_ACCOUNT_ID,
                "sso_role_name": BEDROCK_ROLE_NAME,
            },
        },
    )

    assert "old" not in merged
    assert "[profile unrelated]" in merged
    assert f"sso_account_id = {BEDROCK_ACCOUNT_ID}" in merged
    assert f"sso_role_name = {BEDROCK_ROLE_NAME}" in merged


def test_configure_bedrock_sso_writes_expected_config(tmp_path: Path) -> None:
    """AWS config 파일에 Bedrock SSO profile을 기록."""
    aws_config = tmp_path / ".aws" / "config"

    result = configure_bedrock_sso(aws_config_path=aws_config)

    assert result.changed
    assert aws_config.exists()
    content = aws_config.read_text()
    assert f"[profile {BEDROCK_PROFILE_NAME}]" in content
    assert f"[sso-session {BEDROCK_SSO_SESSION_NAME}]" in content
    assert is_bedrock_sso_configured(aws_config_path=aws_config)


def test_configure_bedrock_sso_dry_run_does_not_write(tmp_path: Path) -> None:
    """dry-run은 결과 content만 만들고 파일은 쓰지 않음."""
    aws_config = tmp_path / ".aws" / "config"

    result = configure_bedrock_sso(aws_config_path=aws_config, dry_run=True)

    assert result.changed
    assert not aws_config.exists()
    assert f"[profile {BEDROCK_PROFILE_NAME}]" in result.content


def test_configure_bedrock_sso_is_idempotent(tmp_path: Path) -> None:
    """동일 config 재적용은 changed=false."""
    aws_config = tmp_path / ".aws" / "config"
    configure_bedrock_sso(aws_config_path=aws_config)

    result = configure_bedrock_sso(aws_config_path=aws_config)

    assert not result.changed


def test_custom_profile_uses_custom_session_name(tmp_path: Path) -> None:
    """프로필/세션 이름 오버라이드 지원."""
    aws_config = tmp_path / ".aws" / "config"
    config = BedrockSsoConfig(profile_name="bedrock-test", sso_session_name="bedrock-test")

    configure_bedrock_sso(config, aws_config_path=aws_config)

    content = aws_config.read_text()
    assert "[profile bedrock-test]" in content
    assert "[sso-session bedrock-test]" in content


def test_default_gateway_token_helper_uses_home() -> None:
    """token helper 기본 경로는 home 기준."""
    home = Path("/tmp/example-home")

    assert default_gateway_token_helper(home) == (
        home / "claude-code-gateway" / "scripts" / "get-gateway-token.sh"
    )


def test_gateway_token_status_explains_expired_sso(tmp_path: Path) -> None:
    """helper의 AWS_ACCESS_KEY_ID 오류를 SSO 로그인 안내로 변환."""
    helper = tmp_path / "get-gateway-token.sh"
    helper.write_text("#!/usr/bin/env bash\n")

    completed = MagicMock()
    completed.returncode = 1
    completed.stdout = ""
    completed.stderr = "line 46: AWS_ACCESS_KEY_ID: unbound variable"

    with patch("ai_env.core.bedrock.subprocess.run", return_value=completed):
        result = gateway_token_status(helper)

    assert not result.ok
    assert "ai-env bedrock login" in result.stderr
