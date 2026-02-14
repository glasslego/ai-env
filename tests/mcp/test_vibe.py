"""Tests for vibe shell function generation."""

import os
import stat
import subprocess
from unittest.mock import MagicMock, patch

from ai_env.core.config import Settings
from ai_env.mcp.generator import MCPConfigGenerator


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

    def test_contains_claude_rate_limit_recovery_logic(self):
        """Claude rate-limit 감지 후 fallback/복귀 로직 포함 확인"""
        gen = self._make_generator(["claude", "codex"])
        result = gen.generate_shell_functions()

        assert "_vibe_is_rate_limited()" in result
        assert "VIBE_CLAUDE_RETRY_MINUTES" in result
        assert "claude_retry_epoch" in result
        assert "Claude 제한 해제 감지. claude로 복귀합니다" in result

    def test_vibe_switches_to_codex_then_returns_to_claude(self, tmp_path):
        """Claude 한도 도달 시 codex로 전환 후 제한 해제되면 claude로 복귀."""
        gen = self._make_generator(["claude", "codex"])
        shell_fn = gen.generate_shell_functions()

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        trace_file = tmp_path / "trace.log"
        counter_file = tmp_path / "claude.count"
        vibe_file = tmp_path / "vibe.sh"

        claude_script = bin_dir / "claude"
        claude_script.write_text(
            """#!/usr/bin/env bash
count=$(cat "$COUNTER_FILE" 2>/dev/null || echo 0)
count=$((count + 1))
echo "$count" > "$COUNTER_FILE"
echo "claude:$count" >> "$TRACE_FILE"
if [[ "$count" -eq 1 ]]; then
  echo "rate limit exceeded"
  exit 1
fi
exit 0
"""
        )
        claude_script.chmod(claude_script.stat().st_mode | stat.S_IXUSR)

        codex_script = bin_dir / "codex"
        codex_script.write_text(
            """#!/usr/bin/env bash
echo "codex" >> "$TRACE_FILE"
exit 0
"""
        )
        codex_script.chmod(codex_script.stat().st_mode | stat.S_IXUSR)

        vibe_file.write_text(shell_fn)

        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
        env["TRACE_FILE"] = str(trace_file)
        env["COUNTER_FILE"] = str(counter_file)
        env["VIBE_CLAUDE_RETRY_MINUTES"] = "0"
        env.pop("CLAUDECODE", None)  # 테스트에서 Claude 중첩 세션 감지 방지

        result = subprocess.run(
            ["bash", "-c", f"source {vibe_file} && vibe 'hello world'"],
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        assert result.returncode == 0, result.stdout + result.stderr
        assert trace_file.read_text().splitlines() == ["claude:1", "codex", "claude:2"]
