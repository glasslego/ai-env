"""Synchronization logic for ai-env."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .codex_skills import copy_skill_tree_for_codex
from .config import get_project_root, load_settings
from .secrets import get_secrets_manager

# cmux 훅 스크립트 파일명
_CMUX_HOOK_SCRIPT = "cmux_notify.sh"
CDE_RANKING_SKILLS = "cde-ranking-skills"
CDE_RANKING_BASE_BRANCH = "develop"
CDE_RANKING_BASE_REMOTE = "origin"
CDE_RANKING_REMOTE_BASE_REF = f"refs/remotes/{CDE_RANKING_BASE_REMOTE}/{CDE_RANKING_BASE_BRANCH}"
CDE_RANKING_SYNC_WORKTREE = "cde-ranking-skills-rebased"


def safe_copytree(src: Path, dst: Path) -> None:
    """기존 대상을 제거 후 디렉토리 트리 복사.

    rmtree + copytree 패턴을 통합한 유틸리티.
    """
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def _sync_file(src: Path, dst: Path, dry_run: bool) -> tuple[str, int]:
    """단일 파일 동기화

    Args:
        src: 소스 파일 경로
        dst: 목적지 파일 경로
        dry_run: True면 실제 복사하지 않음

    Returns:
        (파일 이름, 복사된 파일 수)

    Raises:
        OSError: 파일 복사 실패 시
        PermissionError: 권한 오류 시
    """
    if not dry_run:
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        except PermissionError as e:
            raise PermissionError(f"Permission denied copying {src} to {dst}") from e
        except OSError as e:
            raise OSError(f"Failed to copy {src} to {dst}: {e}") from e
    return src.name, 1


def _sync_md_files(src: Path, dst: Path, dry_run: bool) -> tuple[str, int]:
    """디렉토리 내 .md 파일만 동기화 (commands/ 디렉토리용)

    Args:
        src: 소스 디렉토리
        dst: 목적지 디렉토리
        dry_run: True면 실제 복사하지 않음

    Returns:
        (설명, 복사된 파일 수)
    """
    md_files = list(src.glob("*.md"))

    if not dry_run:
        dst.mkdir(parents=True, exist_ok=True)
        for md_file in md_files:
            shutil.copy2(md_file, dst / md_file.name)

    return f"{src.name}/ ({len(md_files)} files)", len(md_files)


def _sync_subdirectories(src: Path, dst: Path, dry_run: bool) -> tuple[str, int]:
    """서브디렉토리들 동기화 (skills/ 디렉토리용)

    Args:
        src: 소스 디렉토리
        dst: 목적지 디렉토리
        dry_run: True면 실제 복사하지 않음

    Returns:
        (설명, 복사된 디렉토리 수)
    """
    subdirs = [d for d in src.iterdir() if d.is_dir() and not d.name.startswith(".")]

    if not dry_run:
        dst.mkdir(parents=True, exist_ok=True)
        for subdir in subdirs:
            safe_copytree(subdir, dst / subdir.name)

    return f"{src.name}/ ({len(subdirs)} items)", len(subdirs)


def _sync_directory(src: Path, dst: Path, dry_run: bool) -> tuple[str, int]:
    """일반 디렉토리 동기화 (전체 복사)

    Args:
        src: 소스 디렉토리
        dst: 목적지 디렉토리
        dry_run: True면 실제 복사하지 않음

    Returns:
        (설명, 복사된 항목 수)
    """
    if not dry_run:
        safe_copytree(src, dst)

    return f"{src.name}/", 1


def _sync_hooks(
    src: Path, dst: Path, dry_run: bool, *, cmux_enabled: bool = True
) -> tuple[str, int]:
    """hooks 디렉토리 동기화 (전체 복사 + .sh 실행 권한 설정)

    Args:
        src: 소스 디렉토리
        dst: 목적지 디렉토리
        dry_run: True면 실제 복사하지 않음
        cmux_enabled: False면 cmux_notify.sh를 제외

    Returns:
        (설명, 복사된 항목 수)
    """
    sh_files = list(src.glob("*.sh"))
    if not cmux_enabled:
        sh_files = [f for f in sh_files if f.name != _CMUX_HOOK_SCRIPT]

    if not dry_run:
        safe_copytree(src, dst)
        # cmux 비활성화 시 복사된 cmux 스크립트 제거
        if not cmux_enabled:
            cmux_script = dst / _CMUX_HOOK_SCRIPT
            if cmux_script.exists():
                cmux_script.unlink()
        # .sh 파일에 실행 권한 부여
        for sh_file in dst.glob("*.sh"):
            sh_file.chmod(sh_file.stat().st_mode | 0o755)

    return f"hooks/ ({len(sh_files)} scripts)", len(sh_files)


def _sync_file_or_dir(
    src: Path, dst: Path, dry_run: bool = False, *, cmux_enabled: bool = True
) -> tuple[str, int]:
    """파일이나 디렉토리 동기화 (공통 로직)

    동기화 전략:
    - 파일: 단순 복사
    - commands/ 디렉토리: .md 파일만 복사
    - skills/ 디렉토리: 서브디렉토리 전체 복사
    - hooks/ 디렉토리: 전체 복사 + .sh 실행 권한 (cmux 조건부)
    - 기타 디렉토리: 전체 복사

    Args:
        src: 소스 경로
        dst: 목적지 경로
        dry_run: True면 실제 복사하지 않음
        cmux_enabled: hooks/ 동기화 시 cmux 스크립트 포함 여부

    Returns:
        (설명, 복사된 항목 수)
    """
    if not src.exists():
        return "", 0

    if src.is_file():
        return _sync_file(src, dst, dry_run)

    # 디렉토리 처리
    if src.name == "commands":
        return _sync_md_files(src, dst, dry_run)
    elif src.name == "skills":
        return _sync_subdirectories(src, dst, dry_run)
    elif src.name == "hooks":
        return _sync_hooks(src, dst, dry_run, cmux_enabled=cmux_enabled)
    else:
        return _sync_directory(src, dst, dry_run)


def _update_team_skill_repos(
    project_root: Path,
    skills_include: list[str] | None = None,
    skills_exclude: list[str] | None = None,
) -> dict[str, str]:
    """팀 스킬 심링크의 실제 레포에서 git pull (develop 브랜치일 때만)

    Args:
        project_root: ai-env 프로젝트 루트
        skills_include: 포함할 팀 스킬 디렉토리 이름
        skills_exclude: 제외할 팀 스킬 디렉토리 이름

    Returns:
        {디렉토리명: 결과 메시지} 딕셔너리
    """
    results: dict[str, str] = {}

    for item in sorted(project_root.iterdir()):
        if not item.name.startswith("cde-") or not item.name.endswith("skills"):
            continue
        if not item.exists():  # broken symlink
            continue
        if skills_include is not None and item.name not in skills_include:
            continue
        if skills_exclude is not None and item.name in skills_exclude:
            continue

        repo_dir = item.resolve()
        if not (repo_dir / ".git").exists():
            results[item.name] = "not a git repo, skipped"
            continue

        try:
            # 현재 브랜치 확인 — develop일 때만 pull, 작업 브랜치는 그대로 sync
            branch_result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=repo_dir,
                capture_output=True,
                text=True,
                check=True,
            )
            current_branch = branch_result.stdout.strip()
            if current_branch == "develop":
                pull_result = subprocess.run(
                    ["git", "pull", "--ff-only"],
                    cwd=repo_dir,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                output = pull_result.stdout.strip()
                if "Already up to date" in output:
                    results[item.name] = "already up to date"
                else:
                    results[item.name] = "updated"
            elif item.name == CDE_RANKING_SKILLS:
                results[item.name] = (
                    f"on branch '{current_branch}', sync uses develop-rebased worktree"
                )
            else:
                results[item.name] = f"on branch '{current_branch}', skipped pull"
        except subprocess.CalledProcessError as e:
            results[item.name] = f"failed: {e.stderr.strip()}"

    return results


# 정책상 무조건 동기화하는 핵심 팀 스킬 (skills_exclude 로만 옵트아웃 가능)
ALWAYS_TEAM_SKILLS = ("cde-skills", "cde-ranking-skills")

_SKILL_COPY_IGNORED_DIRS = frozenset(
    {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "node_modules",
    }
)
_SKILL_COPY_LARGE_ARTIFACT_SUFFIXES = frozenset(
    {".db", ".sqlite", ".sqlite3", ".parquet", ".zip", ".html", ".json"}
)
_SKILL_COPY_MAX_ARTIFACT_BYTES = 5 * 1024 * 1024


def _strip_wrapping_quotes(value: str) -> str:
    """frontmatter scalar 값의 바깥 quote 한 겹을 제거."""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _skill_copy_ignore(directory: str, names: list[str]) -> set[str]:
    """스킬 복사 시 캐시/빌드 산출물과 큰 생성 파일을 제외."""
    ignored: set[str] = set()
    base = Path(directory)

    for name in names:
        path = base / name
        if path.is_dir():
            if name in _SKILL_COPY_IGNORED_DIRS:
                ignored.add(name)
            continue

        if path.suffix in {".pyc", ".pyo"}:
            ignored.add(name)
            continue

        if path.suffix in _SKILL_COPY_LARGE_ARTIFACT_SUFFIXES:
            try:
                if path.stat().st_size > _SKILL_COPY_MAX_ARTIFACT_BYTES:
                    ignored.add(name)
            except OSError:
                continue

    return ignored


def safe_copy_skill_tree(src: Path, dst: Path) -> None:
    """스킬 디렉토리를 복사하되 캐시와 큰 생성 산출물은 제외."""
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=_skill_copy_ignore)


def _git_stdout(repo: Path, args: list[str]) -> str:
    """Run git in repo and return stripped stdout."""
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _git_ref_exists(repo: Path, ref: str) -> bool:
    """Return whether a git ref exists in repo."""
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", ref],
        cwd=repo,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def _fetch_git_remote_branch(repo: Path, remote: str, branch: str, target_ref: str) -> bool:
    """Fetch a remote branch into a local ref without checking it out."""
    if (
        subprocess.run(
            ["git", "remote", "get-url", remote],
            cwd=repo,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        ).returncode
        != 0
    ):
        return False

    result = subprocess.run(
        ["git", "fetch", "--quiet", remote, f"{branch}:{target_ref}"],
        cwd=repo,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def _cde_ranking_base_ref_for_sync(repo: Path) -> str | None:
    """Return the best available develop ref for cde-ranking sync."""
    _fetch_git_remote_branch(
        repo,
        CDE_RANKING_BASE_REMOTE,
        CDE_RANKING_BASE_BRANCH,
        CDE_RANKING_REMOTE_BASE_REF,
    )
    if _git_ref_exists(repo, CDE_RANKING_REMOTE_BASE_REF):
        return CDE_RANKING_REMOTE_BASE_REF
    if _git_ref_exists(repo, CDE_RANKING_BASE_BRANCH):
        return CDE_RANKING_BASE_BRANCH
    return None


def _remove_git_worktree(repo: Path, worktree: Path) -> None:
    """Remove a git worktree path if registered, then delete leftovers."""
    subprocess.run(
        ["git", "worktree", "remove", "--force", str(worktree)],
        cwd=repo,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    shutil.rmtree(worktree, ignore_errors=True)


def _prepare_cde_ranking_skills_for_sync(project_root: Path, repo: Path) -> Path:
    """Return cde-ranking-skills repo path rebased onto develop for sync.

    The source repo worktree is never rebased in place. If the current branch is
    not develop, a detached temporary worktree is created under
    `.claude/worktrees/` and rebased onto `origin/develop` when available, with
    local `develop` as the fallback.
    """
    if not (repo / ".git").exists():
        return repo

    try:
        current_branch = _git_stdout(repo, ["rev-parse", "--abbrev-ref", "HEAD"])
    except subprocess.CalledProcessError:
        return repo

    if current_branch == CDE_RANKING_BASE_BRANCH:
        return repo
    base_ref = _cde_ranking_base_ref_for_sync(repo)
    if base_ref is None:
        return repo

    worktree = project_root / ".claude" / "worktrees" / CDE_RANKING_SYNC_WORKTREE
    worktree.parent.mkdir(parents=True, exist_ok=True)
    _remove_git_worktree(repo, worktree)

    try:
        subprocess.run(
            ["git", "worktree", "add", "--detach", str(worktree), "HEAD"],
            cwd=repo,
            capture_output=True,
            text=True,
            check=True,
        )
        subprocess.run(
            ["git", "rebase", base_ref],
            cwd=worktree,
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        subprocess.run(
            ["git", "rebase", "--abort"],
            cwd=worktree,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        _remove_git_worktree(repo, worktree)
        detail = (e.stderr or e.stdout or str(e)).strip()
        raise RuntimeError(
            f"failed to prepare {CDE_RANKING_SKILLS} rebased on {CDE_RANKING_BASE_BRANCH}: {detail}"
        ) from e

    return worktree


def _team_repo_for_sync(project_root: Path, link: Path) -> Path:
    """Resolve a team skill repo path, applying sync-time overlays if needed."""
    repo = link.resolve()
    if link.name == CDE_RANKING_SKILLS:
        return _prepare_cde_ranking_skills_for_sync(project_root, repo)
    return repo


def _collect_skill_sources(
    project_root: Path,
    skills_include: list[str] | None = None,
    skills_exclude: list[str] | None = None,
    prepare_team_rebase: bool = True,
) -> list[Path]:
    """스킬 소스 디렉토리 수집 (personal + own + always-team + optional team)

    수집 순서:
      1) personal: ai-env/.claude/skills/<skill>/
      2) own:      ai-env/megan-skills/skills/<category>/<skill>/
      3) always:   ALWAYS_TEAM_SKILLS — skills_exclude 로만 제외
      4) team:     skills_include / skills_exclude 옵션이 있을 때만 cde-*skills 스캔

    Args:
        project_root: ai-env 프로젝트 루트
        skills_include: 포함할 팀 스킬 디렉토리 이름 (예: ["cde-skills"])
        skills_exclude: 제외할 팀 스킬 디렉토리 이름.
            ALWAYS_TEAM_SKILLS 도 이 목록에 있으면 제외된다.
        prepare_team_rebase: True면 cde-ranking 작업 브랜치용 rebase worktree를 준비한다.

    Returns:
        스킬 서브디렉토리 경로 리스트 (resolve 기준 dedup)
    """
    sources: list[Path] = []
    seen: set[Path] = set()

    def _add(skill: Path) -> None:
        key = skill.resolve()
        if key in seen:
            return
        seen.add(key)
        sources.append(skill)

    # 1) personal skills — ai-env/.claude/skills/
    personal_dir = project_root / ".claude" / "skills"
    if personal_dir.is_dir():
        for d in sorted(personal_dir.iterdir()):
            if d.is_dir() and not d.name.startswith("."):
                _add(d)

    # 2) own skills — ai-env/megan-skills/skills/{category}/{skill}/
    # 카테고리(obsidian/work/data/code/meta) 한 단계가 더 있다.
    own_dir = project_root / "megan-skills" / "skills"
    if own_dir.is_dir():
        for category in sorted(own_dir.iterdir()):
            if not category.is_dir() or category.name.startswith((".", "_")):
                continue
            for skill in sorted(category.iterdir()):
                if not skill.is_dir() or skill.name.startswith((".", "_")):
                    continue
                if (skill / "SKILL.md").exists():
                    _add(skill)

    # 3) ALWAYS 팀 스킬 (skills_exclude 로만 옵트아웃)
    for always_name in ALWAYS_TEAM_SKILLS:
        if skills_exclude is not None and always_name in skills_exclude:
            continue
        link = project_root / always_name
        if not link.exists():
            continue
        repo = _team_repo_for_sync(project_root, link) if prepare_team_rebase else link.resolve()
        scan_dir = _resolve_team_skill_root(repo)
        for d in sorted(scan_dir.iterdir()):
            if not d.is_dir() or d.name.startswith((".", "_")):
                continue
            if (d / "SKILL.md").exists():
                _add(d)

    # 옵션이 없으면 personal + own + always 만
    if skills_include is None and skills_exclude is None:
        return sources

    # 4) 옵션 지정 시 team 스킬 추가 스캔 (cde-*skills 심링크)
    for item in sorted(project_root.iterdir()):
        if not _is_team_skill_link(item, skills_include, skills_exclude):
            continue
        repo = _team_repo_for_sync(project_root, item) if prepare_team_rebase else item.resolve()
        scan_dir = _resolve_team_skill_root(repo)
        for d in sorted(scan_dir.iterdir()):
            if not d.is_dir() or d.name.startswith((".", "_")):
                continue
            if (d / "SKILL.md").exists():
                _add(d)

    return sources


def _is_team_skill_link(
    item: Path,
    skills_include: list[str] | None,
    skills_exclude: list[str] | None,
) -> bool:
    """item이 수집 대상 cde-*skills 심링크인지 판정 (include/exclude 필터 포함)."""
    if not (item.name.startswith("cde-") and item.name.endswith("skills")):
        return False
    if not item.exists():  # broken symlink
        return False
    if skills_include is not None and item.name not in skills_include:
        return False
    if skills_exclude is not None and item.name in skills_exclude:
        return False
    return True


def _has_skill_children(container: Path) -> bool:
    """컨테이너 바로 아래에 유효한 SKILL.md 기반 스킬이 있는지 확인."""
    try:
        children = container.iterdir()
    except OSError:
        return False

    return any(
        child.is_dir() and not child.name.startswith((".", "_")) and (child / "SKILL.md").is_file()
        for child in children
    )


def _resolve_team_skill_root(team_repo: Path) -> Path:
    """팀 스킬 레포 내부의 스킬 컨테이너 디렉토리 결정.

    지원 layout (우선순위):
      1) nested: <repo>/.claude/skills/<skill>/SKILL.md
      2) subdir: <repo>/skills/<skill>/SKILL.md
      3) plugin: <repo>/plugins/<plugin-name>/skills/<skill>/SKILL.md
      4) flat:   <repo>/<skill>/SKILL.md
    """
    for candidate in (team_repo / ".claude" / "skills", team_repo / "skills"):
        if candidate.is_dir() and _has_skill_children(candidate):
            return candidate

    plugins_dir = team_repo / "plugins"
    if plugins_dir.is_dir():
        for candidate in sorted(plugins_dir.glob("*/skills")):
            if candidate.is_dir() and _has_skill_children(candidate):
                return candidate

    return team_repo


def _sync_skills_merged(
    project_root: Path,
    dst: Path,
    dry_run: bool,
    skills_include: list[str] | None = None,
    skills_exclude: list[str] | None = None,
    copy_fn: Callable[[Path, Path], None] | None = None,
) -> tuple[str, int]:
    """personal + team 스킬을 합쳐서 동기화하고 stale 스킬을 정리.

    Args:
        project_root: ai-env 프로젝트 루트
        dst: 목적지 디렉토리 (~/.claude/skills, ~/.codex/skills, ~/.agents/skills 등)
        dry_run: True면 실제 복사하지 않음
        skills_include: 포함할 팀 스킬 디렉토리 이름
        skills_exclude: 제외할 팀 스킬 디렉토리 이름
        copy_fn: 스킬 디렉토리 복사 함수 (기본: safe_copy_skill_tree).
            signature: (src: Path, dst: Path) -> None

    Returns:
        (설명, 복사된 스킬 수)

    Notes:
        Codex 0.125+는 SKILL.md 파싱이 엄격해 stale/잘못된 frontmatter가 남으면
        시작 시 경고를 출력한다. 따라서 dst의 현재 소스에 없는 스킬 서브디렉토리는
        제거한다. dotfile/`_`-prefix 디렉토리(`.system` 등)는 보존한다.
    """
    if copy_fn is None:
        copy_fn = safe_copy_skill_tree

    skill_dirs = _collect_skill_sources(
        project_root,
        skills_include,
        skills_exclude,
        prepare_team_rebase=not dry_run,
    )

    if not dry_run:
        dst.mkdir(parents=True, exist_ok=True)
        _prune_stale_skills(dst, keep={s.name for s in skill_dirs})
        for skill_dir in skill_dirs:
            copy_fn(skill_dir, dst / skill_dir.name)

    return f"skills/ ({len(skill_dirs)} items)", len(skill_dirs)


def _prune_stale_skills(skills_root: Path, keep: set[str]) -> None:
    """skills_root 하위에서 keep에 없는 스킬 디렉토리를 제거.

    `.system`, `_shared` 같은 dotfile / underscore-prefix 디렉토리는 보존한다
    (해당 에이전트가 자체적으로 관리하는 메타 디렉토리일 수 있음).
    """
    if not skills_root.is_dir():
        return
    for entry in skills_root.iterdir():
        if not entry.is_dir() or entry.name.startswith((".", "_")):
            continue
        if entry.name not in keep:
            shutil.rmtree(entry, ignore_errors=True)


def _strip_cmux_hooks(settings_json: str) -> str:
    """settings.json에서 cmux 훅 엔트리를 제거

    cmux_notify.sh를 참조하는 훅을 제거하고, 빈 이벤트 카테고리도 정리한다.

    Args:
        settings_json: settings.json 문자열

    Returns:
        cmux 훅이 제거된 settings.json 문자열
    """
    data = json.loads(settings_json)
    hooks = data.get("hooks", {})

    events_to_remove: list[str] = []
    for event_name, matchers in hooks.items():
        if not isinstance(matchers, list):
            continue
        for matcher_block in matchers:
            hook_list = matcher_block.get("hooks", [])
            # cmux 훅 제거
            matcher_block["hooks"] = [
                h for h in hook_list if _CMUX_HOOK_SCRIPT not in h.get("command", "")
            ]
        # 훅이 모두 제거된 matcher 블록 제거
        hooks[event_name] = [m for m in matchers if m.get("hooks")]
        if not hooks[event_name]:
            events_to_remove.append(event_name)

    for event_name in events_to_remove:
        del hooks[event_name]

    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def _render_settings_template(template: Path, *, cmux_enabled: bool) -> str:
    """Render a Claude Code settings template with secrets and hook policy."""
    sm = get_secrets_manager()
    content = sm.substitute(template.read_text())

    if not cmux_enabled:
        content = _strip_cmux_hooks(content)

    return content


def _write_settings_json(path: Path, content: str) -> None:
    """Write rendered Claude Code settings JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def _ensure_symlink(
    target: Path,
    link: Path,
    *,
    dry_run: bool = False,
    allow_missing_target: bool = False,
) -> bool:
    """Ensure ``link`` is a symlink pointing at ``target``.

    Used to share common Claude assets (CLAUDE.md, commands, skills, ...) into
    the personal config directory without duplicating them. The ``CLAUDE_CONFIG_DIR``
    personal profile replaces the whole user-level config dir, so assets not present
    there would be invisible — symlinks reuse the canonical ``~/.claude`` copies.

    Args:
        target: Path the symlink should point to.
        link: Symlink path to create or repair.
        dry_run: If True, do not touch the filesystem.
        allow_missing_target: If True, create the link even when ``target`` does not
            yet exist. Use for managed paths written later in the same sync run
            (e.g. ``~/.codex/config.toml`` produced by the MCP generator step) — the
            dangling symlink resolves once the target is created.

    Returns:
        True if the link already pointed at ``target`` (or would after creation),
        False if ``target`` is missing (and ``allow_missing_target`` is False) so
        nothing was linked.
    """
    if not target.exists() and not allow_missing_target:
        return False

    if dry_run:
        return True

    # 이미 올바른 심링크면 그대로 둔다.
    if link.is_symlink():
        try:
            # 타깃이 아직 없을 수 있으므로 strict=False로 비교한다.
            if link.resolve(strict=False) == target.resolve(strict=False):
                return True
        except OSError:
            pass  # 깨진 심링크 → 아래에서 교체
        link.unlink()
    elif link.exists():
        # 심링크가 아닌 실제 파일/디렉토리가 있으면 건드리지 않고 건너뛴다.
        return False

    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(target, target_is_directory=target.is_dir())
    return True


