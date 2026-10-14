"""중앙 .env 배포 명령."""

import click

from ..core.config import get_project_root
from ..core.env_sync import sync_env_files
from . import console, main


@main.command("sync-env")
@click.option("--dry-run", is_flag=True, help="배포 대상만 확인")
def sync_env(dry_run: bool) -> None:
    """ai-env/.env에서 팀 저장소에 필요한 key를 복사한다."""
    try:
        paths = sync_env_files(get_project_root(), dry_run=dry_run)
    except (OSError, ValueError) as error:
        raise click.ClickException(str(error)) from error
    for path in paths:
        console.print(f"{'Would sync' if dry_run else 'Synced'}: {path}")
