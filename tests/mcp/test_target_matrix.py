"""MCP target matrix tests for default configuration (Claude+Codex 전용, SPEC-013)."""

from ai_env.core.config import load_mcp_config


def test_known_unstable_servers_not_targeted_to_codex():
    """Servers known to fail handshake/startup in Codex stay excluded from codex target."""
    mcp_config = load_mcp_config()
    excluded_for_codex = [
        "github",
        "github-kakao",
        "kkoto-mcp",
        "cdp-mcp-server",
        "mem0",
    ]

    for server_name in excluded_for_codex:
        assert server_name in mcp_config.mcp_servers
        server = mcp_config.mcp_servers[server_name]
        assert "codex" not in server.targets


def test_replaced_jira_wiki_mcp_is_not_configured():
    """Jira 및 Wiki는 cde-skills로 제공하므로 기존 MCP를 생성하지 않는다."""
    mcp_config = load_mcp_config()
    assert "jira-wiki-mcp" not in mcp_config.mcp_servers


def test_no_dropped_targets_remain():
    """SPEC-013: Gemini/Antigravity/ChatGPT 타겟이 mcp_servers.yaml에 남아있지 않음."""
    mcp_config = load_mcp_config()
    forbidden = {"gemini", "antigravity", "chatgpt_desktop"}
    for name, server in mcp_config.mcp_servers.items():
        leftover = forbidden & set(server.targets)
        assert not leftover, f"{name} still references dropped targets: {leftover}"
