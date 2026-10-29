"""문서 작업에서 호출하는 LLM Wiki 검색·등록 CLI."""

from pathlib import Path

import click
import yaml

from ..core.wiki_documents import register_document, resolve_vault, search_wiki
from . import console, main


@main.group("wiki")
@click.option("--vault", "vault_path", type=str, help="Vault 경로 (기본: OBSIDIAN_BASE)")
@click.pass_context
def wiki(ctx: click.Context, vault_path: str | None) -> None:
    """Obsidian LLM Wiki의 출처 등록과 로컬 검색."""
    try:
        ctx.obj = resolve_vault(vault_path)
    except ValueError as error:
        raise click.ClickException(str(error)) from error


@wiki.command("search")
@click.argument("query")
@click.option("--limit", type=click.IntRange(1, 100), default=5, show_default=True)
@click.pass_obj
def search(vault: Path, query: str, limit: int) -> None:
    """종합 페이지·등록 출처를 읽기 전용으로 검색하고 JSON 반환."""
    try:
        hits = search_wiki(vault, query, limit)
        console.print_json(data={"results": [hit.model_dump() for hit in hits]})
    except (OSError, ValueError, yaml.YAMLError) as error:
        raise click.ClickException(str(error)) from error


@wiki.command("register")
@click.argument("source", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--dry-run", is_flag=True, help="파일 변경 없이 등록 미리보기")
@click.option("--allow-private", is_flag=True, help="명시한 개인·투자 문서만 등록 허용")
@click.pass_obj
def register(vault: Path, source: Path, dry_run: bool, allow_private: bool) -> None:
    """완성한 Markdown을 등록하고 관련 종합 후보를 JSON 반환."""
    try:
        result = register_document(vault, source, dry_run=dry_run, allow_private=allow_private)
        console.print_json(result.model_dump_json())
    except (OSError, ValueError, yaml.YAMLError) as error:
        raise click.ClickException(str(error)) from error
