"""MCP target matrix tests for default configuration."""

from ai_env.core.config import load_mcp_config

ALL_CLIENT_TARGETS = {
    "claude_desktop",
    "chatgpt_desktop",
    "antigravity",
    "claude_local",
    "codex",
    "gemini",
}


def test_core_servers_cover_all_clients():
    """Core productivity MCPs should be mapped to every client target."""
    mcp_config = load_mcp_config()
    core_servers = [
        "playwright",
        "desktop-commander",
        "brave-search",
        "context7",
        "sequential-thinking",
    ]

    for server_name in core_servers:
        assert server_name in mcp_config.mcp_servers
        server = mcp_config.mcp_servers[server_name]
        assert server.enabled
        missing_targets = sorted(ALL_CLIENT_TARGETS - set(server.targets))
        assert not missing_targets, f"{server_name} missing targets: {missing_targets}"


def test_known_unstable_servers_not_targeted_to_codex():
    """Servers known to fail handshake/startup in Codex stay excluded from codex target."""
    mcp_config = load_mcp_config()
    excluded_for_codex = [
        "github",
        "github-kakao",
        "jira-wiki-mcp",
        "kkoto-mcp",
        "cdp-mcp-server",
        "mem0",
    ]

    for server_name in excluded_for_codex:
        assert server_name in mcp_config.mcp_servers
        server = mcp_config.mcp_servers[server_name]
        assert "codex" not in server.targets
