#!/usr/bin/env python3
"""
Markdown to HTML Converter for Weekly Reports

주간 보고서 Markdown 파일을 HTML로 변환합니다.
Bullet 계층 구조를 텍스트 기반(-/ㄴ)으로 변환합니다.

Usage:
    uv run python .claude/skills/jira-weekly-update/scripts/md_to_html.py [input_md_path]

    # 입력 경로 없으면 가장 최근 weekly 파일 사용

Output:
    reports/weekly/weekly_YYYYMMDD.html
"""

import re
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

# =============================================================================
# 1. Configuration
# =============================================================================


def find_project_root() -> Path:
    """pyproject.toml 기준으로 프로젝트 루트를 탐지합니다."""
    current = Path(__file__).resolve().parent
    for parent in [current] + list(current.parents):
        if (parent / "pyproject.toml").exists():
            return parent
    raise RuntimeError("Cannot find project root (pyproject.toml not found)")


PROJECT_ROOT = find_project_root()


# =============================================================================
# 2. Markdown Parser
# =============================================================================


class LineType(Enum):
    """Markdown 라인 유형"""

    H2 = "h2"
    H3 = "h3"
    EPIC = "epic"
    BULLET_L1 = "bullet_l1"
    BULLET_L2 = "bullet_l2"
    BULLET_L3 = "bullet_l3"
    HR = "hr"
    EMPTY = "empty"
    TEXT = "text"


@dataclass
class ParsedLine:
    """파싱된 라인 정보"""

    line_type: LineType
    content: str
    indent_level: int = 0


def detect_line_type(line: str) -> ParsedLine:
    """Markdown 라인의 유형을 감지하고 내용을 추출합니다."""
    stripped = line.rstrip()

    if not stripped:
        return ParsedLine(LineType.EMPTY, "")

    if stripped == "---":
        return ParsedLine(LineType.HR, "")

    if stripped.startswith("## "):
        return ParsedLine(LineType.H2, stripped[3:])

    if stripped.startswith("### "):
        return ParsedLine(LineType.H3, stripped[4:])

    # Epic: 라인 시작이 **로 시작하고 bullet이 아닌 경우
    if stripped.startswith("**") and not stripped.startswith("- "):
        return ParsedLine(LineType.EPIC, stripped)

    # Bullet 감지 (들여쓰기 레벨로 구분)
    indent = len(line) - len(line.lstrip())
    if line.lstrip().startswith("- "):
        content = line.lstrip()[2:]
        if indent == 0:
            return ParsedLine(LineType.BULLET_L1, content, 1)
        elif indent == 2:
            return ParsedLine(LineType.BULLET_L2, content, 2)
        elif indent >= 4:
            return ParsedLine(LineType.BULLET_L3, content, 3)

    return ParsedLine(LineType.TEXT, stripped)


# =============================================================================
# 3. HTML Generator
# =============================================================================

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>주간 업무 보고서 - {date}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto,
                         'Helvetica Neue', Arial, 'Noto Sans KR', sans-serif;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px 40px;
            line-height: 1.7;
            color: #333;
            background-color: #fff;
        }}
        h1 {{
            font-size: 1.75em;
            border-bottom: 2px solid #333;
            padding-bottom: 10px;
            margin-top: 28px;
            margin-bottom: 20px;
        }}
        h2 {{
            font-size: 1.4em;
            color: #444;
            margin-top: 24px;
            margin-bottom: 14px;
        }}
        .epic {{
            font-weight: bold;
            margin: 16px 0 8px 0;
        }}
        .epic a {{
            font-weight: normal;
            margin-left: 8px;
        }}
        .task {{
            margin: 4px 0;
            white-space: pre-wrap;
            font-family: inherit;
        }}
        .task-l1 {{
            margin-left: 0;
        }}
        .task-l2 {{
            margin-left: 0;
            color: #555;
        }}
        .task-l3 {{
            margin-left: 0;
            color: #666;
        }}
        .status-done {{
            color: #28a745;
            font-weight: 500;
        }}
        .status-progress {{
            color: #fd7e14;
            font-weight: 500;
        }}
        a {{
            color: #0366d6;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        hr {{
            border: none;
            border-top: 1px solid #ddd;
            margin: 24px 0;
        }}
    </style>
