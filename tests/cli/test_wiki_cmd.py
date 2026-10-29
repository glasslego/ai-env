"""문서 작업에서 사용하는 JSON CLI 계약 검증."""

import json
from pathlib import Path

import pytest
from ai_env.cli import main
from click.testing import CliRunner


def test_register_and_search_use_configured_vault(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    (vault / "wiki").mkdir(parents=True)
    doc = tmp_path / "doc.md"
    doc.write_text("# 지식 종합\n등록 검색 자동화\n")
    runner = CliRunner(env={"OBSIDIAN_BASE": str(vault)})
    result = runner.invoke(main, ["wiki", "register", str(doc)])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["status"] == "registered"
    result = runner.invoke(main, ["wiki", "search", "검색 자동화"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["results"][0]["title"] == "지식 종합"


def test_explicit_vault_dry_run_and_invalid_inputs(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    (vault / "wiki").mkdir(parents=True)
    doc = tmp_path / "doc.md"
    doc.write_text("# 지식\n")
    runner = CliRunner(env={"OBSIDIAN_BASE": str(tmp_path / "missing")})
    result = runner.invoke(main, ["wiki", "--vault", str(vault), "register", str(doc), "--dry-run"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["status"] == "would_register"
    assert not (vault / "_meta").exists()
    assert runner.invoke(main, ["wiki", "search", "지식"]).exit_code != 0
    assert (
        runner.invoke(
            main, ["wiki", "--vault", str(vault), "search", "지식", "--limit", "0"]
        ).exit_code
        != 0
    )
    not_md = tmp_path / "doc.txt"
    not_md.write_text("not markdown")
    assert (
        runner.invoke(main, ["wiki", "--vault", str(vault), "register", str(not_md)]).exit_code != 0
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
