"""ai-env session CLI 단위 테스트."""

from __future__ import annotations

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


def test_session_help(runner: CliRunner) -> None:
    result = runner.invoke(main, ["session", "--help"])
    assert result.exit_code == 0
    assert "save" in result.output