def _codex_hook(command: str) -> dict[str, str]:
    """Codex hooks.json command hook entry."""
    return {"type": "command", "command": command}


def _codex_matcher(*commands: str, matcher: str = "") -> dict[str, Any]:
    """Codex hooks.json matcher block."""
    block: dict[str, Any] = {"hooks": [_codex_hook(command) for command in commands]}
    if matcher:
        block["matcher"] = matcher
    return block


def _codex_hooks_json(hooks_dir: Path, *, cmux_enabled: bool) -> str:
    """Generate Codex hooks.json without unsupported async fields."""
    session_start = f"bash '{hooks_dir / 'session_start.sh'}'"
    session_end = f"bash '{hooks_dir / 'session_end.sh'}'"
    pre_compact = f"bash '{hooks_dir / 'pre_compact.sh'}'"
    security_guard = f"bash '{hooks_dir / 'security_guard.sh'}'"
    event_log = f"bash '{hooks_dir / 'hook_event_log.sh'}'"
    cmux = f"bash '{hooks_dir / _CMUX_HOOK_SCRIPT}'"

    notify_hooks = [event_log]
    if cmux_enabled:
        notify_hooks.append(cmux)

    data = {
        "hooks": {
            "SessionStart": [
                _codex_matcher(session_start, *notify_hooks, matcher="startup|resume")
            ],
            "UserPromptSubmit": [_codex_matcher(*notify_hooks)],
            "PreToolUse": [
                _codex_matcher(
                    security_guard,
                    matcher="Bash|shell|shell_command|exec_command|unified_exec|local_shell|user_shell",
                ),
                _codex_matcher(event_log),
            ],
            "PostToolUse": [_codex_matcher(*notify_hooks)],
            "PreCompact": [_codex_matcher(pre_compact, *notify_hooks)],
            "SessionEnd": [_codex_matcher(session_end, *notify_hooks)],
            "Stop": [_codex_matcher(*notify_hooks)],
            "TaskCompleted": [_codex_matcher(*notify_hooks)],
            "Notification": [_codex_matcher(*notify_hooks)],
        }
    }
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def _sync_codex_hooks(
    project_root: Path,
    agent_root: Path,
    dry_run: bool,
    *,
    cmux_enabled: bool,
) -> dict[str, str]:
    """Sync Claude-compatible hook scripts and Codex hooks.json."""
    source_hooks = project_root / ".claude" / "hooks"
    extra_hooks = project_root / ".codex" / "hooks"
    target_hooks = agent_root / "hooks"
    results: dict[str, str] = {}

    if source_hooks.is_dir():
        desc, count = _sync_hooks(source_hooks, target_hooks, dry_run, cmux_enabled=cmux_enabled)
        if count:
            results[desc] = str(target_hooks)

    if extra_hooks.is_dir():
        hook_files = sorted(extra_hooks.glob("*.sh"))
        if not dry_run:
            target_hooks.mkdir(parents=True, exist_ok=True)
            for hook_file in hook_files:
                target = target_hooks / hook_file.name
                shutil.copy2(hook_file, target)
                target.chmod(target.stat().st_mode | 0o755)
        if hook_files:
            results[f"codex hooks/ ({len(hook_files)} scripts)"] = str(target_hooks)

    hooks_json = agent_root / "hooks.json"
    if not dry_run:
        hooks_json.parent.mkdir(parents=True, exist_ok=True)
        hooks_json.write_text(
            _codex_hooks_json(target_hooks, cmux_enabled=cmux_enabled),
            encoding="utf-8",
        )
    results["hooks.json"] = str(hooks_json)
    return results


