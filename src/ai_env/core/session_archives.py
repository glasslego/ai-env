"""본문을 gzip 보관하고 기존 Markdown 링크는 짧은 안내로 유지한다."""

from __future__ import annotations

import gzip
import hashlib
from pathlib import Path
from urllib.parse import quote

from .session_storage import journal_lock, read_metadata, render_record
from .wiki_documents import _atomic_write


def read_entry_text(path: Path) -> str:
    """압축 보관된 기록도 해시를 검증한 후 원문으로 읽는다.

    Args:
        path: 원래 Markdown 기록 경로.

    Returns:
        보관 전의 원문 Markdown.

    Raises:
        ValueError: 보관 경로가 이탈하거나 해시가 일치하지 않을 때.
    """
    if path.is_symlink():
        raise ValueError("Journal record must not be a symlink")
    metadata = read_metadata(path)
    if not metadata.get("archived"):
        return path.read_text(encoding="utf-8")
    archive = path.parent / str(metadata["archive"])
    if archive.is_symlink() or not archive.resolve().is_relative_to(path.parent):
        raise ValueError("Archive path outside journal")
    data = gzip.decompress(archive.read_bytes())
    if hashlib.sha256(data).hexdigest() != metadata["archive_sha256"]:
        raise ValueError("Archive checksum mismatch")
    return data.decode("utf-8")


def archive_entry(path: Path) -> str:
    """디스크의 gzip 복원을 검증한 후 원문 본문을 안내로 교체한다.

    Args:
        path: 보관할 원문 기록.

    Returns:
        archived/unchanged 상태.

    Raises:
        ValueError: 경로 이탈·기존 압축본 불일치.
    """
    with journal_lock(path.parent):
        metadata = read_metadata(path)
        if metadata.get("archived"):
            read_entry_text(path)
            return "unchanged"
        original = read_entry_text(path).encode()
        directory = path.parent / "_archive"
        if directory.is_symlink():
            raise ValueError("Archive directory must not be a symlink")
        directory.mkdir(mode=0o700, exist_ok=True)
        archive = directory / (path.name + ".gz")
        if archive.is_symlink():
            raise ValueError("Archive must not be a symlink")
        packed = gzip.compress(original, mtime=0)
        if archive.exists() and gzip.decompress(archive.read_bytes()) != original:
            raise ValueError("Existing archive does not match original")
        if not archive.exists():
            _atomic_write(archive, packed)
        if gzip.decompress(archive.read_bytes()) != original:
            raise ValueError("Archive verification failed; original retained")
        metadata.pop("path", None)
        # report_status 도입 전 기록은 status에 진행 상태가 있다.
        metadata.setdefault("report_status", metadata.get("status"))
        metadata.update(
            status="archived",
            archived=True,
            archive=str(archive.relative_to(path.parent)),
            archive_sha256=hashlib.sha256(original).hexdigest(),
        )
        body = f"# {metadata['title']}\n\n원문은 검증한 gzip 파일로 보관했습니다. 이 노트는 기존 링크를 유지하는 안내입니다.\n\n"
        body += f"- 작업: {metadata.get('task', '')}\n- 상태: {metadata['report_status']}\n"
        body += f"- [원문 압축파일]({quote(str(archive.relative_to(path.parent)))})\n"
        body += f'- 원문 확인: `ai-env session show "{path}"`\n'
        _atomic_write(path, render_record(metadata, body).encode())
    return "archived"
