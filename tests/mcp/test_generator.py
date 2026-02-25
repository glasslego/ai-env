"""Tests for MCP config generator."""

from unittest.mock import MagicMock, patch

from ai_env.core.config import MCPServerConfig, Settings
from ai_env.mcp.generator import MCPConfigGenerator


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

    @patch("ai_env.mcp.generator.load_settings")
    def test_default_codex_model_is_set(self, mock_settings):
        """codex config는 기본 모델을 settings에서 가져와 설정."""
        secrets = MagicMock()
        secrets.get.side_effect = lambda key, default="": {
            "TEST_SSE_URL": "https://example.com/sse",
            "TEST_TOKEN": "token",
        }.get(key, default)
        secrets.substitute.side_effect = lambda value: value

        with patch("ai_env.mcp.generator.load_mcp_config") as mock_mcp:
            mock_mcp.return_value = MagicMock(mcp_servers={})
            mock_settings.return_value = Settings(
                codex_model="gpt-5.3-codex", codex_model_reasoning_effort="high"
            )
            gen = MCPConfigGenerator(secrets)

        result = gen.generate_codex()

        assert 'model = "gpt-5.3-codex"' in result
        assert 'model_reasoning_effort = "high"' in result

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
        assert "[permissions]" in result
        assert "[permissions.env]" in result
        assert 'allow = ["Read(*)"' in result
        assert '"Bash(*)"' in result
        assert '"mcp__*"' in result
        assert '"Bash(rm -rf /)"' in result
        assert '"Bash(rm -rf /*)"' in result
        assert '"Bash(rm -rf ~)"' in result
        assert '"Bash(rm -rf ~/*)"' in result
        assert 'teammateMode = "tmux"' in result
        assert 'CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS = "1"' in result
