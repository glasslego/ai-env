"""공용 작업 기록의 저장 경로·Markdown 머리말·잠금. 기록 내용과 무관한 저장 계층."""

from __future__ import annotations

import fcntl
import hashlib
import os
import re
import subprocess
import unicodedata
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from typing import Literal, cast
from zoneinfo import ZoneInfo

import yaml

from .config import expand_path

Scope = Literal["kakao", "personal", "unclassified"]
KST = ZoneInfo("Asia/Seoul")
# 기존 세션 노트와 같은 `00_session/<저장소>/` 아래에 공용 기록을 둔다.
VAULT_SESSION_DIRECTORY = Path("00_session")
JOURNAL_DIRECTORY_NAME = "agent-logs"
# 같은 이름의 다른 저장소를 구분하는 소유 표시 파일.
OWNER_FILE = ".repository"
# Git 저장소가 아닌 작업 폴더(홈·Vault 하위 등)의 기록은 저장소 폴더와 섞지 않는다.
MISC_DIRECTORY_NAME = "_misc"
FRONT_MATTER = re.compile(r"---\n(.*?)\n---\n(.*)", re.S)
# ssh·https 원격 URL을 `host/경로`로 맞춘다. 예: git@host:org/repo.git, https://u@host/org/repo
REMOTE_URL = re.compile(r"^(?:[\w+.-]+://)?(?:[^@/]+@)?([^/:]+)[:/](.+)$")


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
        return vault.resolve() / VAULT_SESSION_DIRECTORY
    return Path.home() / ".ai-env" / "session-logs"


def is_vault_journal(relative: Path) -> bool:
    """Vault 상대 경로가 공용 작업 기록 아래인지 판단한다.

    Args:
        relative: Vault 기준 상대 경로.

    Returns:
        `00_session/<저장소>/agent-logs/` 아래이면 True.
    """
    return (
        relative.parts[:1] == VAULT_SESSION_DIRECTORY.parts
        and JOURNAL_DIRECTORY_NAME in relative.parts[1:-1]
    )


def resolve_repository(project: Path) -> Path:
    """worktree를 포함해 같은 Git 저장소를 하나의 경로로 묶는다.

    Args:
        project: 세션의 실제 cwd.

    Returns:
        메인 작업 트리 경로. Git이 아니면 cwd 실제 경로.
    """
    project = resolve_project(project)
    common = git_output(project, "rev-parse", "--path-format=absolute", "--git-common-dir")
    return Path(common).parent.resolve() if common and Path(common).name == ".git" else project


def repository_identity(project: Path) -> str:
    """worktree·별도 clone을 같은 저장소로 묶는 식별자를 반환한다.

    Args:
        project: 세션의 실제 cwd.

    Returns:
        origin 원격의 `host/경로`. 원격이 없으면 메인 작업 트리 경로. 도구마다 다른
        한글 경로의 유니코드 형식(NFD/NFC)은 NFC로 맞춘다.
    """
    repository = resolve_repository(project)
    remote = git_output(repository, "remote", "get-url", "origin").removesuffix("/")
    match = REMOTE_URL.match(remote.removesuffix(".git"))
    identity = f"{match.group(1)}/{match.group(2)}" if match else remote or str(repository)
    return unicodedata.normalize("NFC", identity)


def project_directory(project: Path, root: Path | None = None) -> Path:
    """저장소 이름 폴더를 쓰고, 이름만 같은 다른 저장소는 해시로 분리한다.

    Args:
        project: 프로젝트 cwd. worktree·같은 원격의 clone도 같은 폴더를 쓴다.
        root: 선택적 공용 저장소.

    Returns:
        `<root>/<저장소>/agent-logs` 기록 디렉터리. Git 저장소가 아닌 cwd는
        `<root>/_misc/<폴더>/agent-logs`. 생성하지 않는다.

    Raises:
        ValueError: 기록 디렉터리 경로에 symlink가 있을 때.
    """
    identity = repository_identity(project)
    name = slug(PurePosixPath(identity).name)
    base = resolve_root(root)
    if not git_output(resolve_project(project), "rev-parse", "--git-dir"):
        base = base / MISC_DIRECTORY_NAME
    directory = base / name / JOURNAL_DIRECTORY_NAME
    owner = directory / OWNER_FILE
    if owner.is_file() and owner.read_text(encoding="utf-8").strip() != identity:
        directory = base / f"{name}-{digest(identity)}" / JOURNAL_DIRECTORY_NAME
    if directory.is_symlink() or directory.parent.is_symlink():
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
