"""공용 wrapper와 도구별 배포 설정을 실제 입력으로 검증."""

import json
import os
import subprocess
from pathlib import Path

import pytest

# isort: split
from ai_env.core.session_journal import list_entries
from ai_env.core.sync import JOURNAL_HOOK_TIMEOUT_SECONDS, _codex_hooks_json


def test_hook_wrapper_uses_event_cwd_not_shell_cwd(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[2]
    project = tmp_path / "경로 공백"
    project.mkdir()
    env = {
        **os.environ,
        "AI_ENV_DIR": str(repo),
        "AI_ENV_SESSION_LOG_DIR": str(tmp_path / "logs"),
        "AI_ENV_SESSION_STATE_DIR": str(tmp_path / "state"),
    }
    script = repo / ".claude" / "hooks" / "session_journal.sh"
    for event in (
        {"hook_event_name": "UserPromptSubmit", "prompt": '이름에 따옴표 "와 줄바꿈\n'},
        {"hook_event_name": "Stop", "last_assistant_message": "검증: pytest 통과"},
    ):
        result = subprocess.run(
            ["bash", str(script), "claude"],
            cwd=repo,
            env=env,
            input=json.dumps({"cwd": str(project), "session_id": "s", **event}),
            text=True,
            capture_output=True,
            check=True,
        )
        assert json.loads(result.stdout) == {}
    rows = list_entries(project, tmp_path / "logs")
    assert len(rows) == 1
    assert rows[0]["agent"] == "claude"
    assert rows[0]["cwd"] == str(project)


def test_recorder_in_both_profiles_and_codex_without_cmux() -> None:
    repo = Path(__file__).resolve().parents[2]
    for profile in ("settings.json.template", "settings.personal.json.template"):
        config = json.loads((repo / ".claude" / "global" / profile).read_text())
        for event in ("SessionStart", "UserPromptSubmit", "Stop", "SessionEnd"):
            assert [
                hook["timeout"]
                for group in config["hooks"][event]
                for hook in group["hooks"]
                if "session_journal.sh" in hook["command"] and "claude" in hook["command"]
            ] == [JOURNAL_HOOK_TIMEOUT_SECONDS]
    config = json.loads(_codex_hooks_json(Path("/tmp/with space"), cmux_enabled=False))
    for event in ("SessionStart", "UserPromptSubmit", "Stop", "SessionEnd"):
        journal = [
            hook
            for group in config["hooks"][event]
            for hook in group["hooks"]
            if "session_journal.sh" in hook["command"] and "codex" in hook["command"]
        ]
        # SessionEnd 정리가 Codex에서만 먼저 끊기지 않도록 Claude와 같은 제한을 쓴다.
        assert [hook["timeout"] for hook in journal] == [JOURNAL_HOOK_TIMEOUT_SECONDS]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
