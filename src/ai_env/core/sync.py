"""Synchronization logic for ai-env."""

from __future__ import annotations

import re
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

from .codex_skills import copy_skill_tree_for_codex
from .config import get_project_root
from .secrets import get_secrets_manager


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


def _sync_hooks(src: Path, dst: Path, dry_run: bool) -> tuple[str, int]:
    """hooks 디렉토리 동기화 (전체 복사 + .sh 실행 권한 설정)

    Args:
        src: 소스 디렉토리
        dst: 목적지 디렉토리
        dry_run: True면 실제 복사하지 않음

    Returns:
        (설명, 복사된 항목 수)
    """
    sh_files = list(src.glob("*.sh"))

    if not dry_run:
        safe_copytree(src, dst)
        # .sh 파일에 실행 권한 부여
        for sh_file in dst.glob("*.sh"):
            sh_file.chmod(sh_file.stat().st_mode | 0o755)

    return f"hooks/ ({len(sh_files)} scripts)", len(sh_files)


def _sync_file_or_dir(src: Path, dst: Path, dry_run: bool = False) -> tuple[str, int]:
    """파일이나 디렉토리 동기화 (공통 로직)

    동기화 전략:
    - 파일: 단순 복사
    - commands/ 디렉토리: .md 파일만 복사
    - skills/ 디렉토리: 서브디렉토리 전체 복사
    - hooks/ 디렉토리: 전체 복사 + .sh 실행 권한
    - 기타 디렉토리: 전체 복사

    Args:
        src: 소스 경로
        dst: 목적지 경로
        dry_run: True면 실제 복사하지 않음

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
        return _sync_hooks(src, dst, dry_run)
    else:
        return _sync_directory(src, dst, dry_run)


def _update_team_skill_repos(
    project_root: Path,
    skills_include: list[str] | None = None,
    skills_exclude: list[str] | None = None,
) -> dict[str, str]:
    """팀 스킬 심링크의 실제 레포에서 develop 브랜치 git pull

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
            # develop 브랜치로 전환 후 pull
            subprocess.run(
                ["git", "checkout", "develop"],
                cwd=repo_dir,
                capture_output=True,
                text=True,
                check=True,
            )
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
        except subprocess.CalledProcessError as e:
            results[item.name] = f"failed: {e.stderr.strip()}"

    return results


def _collect_skill_sources(
    project_root: Path,
    skills_include: list[str] | None = None,
    skills_exclude: list[str] | None = None,
) -> list[Path]:
    """스킬 소스 디렉토리 수집 (personal + team)

    personal 소스는 ai-env/.claude/skills/ 이다.
    team 스킬(cde-*skills)은 명시적으로 include/exclude 옵션을 준 경우에만 수집한다.

    Args:
        project_root: ai-env 프로젝트 루트
        skills_include: 포함할 팀 스킬 디렉토리 이름 (예: ["cde-skills"])
            지정 시 이 목록에 있는 디렉토리만 포함.
        skills_exclude: 제외할 팀 스킬 디렉토리 이름 (예: ["cde-ranking-skills"])
            skills_include 없이 지정하면 team 전체에서 제외 필터로 동작.

    Returns:
        스킬 서브디렉토리 경로 리스트
    """
    sources: list[Path] = []

    # 1. personal skills (항상 포함)
    personal_dir = project_root / ".claude" / "skills"

    if personal_dir.is_dir():
        for d in sorted(personal_dir.iterdir()):
            if d.is_dir() and not d.name.startswith("."):
                sources.append(d)

    # 옵션이 없으면 기본은 personal만 동기화
    if skills_include is None and skills_exclude is None:
        return sources

    # 2. team skills: cde-*skills 심링크들 (cde-skills, cde-ranking-skills 등)
    #    각 심링크는 다음 구조 중 하나:
    #    - nested 구조: .claude/skills/skill-name/SKILL.md
    #    - skills subdir 구조: skills/skill-name/SKILL.md
    #    - flat 구조: skill-name/SKILL.md (루트에 스킬 디렉토리)
    for item in sorted(project_root.iterdir()):
        if not item.name.startswith("cde-") or not item.name.endswith("skills"):
            continue
        if not item.exists():  # broken symlink
            continue

        # include/exclude 필터 적용
        if skills_include is not None and item.name not in skills_include:
            continue
        if skills_exclude is not None and item.name in skills_exclude:
            continue

        # 심링크 resolve해서 실제 경로 사용
        cde_skills_dir = item.resolve()

        # 스킬 디렉토리 탐색 (3가지 구조 지원)
        #   1) nested: .claude/skills/skill-name/SKILL.md
        #   2) skills subdir: skills/skill-name/SKILL.md
        #   3) flat: skill-name/SKILL.md (루트에 직접)
        nested_skills = cde_skills_dir / ".claude" / "skills"
        skills_subdir = cde_skills_dir / "skills"

        if nested_skills.is_dir():
            scan_dir = nested_skills
        elif skills_subdir.is_dir():
            scan_dir = skills_subdir
        else:
            scan_dir = cde_skills_dir

        for d in sorted(scan_dir.iterdir()):
            if d.is_dir() and not d.name.startswith(".") and not d.name.startswith("_"):
                if (d / "SKILL.md").exists():
                    sources.append(d)

    return sources


