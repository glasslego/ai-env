"""doctor 명령어"""

from __future__ import annotations

import json

import click

from ..core.doctor import run_doctor
from . import console, main


@main.command()
@click.option("--json-output", "--json", "json_mode", is_flag=True, help="JSON 출력")
def doctor(json_mode: bool) -> None:
    """환경 건강 검사"""
    report = run_doctor()

    if json_mode:
        console.print_json(json.dumps(report.to_dict()))
        return

    console.print("[bold]🏥 AI Environment Health Check[/bold]\n")

    # 카테고리별 그룹핑
    categories = {
        "env": "Environment",
        "tools": "Tools",
        "sync": "Sync Status",
        "shell": "Shell",
    }

    for cat_key, cat_label in categories.items():
        cat_checks = [c for c in report.checks if c.category == cat_key]
        if not cat_checks:
            continue

        console.print(f"  [bold]{cat_label}[/bold]")
        for check in cat_checks:
            if check.status == "pass":
                icon = "[green]✓[/green]"
            elif check.status == "warn":
                icon = "[yellow]⚠[/yellow]"
            else:
                icon = "[red]✗[/red]"
            console.print(f"  {icon} {check.name}: {check.message}")
        console.print()

    # 요약
    summary_parts = []
    if report.passed:
        summary_parts.append(f"[green]{report.passed} passed[/green]")
    if report.warned:
        summary_parts.append(f"[yellow]{report.warned} warnings[/yellow]")
    if report.failed:
        summary_parts.append(f"[red]{report.failed} failed[/red]")

    console.print(f"Summary: {', '.join(summary_parts)}")
