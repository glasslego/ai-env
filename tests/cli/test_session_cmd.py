"""ai-env session CLI 단위 테스트."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from ai_env.cli import main
from click.testing import CliRunner


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture()
def fresh_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@e.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=repo, check=True)
    (repo / "x.txt").write_text("x", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=repo, check=True)
    return repo


def test_session_save_dry_run(runner: CliRunner, tmp_path: Path, fresh_repo: Path) -> None:
    vault = tmp_path / "vault"
    result = runner.invoke(
        main,
        [
            "session",
            "save",
            "--note",
            "iteration test",
            "--vault",
            str(vault),
            "--cwd",
            str(fresh_repo),
            "--dry-run",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "dry-run" in result.output
    assert "iteration test" in result.output
    # dry-run이므로 파일은 생성되지 않아야 함
    assert not (vault / "00_session").exists()


def test_session_save_writes_file(runner: CliRunner, tmp_path: Path, fresh_repo: Path) -> None:
    vault = tmp_path / "vault"
    result = runner.invoke(
        main,
        [
            "session",
            "save",
            "--note",
            "real save",
            "--title",
            "my-test",
            "--vault",
            str(vault),
            "--cwd",
            str(fresh_repo),
        ],
    )
    assert result.exit_code == 0, result.output
    target_dir = vault / "00_session"
    files = list(target_dir.glob("*.md"))
    assert len(files) == 1
    body = files[0].read_text(encoding="utf-8")
    assert "real save" in body
    assert "title: my-test" in body


def test_session_save_accepts_transcript_metadata(
    runner: CliRunner,
    tmp_path: Path,
    fresh_repo: Path,
) -> None:
    vault = tmp_path / "vault"
    transcript = tmp_path / "session.jsonl"
    transcript.write_text(
        json.dumps(
            {"role": "user", "content": "tests/cli/test_session_cmd.py 확인"}, ensure_ascii=False
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        main,
        [
            "session",
            "save",
            "--note",
            "metadata save",
            "--vault",
            str(vault),
            "--cwd",
            str(fresh_repo),
            "--session-id",
            "abcdef123456",
            "--agent",
            "codex",
            "--transcript-path",
            str(transcript),
        ],
    )

    assert result.exit_code == 0, result.output
    files = list((vault / "00_session").glob("*.md"))
    assert len(files) == 1
    assert files[0].name.startswith("202")
    assert "repo-session-abcdef12" in files[0].name
    body = files[0].read_text(encoding="utf-8")
    assert "session_id: abcdef123456" in body
    assert "agent: codex" in body
    assert "Compressed Conversation" in body
    assert "tests/cli/test_session_cmd.py" in body


def test_session_save_custom_subdir(runner: CliRunner, tmp_path: Path, fresh_repo: Path) -> None:
    vault = tmp_path / "vault"
    result = runner.invoke(
        main,
        [
            "session",
            "save",
            "--note",
            "custom",
            "--vault",
            str(vault),
            "--subdir",
            "01_Inbox",
            "--cwd",
            str(fresh_repo),
        ],
    )
    assert result.exit_code == 0, result.output
    assert (vault / "01_Inbox").exists()
    files = list((vault / "01_Inbox").glob("*.md"))
    assert len(files) == 1


def test_session_latest_outputs_project_context(
    runner: CliRunner,
    tmp_path: Path,
    fresh_repo: Path,
) -> None:
    vault = tmp_path / "vault"
    save_result = runner.invoke(
        main,
        [
            "session",
            "save",
            "--note",
            "latest cli context",
            "--vault",
            str(vault),
            "--cwd",
            str(fresh_repo),
            "--session-id",
            "latest123",
        ],
    )
    assert save_result.exit_code == 0, save_result.output

    latest = runner.invoke(
        main,
        [
            "session",
            "latest",
            "--vault",
            str(vault),
            "--cwd",
            str(fresh_repo),
        ],
    )

    assert latest.exit_code == 0, latest.output
    assert "# Latest Session Context: repo" in latest.output
    assert "latest cli context" in latest.output


def test_session_latest_path_only_when_missing(runner: CliRunner, tmp_path: Path) -> None:
    result = runner.invoke(
        main,
        [
            "session",
            "latest",
            "--vault",
            str(tmp_path / "vault"),
            "--path-only",
        ],
    )
    assert result.exit_code == 0, result.output
    assert result.output == ""


def test_session_help(runner: CliRunner) -> None:
    result = runner.invoke(main, ["session", "--help"])
    assert result.exit_code == 0
    assert "save" in result.output
    assert "latest" in result.output
