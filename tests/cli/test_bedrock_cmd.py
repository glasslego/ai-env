"""Bedrock CLI command tests."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from ai_env.cli import main
from click.testing import CliRunner


def test_bedrock_setup_dry_run_does_not_write_config(tmp_path: Path) -> None:
    """bedrock setup --dry-run은 AWS config 파일을 쓰지 않음."""
    runner = CliRunner()
    aws_config = tmp_path / ".aws" / "config"

    result = runner.invoke(
        main,
        ["bedrock", "setup", "--dry-run", "--aws-config", str(aws_config)],
    )

    assert result.exit_code == 0, result.output
    assert "Would update" in result.output
    assert "bedrock-gateway" in result.output
    assert not aws_config.exists()


def test_bedrock_setup_writes_config(tmp_path: Path) -> None:
    """bedrock setup은 AWS config 파일을 생성."""
    runner = CliRunner()
    aws_config = tmp_path / ".aws" / "config"

    result = runner.invoke(
        main,
        ["bedrock", "setup", "--aws-config", str(aws_config)],
    )

    assert result.exit_code == 0, result.output
    assert "Updated" in result.output
    assert aws_config.exists()
    assert "[profile bedrock-gateway]" in aws_config.read_text()


def test_bedrock_status_reports_missing_config(tmp_path: Path) -> None:
    """bedrock status는 설정이 없으면 setup 안내를 출력."""
    runner = CliRunner()
    aws_config = tmp_path / ".aws" / "config"

    result = runner.invoke(
        main,
        ["bedrock", "status", "--aws-config", str(aws_config)],
    )

    assert result.exit_code == 0, result.output
    assert "AWS config needs setup" in result.output
    assert "ai-env bedrock setup" in result.output


def test_bedrock_status_reports_existing_config(tmp_path: Path) -> None:
    """bedrock status는 설정된 profile을 인식."""
    runner = CliRunner()
    aws_config = tmp_path / ".aws" / "config"
    setup_result = runner.invoke(
        main,
        ["bedrock", "setup", "--aws-config", str(aws_config)],
    )
    assert setup_result.exit_code == 0, setup_result.output

    status_result = runner.invoke(
        main,
        ["bedrock", "status", "--aws-config", str(aws_config)],
    )

    assert status_result.exit_code == 0, status_result.output
    assert "AWS config:" in status_result.output


def test_bedrock_status_verify_auth_uses_profile(tmp_path: Path) -> None:
    """--verify-auth는 Bedrock profile로 caller identity를 조회."""
    runner = CliRunner()
    aws_config = tmp_path / ".aws" / "config"

    with patch("ai_env.cli.bedrock_cmd.aws_caller_identity") as mock_identity:
        mock_identity.return_value.ok = True
        mock_identity.return_value.stdout = (
            '{"Account":"673981388588","Arn":"arn:aws:sts::673981388588:assumed-role/x/megan"}'
        )
        mock_identity.return_value.stderr = ""
        mock_identity.return_value.returncode = 0

        result = runner.invoke(
            main,
            ["bedrock", "status", "--verify-auth", "--aws-config", str(aws_config)],
        )

    assert result.exit_code == 0, result.output
    mock_identity.assert_called_once_with("bedrock-gateway")
    assert "account=673981388588" in result.output
