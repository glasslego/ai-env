"""MCP target matrix tests for default configuration (Claude+Codex 전용, SPEC-013)."""

from ai_env.core.config import load_mcp_config

# SPEC-013: Gemini/Antigravity/ChatGPT Desktop 지원 제거.
ALL_CLIENT_TARGETS = {
    "claude_desktop",
    "claude_local",
    "codex",
    "codex_desktop",
}


def test_core_servers_cover_supported_clients():
    """Core productivity MCPs should be mapped to every supported client target."""
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
        # claude_desktop과 claude_local은 모든 코어 서버에 매핑.
        # codex/codex_desktop은 일부 서버만 매핑 (복잡 서버는 teammate mode 위임).
        for required in ("claude_desktop", "claude_local"):
            assert required in server.targets, f"{server_name} missing {required}"


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


def test_no_dropped_targets_remain():
    """SPEC-013: Gemini/Antigravity/ChatGPT 타겟이 mcp_servers.yaml에 남아있지 않음."""
    mcp_config = load_mcp_config()
    forbidden = {"gemini", "antigravity", "chatgpt_desktop"}
    for name, server in mcp_config.mcp_servers.items():
        leftover = forbidden & set(server.targets)
        assert not leftover, f"{name} still references dropped targets: {leftover}"
