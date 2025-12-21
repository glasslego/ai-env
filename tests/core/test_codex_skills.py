"""Tests for Codex skill normalization."""

from __future__ import annotations

from pathlib import Path

from ai_env.core.codex_skills import copy_skill_tree_for_codex, normalize_skill_markdown_for_codex


def test_normalize_skill_markdown_for_codex_repairs_invalid_frontmatter() -> None:
    """느슨한 description 포맷을 Codex 호환 YAML로 정규화한다."""
    raw_content = """---
name: spark-debug
description: Spark application 디버깅 및 로그 모니터링 도구입니다.
  - Kerberos 인증 (kinit) 자동화
  - YARN application 상태 조회
---

# Spark Debug
"""

    normalized = normalize_skill_markdown_for_codex(raw_content, "spark-debug")

    assert "description:" in normalized
    assert "Kerberos 인증" in normalized
    assert normalized.startswith("---\nname: spark-debug\n")


def test_normalize_skill_markdown_for_codex_adds_missing_frontmatter() -> None:
    """frontmatter가 없으면 body에서 설명을 추출해 생성한다."""
    raw_content = """# /service-onboard

신규 랭킹 서비스를 step-by-step으로 온보딩하는 오케스트레이션 스킬.

## 시작하기 전에
"""

    normalized = normalize_skill_markdown_for_codex(raw_content, "service-onboard")

    assert normalized.startswith("---\nname: service-onboard\n")
    assert "신규 랭킹 서비스를 step-by-step으로 온보딩하는 오케스트레이션 스킬." in normalized
    assert "# /service-onboard" in normalized


def test_copy_skill_tree_for_codex_rewrites_skill_md(tmp_path: Path) -> None:
    """skill 트리 복사 시 모든 SKILL.md를 정규화한다."""
    source = tmp_path / "source-skill"
    target = tmp_path / "target-skill"
    source.mkdir()
    (source / "scripts").mkdir()
    (source / "scripts" / "helper.py").write_text("print('ok')\n")
    (source / "SKILL.md").write_text(
        """---
name: feature-crud
description: 랭킹 피처 추가/수정 가이드.
  - 새 시그널 추가
---

# Feature CRUD
"""
    )

    copy_skill_tree_for_codex(source, target)

    normalized = (target / "SKILL.md").read_text()
    assert "description:" in normalized
    assert "새 시그널 추가" in normalized
    assert (target / "scripts" / "helper.py").exists()
