"""Markdown 출처의 불변 등록과 LLM Wiki 로컬 검색.

종합 문장을 생성하지 않는다. 에이전트가 읽을 출처·관련 페이지를 제공한다.
"""

from __future__ import annotations

import fcntl
import hashlib
import os
import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

from .config import expand_path

MAX_DOCUMENT_BYTES = 2 * 1024 * 1024
PRIVATE_DIRECTORIES = {"40_개인", "41_투자_재테크"}
SNAPSHOT_DIRECTORY = Path("00_inbox/llm-wiki")
REGISTRY_PATH = Path("_meta/llm-wiki-registry.json")


class DocumentRecord(BaseModel):
    """원본의 최신 등록과 Vault 내부 근거 위치."""

    origin: str
    snapshot: str
    title: str
    sha256: str
    private: bool = False
    registered_at: str


class DocumentRegistry(BaseModel):
    """버전이 명시된 문서 등록 저장소."""

    version: Literal[1] = 1
    documents: dict[str, DocumentRecord] = Field(default_factory=dict)


class SearchHit(BaseModel):
    """근거를 다시 읽을 수 있는 검색 결과."""

    path: str
    title: str
    kind: Literal["synthesis", "source"]
    status: str
    score: int
    excerpt: str


class RegistrationResult(BaseModel):
    """등록 여부와 후속 종합 후보."""

    status: Literal["registered", "unchanged", "would_register", "skipped"]
    origin: str
    snapshot: str = ""
    sha256: str = ""
    related_pages: list[SearchHit] = Field(default_factory=list)


def resolve_vault(value: str | None = None) -> Path:
    """옵션·환경변수·기본값 순서로 기존 Vault를 찾는다.

    Raises:
        ValueError: 지정한 Vault가 존재하지 않을 때.
    """
    vault = expand_path(value or os.getenv("OBSIDIAN_BASE") or "~/Documents/Obsidian Vault")
    if not vault.is_dir():
        raise ValueError(f"Vault directory not found: {vault}")
    return vault.resolve()


def _contained(vault: Path, relative: Path) -> Path:
    path = vault / relative
    if not path.resolve().is_relative_to(vault):
        raise ValueError(f"Path outside Vault: {relative}")
    return path


def _registry(vault: Path) -> DocumentRegistry:
    path = _contained(vault, REGISTRY_PATH)
    if not path.exists():
        return DocumentRegistry()
    return DocumentRegistry.model_validate_json(path.read_bytes())


def _read_document(path: Path) -> tuple[bytes, str, str, str]:
    if not path.is_file() or path.suffix.lower() != ".md":
        raise ValueError(f"Markdown file required: {path}")
    if path.stat().st_size > MAX_DOCUMENT_BYTES:
        raise ValueError(f"Markdown exceeds {MAX_DOCUMENT_BYTES} bytes: {path}")
    data = path.read_bytes()
    text = data.decode("utf-8")
    body = re.sub(r"\A---\r?\n.*?\r?\n---(?:\r?\n|$)", "", text, count=1, flags=re.S)
    heading = re.search(r"^#\s+(.+)$", body, re.M)
    return data, text, heading.group(1).strip() if heading else path.stem, body


def _match(
    path: str, title: str, body: str, query: str, kind: Literal["synthesis", "source"], status: str
) -> SearchHit | None:
    terms = set(re.findall(r"[\w가-힣]+", query.casefold()))
    score = sum(3 * (term in title.casefold()) + (term in body.casefold()) for term in terms)
    if not score:
        return None
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    excerpt = next((line for line in lines if any(term in line.casefold() for term in terms)), "")
    return SearchHit(
        path=path, title=title, kind=kind, status=status, score=score, excerpt=excerpt[:240]
    )


