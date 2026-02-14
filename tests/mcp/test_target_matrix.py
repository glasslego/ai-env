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
        "brave-search",
        "context7",
        "fetch",
        "filesystem",
        "git",
        "sequential-thinking",
    ]

    for server_name in core_servers:
        assert server_name in mcp_config.mcp_servers
        server = mcp_config.mcp_servers[server_name]
        assert server.enabled
        missing_targets = sorted(ALL_CLIENT_TARGETS - set(server.targets))
        assert not missing_targets, f"{server_name} missing targets: {missing_targets}"


def test_chatgpt_desktop_excludes_compat_servers():
    """ChatGPT Desktop excludes servers known to disconnect or mismatch tool-calls."""
    mcp_config = load_mcp_config()
    for name in ["desktop-commander", "mem0", "supabase", "browserbase"]:
        server = mcp_config.mcp_servers[name]
        assert server.enabled
        assert "chatgpt_desktop" not in server.targets


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
