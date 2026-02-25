"""Tests for claude --fallback shell function generation."""

import os
import stat
import subprocess
import time
from unittest.mock import MagicMock, patch

from ai_env.core.config import Settings
from ai_env.mcp.generator import MCPConfigGenerator
from ai_env.mcp.vibe import generate_shell_functions


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
        assert "entry_cooldown_epochs" in result
        assert "Claude 제한 해제 감지. claude로 복귀합니다" in result
        assert "/rate-limit-option(s)?" in result

    def test_contains_passthrough_guard(self):
        """--fallback 없이 호출 시 원본 바이너리 passthrough 코드 포함 확인"""
        gen = self._make_generator(["claude", "codex"])
        result = gen.generate_shell_functions()

        assert 'command claude "$@"' in result
        assert '"--fallback"' in result

    def test_contains_resolve_bin_helper(self):
        """_resolve_bin 헬퍼 함수로 실제 바이너리 경로 확인"""
        gen = self._make_generator(["claude", "codex"])
        result = gen.generate_shell_functions()

        assert "_resolve_bin()" in result
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

    def test_contains_auto_option(self):
        """--auto 옵션으로 자동 승인 모드 코드 포함 확인"""
        gen = self._make_generator(["claude", "codex"])
        result = gen.generate_shell_functions()

        assert "--auto)" in result
        assert "auto_mode" in result
        assert "CLAUDE_FALLBACK_AUTO" in result
        assert "--dangerously-skip-permissions" in result
        assert "--allow-dangerously-skip-permissions" in result
        assert '"--yolo"' in result

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

    def test_auto_mode_injects_skip_permissions_for_claude(self, tmp_path):
        """--auto 모드에서 claude에 --dangerously-skip-permissions 자동 주입 확인"""
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
                f"source {fn_file} && claude --fallback --auto hello",
            ],
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        assert result.returncode == 0, result.stdout + result.stderr
        # --auto → claude에 --dangerously-skip-permissions 자동 주입
        assert trace_file.read_text().strip() == "args:--dangerously-skip-permissions hello"

    def test_codex_always_gets_yolo(self, tmp_path):
        """codex는 --auto 여부와 무관하게 항상 --yolo 주입 확인"""
        gen = self._make_generator(["claude", "codex"])
        shell_fn = gen.generate_shell_functions()

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        trace_file = tmp_path / "trace.log"
        fn_file = tmp_path / "claude_fn.sh"

        # claude 실패
        claude_script = bin_dir / "claude"
        claude_script.write_text('#!/usr/bin/env bash\necho "claude" >> "$TRACE_FILE"\nexit 1\n')
        claude_script.chmod(claude_script.stat().st_mode | stat.S_IXUSR)

        # codex: 전달받은 인자 기록
        codex_script = bin_dir / "codex"
        codex_script.write_text('#!/usr/bin/env bash\necho "args:$*" >> "$TRACE_FILE"\nexit 0\n')
        codex_script.chmod(codex_script.stat().st_mode | stat.S_IXUSR)

        fn_file.write_text(shell_fn)

        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
        env["TRACE_FILE"] = str(trace_file)
        env["CLAUDE_FALLBACK_RETRY_MINUTES"] = "0"
        env.pop("CLAUDECODE", None)

        # --auto 없이 실행해도 codex에 --yolo 주입
        result = subprocess.run(
            [
                "bash",
                "-c",
                f"source {fn_file} && claude --fallback hello",
            ],
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        assert result.returncode == 0, result.stdout + result.stderr
        lines = trace_file.read_text().splitlines()
        assert lines[0] == "claude"
        assert lines[1] == "args:--yolo hello"

    def test_dangerous_skip_permissions_maps_to_yolo_for_codex(self, tmp_path):
        """--dangerously-skip-permissions는 fallback wrapper에서 소비되어 codex에 --yolo 매핑."""
        gen = self._make_generator(["claude", "codex"])
        shell_fn = gen.generate_shell_functions()

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        trace_file = tmp_path / "trace.log"
        fn_file = tmp_path / "claude_fn.sh"

        # Claude: limit 메시지 출력 후 정상 종료(exit 0) -> rate-limit 감지로 fallback 유도
        claude_script = bin_dir / "claude"
        claude_script.write_text(
            "#!/usr/bin/env bash\n"
            'echo "claude:$*" >> "$TRACE_FILE"\n'
            'echo "You\'ve hit your limit • resets 2pm (Asia/Seoul)"\n'
            "exit 0\n"
        )
        claude_script.chmod(claude_script.stat().st_mode | stat.S_IXUSR)

        # Codex: 전달받은 인자 기록 후 exit 1 (cooldown 중 재시작 루프 방지)
        codex_script = bin_dir / "codex"
        codex_script.write_text('#!/usr/bin/env bash\necho "codex:$*" >> "$TRACE_FILE"\nexit 1\n')
        codex_script.chmod(codex_script.stat().st_mode | stat.S_IXUSR)

        fn_file.write_text(shell_fn)

        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
        env["TRACE_FILE"] = str(trace_file)
        env["CLAUDE_FALLBACK_RETRY_MINUTES"] = "60"
        env.pop("CLAUDECODE", None)

        subprocess.run(
            [
                "bash",
                "-c",
                f"source {fn_file} && claude --fallback --dangerously-skip-permissions test",
            ],
            env=env,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )

        # Codex도 실패하므로 전체 return 1 (플래그 매핑 검증이 핵심)
        lines = trace_file.read_text().splitlines()
        assert lines[0] == "claude:--dangerously-skip-permissions test"
        # rate-limit 시 핸드오프 컨텍스트가 생성되어 codex에 전달됨
        assert lines[1].startswith("codex:--yolo ")
        assert "test" in lines[1]  # 원래 프롬프트가 핸드오프에 포함

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

    def test_fallback_triggers_on_rate_limit_with_exit_zero(self, tmp_path):
        """Claude가 정상 종료(exit 0)해도 rate-limit 메시지가 있으면 fallback 트리거."""
        gen = self._make_generator(["claude", "codex"])
        shell_fn = gen.generate_shell_functions()

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        trace_file = tmp_path / "trace.log"
        fn_file = tmp_path / "claude_fn.sh"

        # Claude: rate limit 메시지 출력 후 정상 종료(exit 0)
        claude_script = bin_dir / "claude"
        claude_script.write_text(
            "#!/usr/bin/env bash\n"
            'echo "claude" >> "$TRACE_FILE"\n'
            'echo "You\'ve reached your usage limit"\n'
            "exit 0\n"
        )
        claude_script.chmod(claude_script.stat().st_mode | stat.S_IXUSR)

        # Codex: exit 1 (cooldown 중 재시작 루프 방지, rate-limit 감지 검증이 핵심)
        codex_script = bin_dir / "codex"
        codex_script.write_text('#!/usr/bin/env bash\necho "codex" >> "$TRACE_FILE"\nexit 1\n')
        codex_script.chmod(codex_script.stat().st_mode | stat.S_IXUSR)

        fn_file.write_text(shell_fn)

        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
        env["TRACE_FILE"] = str(trace_file)
        # cooldown을 충분히 길게 → rate-limit 감지가 실제로 fallback을 유도하는지 확인
        env["CLAUDE_FALLBACK_RETRY_MINUTES"] = "60"
        env.pop("CLAUDECODE", None)

        subprocess.run(
            ["bash", "-c", f"source {fn_file} && claude --fallback test"],
            env=env,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )

        lines = trace_file.read_text().splitlines()
        # Claude가 exit 0이지만 rate limit 메시지 → codex로 fallback
        assert lines == ["claude", "codex"]

    def test_fallback_triggers_on_hit_your_limit_with_exit_zero(self, tmp_path):
        """\"You've hit your limit\" 문구도 exit 0이어도 fallback 트리거."""
        gen = self._make_generator(["claude", "codex"])
        shell_fn = gen.generate_shell_functions()

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        trace_file = tmp_path / "trace.log"
        fn_file = tmp_path / "claude_fn.sh"

        claude_script = bin_dir / "claude"
        claude_script.write_text(
            "#!/usr/bin/env bash\n"
            'echo "claude" >> "$TRACE_FILE"\n'
            'echo "You\'ve hit your limit • resets 2pm (Asia/Seoul)"\n'
            "exit 0\n"
        )
        claude_script.chmod(claude_script.stat().st_mode | stat.S_IXUSR)

        codex_script = bin_dir / "codex"
        codex_script.write_text('#!/usr/bin/env bash\necho "codex" >> "$TRACE_FILE"\nexit 1\n')
        codex_script.chmod(codex_script.stat().st_mode | stat.S_IXUSR)

        fn_file.write_text(shell_fn)

        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
        env["TRACE_FILE"] = str(trace_file)
        env["CLAUDE_FALLBACK_RETRY_MINUTES"] = "60"
        env.pop("CLAUDECODE", None)

        subprocess.run(
            ["bash", "-c", f"source {fn_file} && claude --fallback test"],
            env=env,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )

        assert trace_file.read_text().splitlines() == ["claude", "codex"]

    def test_fallback_triggers_on_rate_limit_option_singular(self, tmp_path):
        """'/rate-limit-option' 단수형 문구도 fallback 트리거."""
        gen = self._make_generator(["claude", "codex"])
        shell_fn = gen.generate_shell_functions()

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        trace_file = tmp_path / "trace.log"
        fn_file = tmp_path / "claude_fn.sh"

        claude_script = bin_dir / "claude"
        claude_script.write_text(
            "#!/usr/bin/env bash\n"
            'echo "claude" >> "$TRACE_FILE"\n'
            'echo "/rate-limit-option"\n'
            "exit 0\n"
        )
        claude_script.chmod(claude_script.stat().st_mode | stat.S_IXUSR)

        codex_script = bin_dir / "codex"
        codex_script.write_text('#!/usr/bin/env bash\necho "codex" >> "$TRACE_FILE"\nexit 1\n')
        codex_script.chmod(codex_script.stat().st_mode | stat.S_IXUSR)

        fn_file.write_text(shell_fn)

        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
        env["TRACE_FILE"] = str(trace_file)
        env["CLAUDE_FALLBACK_RETRY_MINUTES"] = "60"
        env.pop("CLAUDECODE", None)

        subprocess.run(
            ["bash", "-c", f"source {fn_file} && claude --fallback test"],
            env=env,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )

        assert trace_file.read_text().splitlines() == ["claude", "codex"]

    def test_fallback_triggers_on_rate_limit_quota_messages_with_exit_zero(self, tmp_path):
        """quota/limit 문구가 출력되면 exit 0이어도 fallback 트리거."""
        gen = self._make_generator(["claude", "codex"])
        shell_fn = gen.generate_shell_functions()

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        trace_file = tmp_path / "trace.log"
        fn_file = tmp_path / "claude_fn.sh"

        claude_script = bin_dir / "claude"
        claude_script.write_text(
            "#!/usr/bin/env bash\n"
            'echo "claude" >> "$TRACE_FILE"\n'
            'echo "You have exhausted your quota and exceeded your request limit"\n'
            "exit 0\n"
        )
        claude_script.chmod(claude_script.stat().st_mode | stat.S_IXUSR)

        codex_script = bin_dir / "codex"
        codex_script.write_text('#!/usr/bin/env bash\necho "codex" >> "$TRACE_FILE"\nexit 1\n')
        codex_script.chmod(codex_script.stat().st_mode | stat.S_IXUSR)

        fn_file.write_text(shell_fn)

        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
        env["TRACE_FILE"] = str(trace_file)
        env["CLAUDE_FALLBACK_RETRY_MINUTES"] = "60"
        env.pop("CLAUDECODE", None)

        subprocess.run(
            ["bash", "-c", f"source {fn_file} && claude --fallback test"],
            env=env,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )

        assert trace_file.read_text().splitlines() == ["claude", "codex"]

    def test_fallback_triggers_on_reached_monthly_rate_limit_with_exit_zero(self, tmp_path):
        """월/주간 한도 도달 문구도 exit 0이면 fallback 트리거."""
        gen = self._make_generator(["claude", "codex"])
        shell_fn = gen.generate_shell_functions()

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        trace_file = tmp_path / "trace.log"
        fn_file = tmp_path / "claude_fn.sh"

        claude_script = bin_dir / "claude"
        claude_script.write_text(
            "#!/usr/bin/env bash\n"
            'echo "claude" >> "$TRACE_FILE"\n'
            'echo "You have reached your request limit for the month"\n'
            "exit 0\n"
        )
        claude_script.chmod(claude_script.stat().st_mode | stat.S_IXUSR)

        codex_script = bin_dir / "codex"
        codex_script.write_text('#!/usr/bin/env bash\necho "codex" >> "$TRACE_FILE"\nexit 1\n')
        codex_script.chmod(codex_script.stat().st_mode | stat.S_IXUSR)

        fn_file.write_text(shell_fn)

        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
        env["TRACE_FILE"] = str(trace_file)
        env["CLAUDE_FALLBACK_RETRY_MINUTES"] = "60"
        env.pop("CLAUDECODE", None)

        subprocess.run(
            ["bash", "-c", f"source {fn_file} && claude --fallback test"],
            env=env,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )

        assert trace_file.read_text().splitlines() == ["claude", "codex"]

    def test_no_false_positive_on_usage_percentage_with_exit_zero(self, tmp_path):
        """'You've used 85% of your weekly limit' + exit 0: rate-limit 아님, fallback 없음."""
        gen = self._make_generator(["claude", "codex"])
        shell_fn = gen.generate_shell_functions()

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        trace_file = tmp_path / "trace.log"
        fn_file = tmp_path / "claude_fn.sh"

        # Claude: 85% 사용량 정보 메시지 출력 후 정상 종료 (exit 0)
        claude_script = bin_dir / "claude"
        claude_script.write_text(
            "#!/usr/bin/env bash\n"
            'echo "claude" >> "$TRACE_FILE"\n'
            'echo "You\'ve used 85% of your weekly limit · resets Feb 23 at 9am (Asia/Seoul)"\n'
            "exit 0\n"
        )
        claude_script.chmod(claude_script.stat().st_mode | stat.S_IXUSR)

        codex_script = bin_dir / "codex"
        codex_script.write_text('#!/usr/bin/env bash\necho "codex" >> "$TRACE_FILE"\nexit 1\n')
        codex_script.chmod(codex_script.stat().st_mode | stat.S_IXUSR)

        fn_file.write_text(shell_fn)

        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
        env["TRACE_FILE"] = str(trace_file)
        env["CLAUDE_FALLBACK_RETRY_MINUTES"] = "60"
        env.pop("CLAUDECODE", None)

        subprocess.run(
            ["bash", "-c", f"source {fn_file} && claude --fallback test"],
            env=env,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )

        lines = trace_file.read_text().splitlines()
        # 85% 사용량 메시지는 rate-limit이 아님 → strict 패턴도 미매칭 → fallback 없음
        assert lines == ["claude"]

    def test_no_false_positive_on_usage_percentage_with_exit_one(self, tmp_path):
        """'You've used 85% of your weekly limit' + exit 1: rate-limit 오탐 없이 일반 오류 처리."""
        gen = self._make_generator(["claude", "codex"])
        shell_fn = gen.generate_shell_functions()

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        trace_file = tmp_path / "trace.log"
        fn_file = tmp_path / "claude_fn.sh"

        # Claude: 85% 사용량 메시지 출력 후 비정상 종료 (exit 1)
        claude_script = bin_dir / "claude"
        claude_script.write_text(
            "#!/usr/bin/env bash\n"
            'echo "claude" >> "$TRACE_FILE"\n'
            'echo "You\'ve used 85% of your weekly limit · resets Feb 23 at 9am (Asia/Seoul)"\n'
            "exit 1\n"
        )
        claude_script.chmod(claude_script.stat().st_mode | stat.S_IXUSR)

        codex_script = bin_dir / "codex"
        codex_script.write_text('#!/usr/bin/env bash\necho "codex" >> "$TRACE_FILE"\nexit 1\n')
        codex_script.chmod(codex_script.stat().st_mode | stat.S_IXUSR)

        fn_file.write_text(shell_fn)

        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
        env["TRACE_FILE"] = str(trace_file)
        env["CLAUDE_FALLBACK_RETRY_MINUTES"] = "60"
        env.pop("CLAUDECODE", None)

        result = subprocess.run(
            ["bash", "-c", f"source {fn_file} && claude --fallback test"],
            env=env,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )

        lines = trace_file.read_text().splitlines()
        # exit 1이므로 codex로 fallback은 됨 (일반 오류 → 다음 에이전트 전환 설계)
        assert lines == ["claude", "codex"]
        # 하지만 rate-limit 감지가 아니므로 핸드오프/cooldown 메시지 없어야 함
        assert "rate-limit 감지" not in result.stdout
        assert "핸드오프" not in result.stdout

    def test_realtime_detection_interrupts_claude_and_fallbacks(self, tmp_path):
        """Claude가 종료하지 않아도 rate-limit 문구가 보이면 실시간으로 중단 후 fallback."""
        gen = self._make_generator(["claude", "codex"])
        shell_fn = gen.generate_shell_functions()

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        trace_file = tmp_path / "trace.log"
        fn_file = tmp_path / "claude_fn.sh"

        claude_script = bin_dir / "claude"
        claude_script.write_text(
            "#!/usr/bin/env bash\n"
            'echo "claude" >> "$TRACE_FILE"\n'
            'trap \'echo "claude-terminated" >> "$TRACE_FILE"; exit 0\' INT TERM\n'
            'echo "/rate-limit-option"\n'
            "sleep 120\n"
            'echo "claude-after-sleep" >> "$TRACE_FILE"\n'
            "exit 0\n"
        )
        claude_script.chmod(claude_script.stat().st_mode | stat.S_IXUSR)

        # cooldown 중 재시작 루프를 막기 위해 codex는 실패로 종료
        codex_script = bin_dir / "codex"
        codex_script.write_text('#!/usr/bin/env bash\necho "codex" >> "$TRACE_FILE"\nexit 1\n')
        codex_script.chmod(codex_script.stat().st_mode | stat.S_IXUSR)

        fn_file.write_text(shell_fn)

        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
        env["TRACE_FILE"] = str(trace_file)
        env["CLAUDE_FALLBACK_RETRY_MINUTES"] = "60"
        env.pop("CLAUDECODE", None)

        result = subprocess.run(
            ["bash", "-c", f"source {fn_file} && claude --fallback test"],
            env=env,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )

        lines = trace_file.read_text().splitlines()
        assert result.returncode == 1
        assert lines[0] == "claude"
        assert "codex" in lines
        assert "claude-after-sleep" not in lines

    def test_realtime_detection_with_ansi_tui_output(self, tmp_path):
        """ANSI 이스케이프가 포함된 TUI 출력에서도 rate-limit 실시간 감지 후 fallback."""
        gen = self._make_generator(["claude", "codex"])
        shell_fn = gen.generate_shell_functions()

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        trace_file = tmp_path / "trace.log"
        fn_file = tmp_path / "claude_fn.sh"

        # Claude: ANSI TUI 형태로 rate-limit 화면 렌더 후 sleep (종료하지 않음)
        claude_script = bin_dir / "claude"
        claude_script.write_text(
            "#!/usr/bin/env bash\n"
            'echo "claude" >> "$TRACE_FILE"\n'
            'trap \'echo "claude-terminated" >> "$TRACE_FILE"; exit 0\' INT TERM\n'
            "# ANSI TUI 형태의 rate-limit 화면\n"
            "printf '\\e[?1049h\\e[H\\e[2J'\n"
            "printf '\\e[1;33m⚠\\e[0m You\\'ve hit your limit • \\e[2mresets 2pm\\e[0m\\n'\n"
            "printf '\\e[36m  /rate-limit-options\\e[0m  \\e[36m/reset-rate-limit\\e[0m\\n'\n"
            "sleep 120\n"
            'echo "claude-after-sleep" >> "$TRACE_FILE"\n'
            "exit 0\n"
        )
        claude_script.chmod(claude_script.stat().st_mode | stat.S_IXUSR)

        codex_script = bin_dir / "codex"
        codex_script.write_text('#!/usr/bin/env bash\necho "codex" >> "$TRACE_FILE"\nexit 1\n')
        codex_script.chmod(codex_script.stat().st_mode | stat.S_IXUSR)

        fn_file.write_text(shell_fn)

        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
        env["TRACE_FILE"] = str(trace_file)
        env["CLAUDE_FALLBACK_RETRY_MINUTES"] = "60"
        env.pop("CLAUDECODE", None)

        result = subprocess.run(
            ["bash", "-c", f"source {fn_file} && claude --fallback test"],
            env=env,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )

        lines = trace_file.read_text().splitlines()
        assert result.returncode == 1
        assert lines[0] == "claude"
        assert "codex" in lines
        # 실시간 감지로 sleep 120 전에 종료되어야 함
        assert "claude-after-sleep" not in lines

    def test_realtime_detection_with_long_rate_limit_screen_output(self, tmp_path):
        """Rate-limit 문구 뒤에 긴 TUI 출력이 이어져도 실시간 감지 후 fallback."""
        gen = self._make_generator(["claude", "codex"])
        shell_fn = gen.generate_shell_functions()

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        trace_file = tmp_path / "trace.log"
        fn_file = tmp_path / "claude_fn.sh"

        # Claude: rate-limit 화면 출력 후 긴 노이즈 라인 추가 + sleep (종료하지 않음)
        claude_script = bin_dir / "claude"
        claude_script.write_text(
            "#!/usr/bin/env bash\n"
            'echo "claude" >> "$TRACE_FILE"\n'
            'trap \'echo "claude-terminated" >> "$TRACE_FILE"; exit 0\' INT TERM\n'
            'echo "You\'ve hit your limit • resets 12am (Asia/Seoul)"\n'
            'echo "/rate-limit-options"\n'
            'echo "What do you want to do?"\n'
            'for i in $(seq 1 140); do echo "tui-noise-line-$i........................................"; done\n'
            "sleep 120\n"
            'echo "claude-after-sleep" >> "$TRACE_FILE"\n'
            "exit 0\n"
        )
        claude_script.chmod(claude_script.stat().st_mode | stat.S_IXUSR)

        # cooldown 중 재시작 루프 방지: codex는 실패 종료
        codex_script = bin_dir / "codex"
        codex_script.write_text('#!/usr/bin/env bash\necho "codex" >> "$TRACE_FILE"\nexit 1\n')
        codex_script.chmod(codex_script.stat().st_mode | stat.S_IXUSR)

        fn_file.write_text(shell_fn)

        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
        env["TRACE_FILE"] = str(trace_file)
        env["CLAUDE_FALLBACK_RETRY_MINUTES"] = "60"
        env.pop("CLAUDECODE", None)

        result = subprocess.run(
            ["bash", "-c", f"source {fn_file} && claude --fallback test"],
            env=env,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )

        lines = trace_file.read_text().splitlines()
        assert result.returncode == 1
        assert lines[0] == "claude"
        assert "codex" in lines
        # 긴 출력 이후 sleep 진입 전에 끊겨야 함
        assert "claude-after-sleep" not in lines

    def test_codex_restarts_while_claude_cooldown_active(self, tmp_path):
        """Claude cooldown 중 Codex 세션 종료(exit 0) 시 Codex 자동 재시작 확인."""
        gen = self._make_generator(["claude", "codex"])
        shell_fn = gen.generate_shell_functions()

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        trace_file = tmp_path / "trace.log"
        counter_file = tmp_path / "codex.count"
        fn_file = tmp_path / "claude_fn.sh"

        # Claude: rate-limit 메시지 출력 후 exit 0
        claude_script = bin_dir / "claude"
        claude_script.write_text(
            "#!/usr/bin/env bash\n"
            'echo "claude" >> "$TRACE_FILE"\n'
            'echo "You\'ve hit your limit • resets 2pm"\n'
            "exit 0\n"
        )
        claude_script.chmod(claude_script.stat().st_mode | stat.S_IXUSR)

        # Codex: 카운터 기반 - 2회 exit 0 후 3회차에 exit 1 (루프 종료)
        codex_script = bin_dir / "codex"
        codex_script.write_text(
            "#!/usr/bin/env bash\n"
            'count=$(cat "$COUNTER_FILE" 2>/dev/null || echo 0)\n'
            "count=$((count + 1))\n"
            'echo "$count" > "$COUNTER_FILE"\n'
            'echo "codex:$count" >> "$TRACE_FILE"\n'
            'if [[ "$count" -ge 3 ]]; then exit 1; fi\n'
            "exit 0\n"
        )
        codex_script.chmod(codex_script.stat().st_mode | stat.S_IXUSR)

        fn_file.write_text(shell_fn)

        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
        env["TRACE_FILE"] = str(trace_file)
        env["COUNTER_FILE"] = str(counter_file)
        env["CLAUDE_FALLBACK_RETRY_MINUTES"] = "60"
        env.pop("CLAUDECODE", None)

        subprocess.run(
            ["bash", "-c", f"source {fn_file} && claude --fallback test"],
            env=env,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )

        lines = trace_file.read_text().splitlines()
        # Claude rate-limit → Codex 시작 → exit 0이지만 cooldown 활성 → Codex 재시작 (×2)
        # 3회차에 exit 1로 루프 종료
        assert lines == ["claude", "codex:1", "codex:2", "codex:3"]

    def test_handoff_context_passed_to_codex_on_rate_limit(self, tmp_path):
        """Claude rate-limit 시 핸드오프 컨텍스트가 codex에 전달되는지 확인."""
        gen = self._make_generator(["claude", "codex"])
        shell_fn = gen.generate_shell_functions()

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        trace_file = tmp_path / "trace.log"
        fn_file = tmp_path / "claude_fn.sh"

        # Claude: rate-limit 메시지 출력 후 exit 0
        claude_script = bin_dir / "claude"
        claude_script.write_text(
            "#!/usr/bin/env bash\n"
            'echo "claude" >> "$TRACE_FILE"\n'
            'echo "You\'ve hit your limit"\n'
            "exit 0\n"
        )
        claude_script.chmod(claude_script.stat().st_mode | stat.S_IXUSR)

        # Codex: 전달받은 인자를 trace에 기록
        codex_script = bin_dir / "codex"
        codex_script.write_text('#!/usr/bin/env bash\necho "codex:$*" >> "$TRACE_FILE"\nexit 1\n')
        codex_script.chmod(codex_script.stat().st_mode | stat.S_IXUSR)

        fn_file.write_text(shell_fn)

        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
        env["TRACE_FILE"] = str(trace_file)
        env["CLAUDE_FALLBACK_RETRY_MINUTES"] = "60"
        env.pop("CLAUDECODE", None)

        subprocess.run(
            [
                "bash",
                "-c",
                f"source {fn_file} && claude --fallback 'implement login feature'",
            ],
            env=env,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )

        lines = trace_file.read_text().splitlines()
        assert lines[0] == "claude"
        # Codex가 핸드오프 프롬프트를 받음 (원래 작업 + 핸드오프 파일 참조)
        assert "codex:" in lines[1]
        assert "implement login feature" in lines[1]
        assert "handoff" in lines[1].lower() or "claude-fb-handoff" in lines[1]

    def test_handoff_includes_original_prompt_in_codex_args(self, tmp_path):
        """핸드오프 시 원래 프롬프트가 codex에 전달되는 인자에 포함되는지 확인."""
        gen = self._make_generator(["claude", "codex"])
        shell_fn = gen.generate_shell_functions()

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        trace_file = tmp_path / "trace.log"
        fn_file = tmp_path / "claude_fn.sh"

        claude_script = bin_dir / "claude"
        claude_script.write_text(
            "#!/usr/bin/env bash\n"
            'echo "claude" >> "$TRACE_FILE"\n'
            'echo "rate limit exceeded"\n'
            "exit 1\n"
        )
        claude_script.chmod(claude_script.stat().st_mode | stat.S_IXUSR)

        # Codex: 인자 기록 후 exit 1 (cooldown 중 재시작 루프 방지)
        codex_script = bin_dir / "codex"
        codex_script.write_text('#!/usr/bin/env bash\necho "codex:$*" >> "$TRACE_FILE"\nexit 1\n')
        codex_script.chmod(codex_script.stat().st_mode | stat.S_IXUSR)

        fn_file.write_text(shell_fn)

        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
        env["TRACE_FILE"] = str(trace_file)
        env["CLAUDE_FALLBACK_RETRY_MINUTES"] = "60"
        env.pop("CLAUDECODE", None)

        subprocess.run(
            [
                "bash",
                "-c",
                f"source {fn_file} && claude --fallback '/wf-code bitcoin'",
            ],
            env=env,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )

        lines = trace_file.read_text().splitlines()
        assert lines[0] == "claude"
        # 원래 프롬프트가 codex 인자에 포함
        assert "/wf-code bitcoin" in lines[1]

    def test_handoff_file_cleaned_on_codex_success(self, tmp_path):
        """Codex 성공 후 핸드오프 임시 파일이 정리되는지 확인."""
        gen = self._make_generator(["claude", "codex"])
        shell_fn = gen.generate_shell_functions()

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        trace_file = tmp_path / "trace.log"
        counter_file = tmp_path / "claude.count"
        fn_file = tmp_path / "claude_fn.sh"

        # Claude: 1회차 rate-limit, 2회차 정상 종료 (카운터 기반)
        claude_script = bin_dir / "claude"
        claude_script.write_text(
            "#!/usr/bin/env bash\n"
            'count=$(cat "$COUNTER_FILE" 2>/dev/null || echo 0)\n'
            "count=$((count + 1))\n"
            'echo "$count" > "$COUNTER_FILE"\n'
            'echo "claude:$count" >> "$TRACE_FILE"\n'
            'if [[ "$count" -eq 1 ]]; then\n'
            '  echo "rate limit exceeded"\n'
            "  exit 1\n"
            "fi\n"
            "exit 0\n"
        )
        claude_script.chmod(claude_script.stat().st_mode | stat.S_IXUSR)

        # Codex: 핸드오프 파일 경로를 추출하여 기록 후 성공 종료
        codex_script = bin_dir / "codex"
        codex_script.write_text(
            "#!/usr/bin/env bash\n"
            "# 인자에서 핸드오프 파일 경로 추출\n"
            'hf=$(echo "$*" | grep -oE "/[^ ]*claude-fb-handoff[^ ]*")\n'
            'echo "handoff:$hf" >> "$TRACE_FILE"\n'
            "exit 0\n"
        )
        codex_script.chmod(codex_script.stat().st_mode | stat.S_IXUSR)

        fn_file.write_text(shell_fn)

        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
        env["TRACE_FILE"] = str(trace_file)
        env["COUNTER_FILE"] = str(counter_file)
        env["CLAUDE_FALLBACK_RETRY_MINUTES"] = "0"
        env.pop("CLAUDECODE", None)

        result = subprocess.run(
            ["bash", "-c", f"source {fn_file} && claude --fallback test"],
            env=env,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )

        assert result.returncode == 0
        lines = trace_file.read_text().splitlines()
        # claude:1 → codex(handoff) → claude:2(성공)
        assert lines[0] == "claude:1"
        # 핸드오프 파일 경로를 codex가 기록했어야 함
        handoff_line = next((line for line in lines if line.startswith("handoff:")), "")
        handoff_path = handoff_line.replace("handoff:", "").strip()
        # 핸드오프 파일이 정리되어 없어야 함
        if handoff_path:
            import pathlib

            assert not pathlib.Path(
                handoff_path
            ).exists(), f"핸드오프 파일이 정리되지 않음: {handoff_path}"

    def test_no_handoff_when_claude_exits_normally(self, tmp_path):
        """Claude가 rate-limit 없이 정상 종료 시 핸드오프 없음 확인."""
        gen = self._make_generator(["claude", "codex"])
        shell_fn = gen.generate_shell_functions()

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        trace_file = tmp_path / "trace.log"
        fn_file = tmp_path / "claude_fn.sh"

        # Claude: 정상 종료 (rate-limit 없음)
        claude_script = bin_dir / "claude"
        claude_script.write_text('#!/usr/bin/env bash\necho "claude:$*" >> "$TRACE_FILE"\nexit 0\n')
        claude_script.chmod(claude_script.stat().st_mode | stat.S_IXUSR)

        # Codex: 호출되면 안됨
        codex_script = bin_dir / "codex"
        codex_script.write_text('#!/usr/bin/env bash\necho "codex:$*" >> "$TRACE_FILE"\nexit 0\n')
        codex_script.chmod(codex_script.stat().st_mode | stat.S_IXUSR)

        fn_file.write_text(shell_fn)

        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
        env["TRACE_FILE"] = str(trace_file)
        env.pop("CLAUDECODE", None)

        result = subprocess.run(
            ["bash", "-c", f"source {fn_file} && claude --fallback hello"],
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        assert result.returncode == 0
        lines = trace_file.read_text().splitlines()
        # Claude만 실행되고, 핸드오프/codex 호출 없음
        assert lines == ["claude:hello"]


class TestModelLevelFallback:
    """model-level fallback (agent:model 문법) 테스트"""

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

    def test_model_suffix_in_agents_array(self):
        """claude:sonnet 엔트리가 agents 배열에 포함되는지 확인"""
        gen = self._make_generator(["claude", "claude:sonnet", "codex"])
        result = gen.generate_shell_functions()
        assert 'agents=("claude" "claude:sonnet" "codex")' in result

    def test_model_suffix_priority_display(self):
        """priority 표시에서 claude:sonnet이 claude (sonnet) 형태로 출력"""
        gen = self._make_generator(["claude", "claude:sonnet", "codex"])
        result = gen.generate_shell_functions()
        assert "claude → claude (sonnet) → codex" in result

    def test_contains_parse_agent_entry_helper(self):
        """_parse_agent_entry 헬퍼 함수 포함 확인"""
        gen = self._make_generator(["claude", "claude:sonnet", "codex"])
        result = gen.generate_shell_functions()
        assert "_parse_agent_entry()" in result
        assert "base_agent" in result
        assert "model_suffix" in result

    def test_contains_per_entry_cooldown(self):
        """per-entry cooldown 배열 포함 확인"""
        gen = self._make_generator(["claude", "claude:sonnet", "codex"])
        result = gen.generate_shell_functions()
        assert "entry_cooldown_epochs" in result

    def test_model_flag_injected_for_claude_sonnet(self, tmp_path):
        """claude:sonnet 엔트리에서 --model sonnet 플래그가 주입되는지 확인"""
        gen = self._make_generator(["claude:sonnet"])
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
            ["bash", "-c", f"source {fn_file} && claude --fallback hello"],
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        assert result.returncode == 0, result.stdout + result.stderr
        assert trace_file.read_text().strip() == "args:--model sonnet hello"

    def test_no_model_flag_for_plain_claude(self, tmp_path):
        """plain claude 엔트리에서는 --model 플래그가 주입되지 않음"""
        gen = self._make_generator(["claude"])
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
            ["bash", "-c", f"source {fn_file} && claude --fallback hello"],
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        assert result.returncode == 0
        assert trace_file.read_text().strip() == "args:hello"

    def test_model_fallback_opus_to_sonnet_to_codex(self, tmp_path):
        """Claude Opus rate-limit → Claude Sonnet 성공 전체 경로 테스트"""
        gen = self._make_generator(["claude", "claude:sonnet", "codex"])
        shell_fn = gen.generate_shell_functions()

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        trace_file = tmp_path / "trace.log"
        counter_file = tmp_path / "claude.count"
        fn_file = tmp_path / "claude_fn.sh"

        # Claude: 1회차(opus) rate-limit, 2회차(sonnet) 성공
        claude_script = bin_dir / "claude"
        claude_script.write_text(
            "#!/usr/bin/env bash\n"
            'count=$(cat "$COUNTER_FILE" 2>/dev/null || echo 0)\n'
            "count=$((count + 1))\n"
            'echo "$count" > "$COUNTER_FILE"\n'
            'echo "claude:$count:$*" >> "$TRACE_FILE"\n'
            'if [[ "$count" -eq 1 ]]; then\n'
            '  echo "rate limit exceeded"\n'
            "  exit 1\n"
            "fi\n"
            "exit 0\n"
        )
        claude_script.chmod(claude_script.stat().st_mode | stat.S_IXUSR)

        codex_script = bin_dir / "codex"
        codex_script.write_text('#!/usr/bin/env bash\necho "codex" >> "$TRACE_FILE"\nexit 0\n')
        codex_script.chmod(codex_script.stat().st_mode | stat.S_IXUSR)

        fn_file.write_text(shell_fn)

        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
        env["TRACE_FILE"] = str(trace_file)
        env["COUNTER_FILE"] = str(counter_file)
        env["CLAUDE_FALLBACK_RETRY_MINUTES"] = "0"
        env.pop("CLAUDECODE", None)

        result = subprocess.run(
            ["bash", "-c", f"source {fn_file} && claude --fallback hello"],
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        assert result.returncode == 0, result.stdout + result.stderr
        lines = trace_file.read_text().splitlines()
        # 1st call: opus (no --model), rate-limited
        assert lines[0] == "claude:1:hello"
        # 2nd call: sonnet (--model sonnet), success
        assert lines[1] == "claude:2:--model sonnet hello"

    def test_model_fallback_all_claude_rate_limited_then_codex(self, tmp_path):
        """Claude Opus + Sonnet 모두 rate-limit → Codex 전환 테스트"""
        gen = self._make_generator(["claude", "claude:sonnet", "codex"])
        shell_fn = gen.generate_shell_functions()

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        trace_file = tmp_path / "trace.log"
        fn_file = tmp_path / "claude_fn.sh"

        # Claude: 항상 rate-limit
        claude_script = bin_dir / "claude"
        claude_script.write_text(
            "#!/usr/bin/env bash\n"
            'echo "claude:$*" >> "$TRACE_FILE"\n'
            'echo "rate limit exceeded"\n'
            "exit 1\n"
        )
        claude_script.chmod(claude_script.stat().st_mode | stat.S_IXUSR)

        # Codex: 성공 (exit 1로 루프 종료 방지)
        codex_script = bin_dir / "codex"
        codex_script.write_text('#!/usr/bin/env bash\necho "codex:$*" >> "$TRACE_FILE"\nexit 1\n')
        codex_script.chmod(codex_script.stat().st_mode | stat.S_IXUSR)

        fn_file.write_text(shell_fn)

        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
        env["TRACE_FILE"] = str(trace_file)
        env["CLAUDE_FALLBACK_RETRY_MINUTES"] = "60"
        env.pop("CLAUDECODE", None)

        subprocess.run(
            ["bash", "-c", f"source {fn_file} && claude --fallback hello"],
            env=env,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )

        lines = trace_file.read_text().splitlines()
        # Opus rate-limited → Sonnet rate-limited → Codex
        assert lines[0] == "claude:hello"
        assert lines[1] == "claude:--model sonnet hello"
        assert lines[2].startswith("codex:")

    def test_model_suffix_auto_mode_injects_skip_permissions(self, tmp_path):
        """--auto 모드에서 claude:sonnet에도 --dangerously-skip-permissions 주입"""
        gen = self._make_generator(["claude:sonnet"])
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
                f"source {fn_file} && claude --fallback --auto hello",
            ],
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        assert result.returncode == 0
        # --model sonnet이 맨 앞에 주입되고, --dangerously-skip-permissions 그 뒤
        assert (
            trace_file.read_text().strip()
            == "args:--model sonnet --dangerously-skip-permissions hello"
        )

    def test_list_display_with_model_suffix(self, tmp_path):
        """claude --fallback -l 에서 모델 suffix가 표시되는지 확인"""
        gen = self._make_generator(["claude", "claude:sonnet", "codex"])
        shell_fn = gen.generate_shell_functions()

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        fn_file = tmp_path / "claude_fn.sh"

        claude_script = bin_dir / "claude"
        claude_script.write_text("#!/usr/bin/env bash\nexit 0\n")
        claude_script.chmod(claude_script.stat().st_mode | stat.S_IXUSR)

        fn_file.write_text(shell_fn)

        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"

        result = subprocess.run(
            ["bash", "-c", f"source {fn_file} && claude --fallback -l"],
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        assert result.returncode == 0
        assert "claude (sonnet)" in result.stdout
        assert "codex" in result.stdout


class TestSessionLogAndExit:
    """세션 로그 영구 보관 + /exit 종료 테스트"""

    def _make_generator(
        self,
        agent_priority: list[str],
        fallback_log_dir: str | None = None,
    ) -> MCPConfigGenerator:
        """테스트용 generator 생성"""
        secrets = MagicMock()
        secrets.get.return_value = ""
        with (
            patch("ai_env.mcp.generator.load_mcp_config") as mock_mcp,
            patch("ai_env.mcp.generator.load_settings") as mock_settings,
        ):
            mock_mcp.return_value = MagicMock(mcp_servers={})
            settings = Settings(
                agent_priority=agent_priority,
                fallback_log_dir=fallback_log_dir,
            )
            mock_settings.return_value = settings
            return MCPConfigGenerator(secrets)

    def test_generate_accepts_fallback_log_dir(self):
        """generate_shell_functions에 fallback_log_dir 전달 가능."""
        result = generate_shell_functions(["claude", "codex"], fallback_log_dir="~/my-logs")
        assert "CLAUDE_FALLBACK_LOG_DIR" in result
        assert "~/my-logs" in result

    def test_generate_empty_log_dir_when_none(self):
        """fallback_log_dir=None이면 기본값 빈 문자열."""
        result = generate_shell_functions(["claude", "codex"])
        # 환경변수 미설정 시 빈 문자열 → 기존 temp 동작
        assert "CLAUDE_FALLBACK_LOG_DIR:-}" in result

    def test_contains_session_id_helper(self):
        """_get_claude_session_id 헬퍼 함수 포함 확인."""
        result = generate_shell_functions(["claude", "codex"])
        assert "_get_claude_session_id()" in result
        assert ".claude/projects/" in result
        assert "shasum" in result

    def test_contains_exit_detection(self):
        """_user_explicitly_exited 헬퍼 함수 포함 확인."""
        result = generate_shell_functions(["claude", "codex"])
        assert "_user_explicitly_exited()" in result
        assert "/exit" in result
        assert "/quit" in result

    def test_contains_save_session_log(self):
        """_save_session_log 헬퍼 함수 포함 확인."""
        result = generate_shell_functions(["claude", "codex"])
        assert "_save_session_log()" in result

    def test_exit_command_prevents_codex_restart(self, tmp_path):
        """Codex에서 /exit 입력 시 래퍼가 재시작하지 않는지 확인."""
        gen = self._make_generator(["claude", "codex"])
        shell_fn = gen.generate_shell_functions()

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        trace_file = tmp_path / "trace.log"
        codex_counter = tmp_path / "codex.count"
        fn_file = tmp_path / "claude_fn.sh"

        # Claude: 항상 rate-limit
        claude_script = bin_dir / "claude"
        claude_script.write_text(
            "#!/usr/bin/env bash\n"
            'echo "claude" >> "$TRACE_FILE"\n'
            'echo "rate limit exceeded"\n'
            "exit 1\n"
        )
        claude_script.chmod(claude_script.stat().st_mode | stat.S_IXUSR)

        # Codex: /exit 출력 후 종료, 호출 횟수 카운트
        codex_script = bin_dir / "codex"
        codex_script.write_text(
            "#!/usr/bin/env bash\n"
            'count=$(cat "$CODEX_COUNTER" 2>/dev/null || echo 0)\n'
            "count=$((count + 1))\n"
            'echo "$count" > "$CODEX_COUNTER"\n'
            'echo "codex:$count" >> "$TRACE_FILE"\n'
            'echo "> /exit"\n'
            "exit 0\n"
        )
        codex_script.chmod(codex_script.stat().st_mode | stat.S_IXUSR)

        fn_file.write_text(shell_fn)

        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
        env["TRACE_FILE"] = str(trace_file)
        env["CODEX_COUNTER"] = str(codex_counter)
        env["CLAUDE_FALLBACK_RETRY_MINUTES"] = "60"
        env.pop("CLAUDECODE", None)

        result = subprocess.run(
            ["bash", "-c", f"source {fn_file} && claude --fallback test"],
            env=env,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )

        assert result.returncode == 0
        lines = trace_file.read_text().splitlines()
        codex_lines = [line for line in lines if line.startswith("codex:")]
        # /exit 감지로 Codex가 1회만 실행 (재시작 안 함)
        assert len(codex_lines) == 1

    def test_session_log_saved_to_log_dir(self, tmp_path):
        """CLAUDE_FALLBACK_LOG_DIR 설정 시 세션 로그가 해당 디렉토리에 저장."""
        gen = self._make_generator(["claude"])
        shell_fn = gen.generate_shell_functions()

        log_dir = tmp_path / "agent-log"
        workdir = tmp_path / "my-project"
        workdir.mkdir()

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        fn_file = tmp_path / "claude_fn.sh"

        claude_script = bin_dir / "claude"
        claude_script.write_text('#!/usr/bin/env bash\necho "hello from claude"\nexit 0\n')
        claude_script.chmod(claude_script.stat().st_mode | stat.S_IXUSR)

        fn_file.write_text(shell_fn)

        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
        env["CLAUDE_FALLBACK_LOG_DIR"] = str(log_dir)
        env.pop("CLAUDECODE", None)

        result = subprocess.run(
            ["bash", "-c", f"source {fn_file} && claude --fallback test"],
            env=env,
            text=True,
            capture_output=True,
            check=False,
            cwd=str(workdir),
            timeout=30,
        )

        assert result.returncode == 0
        # 로그 디렉토리가 자동 생성되었는지
        assert log_dir.exists()
        # {dirname}__*_claude.log 파일 존재 확인
        log_files = list(log_dir.glob("my-project__*_claude.log"))
        assert len(log_files) == 1
        # __ 구분자로 session_id 포함 확인
        name = log_files[0].name
        assert name.startswith("my-project__")
        assert name.endswith("_claude.log")

    def test_handoff_preserved_in_log_dir(self, tmp_path):
        """로그 디렉토리 설정 시 핸드오프 파일이 보관됨."""
        gen = self._make_generator(["claude", "codex"])
        shell_fn = gen.generate_shell_functions()

        log_dir = tmp_path / "agent-log"
        workdir = tmp_path / "my-project"
        workdir.mkdir()

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        fn_file = tmp_path / "claude_fn.sh"

        # Claude: rate-limit
        claude_script = bin_dir / "claude"
        claude_script.write_text('#!/usr/bin/env bash\necho "rate limit exceeded"\nexit 1\n')
        claude_script.chmod(claude_script.stat().st_mode | stat.S_IXUSR)

        # Codex: exit 1 (종료)
        codex_script = bin_dir / "codex"
        codex_script.write_text("#!/usr/bin/env bash\nexit 1\n")
        codex_script.chmod(codex_script.stat().st_mode | stat.S_IXUSR)

        fn_file.write_text(shell_fn)

        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
        env["CLAUDE_FALLBACK_LOG_DIR"] = str(log_dir)
        env["CLAUDE_FALLBACK_RETRY_MINUTES"] = "60"
        env.pop("CLAUDECODE", None)

        subprocess.run(
            ["bash", "-c", f"source {fn_file} && claude --fallback test"],
            env=env,
            text=True,
            capture_output=True,
            check=False,
            cwd=str(workdir),
            timeout=30,
        )

        # 핸드오프 파일이 로그 디렉토리에 보관됨
        handoff_files = list(log_dir.glob("my-project__*_handoff.md"))
        assert len(handoff_files) == 1
        content = handoff_files[0].read_text()
        assert "Handoff" in content

    def test_dirname_prefix_in_filenames(self, tmp_path):
        """파일명에 현재 디렉토리명이 prefix로 포함."""
        gen = self._make_generator(["claude"])
        shell_fn = gen.generate_shell_functions()

        log_dir = tmp_path / "agent-log"
        workdir = tmp_path / "test-repo-name"
        workdir.mkdir()

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        fn_file = tmp_path / "claude_fn.sh"

        claude_script = bin_dir / "claude"
        claude_script.write_text('#!/usr/bin/env bash\necho "done"\nexit 0\n')
        claude_script.chmod(claude_script.stat().st_mode | stat.S_IXUSR)

        fn_file.write_text(shell_fn)

        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
        env["CLAUDE_FALLBACK_LOG_DIR"] = str(log_dir)
        env.pop("CLAUDECODE", None)

        subprocess.run(
            ["bash", "-c", f"source {fn_file} && claude --fallback hello"],
            env=env,
            text=True,
            capture_output=True,
            check=False,
            cwd=str(workdir),
            timeout=30,
        )

        # 디렉토리명 "test-repo-name"이 prefix로 사용됨 (내부 메타파일 제외)
        all_files = [f for f in log_dir.glob("*") if not f.name.startswith(".")]
        assert len(all_files) >= 1
        for f in all_files:
            assert f.name.startswith("test-repo-name__")

    def test_generator_passes_fallback_log_dir(self):
        """MCPConfigGenerator가 Settings.fallback_log_dir을 vibe에 전달."""
        gen = self._make_generator(
            ["claude", "codex"],
            fallback_log_dir="~/work/ai-agent-log",
        )
        result = gen.generate_shell_functions()
        assert "~/work/ai-agent-log" in result


class TestPersistentCooldown:
    """cooldown 영속 저장/복원 + 리셋 시각 파싱 테스트"""

    def _make_generator(
        self,
        agent_priority: list[str],
        fallback_log_dir: str | None = None,
    ) -> MCPConfigGenerator:
        """테스트용 generator 생성"""
        secrets = MagicMock()
        secrets.get.return_value = ""
        with (
            patch("ai_env.mcp.generator.load_mcp_config") as mock_mcp,
            patch("ai_env.mcp.generator.load_settings") as mock_settings,
        ):
            mock_mcp.return_value = MagicMock(mcp_servers={})
            settings = Settings(
                agent_priority=agent_priority,
                fallback_log_dir=fallback_log_dir,
            )
            mock_settings.return_value = settings
            return MCPConfigGenerator(secrets)

    def test_contains_persistent_cooldown_functions(self):
        """영속 cooldown 관련 함수 포함 확인."""
        result = generate_shell_functions(["claude", "codex"])
        assert "_save_cooldown_state()" in result
        assert "_load_cooldown_state()" in result
        assert "_parse_reset_epoch()" in result
        assert ".fallback_cooldown" in result

    def test_cooldown_saved_but_not_loaded_across_sessions(self, tmp_path):
        """Rate-limit 후 cooldown이 파일에 저장되지만, 새 세션에서는 로드하지 않음."""
        log_dir = tmp_path / "log"
        gen = self._make_generator(["claude", "codex"], fallback_log_dir=str(log_dir))
        shell_fn = gen.generate_shell_functions()

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        trace_file = tmp_path / "trace.log"
        fn_file = tmp_path / "claude_fn.sh"

        # Claude: 1차에서 rate-limit, 2차에서 정상 종료
        counter_file = tmp_path / "claude.count"
        claude_script = bin_dir / "claude"
        claude_script.write_text(
            "#!/usr/bin/env bash\n"
            'count=$(cat "$COUNTER_FILE" 2>/dev/null || echo 0)\n'
            "count=$((count + 1))\n"
            'echo "$count" > "$COUNTER_FILE"\n'
            'echo "claude:$count" >> "$TRACE_FILE"\n'
            'if [[ "$count" -eq 1 ]]; then\n'
            '  echo "You\'ve hit your limit"\n'
            "  exit 0\n"
            "fi\n"
            "exit 0\n"
        )
        claude_script.chmod(claude_script.stat().st_mode | stat.S_IXUSR)

        # Codex: exit 1 (루프 종료)
        codex_script = bin_dir / "codex"
        codex_script.write_text('#!/usr/bin/env bash\necho "codex" >> "$TRACE_FILE"\nexit 1\n')
        codex_script.chmod(codex_script.stat().st_mode | stat.S_IXUSR)

        fn_file.write_text(shell_fn)

        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
        env["TRACE_FILE"] = str(trace_file)
        env["COUNTER_FILE"] = str(counter_file)
        env["CLAUDE_FALLBACK_RETRY_MINUTES"] = "60"
        env["CLAUDE_FALLBACK_LOG_DIR"] = str(log_dir)
        env.pop("CLAUDECODE", None)

        # 1차 실행: Claude rate-limit → Codex
        subprocess.run(
            ["bash", "-c", f"source {fn_file} && claude --fallback test"],
            env=env,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )

        # cooldown 파일이 생성되었는지 확인
        cooldown_file = log_dir / ".fallback_cooldown"
        assert cooldown_file.exists()
        content = cooldown_file.read_text().strip()
        assert "claude\t" in content

        # 2차 실행: cooldown 파일이 있어도 Claude부터 시도 (이전 cooldown 무시)
        trace_file.write_text("")
        subprocess.run(
            ["bash", "-c", f"source {fn_file} && claude --fallback test"],
            env=env,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )

        lines = trace_file.read_text().splitlines()
        # 2차 실행에서도 Claude부터 시도 (cooldown 파일 무시)
        assert lines[0].startswith("claude:")

    def test_cooldown_cleared_when_expired(self, tmp_path):
        """Cooldown이 만료되면 Claude가 다시 시도되는지 확인."""
        log_dir = tmp_path / "log"
        log_dir.mkdir()
        gen = self._make_generator(["claude", "codex"], fallback_log_dir=str(log_dir))
        shell_fn = gen.generate_shell_functions()

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        trace_file = tmp_path / "trace.log"
        fn_file = tmp_path / "claude_fn.sh"

        # Claude: 정상 종료
        claude_script = bin_dir / "claude"
        claude_script.write_text('#!/usr/bin/env bash\necho "claude" >> "$TRACE_FILE"\nexit 0\n')
        claude_script.chmod(claude_script.stat().st_mode | stat.S_IXUSR)

        fn_file.write_text(shell_fn)

        # cooldown 파일을 수동으로 생성 (과거 시간 = 이미 만료)
        past_epoch = int(time.time()) - 100
        cooldown_file = log_dir / ".fallback_cooldown"
        cooldown_file.write_text(f"claude\t{past_epoch}\n")

        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
        env["TRACE_FILE"] = str(trace_file)
        env["CLAUDE_FALLBACK_LOG_DIR"] = str(log_dir)
        env.pop("CLAUDECODE", None)

        result = subprocess.run(
            ["bash", "-c", f"source {fn_file} && claude --fallback test"],
            env=env,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )

        assert result.returncode == 0
        lines = trace_file.read_text().splitlines()
        # cooldown이 만료되었으므로 Claude가 정상 실행됨
        assert lines == ["claude"]

    def test_cooldown_skip_shows_remaining_time_within_session(self, tmp_path):
        """세션 내 rate-limit 후 같은 세션에서 재시도 시 남은 시간 표시."""
        log_dir = tmp_path / "log"
        gen = self._make_generator(
            ["claude", "claude:sonnet", "codex"], fallback_log_dir=str(log_dir)
        )
        shell_fn = gen.generate_shell_functions()

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        trace_file = tmp_path / "trace.log"
        fn_file = tmp_path / "claude_fn.sh"

        # Claude: 항상 rate-limit
        claude_script = bin_dir / "claude"
        claude_script.write_text(
            "#!/usr/bin/env bash\n"
            'echo "claude:$*" >> "$TRACE_FILE"\n'
            'echo "You\'ve hit your limit"\n'
            "exit 1\n"
        )
        claude_script.chmod(claude_script.stat().st_mode | stat.S_IXUSR)

        # Codex: exit 1 (루프 종료)
        codex_script = bin_dir / "codex"
        codex_script.write_text('#!/usr/bin/env bash\necho "codex" >> "$TRACE_FILE"\nexit 1\n')
        codex_script.chmod(codex_script.stat().st_mode | stat.S_IXUSR)

        fn_file.write_text(shell_fn)

        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
        env["TRACE_FILE"] = str(trace_file)
        env["CLAUDE_FALLBACK_RETRY_MINUTES"] = "60"
        env["CLAUDE_FALLBACK_LOG_DIR"] = str(log_dir)
        env.pop("CLAUDECODE", None)

        result = subprocess.run(
            ["bash", "-c", f"source {fn_file} && claude --fallback test"],
            env=env,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )

        # Claude와 Claude:sonnet 모두 rate-limit, Codex도 실패
        lines = trace_file.read_text().splitlines()
        assert any(line.startswith("claude:") for line in lines)
        assert "codex" in lines
        # rate-limit 메시지가 출력되어야 함
        combined_output = result.stdout + result.stderr
        assert "rate-limit" in combined_output or "재시도" in combined_output

    def test_reset_time_parsed_uses_accurate_cooldown(self, tmp_path):
        """'resets Feb 23 at 9am' 형식의 리셋 시각이 파싱되어 cooldown에 적용되는지 확인."""
        log_dir = tmp_path / "log"
        gen = self._make_generator(["claude", "codex"], fallback_log_dir=str(log_dir))
        shell_fn = gen.generate_shell_functions()

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        trace_file = tmp_path / "trace.log"
        fn_file = tmp_path / "claude_fn.sh"

        # Claude: rate-limit 메시지에 리셋 시각 포함 (항상 미래 날짜 사용)
        import datetime

        future_date = datetime.date.today() + datetime.timedelta(days=2)
        reset_str = future_date.strftime("%b %-d")
        claude_script = bin_dir / "claude"
        claude_script.write_text(
            "#!/usr/bin/env bash\n"
            'echo "claude" >> "$TRACE_FILE"\n'
            f'echo "You\'ve hit your limit · resets {reset_str} at 9am (Asia/Seoul)"\n'
            "exit 0\n"
        )
        claude_script.chmod(claude_script.stat().st_mode | stat.S_IXUSR)

        # Codex: exit 1
        codex_script = bin_dir / "codex"
        codex_script.write_text('#!/usr/bin/env bash\necho "codex" >> "$TRACE_FILE"\nexit 1\n')
        codex_script.chmod(codex_script.stat().st_mode | stat.S_IXUSR)

        fn_file.write_text(shell_fn)

        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
        env["TRACE_FILE"] = str(trace_file)
        env["CLAUDE_FALLBACK_LOG_DIR"] = str(log_dir)
        env["CLAUDE_FALLBACK_RETRY_MINUTES"] = "15"
        env.pop("CLAUDECODE", None)

        result = subprocess.run(
            ["bash", "-c", f"source {fn_file} && claude --fallback test"],
            env=env,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )

        lines = trace_file.read_text().splitlines()
        assert lines[0] == "claude"
        assert "codex" in lines

        # cooldown 파일 확인: 리셋 시각이 파싱되어 15분 기본값과 다른 epoch 저장
        cooldown_file = log_dir / ".fallback_cooldown"
        assert cooldown_file.exists()
        content = cooldown_file.read_text().strip()
        if content:
            epoch_str = content.split("\t")[1]
            cooldown_epoch = int(epoch_str)
            now = int(time.time())
            default_cooldown = now + 900  # 15분 기본값
            # 파싱 성공 시: cooldown이 15분 기본값과 의미있게 다름
            # (Feb 23 9am은 최소 수시간 이후이므로 15분과 차이가 큼)
            assert (
                abs(cooldown_epoch - default_cooldown) > 600
            ), "Cooldown should be set to parsed reset time, not default 15 min"

        # "리셋까지" 메시지 출력 확인
        combined_output = result.stdout + result.stderr
        assert "리셋까지" in combined_output

    def test_model_level_cooldown_persisted_separately(self, tmp_path):
        """claude와 claude:sonnet의 cooldown이 각각 독립적으로 영속 저장되는지 확인."""
        log_dir = tmp_path / "log"
        gen = self._make_generator(
            ["claude", "claude:sonnet", "codex"],
            fallback_log_dir=str(log_dir),
        )
        shell_fn = gen.generate_shell_functions()

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        trace_file = tmp_path / "trace.log"
        fn_file = tmp_path / "claude_fn.sh"

        # Claude: 항상 rate-limit
        claude_script = bin_dir / "claude"
        claude_script.write_text(
            "#!/usr/bin/env bash\n"
            'echo "claude:$*" >> "$TRACE_FILE"\n'
            'echo "rate limit exceeded"\n'
            "exit 1\n"
        )
        claude_script.chmod(claude_script.stat().st_mode | stat.S_IXUSR)

        # Codex: exit 1
        codex_script = bin_dir / "codex"
        codex_script.write_text('#!/usr/bin/env bash\necho "codex" >> "$TRACE_FILE"\nexit 1\n')
        codex_script.chmod(codex_script.stat().st_mode | stat.S_IXUSR)

        fn_file.write_text(shell_fn)

        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
        env["TRACE_FILE"] = str(trace_file)
        env["CLAUDE_FALLBACK_RETRY_MINUTES"] = "60"
        env["CLAUDE_FALLBACK_LOG_DIR"] = str(log_dir)
        env.pop("CLAUDECODE", None)

        subprocess.run(
            ["bash", "-c", f"source {fn_file} && claude --fallback test"],
            env=env,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )

        # cooldown 파일에 claude와 claude:sonnet 모두 저장되어야 함
        cooldown_file = log_dir / ".fallback_cooldown"
        assert cooldown_file.exists()
        content = cooldown_file.read_text()
        assert "claude\t" in content
        assert "claude:sonnet\t" in content

    def test_reverse_handoff_created_on_claude_recovery(self, tmp_path):
        """Codex → Claude 복귀 시 reverse handoff 파일이 생성되어 Claude에 전달되는지 확인."""
        log_dir = tmp_path / "log"
        gen = self._make_generator(
            ["claude", "codex"],
            fallback_log_dir=str(log_dir),
        )
        shell_fn = gen.generate_shell_functions()

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        trace_file = tmp_path / "trace.log"
        counter_file = tmp_path / "claude.count"
        fn_file = tmp_path / "claude_fn.sh"

        # Claude: 1회차 rate-limit, 2회차 인자 기록 후 성공
        claude_script = bin_dir / "claude"
        claude_script.write_text(
            "#!/usr/bin/env bash\n"
            'count=$(cat "$COUNTER_FILE" 2>/dev/null || echo 0)\n'
            "count=$((count + 1))\n"
            'echo "$count" > "$COUNTER_FILE"\n'
            'echo "claude:$count:$*" >> "$TRACE_FILE"\n'
            'if [[ "$count" -eq 1 ]]; then\n'
            '  echo "rate limit exceeded"\n'
            "  exit 1\n"
            "fi\n"
            "exit 0\n"
        )
        claude_script.chmod(claude_script.stat().st_mode | stat.S_IXUSR)

        # Codex: 작업 수행 후 정상 종료
        codex_script = bin_dir / "codex"
        codex_script.write_text(
            "#!/usr/bin/env bash\n"
            'echo "codex:$*" >> "$TRACE_FILE"\n'
            'echo "I fixed the login bug and added tests"\n'
            "exit 0\n"
        )
        codex_script.chmod(codex_script.stat().st_mode | stat.S_IXUSR)

        fn_file.write_text(shell_fn)

        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
        env["TRACE_FILE"] = str(trace_file)
        env["COUNTER_FILE"] = str(counter_file)
        env["CLAUDE_FALLBACK_RETRY_MINUTES"] = "0"
        env["CLAUDE_FALLBACK_LOG_DIR"] = str(log_dir)
        env.pop("CLAUDECODE", None)

        result = subprocess.run(
            ["bash", "-c", f"source {fn_file} && claude --fallback 'fix login'"],
            env=env,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )

        assert result.returncode == 0
        lines = trace_file.read_text().splitlines()
        # claude:1 (rate-limit) → codex (작업) → claude:2 (복귀)
        assert lines[0] == "claude:1:fix login"
        assert lines[1].startswith("codex:")
        assert lines[2].startswith("claude:2:")
        # Claude 2회차에 핸드오프 프롬프트가 주입되어야 함
        assert "이전 에이전트에서 작업 수행됨" in lines[2]
        assert "handoff" in lines[2].lower() or "fix login" in lines[2]

        # reverse handoff 파일이 log_dir에 존재
        handoff_files = list(log_dir.glob("*_handoff.md"))
        assert len(handoff_files) >= 1
        # 최소 1개는 "codex → Claude Code" 방향이어야 함
        reverse_found = False
        for hf in handoff_files:
            content = hf.read_text()
            if "codex" in content.lower() and "Claude Code" in content:
                reverse_found = True
                break
        assert reverse_found, "Reverse handoff (codex → Claude) not found"

    def test_handoff_header_direction(self):
        """핸드오프 파일 헤더가 전환 방향에 따라 다른지 확인."""
        result = generate_shell_functions(["claude", "codex"])
        # Claude → Fallback 방향
        assert "Handoff: Claude Code → Fallback Agent" in result
        # Fallback → Claude 방향
        assert "Handoff: $from_agent → Claude Code" in result


class TestClaudeExitAndCooldownReset:
    """Claude /exit 클린 종료 및 --reset cooldown 초기화 테스트"""

    def _make_generator(
        self, agent_priority: list[str], fallback_log_dir: str | None = None
    ) -> MCPConfigGenerator:
        secrets = MagicMock()
        secrets.get.return_value = ""
        with (
            patch("ai_env.mcp.generator.load_mcp_config") as mock_mcp,
            patch("ai_env.mcp.generator.load_settings") as mock_settings,
        ):
            mock_mcp.return_value = MagicMock(mcp_servers={})
            settings = Settings(
                agent_priority=agent_priority,
                fallback_log_dir=fallback_log_dir,
            )
            mock_settings.return_value = settings
            return MCPConfigGenerator(secrets)

    def test_claude_exit_skips_rate_limit_detection(self, tmp_path):
        """Claude에서 /exit 시 rate-limit 로그가 있어도 클린 종료."""
        gen = self._make_generator(["claude", "codex"])
        shell_fn = gen.generate_shell_functions()

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        trace_file = tmp_path / "trace.log"
        fn_file = tmp_path / "claude_fn.sh"

        # Claude: rate-limit 메시지를 출력하지만 /exit도 출력
        claude_script = bin_dir / "claude"
        claude_script.write_text(
            "#!/usr/bin/env bash\n"
            'echo "claude" >> "$TRACE_FILE"\n'
            'echo "you have hit your limit"\n'
            'echo "> /exit"\n'
            'echo "Bye!"\n'
            "exit 0\n"
        )
        claude_script.chmod(claude_script.stat().st_mode | stat.S_IXUSR)

        # Codex: 호출되면 안 됨
        codex_script = bin_dir / "codex"
        codex_script.write_text(
            "#!/usr/bin/env bash\n" 'echo "codex" >> "$TRACE_FILE"\n' "exit 0\n"
        )
        codex_script.chmod(codex_script.stat().st_mode | stat.S_IXUSR)

        fn_file.write_text(shell_fn)

        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
        env["TRACE_FILE"] = str(trace_file)
        env["CLAUDE_FALLBACK_RETRY_MINUTES"] = "60"
        env.pop("CLAUDECODE", None)

        result = subprocess.run(
            ["bash", "-c", f"source {fn_file} && claude --fallback test"],
            env=env,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )

        assert result.returncode == 0
        lines = trace_file.read_text().splitlines()
        # Claude만 실행, Codex는 호출되지 않아야 함
        assert lines == ["claude"]
        assert "세션 종료" in result.stdout or "세션 종료" in result.stderr

    def test_claude_exit_clears_cooldown(self, tmp_path):
        """Claude /exit 시 해당 엔트리의 cooldown이 0으로 초기화."""
        log_dir = tmp_path / "log"
        gen = self._make_generator(
            ["claude", "codex"],
            fallback_log_dir=str(log_dir),
        )
        shell_fn = gen.generate_shell_functions()

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        trace_file = tmp_path / "trace.log"
        fn_file = tmp_path / "claude_fn.sh"
        log_dir.mkdir(parents=True)

        # Claude: rate-limit 메시지 + /exit 출력 (cooldown 없이 바로 실행됨)
        claude_script = bin_dir / "claude"
        claude_script.write_text(
            "#!/usr/bin/env bash\n"
            'echo "claude" >> "$TRACE_FILE"\n'
            'echo "you have hit your limit"\n'
            'echo "> /exit"\n'
            "exit 0\n"
        )
        claude_script.chmod(claude_script.stat().st_mode | stat.S_IXUSR)

        codex_script = bin_dir / "codex"
        codex_script.write_text(
            "#!/usr/bin/env bash\n" 'echo "codex" >> "$TRACE_FILE"\n' "exit 0\n"
        )
        codex_script.chmod(codex_script.stat().st_mode | stat.S_IXUSR)

        fn_file.write_text(shell_fn)

        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
        env["TRACE_FILE"] = str(trace_file)
        env["CLAUDE_FALLBACK_LOG_DIR"] = str(log_dir)
        env["CLAUDE_FALLBACK_RETRY_MINUTES"] = "60"
        env.pop("CLAUDECODE", None)

        subprocess.run(
            ["bash", "-c", f"source {fn_file} && claude --fallback test"],
            env=env,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )

        # Claude만 실행 (Codex로 fallback 하지 않음)
        lines = trace_file.read_text().splitlines()
        assert lines == ["claude"]

        # cooldown 파일에 claude 항목이 없어야 함 (0으로 설정 → _save_cooldown_state에서 제외)
        cooldown_file = log_dir / ".fallback_cooldown"
        if cooldown_file.exists():
            content = cooldown_file.read_text().strip()
            assert "claude\t" not in content

    def test_new_session_always_tries_claude_first(self, tmp_path):
        """새 세션은 이전 cooldown 파일을 무시하고 항상 Claude부터 시도."""
        log_dir = tmp_path / "log"
        gen = self._make_generator(
            ["claude", "codex"],
            fallback_log_dir=str(log_dir),
        )
        shell_fn = gen.generate_shell_functions()

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        trace_file = tmp_path / "trace.log"
        fn_file = tmp_path / "claude_fn.sh"

        # cooldown 파일 생성 (이전 세션에서 Claude가 1시간 cooldown)
        log_dir.mkdir(parents=True)
        future_epoch = int(time.time()) + 3600
        cooldown_file = log_dir / ".fallback_cooldown"
        cooldown_file.write_text(f"claude\t{future_epoch}\n")

        # Claude: 정상 종료
        claude_script = bin_dir / "claude"
        claude_script.write_text(
            "#!/usr/bin/env bash\n" 'echo "claude" >> "$TRACE_FILE"\n' "exit 0\n"
        )
        claude_script.chmod(claude_script.stat().st_mode | stat.S_IXUSR)

        # Codex
        codex_script = bin_dir / "codex"
        codex_script.write_text(
            "#!/usr/bin/env bash\n" 'echo "codex" >> "$TRACE_FILE"\n' "exit 0\n"
        )
        codex_script.chmod(codex_script.stat().st_mode | stat.S_IXUSR)

        fn_file.write_text(shell_fn)

        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
        env["TRACE_FILE"] = str(trace_file)
        env["CLAUDE_FALLBACK_LOG_DIR"] = str(log_dir)
        env["CLAUDE_FALLBACK_RETRY_MINUTES"] = "60"
        env.pop("CLAUDECODE", None)

        result = subprocess.run(
            ["bash", "-c", f"source {fn_file} && claude --fallback test"],
            env=env,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )

        assert result.returncode == 0
        lines = trace_file.read_text().splitlines()
        # cooldown 파일이 있어도 Claude부터 실행 (Codex로 건너뛰지 않음)
        assert lines[0] == "claude"