def search_wiki(vault: Path, query: str, limit: int = 5) -> list[SearchHit]:
    """종합 페이지와 등록 출처를 키워드 검색한다. 파일을 수정하지 않는다.

    Args:
        vault: 기존 Vault 경로.
        query: 한글·영문 키워드. 부분 일치 결과도 반환한다.
        limit: 반환할 최대 결과 수.

    Raises:
        ValueError: 빈 질의·잘못된 제한·손상된 등록 정보가 있을 때.
    """
    vault = resolve_vault(str(vault))
    if not re.search(r"\w", query) or limit < 1:
        raise ValueError("Non-empty query and positive limit required")
    hits: list[SearchHit] = []
    wiki = _contained(vault, Path("wiki"))
    for path in sorted(wiki.rglob("*.md")):
        if path.is_symlink() or not path.resolve().is_relative_to(vault):
            continue
        _, text, title, body = _read_document(path)
        match = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)", text, re.S)
        meta = yaml.safe_load(match.group(1)) if match else {}
        if not isinstance(meta, dict) or meta.get("note_type") != "synthesis":
            continue
        hit = _match(
            str(path.relative_to(vault)),
            title,
            body,
            query,
            "synthesis",
            str(meta.get("status", "unknown")),
        )
        if hit:
            hits.append(hit)
    for record in _registry(vault).documents.values():
        path = _contained(vault, Path(record.snapshot))
        if record.private or not path.is_file():
            continue
        data, _, title, body = _read_document(path)
        changed = hashlib.sha256(data).hexdigest() != record.sha256
        if changed and Path(record.origin) != path:
            raise ValueError(f"Snapshot content changed: {record.snapshot}")
        hit = _match(
            record.snapshot,
            title,
            body,
            query,
            "source",
            "source_changed" if changed else "registered",
        )
        if hit:
            hits.append(hit)
    return sorted(hits, key=lambda h: (-h.score, h.kind != "synthesis", h.path))[:limit]


def _atomic_write(path: Path, data: bytes) -> None:
    """같은 디렉터리의 임시 파일에서 완전한 내용만 원자적으로 공개한다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def register_document(
    vault: Path, source: Path, *, dry_run: bool = False, allow_private: bool = False
) -> RegistrationResult:
    """명시한 문서의 출처를 등록하고 관련 종합 후보를 반환한다.

    Args:
        vault: 기준 원본을 보관하는 Vault.
        source: 로컬 UTF-8 Markdown. 외부 문서는 내용별 스냅샷 보관.
        dry_run: 파일을 생성·수정하지 않고 결과만 예고.
        allow_private: 명시한 개인·투자 원본만 등록 허용. 기본 검색에서는 제외.

    Raises:
        ValueError: 문서·등록 정보·저장 경로가 유효하지 않을 때.
    """
    vault = resolve_vault(str(vault))
    source = expand_path(str(source)).resolve()
    private = bool(PRIVATE_DIRECTORIES.intersection(source.parts))
    if private and not allow_private:
        raise ValueError("Private document requires --allow-private")
    if source.is_relative_to(vault):
        relative = source.relative_to(vault)
        if relative.parts[0] in {"wiki", "_meta"} or source.is_relative_to(
            vault / SNAPSHOT_DIRECTORY
        ):
            return RegistrationResult(status="skipped", origin=str(source))
    data, _, title, _ = _read_document(source)
    digest = hashlib.sha256(data).hexdigest()
    snapshot = (
        source.relative_to(vault)
        if source.is_relative_to(vault)
        else SNAPSHOT_DIRECTORY / f"{digest}.md"
    )
    destination = _contained(vault, snapshot)
    record = DocumentRecord(
        origin=str(source),
        snapshot=str(snapshot),
        title=title,
        sha256=digest,
        private=private,
        registered_at=datetime.now(UTC).isoformat(),
    )
    # 스냅샷 저장 전에 검색하여 등록 문서 자신이 종합 후보가 되지 않게 한다.
    related = (
        [hit for hit in search_wiki(vault, title, limit=100) if hit.kind == "synthesis"][:3]
        if re.search(r"\w", title)
        else []
    )
    result = RegistrationResult(
        status="would_register",
        origin=str(source),
        snapshot=str(snapshot),
        sha256=digest,
        related_pages=related,
    )
    registry_path = _contained(vault, REGISTRY_PATH)

    def update(*, write: bool) -> None:
        registry = _registry(vault)
        previous = registry.documents.get(str(source))
        if (
            previous
            and previous.sha256 == digest
            and previous.private == private
            and destination.is_file()
        ):
            if hashlib.sha256(destination.read_bytes()).hexdigest() != digest:
                raise ValueError(f"Snapshot content changed: {snapshot}")
            result.status = "unchanged"
            return
        if destination.exists() and destination != source and destination.read_bytes() != data:
            raise ValueError(f"Snapshot content changed: {snapshot}")
        if write:
            if destination != source and not destination.exists():
                _atomic_write(destination, data)
            registry.documents[str(source)] = record
            _atomic_write(registry_path, (registry.model_dump_json(indent=2) + "\n").encode())
            result.status = "registered"

    if dry_run:
        update(write=False)
    else:
        lock_path = _contained(vault, Path("_meta/llm-wiki-registry.lock"))
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with lock_path.open("a") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            update(write=True)
    return result
