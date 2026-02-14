"""Tests for claude --fallback shell function generation."""

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

        assert "claude()" in result
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

        assert "_claude_is_rate_limited()" in result
        assert "CLAUDE_FALLBACK_RETRY_MINUTES" in result
        assert "claude_retry_epoch" in result
        assert "Claude 제한 해제 감지. claude로 복귀합니다" in result

    def test_contains_passthrough_guard(self):
        """--fallback 없이 호출 시 원본 바이너리 passthrough 코드 포함 확인"""
        gen = self._make_generator(["claude", "codex"])
        result = gen.generate_shell_functions()

        assert 'command claude "$@"' in result
        assert '"--fallback"' in result

    def test_contains_run_agent_helper(self):
        """_run_agent 헬퍼 함수로 command claude 사용 확인"""
        gen = self._make_generator(["claude", "codex"])
        result = gen.generate_shell_functions()

        assert "_run_agent()" in result
        assert "command claude" in result

    def test_uses_agent_args_array(self):
        """인자를 배열로 보존하여 플래그 passthrough 확인"""
        gen = self._make_generator(["claude", "codex"])
        result = gen.generate_shell_functions()

        assert 'agent_args=("$@")' in result
        assert '"${agent_args[@]}"' in result

    def test_contains_to_option(self):
        """--to 옵션으로 fallback 대상 지정 코드 포함 확인"""
        gen = self._make_generator(["claude", "codex"])
        result = gen.generate_shell_functions()

        assert "--to)" in result
        assert "fallback_targets" in result

    def test_passthrough_without_fallback_flag(self, tmp_path):
        """--fallback 없이 claude 호출 시 원본 바이너리로 passthrough 확인"""
        gen = self._make_generator(["claude", "codex"])
        shell_fn = gen.generate_shell_functions()

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        trace_file = tmp_path / "trace.log"
        fn_file = tmp_path / "claude_fn.sh"

        # 원본 claude 바이너리 역할을 하는 가짜 스크립트
        claude_script = bin_dir / "claude"
        claude_script.write_text(
            '#!/usr/bin/env bash\necho "passthrough:$*" > "$TRACE_FILE"\nexit 0\n'
        )
        claude_script.chmod(claude_script.stat().st_mode | stat.S_IXUSR)
        fn_file.write_text(shell_fn)

        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
        env["TRACE_FILE"] = str(trace_file)
        env.pop("CLAUDECODE", None)

        result = subprocess.run(
            ["bash", "-c", f"source {fn_file} && claude --resume session-id"],
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        assert result.returncode == 0, result.stdout + result.stderr
        assert trace_file.read_text().strip() == "passthrough:--resume session-id"

    def test_fallback_passes_flags_to_agent(self, tmp_path):
        """claude --fallback --dangerously-skip-permissions 같은 플래그가 에이전트에 전달되는지 확인"""
        gen = self._make_generator(["claude", "codex"])
        shell_fn = gen.generate_shell_functions()

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        trace_file = tmp_path / "trace.log"
        fn_file = tmp_path / "claude_fn.sh"

        claude_script = bin_dir / "claude"
        claude_script.write_text('#!/usr/bin/env bash\necho "args:$*" > "$TRACE_FILE"\nexit 0\n')
        claude_script.chmod(claude_script.stat().st_mode | stat.S_IXUSR)
        fn_file.write_text(shell_fn)

        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
        env["TRACE_FILE"] = str(trace_file)
        env.pop("CLAUDECODE", None)

        result = subprocess.run(
            [
                "bash",
                "-c",
                f"source {fn_file} && claude --fallback --dangerously-skip-permissions",
            ],
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        assert result.returncode == 0, result.stdout + result.stderr
        assert trace_file.read_text().strip() == "args:--dangerously-skip-permissions"

    def test_fallback_to_option_overrides_agent(self, tmp_path):
        """claude --fallback --to gemini 로 fallback 대상을 런타임에 변경 확인"""
        gen = self._make_generator(["claude", "codex"])
        shell_fn = gen.generate_shell_functions()

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        trace_file = tmp_path / "trace.log"
        fn_file = tmp_path / "claude_fn.sh"

        # claude는 항상 실패
        claude_script = bin_dir / "claude"
        claude_script.write_text('#!/usr/bin/env bash\necho "claude" >> "$TRACE_FILE"\nexit 1\n')
        claude_script.chmod(claude_script.stat().st_mode | stat.S_IXUSR)

        # gemini 성공
        gemini_script = bin_dir / "gemini"
        gemini_script.write_text('#!/usr/bin/env bash\necho "gemini" >> "$TRACE_FILE"\nexit 0\n')
        gemini_script.chmod(gemini_script.stat().st_mode | stat.S_IXUSR)

        fn_file.write_text(shell_fn)

        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
        env["TRACE_FILE"] = str(trace_file)
        env["CLAUDE_FALLBACK_RETRY_MINUTES"] = "0"
        env.pop("CLAUDECODE", None)

        result = subprocess.run(
            ["bash", "-c", f"source {fn_file} && claude --fallback --to gemini"],
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        assert result.returncode == 0, result.stdout + result.stderr
        lines = trace_file.read_text().splitlines()
        # claude 실패 → gemini 성공 (codex는 사용되지 않음)
        assert lines == ["claude", "gemini"]

    def test_fallback_to_option_with_multiple_agents(self, tmp_path):
        """claude --fallback --to gemini,codex 로 다중 fallback 대상 지정 확인"""
        gen = self._make_generator(["claude", "codex"])
        shell_fn = gen.generate_shell_functions()

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        trace_file = tmp_path / "trace.log"
        fn_file = tmp_path / "claude_fn.sh"

        # claude, gemini 모두 실패
        for name in ["claude", "gemini"]:
            script = bin_dir / name
            script.write_text(f'#!/usr/bin/env bash\necho "{name}" >> "$TRACE_FILE"\nexit 1\n')
            script.chmod(script.stat().st_mode | stat.S_IXUSR)

        # codex 성공
        codex_script = bin_dir / "codex"
        codex_script.write_text('#!/usr/bin/env bash\necho "codex" >> "$TRACE_FILE"\nexit 0\n')
        codex_script.chmod(codex_script.stat().st_mode | stat.S_IXUSR)

        fn_file.write_text(shell_fn)

        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
        env["TRACE_FILE"] = str(trace_file)
        env["CLAUDE_FALLBACK_RETRY_MINUTES"] = "0"
        env.pop("CLAUDECODE", None)

        result = subprocess.run(
            [
                "bash",
                "-c",
                f"source {fn_file} && claude --fallback --to gemini,codex",
            ],
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        assert result.returncode == 0, result.stdout + result.stderr
        lines = trace_file.read_text().splitlines()
        # claude 실패 → gemini 실패 → codex 성공
        assert lines == ["claude", "gemini", "codex"]

    def test_claude_fallback_switches_to_codex_then_returns_to_claude(self, tmp_path):
        """Claude 한도 도달 시 codex로 전환 후 제한 해제되면 claude로 복귀."""
        gen = self._make_generator(["claude", "codex"])
        shell_fn = gen.generate_shell_functions()

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        trace_file = tmp_path / "trace.log"
        counter_file = tmp_path / "claude.count"
        fn_file = tmp_path / "claude_fn.sh"

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

        fn_file.write_text(shell_fn)

        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
        env["TRACE_FILE"] = str(trace_file)
        env["COUNTER_FILE"] = str(counter_file)
        env["CLAUDE_FALLBACK_RETRY_MINUTES"] = "0"
        env.pop("CLAUDECODE", None)  # 테스트에서 Claude 중첩 세션 감지 방지

        result = subprocess.run(
            ["bash", "-c", f"source {fn_file} && claude --fallback 'hello world'"],
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        assert result.returncode == 0, result.stdout + result.stderr
        assert trace_file.read_text().splitlines() == ["claude:1", "codex", "claude:2"]
