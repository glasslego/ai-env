"""LLM Wiki 등록의 원본 보존·검색·동시성 계약 검증."""

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from ai_env.core.wiki_documents import register_document, search_wiki


def make_vault(tmp_path: Path) -> Path:
    """원본과 종합이 분리된 테스트 Vault를 만든다."""
    vault = tmp_path / "vault"
    (vault / "wiki").mkdir(parents=True)
    (vault / "wiki/배치.md").write_text(
        "---\nnote_type: synthesis\nstatus: draft\n---\n# 배치 검증\n성능 정합성 완료 판단\n"
    )
    return vault


def test_search_is_read_only_and_finds_korean_synthesis(tmp_path: Path) -> None:
    vault = make_vault(tmp_path)
    hits = search_wiki(vault, "배치 정합성")
    assert hits[0].path == "wiki/배치.md"
    assert hits[0].status == "draft"
    assert not (vault / "_meta").exists()
    assert search_wiki(vault, "없는단어") == []
    with pytest.raises(ValueError, match="query"):
        search_wiki(vault, "   ")


def test_register_external_snapshot_is_idempotent_and_preserves_history(tmp_path: Path) -> None:
    vault = make_vault(tmp_path)
    doc = tmp_path / "설계.md"
    doc.write_text("# 배치 설계\n성능 정합성\n")
    original = doc.read_bytes()
    first = register_document(vault, doc)
    assert first.status == "registered"
    assert first.related_pages[0].path == "wiki/배치.md"
    snapshot = vault / first.snapshot
    assert snapshot.read_bytes() == original == doc.read_bytes()
    registry = vault / "_meta/llm-wiki-registry.json"
    registered_bytes = registry.read_bytes()
    assert register_document(vault, doc).status == "unchanged"
    assert registry.read_bytes() == registered_bytes
    doc.write_text("# 배치 설계\n성능 정합성 개선\n")
    second = register_document(vault, doc)
    assert second.status == "registered"
    assert second.snapshot != first.snapshot
    assert snapshot.read_bytes() == original
    assert any(h.kind == "source" for h in search_wiki(vault, "정합성 개선"))


def test_register_internal_source_and_dry_run_do_not_copy_or_mutate(tmp_path: Path) -> None:
    vault = make_vault(tmp_path)
    doc = vault / "원본.md"
    doc.write_text("# 배치\n정합성\n")
    before = doc.read_bytes()
    preview = register_document(vault, doc, dry_run=True)
    assert preview.status == "would_register"
    assert not (vault / "_meta").exists()
    result = register_document(vault, doc)
    assert result.snapshot == "원본.md"
    assert doc.read_bytes() == before
    assert not (vault / "00_inbox").exists()
    assert register_document(vault, vault / "wiki/배치.md").status == "skipped"


def test_private_documents_require_opt_in_and_are_not_searchable(tmp_path: Path) -> None:
    vault = make_vault(tmp_path)
    (vault / "40_개인").mkdir()
    doc = vault / "40_개인/메모.md"
    doc.write_text("# 개인비공개\n개인비공개\n")
    with pytest.raises(ValueError, match="allow-private"):
        register_document(vault, doc)
    register_document(vault, doc, allow_private=True)
    assert search_wiki(vault, "개인비공개") == []
    assert not any(h.kind == "source" for h in search_wiki(vault, "배치"))


def test_corrupt_registry_and_escaping_symlinks_fail_without_overwrite(tmp_path: Path) -> None:
    vault = make_vault(tmp_path)
    doc = tmp_path / "doc.md"
    doc.write_text("# 배치\n")
    meta = vault / "_meta"
    meta.mkdir()
    registry = meta / "llm-wiki-registry.json"
    registry.write_text("broken")
    with pytest.raises(ValueError, match="Invalid JSON"):
        register_document(vault, doc)
    assert registry.read_text() == "broken"
    registry.unlink()
    (vault / "00_inbox").symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError, match="outside"):
        register_document(vault, doc)
    assert not (tmp_path / "llm-wiki").exists()


def test_concurrent_registration_keeps_both_sources(tmp_path: Path) -> None:
    vault = make_vault(tmp_path)
    docs = [tmp_path / f"{i}.md" for i in range(2)]
    for i, doc in enumerate(docs):
        doc.write_text(f"# 문서 {i}\n내용 {i}\n")
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda p: register_document(vault, p), docs))
    assert all(r.status == "registered" for r in results)
    registry = json.loads((vault / "_meta/llm-wiki-registry.json").read_text())
    assert len(registry["documents"]) == 2


def test_registry_paths_and_wiki_symlinks_cannot_escape_vault(tmp_path: Path) -> None:
    vault = make_vault(tmp_path)
    outside = tmp_path / "outside.md"
    outside.write_text("---\nnote_type: synthesis\n---\n# 외부비공개\n")
    (vault / "wiki/escape.md").symlink_to(outside)
    assert search_wiki(vault, "외부비공개") == []
    register_document(vault, outside)
    registry = vault / "_meta/llm-wiki-registry.json"
    data = json.loads(registry.read_text())
    next(iter(data["documents"].values()))["snapshot"] = "../outside.md"
    registry.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="outside"):
        search_wiki(vault, "외부비공개")


def test_search_marks_modified_internal_source_and_rejects_changed_snapshot(tmp_path: Path) -> None:
    vault = make_vault(tmp_path)
    internal = vault / "원본.md"
    internal.write_text("# 원본\n정합성\n")
    register_document(vault, internal)
    internal.write_text("# 원본\n정합성 수정\n")
    assert (
        next(h for h in search_wiki(vault, "수정") if h.kind == "source").status == "source_changed"
    )
    external = tmp_path / "external.md"
    external.write_text("# 외부자료\n근거\n")
    result = register_document(vault, external)
    (vault / result.snapshot).write_text("# 외부자료\n손상\n")
    with pytest.raises(ValueError, match="Snapshot content changed"):
        search_wiki(vault, "외부자료")


def test_markdown_without_searchable_title_can_be_registered(tmp_path: Path) -> None:
    vault = make_vault(tmp_path)
    doc = tmp_path / "기록.md"
    doc.write_text("# !!!\n정합성 검증\n")
    assert register_document(vault, doc).status == "registered"


def test_session_journal_record_is_snapshotted_before_archive(tmp_path: Path) -> None:
    vault = make_vault(tmp_path)
    record = vault / "00_session/agent-logs/ai-env-0123/codex__work__보고.md"
    record.parent.mkdir(parents=True)
    record.write_text("# 배치 보고\n성능 정합성 검증 완료\n")
    result = register_document(vault, record)
    # 7일 뒤 gzip 보관이 본문을 안내로 바꿔도 등록한 근거는 그대로 검색된다.
    assert result.snapshot.startswith("00_inbox/llm-wiki/")
    record.write_text("# 배치 보고\n원문은 gzip으로 보관했습니다.\n")
    hits = [hit for hit in search_wiki(vault, "정합성 검증") if hit.kind == "source"]
    assert [(hit.path, hit.status) for hit in hits] == [(result.snapshot, "registered")]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