def sync_claude_global_config(
    dry_run: bool = False,
    skills_include: list[str] | None = None,
    skills_exclude: list[str] | None = None,
) -> dict[str, str]:
    """
    글로벌 Claude Code 설정 동기화
    ai-env/.claude → ~/.claude
    (CLAUDE.md, commands/, skills/, settings.json, hooks/)

    cmux_enabled 설정에 따라 cmux 훅을 조건부로 포함/제외한다.
    skills는 ai-env/.claude/skills/ (personal)를 동기화한다.
    team 스킬(cde-*skills)은 옵션으로 지정했을 때만 함께 동기화한다.

    Args:
        dry_run: True면 실제 복사하지 않음
        skills_include: 포함할 팀 스킬 디렉토리 이름 (예: ["cde-skills"])
        skills_exclude: 제외할 팀 스킬 디렉토리 이름 (예: ["cde-ranking-skills"])
    """
    project_root = get_project_root()
    source_dir = project_root / ".claude"
    global_dir = source_dir / "global"  # CLAUDE.md와 settings.json.template 위치
    target_dir = Path.home() / ".claude"

    # settings.yaml에서 cmux 활성화 여부 확인
    settings = load_settings()
    cmux_enabled = settings.cmux_enabled

    results: dict[str, str] = {}

    if not source_dir.exists():
        return results

    # 1. CLAUDE.md 동기화 (global/에서)
    desc, _ = _sync_file_or_dir(global_dir / "CLAUDE.md", target_dir / "CLAUDE.md", dry_run)
    if desc:
        results[desc] = str(target_dir / "CLAUDE.md")

    # 2. settings.json 생성 (환경변수 치환 + cmux 조건부 처리, global/에서)
    settings_template = global_dir / "settings.json.template"
    settings_dst = target_dir / "settings.json"
    if settings_template.exists():
        content = _render_settings_template(settings_template, cmux_enabled=cmux_enabled)

        if not dry_run:
            _write_settings_json(settings_dst, content)
        results["settings.json"] = str(settings_dst)

        # 명시적인 enterprise 프로필도 같은 내용으로 생성한다. 기본 실행은
        # settings.json을 쓰고, wrapper의 `claude enterprise ...`는 이 파일을 쓴다.
        enterprise_dst = target_dir / "settings.enterprise.json"
        if not dry_run:
            _write_settings_json(enterprise_dst, content)
        results["settings.enterprise.json"] = str(enterprise_dst)

    # personal 프로필은 별도 config 디렉토리(~/.claude-personal)로 분리한다.
    # `claude personal`은 CLAUDE_CONFIG_DIR로 이 디렉토리를 user-level 설정으로 쓰며,
    # Bedrock env/apiKeyHelper가 없는 settings.json만 둬 개인 Anthropic 로그인을 쓴다.
    # (공용 자산 심링크는 모든 자산을 ~/.claude에 동기화한 뒤 함수 끝에서 건다.)
    personal_settings_template = global_dir / "settings.personal.json.template"
    if personal_settings_template.exists():
        personal_dir = Path.home() / ".claude-personal"
        personal_settings_dst = personal_dir / "settings.json"
        personal_content = _render_settings_template(
            personal_settings_template,
            cmux_enabled=cmux_enabled,
        )
        if not dry_run:
            _write_settings_json(personal_settings_dst, personal_content)
        results["settings.personal.json"] = str(personal_settings_dst)

    # 3. commands/ 동기화 (.claude/commands → ~/.claude/commands)
    desc, _ = _sync_file_or_dir(source_dir / "commands", target_dir / "commands", dry_run)
    if desc:
        results[desc] = str(target_dir / "commands")

    # 4. agents/ 동기화 (.claude/agents → ~/.claude/agents)
    src_agents = source_dir / "agents"
    if src_agents.is_dir():
        agent_count = _copy_commands_tree(src_agents, target_dir / "agents", dry_run)
        if agent_count:
            results[f"agents/ ({agent_count} files)"] = str(target_dir / "agents")

    # 5. hooks/ 동기화 (.claude/hooks → ~/.claude/hooks, cmux 조건부)
    desc, _ = _sync_file_or_dir(
        source_dir / "hooks", target_dir / "hooks", dry_run, cmux_enabled=cmux_enabled
    )
    if desc:
        results[desc] = str(target_dir / "hooks")

    # 6. skills/ 동기화 (personal + team 합쳐서 → ~/.claude/skills)
    desc, _ = _sync_skills_merged(
        project_root, target_dir / "skills", dry_run, skills_include, skills_exclude
    )
    if desc:
        results[desc] = str(target_dir / "skills")

    # 공용 자산을 personal config 디렉토리에 심링크로 재사용한다.
    # (settings.json은 위에서 personal 전용 내용으로 이미 기록함)
    if (global_dir / "settings.personal.json.template").exists():
        personal_dir = Path.home() / ".claude-personal"
        for asset in ("CLAUDE.md", "commands", "skills", "agents", "hooks"):
            if _ensure_symlink(target_dir / asset, personal_dir / asset, dry_run=dry_run):
                results[f"personal:{asset}"] = str(personal_dir / asset)

    return results


