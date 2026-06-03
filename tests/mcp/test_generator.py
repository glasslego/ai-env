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
                codex_model="gpt-5.5", codex_model_reasoning_effort="xhigh"
            )
            gen = MCPConfigGenerator(secrets)

        result = gen.generate_codex()

        assert 'model = "gpt-5.5"' in result
        assert 'model_reasoning_effort = "xhigh"' in result

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
        assert 'model = "gpt-5.5"' in result
        assert "[env]" not in result
        assert "[features]" not in result
        assert "rmcp_client" not in result
        assert "teammateMode" not in result  # teammateMode는 제거됨

    def test_merge_codex_config_preserves_app_managed_sections(self):
        """전역 Codex config 저장 시 앱/플러그인 관리 섹션은 보존."""
        existing = """model = "old"
notify = ["app", "turn-ended"]

[env]
EXISTING_ENV = "1"

[features]
rmcp_client = false
js_repl = false

[mcp_servers.brave-search]
command = "old"
args = ["old-package"]

[mcp_servers.node_repl]
command = "/Applications/Codex.app/node_repl"
args = []

[projects."~/work/glasslego/ai-env"]
trust_level = "trusted"

[plugins."browser@openai-bundled"]
enabled = true
"""
        generated = """model = "gpt-5.5"
model_reasoning_effort = "xhigh"

[mcp_servers.brave-search]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-brave-search"]
startup_timeout_sec = 30
"""

        result = MCPConfigGenerator.merge_codex_config(existing, generated)

        assert 'model = "gpt-5.5"' in result
        assert 'model_reasoning_effort = "xhigh"' in result
        assert 'notify = ["app", "turn-ended"]' in result
        assert "[env]" not in result
        assert 'EXISTING_ENV = "1"' not in result
        assert "[features]" not in result
        assert "rmcp_client" not in result
        assert "js_repl" not in result
        assert 'command = "old"' not in result
        assert "@modelcontextprotocol/server-brave-search" in result
        assert "[mcp_servers.node_repl]" in result
        assert '[projects."~/work/glasslego/ai-env"]' in result
        assert '[plugins."browser@openai-bundled"]' in result


class TestSaveAllTargets:
    """SPEC-013: save_all이 Claude+Codex 타겟만 생성한다."""

    def _make_generator(self) -> MCPConfigGenerator:
        secrets = MagicMock()
        secrets.get.return_value = ""
        secrets.substitute.side_effect = lambda value: value
        secrets.export_to_shell.return_value = ""

        with (
            patch("ai_env.mcp.generator.load_mcp_config") as mock_mcp,
            patch("ai_env.mcp.generator.load_settings") as mock_settings,
        ):
            mock_mcp.return_value = MagicMock(mcp_servers={})
            mock_settings.return_value = Settings()
            return MCPConfigGenerator(secrets)

    def test_save_all_dry_run_emits_only_supported_targets(self):
        gen = self._make_generator()
        result = gen.save_all(dry_run=True)
        assert set(result.keys()) == {
            "claude_desktop",
            "codex_desktop",
            "codex_global",
            "claude_local",
            "codex_local",
            "shell_exports",
        }


class TestDestructiveDenyRules:
    """파괴적 삭제 명령 deny 규칙 회귀 가드.

    rm -rf 와 hdfs dfs -rm -r 계열은 어떤 형태로도 차단되어야 한다.
    """

    def test_rm_rf_root_and_home_blocked(self):
        rules = MCPConfigGenerator.RM_RF_DENY_RULES
        assert "Bash(rm -rf /)" in rules
        assert "Bash(rm -rf /*)" in rules
        assert "Bash(rm -rf ~)" in rules
        assert "Bash(rm -rf ~/*)" in rules

    def test_hdfs_recursive_delete_blocked(self):
        """HDFS recursive 삭제 명령의 모든 변형이 deny에 포함되어야 한다."""
        rules = MCPConfigGenerator.RM_RF_DENY_RULES
        for required in (
            "Bash(hdfs dfs -rm -r:*)",
            "Bash(hdfs dfs -rm -rf:*)",
            "Bash(hdfs dfs -rm -r -f:*)",
            "Bash(hdfs dfs -rmr:*)",
        ):
            assert required in rules, f"missing HDFS deny rule: {required}"
