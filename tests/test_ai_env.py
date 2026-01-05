"""Tests for ai-env CLI."""

import os
from unittest.mock import patch, MagicMock
from pathlib import Path

import pytest
from click.testing import CliRunner

from ai_env.cli import main, setup, secrets, generate_all, sync, status
from ai_env.core import load_settings


@pytest.fixture
def runner():
    """Click CLI runner fixture."""
    return CliRunner()


@pytest.fixture
def mock_settings():
    """Mock settings."""
    with patch("ai_env.cli.load_settings") as mock:
        settings = MagicMock()
        settings.version = "0.1.0"
        settings.default_agent = "claude"
        settings.env_file = ".env"
        
        # Mock providers
        provider = MagicMock()
        provider.enabled = True
        provider.env_key = "CLAUDE_API_KEY"
        settings.providers = {"claude": provider}
        
        mock.return_value = settings
        yield mock


@pytest.fixture
def mock_secrets_manager():
    """Mock secrets manager."""
    with patch("ai_env.cli.get_secrets_manager") as mock:
        manager = MagicMock()
        manager.get_secret.return_value = "secret_value"
        mock.return_value = manager
        yield mock


@pytest.fixture
def mock_mcp_config():
    """Mock MCP config."""
    with patch("ai_env.cli.load_mcp_config") as mock:
        config = MagicMock()
        config.mcp_servers = {}
        mock.return_value = config
        yield mock


def test_status_command(runner, mock_settings, mock_mcp_config):
    """Test status command."""
    # Mock environment variables
    with patch.dict(os.environ, {"CLAUDE_API_KEY": "present"}):
        result = runner.invoke(main, ["status"])
        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "AI Environment Status" in result.output


def test_secrets_list_command(runner, mock_secrets_manager):
    """Test secrets list command."""
    result = runner.invoke(main, ["secrets", "--show"])
    assert result.exit_code == 0


def test_generate_all_command(runner, mock_secrets_manager):
    """Test generate all command (dry run)."""
    with patch("ai_env.cli.MCPConfigGenerator") as MockGenerator:
        # Valid execution
        result = runner.invoke(main, ["generate", "all", "--dry-run"])
        
        assert result.exit_code == 0, f"Command failed with output: {result.output}"
        
        # Verify MCPConfigGenerator usage
        MockGenerator.assert_called_once()
        instance = MockGenerator.return_value
        instance.save_all.assert_called_once_with(dry_run=True)