def _extract_skill_summary(skill_dir: Path) -> tuple[str, str] | None:
    """SKILL.md frontmatter에서 name과 description 첫 줄을 추출.

    Args:
        skill_dir: 스킬 디렉토리 (SKILL.md 포함)

    Returns:
        (name, description_first_line) 또는 None
    """
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return None

    content = skill_md.read_text(encoding="utf-8")

    # frontmatter 파싱 (--- ... ---)
    fm_match = re.search(r"^---\s*\n(.*?)\n---", content, re.DOTALL | re.MULTILINE)
    if not fm_match:
        return None

    fm_text = fm_match.group(1)

    # name 추출
    name_match = re.search(r"^name:\s*(.+)$", fm_text, re.MULTILINE)
    name = _strip_wrapping_quotes(name_match.group(1).strip()) if name_match else skill_dir.name

    # description 추출 (첫 줄만, | 블록이면 다음 줄)
    desc_match = re.search(r"^description:\s*\|?\s*\n?\s*(.+)$", fm_text, re.MULTILINE)
    if desc_match:
        desc = _strip_wrapping_quotes(desc_match.group(1).strip())
    else:
        # 인라인 description
        desc_inline = re.search(r"^description:\s*(.+)$", fm_text, re.MULTILINE)
        desc = _strip_wrapping_quotes(desc_inline.group(1).strip()) if desc_inline else name

    return name, desc


