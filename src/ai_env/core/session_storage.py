"""공용 작업 기록의 저장 경로·Markdown 머리말·잠금. 기록 내용과 무관한 저장 계층."""

from __future__ import annotations

import fcntl
import hashlib
import os
import re
import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Literal, cast
from zoneinfo import ZoneInfo

import yaml

from .config import expand_path

Scope = Literal["kakao", "personal", "unclassified"]
KST = ZoneInfo("Asia/Seoul")
# Vault 안의 기록은 gzip 보관으로 본문이 바뀌므로 wiki 출처는 스냅샷으로 등록한다.
VAULT_JOURNAL_DIRECTORY = Path("00_session") / "agent-logs"
FRONT_MATTER = re.compile(r"---\n(.*?)\n---\n(.*)", re.S)


def digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def slug(text: str, limit: int = 40) -> str:
    # macOS 파일명 한도를 넘지 않도록 한글도 UTF-8 바이트 수로 제한한다.
    cleaned = re.sub(r"[^\w가-힣.-]+", "-", text).strip(".-_")
    return cleaned.encode()[:limit].decode("utf-8", errors="ignore").rstrip(".-_") or "untitled"


def git_output(project: Path, *arguments: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(project), *arguments],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def resolve_project(project: Path) -> Path:
    """Git 루트 또는 지정 디렉터리의 실제 경로를 반환한다.

    Args:
        project: 세션의 실제 cwd.

    Returns:
        동일 이름·다른 경로와 worktree를 구분하는 경로.

    Raises:
        ValueError: 작업 디렉터리가 없을 때.
    """
    project = project.expanduser().resolve()
    if not project.is_dir():
        raise ValueError(f"Project directory not found: {project}")
    return Path(git_output(project, "rev-parse", "--show-toplevel") or project).resolve()


def resolve_root(value: Path | None = None) -> Path:
    """명시 경로·환경변수·Obsidian 순서로 기록 루트를 선택한다.

    Args:
        value: 명시적 저장소 경로.

    Returns:
        생성하지 않은 절대 저장 경로. Vault가 없으면 로컬 fallback.
    """
    explicit = value or os.getenv("AI_ENV_SESSION_LOG_DIR")
    if explicit:
        return expand_path(str(explicit)).resolve()
    vault = expand_path(os.getenv("OBSIDIAN_BASE") or "~/Documents/Obsidian Vault")
    if vault.is_dir():
        return vault.resolve() / VAULT_JOURNAL_DIRECTORY
    return Path.home() / ".ai-env" / "session-logs"


def project_directory(project: Path, root: Path | None = None) -> Path:
    """프로젝트 경로 해시로 같은 이름의 저장소도 격리한다.

    Args:
        project: 프로젝트 cwd.
        root: 선택적 공용 저장소.

    Returns:
        프로젝트별 기록 디렉터리. 생성하지 않는다.
    """
    project = resolve_project(project)
    directory = resolve_root(root) / f"{slug(project.name)}-{digest(str(project))}"
    if directory.is_symlink():
        raise ValueError("Journal project directory must not be a symlink")
    return directory


def project_scope(project: Path) -> Scope:
    """프로젝트 프로파일의 명시적 분류만 읽는다.

    Args:
        project: 프로젝트 루트.

    Returns:
        kakao, personal 또는 미지정 분류.

    Raises:
        ValueError: 분류 설정이 유효하지 않을 때.
    """
    profile = project / ".claude" / "project-profile.yaml"
    data = yaml.safe_load(profile.read_text()) if profile.is_file() else {}
    if not isinstance(data, dict) or not isinstance(data.get("project", {}), dict):
        raise ValueError("Invalid project profile")
    value = data.get("project", {}).get("session_scope", "unclassified")
    if value not in ("kakao", "personal", "unclassified"):
        raise ValueError("project.session_scope must be kakao, personal or unclassified")
    return cast(Scope, value)


def split_record(text: str) -> tuple[str, str]:
    """줄 단위 `---` 구분선으로 YAML 머리말과 본문을 나눈다.

    Args:
        text: 기록 Markdown 원문.

    Returns:
        (머리말 YAML, 본문).

    Raises:
        ValueError: 머리말이 없을 때.
    """
    match = FRONT_MATTER.match(text)
    if not match:
        raise ValueError("Invalid journal header")
    return match.group(1), match.group(2)


def render_record(metadata: dict[str, object], body: str) -> str:
    """메타데이터를 YAML 머리말로 붙인 기록 Markdown을 만든다.

    Args:
        metadata: 머리말 필드.
        body: 머리말 뒤 Markdown 본문.

    Returns:
        저장할 Markdown 원문.
    """
    header = yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False)
    return f"---\n{header}---\n\n{body}"


def read_metadata(path: Path) -> dict[str, object]:
    header, _ = split_record(path.read_text(encoding="utf-8"))
    data = yaml.safe_load(header)
    if not isinstance(data, dict):
        raise ValueError(f"Invalid journal metadata: {path}")
    return {**data, "path": str(path)}


@contextmanager
def journal_lock(directory: Path, name: str = ".lock") -> Iterator[None]:
    """프로젝트 기록 디렉터리의 쓰기를 프로세스 간에 직렬화한다.

    Args:
        directory: 이미 존재하는 프로젝트 기록 디렉터리.
        name: 잠금 파일명. 다른 잠금을 잡는 작업 전체를 묶을 때 별도 이름을 쓴다.

    Yields:
        배타 잠금을 보유한 구간.

    Raises:
        ValueError: 잠금 파일이 symlink일 때.
    """
    lock_path = directory / name
    if lock_path.is_symlink():
        raise ValueError("Journal lock must not be a symlink")
    descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    with os.fdopen(descriptor, "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield
