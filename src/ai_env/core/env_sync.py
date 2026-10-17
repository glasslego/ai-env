"""ai-env 원본에서 팀 저장소에 필요한 환경변수를 배포한다."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Mapping
from pathlib import Path
from urllib.parse import urlparse

from dotenv import dotenv_values
from dotenv.parser import parse_stream

from .env_example import collect_team_env_keys

ATLASSIAN_ENV_KEYS = frozenset(
    {"JIRA_URL", "JIRA_EMAIL", "JIRA_TOKEN", "WIKI_BASE_URL", "WIKI_EMAIL", "WIKI_TOKEN"}
)


def wiki_uses_jira_cloud_auth(values: Mapping[str, str | None]) -> bool:
    """같은 Cloud 사이트에서 빈 Wiki 토큰을 Jira 인증으로 대체할 수 있는지 확인한다.

    Args:
        values: 원본 환경변수 값.

    Returns:
        같은 사이트·계정의 Jira Cloud 인증이 설정됐으면 True.
    """
    jira_url = values.get("JIRA_URL") or ""
    try:
        jira_host = urlparse(jira_url).hostname or ""
        wiki_host = urlparse(values.get("WIKI_BASE_URL") or jira_url).hostname or ""
    except ValueError:
        return False
    return bool(
        jira_host.endswith(".atlassian.net")
        and jira_host == wiki_host
        and values.get("JIRA_EMAIL")
        and values.get("JIRA_TOKEN")
        and (not values.get("WIKI_EMAIL") or values["WIKI_EMAIL"] == values["JIRA_EMAIL"])
    )


def sync_env_files(project_root: Path, dry_run: bool = False) -> list[Path]:
    """팀별 참조 key만 복사하며 비밀값은 반환하지 않는다.

    Args:
        project_root: 원본 .env와 팀 저장소 링크가 있는 ai-env 루트.
        dry_run: 파일을 변경하지 않고 배포 대상만 확인한다.

    Returns:
        배포 대상으로 확인된 .env 경로.

    Raises:
        ValueError: 원본이 잘못됐거나 대상의 유효한 값을 누락·빈 값으로 지우는 경우.
    """
    source = project_root / ".env"
    with source.open(encoding="utf-8") as stream:
        bindings = list(parse_stream(stream))
    if any(binding.error for binding in bindings):
        raise ValueError("원본 .env 구문 오류; 배포하지 않았습니다.")
    values = dotenv_values(source, interpolate=False)
    catalog = collect_team_env_keys(project_root)
    plans: list[tuple[Path, str]] = []
    targets: list[tuple[str, Path, set[str]]] = []
    for name in ("cde-skills", "cde-ranking-skills"):
        repo = project_root / name
        if not repo.is_dir():
            continue
        target = repo / ".env"
        required = {
            key
            for key, origins in catalog.items()
            if any(origin.startswith(f"{name}:") for origin in origins)
        }
        # 랭킹 helper가 cde-skills 인증 모듈을 호출하므로 공통 인증도 배포한다.
        required.update(
            key for key in values if key.startswith(("JIRA_", "WIKI_", "VAULT_", "CDE_SKILLS_"))
        )
        targets.append((name, target, required))
    # checkout이나 다른 에이전트의 marketplace 설정에 의존하지 않는 공식 fallback.
    portable_keys = {key for key in values if key.startswith(("JIRA_", "WIKI_", "CDE_SKILLS_"))}
    if portable_keys:
        targets.append(
            ("global fallback", Path.home() / ".cde-skills.env", portable_keys | ATLASSIAN_ENV_KEYS)
        )
    for name, target, required in targets:
        previous = dotenv_values(target, interpolate=False) if target.exists() else {}
        missing = sorted(
            key
            for key in required
            if previous.get(key)
            and not values.get(key)
            and not (
                key == "WIKI_TOKEN" and values.get(key) == "" and wiki_uses_jira_cloud_auth(values)
            )
        )
        if missing:
            raise ValueError(f"{name}: 원본에 유효한 값이 없는 key: {', '.join(missing)}")
        content = "# Managed by ai-env sync-env; edit ai-env/.env instead.\n"
        # 원본의 quote·다중행 표현을 그대로 유지한다. 중복 key는 최종 선언만 복사한다.
        selected = {
            binding.key: binding.original.string for binding in bindings if binding.key in required
        }
        if name == "global fallback" and target.exists():
            # 사용자가 다른 용도로 둔 인증은 중앙 관리 대상 밖으로 보존한다.
            with target.open(encoding="utf-8") as stream:
                existing = list(parse_stream(stream))
            if any(binding.error for binding in existing):
                raise ValueError("global fallback: .env 구문 오류; 배포하지 않았습니다.")
            for binding in existing:
                if binding.key and binding.key not in required:
                    selected[binding.key] = binding.original.string
        content += "".join(raw if raw.endswith("\n") else raw + "\n" for raw in selected.values())
        plans.append((target, content))
    if dry_run:
        return [target for target, _ in plans]
    for target, content in plans:
        if target.is_file() and not target.is_symlink() and target.read_text() == content:
            target.chmod(0o600)
            continue
        if target.exists():
            backup_dir = project_root / ".env-backups"
            backup_dir.mkdir(mode=0o700, exist_ok=True)
            backup_dir.chmod(0o700)
            fd, name = tempfile.mkstemp(
                prefix=f"{target.parent.name}-", suffix=".env", dir=backup_dir
            )
            with os.fdopen(fd, "wb") as stream:
                stream.write(target.read_bytes())
        fd, name = tempfile.mkstemp(prefix=".env-", dir=target.parent)
        temporary = Path(name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                stream.write(content)
            # 원본의 파싱 값과 같음을 확인한 뒤 교체한다.
            actual = dotenv_values(temporary, interpolate=False)
            if any(actual.get(key) != values.get(key) for key in required if key in values):
                raise ValueError(".env 배포 값 검증에 실패했습니다.")
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
    return [target for target, _ in plans]
