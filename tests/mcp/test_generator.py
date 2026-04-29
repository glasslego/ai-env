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
                codex_model="gpt-5.4", codex_model_reasoning_effort="high"
            )
            gen = MCPConfigGenerator(secrets)

        result = gen.generate_codex()

        assert 'model = "gpt-5.4"' in result
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

    def test_codex_config_structure(self):
        """Codex config.toml 기본 구조 확인 (0.113.0+ 호환)."""
        gen = self._make_generator({})
        result = gen.generate_codex()

        # 0.113.0에서 제거된 필드가 없어야 함
        assert "approval_policy" not in result
        assert "sandbox_mode" not in result
        assert "trust_level" not in result
        assert "[permissions]" not in result
        # 필수 필드 존재
        assert 'model = "gpt-5.4"' in result
        assert "[env]" in result
        assert "teammateMode" not in result  # teammateMode는 제거됨
        assert 'CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS = "1"' in result


class TestProviderEnabledGuard:
    """SPEC-013: providers[*].enabled에 따른 save_all 가드 테스트."""

    def _make_generator(self, providers: dict | None = None) -> MCPConfigGenerator:
        from ai_env.core.config import ProviderConfig

        secrets = MagicMock()
        secrets.get.return_value = ""
        secrets.substitute.side_effect = lambda value: value
        secrets.export_to_shell.return_value = ""

        with (
            patch("ai_env.mcp.generator.load_mcp_config") as mock_mcp,
            patch("ai_env.mcp.generator.load_settings") as mock_settings,
        ):
            mock_mcp.return_value = MagicMock(mcp_servers={})
            settings = Settings()
            if providers is not None:
                settings.providers = {
                    name: ProviderConfig(**cfg) for name, cfg in providers.items()
                }
            mock_settings.return_value = settings
            return MCPConfigGenerator(secrets)

    def test_default_settings_enables_all_targets(self):
        """providers 미정의면 모든 타겟이 enabled로 간주."""
        gen = self._make_generator(providers=None)
        for name in [
            "claude_desktop",
            "codex_global",
            "gemini_global",
            "antigravity",
            "chatgpt_desktop",
            "shell_exports",
        ]:
            assert gen._is_target_enabled(name) is True

    def test_disabled_provider_skips_target(self):
        """providers.gemini.enabled=false면 gemini_global/local 스킵."""
        gen = self._make_generator(
            providers={
                "claude": {"enabled": True},
                "codex": {"enabled": True},
                "gemini": {"enabled": False},
                "antigravity": {"enabled": False},
                "chatgpt": {"enabled": False},
            }
        )
        assert gen._is_target_enabled("claude_desktop") is True
        assert gen._is_target_enabled("codex_global") is True
        assert gen._is_target_enabled("gemini_global") is False
        assert gen._is_target_enabled("gemini_local") is False
        assert gen._is_target_enabled("antigravity") is False
        assert gen._is_target_enabled("chatgpt_desktop") is False

    def test_save_all_dry_run_skips_disabled(self, tmp_path):
        """save_all dry_run에서 disabled 타겟은 결과에 포함되지 않음."""
        gen = self._make_generator(
            providers={
                "claude": {"enabled": True},
                "codex": {"enabled": True},
                "gemini": {"enabled": False},
                "antigravity": {"enabled": False},
                "chatgpt": {"enabled": False},
            }
        )
        result = gen.save_all(dry_run=True)
        assert "claude_desktop" in result
        assert "codex_global" in result
        assert "shell_exports" in result
        # 비활성 타겟은 결과에 없어야 함
        assert "gemini_global" not in result
        assert "gemini_local" not in result
        assert "antigravity" not in result
        assert "chatgpt_desktop" not in result