def _build_skills_index(
    project_root: Path,
    skills_include: list[str] | None = None,
    skills_exclude: list[str] | None = None,
    prepare_team_rebase: bool = True,
) -> str:
    """스킬 인덱스 Markdown 섹션 생성.

    수집된 스킬의 name + description 첫 줄로 "Available Skills" 섹션을 만든다.

    Args:
        project_root: ai-env 프로젝트 루트
        skills_include: 포함할 팀 스킬 디렉토리 이름
        skills_exclude: 제외할 팀 스킬 디렉토리 이름
        prepare_team_rebase: True면 cde-ranking 작업 브랜치용 rebase worktree를 준비한다.

    Returns:
        Markdown 섹션 문자열 (스킬 없으면 빈 문자열)
    """
    skill_dirs = _collect_skill_sources(
        project_root,
        skills_include,
        skills_exclude,
        prepare_team_rebase=prepare_team_rebase,
    )
    if not skill_dirs:
        return ""

    lines = [
        "",
        "---",
        "",
        "## Available Skills",
        "",
    ]
    for skill_dir in skill_dirs:
        summary = _extract_skill_summary(skill_dir)
        if summary:
            name, desc = summary
            lines.append(f"- **{name}**: {desc}")
        else:
            lines.append(f"- **{skill_dir.name}**")

    lines.append("")
    lines.append("각 스킬의 상세 가이드: `.claude/skills/{name}/SKILL.md` 참조")
    lines.append("")

    return "\n".join(lines)


