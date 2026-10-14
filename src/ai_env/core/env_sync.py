"""ai-env 원본에서 팀 저장소에 필요한 환경변수를 배포한다."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from dotenv import dotenv_values
from dotenv.parser import parse_stream

from .env_example import collect_team_env_keys


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
        previous = dotenv_values(target, interpolate=False) if target.exists() else {}
        missing = sorted(key for key in required if previous.get(key) and not values.get(key))
        if missing:
            raise ValueError(f"{name}: 원본에 유효한 값이 없는 key: {', '.join(missing)}")
        content = "# Managed by ai-env sync-env; edit ai-env/.env instead.\n"
        # 원본의 quote·다중행 표현을 그대로 유지한다. 중복 key는 최종 선언만 복사한다.
        selected = {
            binding.key: binding.original.string for binding in bindings if binding.key in required
        }
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
            if any(actual[key] != values[key] for key in actual):
                raise ValueError(".env 배포 값 검증에 실패했습니다.")
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
    return [target for target, _ in plans]
