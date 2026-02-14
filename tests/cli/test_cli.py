"""Tests for ai-env CLI commands."""

import os
from unittest.mock import MagicMock, patch

import pytest
from ai_env.cli import main
from click.testing import CliRunner


@pytest.fixture()
def runner():
    """Click CLI runner fixture."""
    return CliRunner()


def test_status_command(runner):
    """Test status command."""
    with (
        patch("ai_env.cli.status_cmd.load_settings") as mock_settings,
        patch("ai_env.cli.status_cmd.load_mcp_config") as mock_mcp,
    ):
        settings = MagicMock()
        settings.version = "0.1.0"
        settings.default_agent = "claude"
        settings.env_file = ".env"

        provider = MagicMock()
        provider.enabled = True
        provider.env_key = "CLAUDE_API_KEY"
        settings.providers = {"claude": provider}

        mock_settings.return_value = settings

        config = MagicMock()
        config.mcp_servers = {}
        mock_mcp.return_value = config

        with patch.dict(os.environ, {"CLAUDE_API_KEY": "present"}):
            result = runner.invoke(main, ["status"])
            assert result.exit_code == 0, f"Command failed: {result.output}"
            assert "AI Environment Status" in result.output


def test_secrets_list_command(runner):
    """Test secrets list command."""
    with patch("ai_env.cli.get_secrets_manager") as mock:
        manager = MagicMock()
        manager.get_secret.return_value = "secret_value"
        mock.return_value = manager

        result = runner.invoke(main, ["secrets", "--show"])
        assert result.exit_code == 0


def test_generate_all_command(runner):
    """Test generate all command (dry run)."""
    with (
        patch("ai_env.cli.generate_cmd.get_secrets_manager") as mock_sm,
        patch("ai_env.cli.generate_cmd.MCPConfigGenerator") as mock_generator,
    ):
        mock_sm.return_value = MagicMock()

        result = runner.invoke(main, ["generate", "all", "--dry-run"])

        assert result.exit_code == 0, f"Command failed with output: {result.output}"

        mock_generator.assert_called_once()
        instance = mock_generator.return_value
        instance.save_all.assert_called_once_with(dry_run=True)