def _copy_commands_tree(src: Path, dst: Path, dry_run: bool) -> int:
    """commands/ 트리에서 .md 파일만 보존 복사 (서브디렉토리 포함).

    Codex는 슬래시 커맨드를 직접 실행하지 않지만, 워크플로우 정의 MD를
    참조 자료로 활용할 수 있다.

    Returns:
        복사된 .md 파일 수
    """
    if not dry_run and dst.exists():
        shutil.rmtree(dst)

    count = 0
    md_files = sorted(src.rglob("*.md"))
    for md_file in md_files:
        rel = md_file.relative_to(src)
        target_path = dst / rel
        if not dry_run:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(md_file, target_path)
        count += 1
    return count


def sync_codex_global_config(
    dry_run: bool = False,
    skills_include: list[str] | None = None,
    skills_exclude: list[str] | None = None,
) -> dict[str, str]:
    """Codex CLI 글로벌 설정 동기화.

    출력:
    - ~/.codex/AGENTS.md          ← .claude/global/CLAUDE.md + 스킬 인덱스
    - ~/.codex/skills/            ← .claude/skills + team skills (Codex YAML로 정규화)
    - ~/.agents/skills/           ← 동일 (Codex 0.125+ 통합 스킬 위치)
    - ~/.codex/commands/          ← .claude/commands/ MD 트리 (참조)
    - ~/.codex/project-profile.yaml ← .claude/project-profile.yaml
    """
    project_root = get_project_root()
    source = project_root / ".claude" / "global" / "CLAUDE.md"

    if not source.exists():
        return {}

    # 1) AGENTS.md = CLAUDE.md + 스킬 인덱스
    content = source.read_text(encoding="utf-8")
    skills_index = _build_skills_index(
        project_root,
        skills_include,
        skills_exclude,
        prepare_team_rebase=not dry_run,
    )
    if skills_index:
        content = content.rstrip() + "\n" + skills_index

    agent_root = Path.home() / ".codex"
    agents_md = agent_root / "AGENTS.md"
    if not dry_run:
        agents_md.parent.mkdir(parents=True, exist_ok=True)
        agents_md.write_text(content, encoding="utf-8")

    results: dict[str, str] = {"AGENTS.md": str(agents_md)}

    settings = load_settings()
    results.update(
        _sync_codex_hooks(project_root, agent_root, dry_run, cmux_enabled=settings.cmux_enabled)
    )

    # 2) skills/ — Codex 호환 frontmatter로 정규화하여 ~/.codex/skills 와
    #    ~/.agents/skills (Codex 0.125+ 통합 위치) 두 곳에 복사
    for skills_dir in (agent_root / "skills", Path.home() / ".agents" / "skills"):
        desc, count = _sync_skills_merged(
            project_root,
            skills_dir,
            dry_run,
            skills_include,
            skills_exclude,
            copy_fn=copy_skill_tree_for_codex,
        )
        if count:
            results[f"{desc} → {skills_dir}"] = str(skills_dir)

    # 3) commands/ — Claude 슬래시 커맨드 정의 트리를 참조 자료로 미러
    src_commands = project_root / ".claude" / "commands"
    if src_commands.is_dir():
        dst_commands = agent_root / "commands"
        md_count = _copy_commands_tree(src_commands, dst_commands, dry_run)
        if md_count:
            results[f"commands/ ({md_count} files)"] = str(dst_commands)

    # 4) agents/ — Claude agent definitions as shared reference material
    src_agents = project_root / ".claude" / "agents"
    if src_agents.is_dir():
        dst_agents = agent_root / "agents"
        agent_count = _copy_commands_tree(src_agents, dst_agents, dry_run)
        if agent_count:
            results[f"agents/ ({agent_count} files)"] = str(dst_agents)

    # 5) project-profile.yaml — 그대로 복사
    src_profile = project_root / ".claude" / "project-profile.yaml"
    if src_profile.is_file():
        dst_profile = agent_root / "project-profile.yaml"
        if not dry_run:
            dst_profile.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_profile, dst_profile)
        results["project-profile.yaml"] = str(dst_profile)

    # 6) personal 프로필 미러 (~/.codex-personal)
    # `codex personal`은 CODEX_HOME=~/.codex-personal로 별도 auth.json(개인 계정)만
    # 분리하고, 공용 자산(AGENTS.md/skills/commands/agents/config.toml 등)은 ~/.codex를
    # 심링크로 재사용한다. auth.json은 절대 심링크하지 않아 계정이 섞이지 않게 한다.
    #
    # config.toml은 이 함수가 아니라 이후 단계(MCP generator의 save_all)에서 생성되므로,
    # 첫 sync 시점엔 아직 없을 수 있다. allow_missing_target로 dangling 심링크를 먼저 만들어
    # 두면 generator가 config.toml을 쓰는 순간 자동으로 해석되어 첫 sync에서도 동작한다.
    personal_root = Path.home() / ".codex-personal"
    # 같은 sync 실행 안에서 나중에 생성되는 managed 경로 (generator가 기록)
    generated_later = {"config.toml"}
    for asset in (
        "AGENTS.md",
        "skills",
        "commands",
        "agents",
        "project-profile.yaml",
        "config.toml",
        "hooks",
        "hooks.json",
    ):
        if _ensure_symlink(
            agent_root / asset,
            personal_root / asset,
            dry_run=dry_run,
            allow_missing_target=asset in generated_later,
        ):
            results[f"codex-personal:{asset}"] = str(personal_root / asset)

    return results