def _sync_skills_merged(
    project_root: Path,
    dst: Path,
    dry_run: bool,
    skills_include: list[str] | None = None,
    skills_exclude: list[str] | None = None,
    copy_fn: Callable[[Path, Path], None] | None = None,
) -> tuple[str, int]:
    """personal + team 스킬을 합쳐서 동기화

    Args:
        project_root: ai-env 프로젝트 루트
        dst: 목적지 디렉토리 (~/.claude/skills)
        dry_run: True면 실제 복사하지 않음
        skills_include: 포함할 팀 스킬 디렉토리 이름
        skills_exclude: 제외할 팀 스킬 디렉토리 이름
        copy_fn: 스킬 디렉토리 복사 함수 (기본: safe_copytree).
            signature: (src: Path, dst: Path) -> None

    Returns:
        (설명, 복사된 스킬 수)
    """
    if copy_fn is None:
        copy_fn = safe_copytree

    skill_dirs = _collect_skill_sources(project_root, skills_include, skills_exclude)

    if not dry_run:
        dst.mkdir(parents=True, exist_ok=True)
        for skill_dir in skill_dirs:
            copy_fn(skill_dir, dst / skill_dir.name)

    return f"skills/ ({len(skill_dirs)} items)", len(skill_dirs)


def sync_claude_global_config(
    dry_run: bool = False,
    skills_include: list[str] | None = None,
    skills_exclude: list[str] | None = None,
) -> dict[str, str]:
    """
    글로벌 Claude Code 설정 동기화
    ai-env/.claude → ~/.claude
    (CLAUDE.md, commands/, skills/, settings.json)

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

    results: dict[str, str] = {}

    if not source_dir.exists():
        return results

    # 1. CLAUDE.md 동기화 (global/에서)
    desc, _ = _sync_file_or_dir(global_dir / "CLAUDE.md", target_dir / "CLAUDE.md", dry_run)
    if desc:
        results[desc] = str(target_dir / "CLAUDE.md")

    # 2. settings.json 생성 (환경변수 치환, global/에서)
    settings_template = global_dir / "settings.json.template"
    settings_dst = target_dir / "settings.json"
    if settings_template.exists():
        sm = get_secrets_manager()
        with open(settings_template) as f:
            content = sm.substitute(f.read())

        if not dry_run:
            settings_dst.parent.mkdir(parents=True, exist_ok=True)
            with open(settings_dst, "w") as f:
                f.write(content)
        results["settings.json"] = str(settings_dst)

    # 3. commands/ 동기화 (.claude/commands → ~/.claude/commands)
    desc, _ = _sync_file_or_dir(source_dir / "commands", target_dir / "commands", dry_run)
    if desc:
        results[desc] = str(target_dir / "commands")

    # 4. hooks/ 동기화 (.claude/hooks → ~/.claude/hooks)
    desc, _ = _sync_file_or_dir(source_dir / "hooks", target_dir / "hooks", dry_run)
    if desc:
        results[desc] = str(target_dir / "hooks")

    # 5. skills/ 동기화 (personal + team 합쳐서 → ~/.claude/skills)
    desc, _ = _sync_skills_merged(
        project_root, target_dir / "skills", dry_run, skills_include, skills_exclude
    )
    if desc:
        results[desc] = str(target_dir / "skills")

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
    name = name_match.group(1).strip() if name_match else skill_dir.name

    # description 추출 (첫 줄만, | 블록이면 다음 줄)
    desc_match = re.search(r"^description:\s*\|?\s*\n?\s*(.+)$", fm_text, re.MULTILINE)
    if desc_match:
        desc = desc_match.group(1).strip()
    else:
        # 인라인 description
        desc_inline = re.search(r"^description:\s*(.+)$", fm_text, re.MULTILINE)
        desc = desc_inline.group(1).strip() if desc_inline else name

    return name, desc


def _build_skills_index(
    project_root: Path,
    skills_include: list[str] | None = None,
    skills_exclude: list[str] | None = None,
) -> str:
    """스킬 인덱스 Markdown 섹션 생성.

    수집된 스킬의 name + description 첫 줄로 "Available Skills" 섹션을 만든다.

    Args:
        project_root: ai-env 프로젝트 루트
        skills_include: 포함할 팀 스킬 디렉토리 이름
        skills_exclude: 제외할 팀 스킬 디렉토리 이름

    Returns:
        Markdown 섹션 문자열 (스킬 없으면 빈 문자열)
    """
    skill_dirs = _collect_skill_sources(project_root, skills_include, skills_exclude)
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


def _sync_agent_global_md(
    target_dir_name: str,
    target_filename: str,
    dry_run: bool,
    skills_include: list[str] | None = None,
    skills_exclude: list[str] | None = None,
) -> dict[str, str]:
    """에이전트별 글로벌 MD 파일 동기화 (공통 로직)

    ai-env/.claude/global/CLAUDE.md → ~/.<target_dir_name>/<target_filename>
    스킬 인덱스를 하단에 추가한다.

    Args:
        target_dir_name: 홈 디렉토리 하위 폴더 이름 (예: ".codex", ".gemini")
        target_filename: 대상 파일 이름 (예: "AGENTS.md", "GEMINI.md")
        dry_run: True면 실제 복사하지 않음
        skills_include: 포함할 팀 스킬 디렉토리 이름
        skills_exclude: 제외할 팀 스킬 디렉토리 이름
    """
    project_root = get_project_root()
    source = project_root / ".claude" / "global" / "CLAUDE.md"

    if not source.exists():
        return {}

    # 원본 내용 + 스킬 인덱스 append
    content = source.read_text(encoding="utf-8")
    skills_index = _build_skills_index(project_root, skills_include, skills_exclude)
    if skills_index:
        content = content.rstrip() + "\n" + skills_index

    dst = Path.home() / target_dir_name / target_filename
    if not dry_run:
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(content, encoding="utf-8")

    return {target_filename: str(dst)}


def _sync_agent_global(
    target_dir_name: str,
    target_filename: str,
    skills_copy_fn: Callable[[Path, Path], None] | None,
    dry_run: bool,
    skills_include: list[str] | None,
    skills_exclude: list[str] | None,
) -> dict[str, str]:
    """에이전트별 글로벌 설정 동기화 (공통 로직)

    Args:
        target_dir_name: 홈 디렉토리 하위 폴더 이름 (예: ".codex", ".gemini")
        target_filename: 대상 파일 이름 (예: "AGENTS.md", "GEMINI.md")
        skills_copy_fn: 스킬 복사 함수 (None이면 스킬 동기화 건너뜀)
        dry_run: True면 실제 복사하지 않음
        skills_include: 포함할 팀 스킬 디렉토리 이름
        skills_exclude: 제외할 팀 스킬 디렉토리 이름
    """
    results = _sync_agent_global_md(
        target_dir_name, target_filename, dry_run, skills_include, skills_exclude
    )
    if not results:
        return results

    # 스킬 파일 동기화 (copy_fn이 있는 에이전트만)
    if skills_copy_fn is not None:
        skills_dir = Path.home() / target_dir_name / "skills"
        desc, count = _sync_skills_merged(
            get_project_root(),
            skills_dir,
            dry_run,
            skills_include,
            skills_exclude,
            copy_fn=skills_copy_fn,
        )
        if count:
            results[desc] = str(skills_dir)

    return results


def sync_codex_global_config(
    dry_run: bool = False,
    skills_include: list[str] | None = None,
    skills_exclude: list[str] | None = None,
) -> dict[str, str]:
    """Codex CLI 글로벌 설정 동기화

    ai-env/.claude/global/CLAUDE.md + 스킬 인덱스 → ~/.codex/AGENTS.md
    ai-env/.claude/skills + team skills 병합 → ~/.codex/skills
    """
    return _sync_agent_global(
        ".codex", "AGENTS.md", copy_skill_tree_for_codex, dry_run, skills_include, skills_exclude
    )


def sync_gemini_global_config(
    dry_run: bool = False,
    skills_include: list[str] | None = None,
    skills_exclude: list[str] | None = None,
) -> dict[str, str]:
    """Gemini CLI 글로벌 설정 동기화

    ai-env/.claude/global/CLAUDE.md + 스킬 인덱스 → ~/.gemini/GEMINI.md
    """
    return _sync_agent_global(".gemini", "GEMINI.md", None, dry_run, skills_include, skills_exclude)