</head>
<body>
{content}
</body>
</html>
"""


def convert_inline_markdown(text: str) -> str:
    """인라인 Markdown을 HTML로 변환합니다."""
    # 이스케이프된 괄호 처리: \[text\] -> [text]
    text = re.sub(r"\\\[", "[", text)
    text = re.sub(r"\\\]", "]", text)

    # 링크 변환: [text](url) -> <a href="url">text</a>
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)

    # 볼드 변환: **text** -> <strong>text</strong>
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)

    return text


def format_status_badge(text: str) -> str:
    """상태 표시를 스타일링된 span으로 감싸줍니다."""
    text = re.sub(r"\[완료\]", '<span class="status-done">[완료]</span>', text)
    text = re.sub(r"\[진행중\]", '<span class="status-progress">[진행중]</span>', text)
    return text


def get_bullet_prefix(level: int) -> str:
    """레벨에 따른 bullet prefix를 반환합니다."""
    if level == 1:
        return "-"
    elif level == 2:
        return "  ㄴ"
    else:  # level >= 3
        return "    ㄴ"


def convert_md_to_html(md_content: str, date_str: str) -> str:
    """Markdown 내용을 HTML로 변환합니다."""
    lines = md_content.split("\n")
    html_parts = []
    prev_type = None

    for line in lines:
        parsed = detect_line_type(line)

        if parsed.line_type == LineType.EMPTY:
            continue

        elif parsed.line_type == LineType.H2:
            html_parts.append(f"<h1>{convert_inline_markdown(parsed.content)}</h1>")

        elif parsed.line_type == LineType.H3:
            html_parts.append(f"<h2>{convert_inline_markdown(parsed.content)}</h2>")

        elif parsed.line_type == LineType.EPIC:
            # 이전에 Task가 있었으면 Epic 앞에 빈줄 추가
            if prev_type in (LineType.BULLET_L1, LineType.BULLET_L2, LineType.BULLET_L3):
                html_parts.append('<div class="spacer">&nbsp;</div>')
            html_parts.append(f'<div class="epic">{convert_inline_markdown(parsed.content)}</div>')

        elif parsed.line_type in (LineType.BULLET_L1, LineType.BULLET_L2, LineType.BULLET_L3):
            level = parsed.indent_level
            prefix = get_bullet_prefix(level)
            content = format_status_badge(convert_inline_markdown(parsed.content))

            html_parts.append(f'<div class="task task-l{level}">{prefix} {content}</div>')

        elif parsed.line_type == LineType.HR:
            html_parts.append("<hr>")

        else:
            html_parts.append(f"<p>{convert_inline_markdown(parsed.content)}</p>")

        prev_type = parsed.line_type

    content = "\n".join(html_parts)
    return HTML_TEMPLATE.format(date=date_str, content=content)


# =============================================================================
# 4. Main
# =============================================================================


def find_latest_weekly_md(reports_dir: Path) -> Path | None:
    """가장 최근 weekly markdown 파일을 찾습니다."""
    weekly_files = sorted(reports_dir.glob("weekly_*.md"), key=lambda p: p.stem, reverse=True)
    return weekly_files[0] if weekly_files else None


def main():
    """Markdown을 HTML로 변환합니다."""
    # 입력 파일 결정
    if len(sys.argv) > 1:
        input_path = Path(sys.argv[1])
        if not input_path.is_absolute():
            input_path = PROJECT_ROOT / input_path
    else:
        reports_dir = PROJECT_ROOT / "reports" / "weekly"
        input_path = find_latest_weekly_md(reports_dir)
        if not input_path:
            print("No weekly markdown files found in reports/weekly/")
            return

    if not input_path.exists():
        print(f"File not found: {input_path}")
        return

    # 파일명에서 날짜 추출 (weekly_YYYYMMDD.md)
    date_match = re.search(r"weekly_(\d{8})", input_path.stem)
    date_str = date_match.group(1) if date_match else "unknown"

    # 변환
    print(f"Converting: {input_path}")
    md_content = input_path.read_text(encoding="utf-8")
    html_content = convert_md_to_html(md_content, date_str)

    # 저장
    output_path = input_path.with_suffix(".html")
    output_path.write_text(html_content, encoding="utf-8")
    print(f"HTML saved to: {output_path}")


if __name__ == "__main__":
    main()
