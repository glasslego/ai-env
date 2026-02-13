"""Tests for ai-env CLI."""

import os
from unittest.mock import MagicMock, patch

import pytest
from ai_env.cli import main
from ai_env.core.config import MCPServerConfig, Settings
from ai_env.mcp.generator import MCPConfigGenerator
from click.testing import CliRunner


@pytest.fixture()
def runner():
    """Click CLI runner fixture."""
    return CliRunner()


@pytest.fixture()
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


@pytest.fixture()
def mock_secrets_manager():
    """Mock secrets manager."""
    with patch("ai_env.cli.get_secrets_manager") as mock:
        manager = MagicMock()
        manager.get_secret.return_value = "secret_value"
        mock.return_value = manager
        yield mock


@pytest.fixture()
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
    with patch("ai_env.cli.MCPConfigGenerator") as mock_generator:
        # Valid execution
        result = runner.invoke(main, ["generate", "all", "--dry-run"])

        assert result.exit_code == 0, f"Command failed with output: {result.output}"

        # Verify MCPConfigGenerator usage
        mock_generator.assert_called_once()
        instance = mock_generator.return_value
        instance.save_all.assert_called_once_with(dry_run=True)


# === vibe 쉘 함수 생성 테스트 ===


class TestGenerateShellFunctions:
    """generate_shell_functions() 테스트"""

    def _make_generator(self, agent_priority: list[str]) -> MCPConfigGenerator:
        """테스트용 generator 생성"""
        secrets = MagicMock()
        secrets.get.return_value = ""
        with (
            patch("ai_env.mcp.generator.load_mcp_config") as mock_mcp,
            patch("ai_env.mcp.generator.load_settings") as mock_settings,
        ):
            mock_mcp.return_value = MagicMock(mcp_servers={})
            settings = Settings(agent_priority=agent_priority)
            mock_settings.return_value = settings
            return MCPConfigGenerator(secrets)

    def test_default_priority(self):
        """기본 우선순위 (claude → codex) 테스트"""
        gen = self._make_generator(["claude", "codex"])
        result = gen.generate_shell_functions()

        assert "vibe()" in result
        assert 'agents=("claude" "codex")' in result
        assert "claude → codex" in result

    def test_custom_priority(self):
        """커스텀 우선순위 (codex → gemini) 테스트"""
        gen = self._make_generator(["codex", "gemini"])
        result = gen.generate_shell_functions()

        assert 'agents=("codex" "gemini")' in result
        assert "codex → gemini" in result

    def test_single_agent(self):
        """에이전트가 하나일 때"""
        gen = self._make_generator(["claude"])
        result = gen.generate_shell_functions()

        assert 'agents=("claude")' in result

    def test_empty_priority(self):
        """agent_priority가 비어있으면 빈 문자열 반환"""
        gen = self._make_generator([])
        result = gen.generate_shell_functions()

        assert result == ""

    def test_contains_claudecode_guard(self):
        """Claude Code 중첩 세션 방지 코드 포함 확인"""
        gen = self._make_generator(["claude", "codex"])
        result = gen.generate_shell_functions()

        assert "CLAUDECODE" in result

    def test_contains_skip_option(self):
        """-2 옵션으로 2순위부터 시작하는 기능 포함 확인"""
        gen = self._make_generator(["claude", "codex"])
        result = gen.generate_shell_functions()

        assert "-[0-9]" in result
        assert "start_idx" in result


class TestGenerateCodexConfig:
    """generate_codex() 테스트"""

    def _make_generator(self, mcp_servers: dict[str, MCPServerConfig]) -> MCPConfigGenerator:
        """테스트용 generator 생성"""
        secrets = MagicMock()
        secrets.get.side_effect = lambda key, default="": {
            "TEST_SSE_URL": "https://example.com/sse",
            "TEST_TOKEN": "token",
        }.get(key, default)
        secrets.substitute.side_effect = lambda value: value

        with (
            patch("ai_env.mcp.generator.load_mcp_config") as mock_mcp,
            patch("ai_env.mcp.generator.load_settings") as mock_settings,
        ):
            mock_mcp.return_value = MagicMock(mcp_servers=mcp_servers)
            mock_settings.return_value = Settings()
            return MCPConfigGenerator(secrets)

    def test_default_startup_timeout_for_codex(self):
        """codex 타겟은 기본 startup_timeout_sec=30 적용."""
        gen = self._make_generator(
            {
                "sample": MCPServerConfig(
                    enabled=True,
                    type="stdio",
                    command="npx",
                    args=["-y", "@example/mcp"],
                    targets=["codex"],
                )
            }
        )

        result = gen.generate_codex()
        assert "[mcp_servers.sample]" in result
        assert "startup_timeout_sec = 30" in result

    def test_custom_startup_timeout_for_codex(self):
        """startup_timeout_sec 지정 시 custom 값 반영."""
        gen = self._make_generator(
            {
                "sample": MCPServerConfig(
                    enabled=True,
                    type="stdio",
                    command="npx",
                    args=["-y", "@example/mcp"],
                    targets=["codex"],
                    startup_timeout_sec=75,
                )
            }
        )

        result = gen.generate_codex()
        assert "[mcp_servers.sample]" in result
        assert "startup_timeout_sec = 75" in result

    def test_custom_startup_timeout_for_codex_sse(self):
        """SSE 서버도 startup_timeout_sec 반영."""
        gen = self._make_generator(
            {
                "sse-sample": MCPServerConfig(
                    enabled=True,
                    type="sse",
                    url_env="TEST_SSE_URL",
                    targets=["codex"],
                    startup_timeout_sec=40,
                )
            }
        )

        result = gen.generate_codex()
        assert "[mcp_servers.sse-sample]" in result
        assert 'type = "sse"' in result
        assert "startup_timeout_sec = 40" in result

    def test_codex_permissions_defaults_and_rmrf_rule(self):
        """Codex 권한 기본값(거의 허용) + rm -rf 금지 룰 포함."""
        gen = self._make_generator({})
        result = gen.generate_codex()

        assert 'approval_policy = "never"' in result
        assert 'sandbox_mode = "danger-full-access"' in result
        assert "[rules]" in result
        assert 'decision = "forbidden"' in result
        assert '{ token = "rm" }' in result
        assert '{ token = "-rf" }' in result
