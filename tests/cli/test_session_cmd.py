"""실제 hook과 CLI를 같은 로컬 저장소에서 연결한다."""

import json
import os
from pathlib import Path

import pytest
from click.testing import CliRunner

# isort: split
from ai_env.cli import main


def invoke_hook(
    runner: CliRunner, project: Path, agent: str, payload: dict[str, object]
) -> dict[str, object]:
    result = runner.invoke(
        main,
        ["session", "--project", str(project), "hook", "--agent", agent],
        input=json.dumps({"cwd": str(project), "session_id": "s", **payload}),
    )
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


def test_hook_prompt_stop_restart_and_no_success_inference(tmp_path: Path) -> None:
    agent = "claude"
    runner = CliRunner(
        env={
            "AI_ENV_SESSION_LOG_DIR": str(tmp_path / "logs"),
            "AI_ENV_SESSION_STATE_DIR": str(tmp_path / "state"),
        }
    )
    invoke_hook(
        runner, tmp_path, agent, {"hook_event_name": "UserPromptSubmit", "prompt": "첫 작업"}
    )
    payload = {"hook_event_name": "Stop", "last_assistant_message": "검증 실패, 수정 필요"}
    assert invoke_hook(runner, tmp_path, agent, payload) == {}
    assert invoke_hook(runner, tmp_path, agent, payload) == {}
    invoke_hook(
        runner, tmp_path, agent, {"hook_event_name": "UserPromptSubmit", "prompt": "두 번째 작업"}
    )
    invoke_hook(runner, tmp_path, agent, payload)
    # 도구가 주입한 백그라운드 알림은 사용자 지시가 아니므로 기록하지 않는다.
    invoke_hook(
        runner,
        tmp_path,
        agent,
        {"hook_event_name": "UserPromptSubmit", "prompt": "<task-notification>\n<status>done"},
    )
    invoke_hook(runner, tmp_path, agent, {**payload, "last_assistant_message": "알림 처리"})
    result = runner.invoke(main, ["session", "--project", str(tmp_path), "list"])
    rows = json.loads(result.output)["records"]
    # 같은 세션의 응답은 하루 하나의 checkpoint 노트에 이어 붙인다.
    assert [(row["kind"], row["report_status"]) for row in rows] == [("checkpoint", "stopped")]
    text = Path(str(rows[0]["path"])).read_text()
    assert text.count("검증 실패, 수정 필요") == 2
    assert "첫 작업" in text
    assert "두 번째 작업" in text
    assert "알림 처리" not in text
    start = invoke_hook(runner, tmp_path, agent, {"hook_event_name": "SessionStart"})
    assert "additionalContext" in start["hookSpecificOutput"]
    stale = tmp_path / "state" / "ended-elsewhere.json"
    stale.write_text("{}")
    os.utime(stale, (0, 0))
    assert invoke_hook(runner, tmp_path, agent, {"hook_event_name": "SessionEnd"}) == {}
    # 종료한 세션과 오래 방치된 요청 상태는 남기지 않는다.
    assert list((tmp_path / "state").iterdir()) == []
    result = runner.invoke(
        main, ["session", "--project", str(tmp_path), "list", "--kind", "summary"]
    )
    # checkpoint 노트가 이미 세션 흐름이므로 같은 내용의 세션 요약을 또 만들지 않는다.
    assert json.loads(result.output)["records"] == []


def test_missing_hook_fields_report_without_success_record(tmp_path: Path) -> None:
    runner = CliRunner(
        env={
            "AI_ENV_SESSION_LOG_DIR": str(tmp_path / "logs"),
            "AI_ENV_SESSION_STATE_DIR": str(tmp_path / "state"),
        }
    )
    # 완료 답변이 없으면 성공 기록을 만들지 않는다. 사용자에게 누락 사실만 알린다.
    result = invoke_hook(runner, tmp_path, "codex", {"hook_event_name": "Stop"})
    assert "systemMessage" in result
    result = runner.invoke(main, ["session", "hook", "--agent", "codex"], input="not JSON")
    assert result.exit_code == 0
    assert "systemMessage" in json.loads(result.output)


def test_compact_and_show_archived_original_without_cross_project_read(tmp_path: Path) -> None:
    runner = CliRunner(env={"AI_ENV_SESSION_LOG_DIR": str(tmp_path / "logs")})
    body = tmp_path / "report.md"
    body.write_text("## 검증\n검증 내역\n## TODO\n코드 리뷰\n")
    result = runner.invoke(
        main,
        [
            "session",
            "--project",
            str(tmp_path),
            "record",
            "--agent",
            "codex",
            "--session-id",
            "s",
            "--body-file",
            str(body),
        ],
    )
    path = json.loads(result.output)["path"]
    result = runner.invoke(
        main, ["session", "--project", str(tmp_path), "compact", "--session-id", "s", "--archive"]
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["summaries"]
    result = runner.invoke(main, ["session", "--project", str(tmp_path), "show", path])
    assert result.exit_code == 0, result.output
    assert "검증 내역" in result.output
    assert "코드 리뷰" in result.output
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    result = runner.invoke(main, ["session", "--project", str(foreign), "show", path])
    assert result.exit_code != 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
