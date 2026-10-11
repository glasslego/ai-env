"""Tests for .env.example generation."""

from unittest.mock import MagicMock, patch

from ai_env.core.config import MCPServerConfig, ProviderConfig, Settings
from ai_env.core.env_example import generate_env_example


def test_team_env_catalog_never_copies_template_secrets(tmp_path):
    """팀 변수는 주석 placeholder만 생성하여 비밀값과 기본값을 복사하지 않는다."""
    template = tmp_path / "cde-skills/plugins/cde-skills/skills/_shared/env.template"
    template.parent.mkdir(parents=True)
    template.write_text("TOKEN=sensitive-template-value\n# OPTIONAL_PORT=443\n")
    code = template.parent.parent / "data/scripts/client.py"
    code.parent.mkdir(parents=True)
    code.write_text('import os\nos.getenv("CODE_ONLY_TOKEN")\nos.environ.get("USER")\n')
    with (
        patch("ai_env.core.env_example.get_project_root", return_value=tmp_path),
        patch("ai_env.core.env_example.load_settings", return_value=Settings(providers={})),
        patch("ai_env.core.env_example.load_mcp_config", return_value=MagicMock(mcp_servers={})),
    ):
        result = generate_env_example()
    assert "sensitive-template-value" not in result
    assert "443" not in result
    assert "# TOKEN=" in result
    assert "# OPTIONAL_PORT=" in result
    assert "# CODE_ONLY_TOKEN=" in result
    assert "# USER=" not in result


def test_generate_env_example_includes_provider_keys():
    """Provider API 키가 .env.example에 포함되는지 확인."""
    settings = Settings(
        providers={
            "claude": ProviderConfig(enabled=True, env_key="ANTHROPIC_API_KEY"),
            "codex": ProviderConfig(enabled=True, env_key="OPENAI_API_KEY"),
        }
    )
    mcp_config = MagicMock(mcp_servers={})

    with (
        patch("ai_env.core.env_example.load_settings", return_value=settings),
        patch("ai_env.core.env_example.load_mcp_config", return_value=mcp_config),
    ):
        result = generate_env_example()

    assert "ANTHROPIC_API_KEY=" in result
    assert "OPENAI_API_KEY=" in result


def test_generate_env_example_includes_mcp_env_keys():
    """MCP 서버 env_keys가 .env.example에 포함되는지 확인."""
    settings = Settings(providers={})
    mcp_config = MagicMock(
        mcp_servers={
            "jira": MCPServerConfig(
                enabled=True,
                type="stdio",
                command="docker",
                env_keys=["JIRA_URL", "JIRA_TOKEN"],
                targets=["claude_local"],
            ),
        }
    )

    with (
        patch("ai_env.core.env_example.load_settings", return_value=settings),
        patch("ai_env.core.env_example.load_mcp_config", return_value=mcp_config),
    ):
        result = generate_env_example()

    assert "JIRA_URL=" in result
    assert "JIRA_TOKEN=" in result
    assert "jira" in result


def test_generate_env_example_includes_sse_url_env():
    """SSE url_env가 .env.example에 포함되는지 확인."""
    settings = Settings(providers={})
    mcp_config = MagicMock(
        mcp_servers={
            "kkoto-mcp": MCPServerConfig(
                enabled=True,
                type="sse",
                url_env="KKOTO_MCP_URL",
                targets=["claude_local"],
            ),
        }
    )

    with (
        patch("ai_env.core.env_example.load_settings", return_value=settings),
        patch("ai_env.core.env_example.load_mcp_config", return_value=mcp_config),
    ):
        result = generate_env_example()

    assert "KKOTO_MCP_URL=" in result


def test_generate_env_example_no_duplicates():
    """Provider 키와 MCP 키가 중복되지 않도록 확인."""
    settings = Settings(
        providers={
            "claude": ProviderConfig(enabled=True, env_key="ANTHROPIC_API_KEY"),
        }
    )
    mcp_config = MagicMock(
        mcp_servers={
            "test": MCPServerConfig(
                enabled=True,
                type="stdio",
                command="test",
                env_keys=["ANTHROPIC_API_KEY"],
                targets=["claude_local"],
            ),
        }
    )

    with (
        patch("ai_env.core.env_example.load_settings", return_value=settings),
        patch("ai_env.core.env_example.load_mcp_config", return_value=mcp_config),
    ):
        result = generate_env_example()

    # ANTHROPIC_API_KEY= should appear exactly once (in provider section)
    assert result.count("ANTHROPIC_API_KEY=") == 1


def test_generate_env_example_skips_disabled_servers():
    """비활성 MCP 서버의 키는 제외."""
    settings = Settings(providers={})
    mcp_config = MagicMock(
        mcp_servers={
            "disabled": MCPServerConfig(
                enabled=False,
                type="stdio",
                command="test",
                env_keys=["DISABLED_KEY"],
                targets=["claude_local"],
            ),
        }
    )

    with (
        patch("ai_env.core.env_example.load_settings", return_value=settings),
        patch("ai_env.core.env_example.load_mcp_config", return_value=mcp_config),
    ):
        result = generate_env_example()

    assert "DISABLED_KEY" not in result
