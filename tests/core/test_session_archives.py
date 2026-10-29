"""압축본 검증 전에는 원문을 바꾸지 않는다."""

import gzip
from pathlib import Path

import pytest

# isort: split
from ai_env.core.session_archives import archive_entry, read_entry_text
from ai_env.core.session_journal import JournalEntry, list_entries, save_entry


def test_archive_roundtrip_and_tamper_detection(tmp_path: Path) -> None:
    root = tmp_path / "logs"
    result = save_entry(
        JournalEntry(
            cwd=str(tmp_path),
            agent="codex",
            session_id="s",
            turn_id="t",
            title="압축보관-검증",
            summary="원문 보고\n" * 1000,
        ),
        root,
    )
    path = Path(result["path"])
    original = path.read_text()
    assert archive_entry(path) == "archived"
    assert path.stat().st_size < len(original.encode())
    assert "원문 보고" not in path.read_text()
    assert read_entry_text(path) == original
    assert archive_entry(path) == "unchanged"
    row = list_entries(tmp_path, root)[0]
    archive = path.parent / str(row["archive"])
    assert archive.stat().st_mode & 0o777 == 0o600
    assert gzip.decompress(archive.read_bytes()).decode() == original
    archive.write_bytes(gzip.compress(b"tampered"))
    with pytest.raises(ValueError, match="checksum"):
        read_entry_text(path)


def test_conflicting_archive_retains_original(tmp_path: Path) -> None:
    result = save_entry(
        JournalEntry(cwd=str(tmp_path), agent="claude", summary="원본 보존"), tmp_path / "logs"
    )
    path = Path(result["path"])
    original = path.read_bytes()
    archive = path.parent / "_archive" / (path.name + ".gz")
    archive.parent.mkdir()
    archive.write_bytes(gzip.compress(b"different"))
    with pytest.raises(ValueError, match="does not match"):
        archive_entry(path)
    assert path.read_bytes() == original


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
