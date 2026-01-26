"""Data models for Notion to Obsidian conversion."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class NotionPage:
    """Represents a Notion page exported as markdown."""

    source_path: Path
    title: str
    content: str
    notion_id: str = ""
    tags: list[str] = field(default_factory=list)
    created: datetime | None = None
    updated: datetime | None = None
    parent_folder: str = ""

    @property
    def clean_title(self) -> str:
        """Remove Notion ID hash from title."""
        # "trino 사용하기 9b305ba1e3e582c9aa2f8121ac069c86" -> "trino 사용하기"
        parts = self.title.rsplit(" ", 1)
        if len(parts) == 2 and len(parts[1]) == 32 and parts[1].isalnum():
            return parts[0]
        return self.title


@dataclass
class ObsidianNote:
    """Represents an Obsidian-compatible markdown note."""

    title: str
    content: str
    folder: str = ""
    tags: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)
    created: datetime | None = None
    updated: datetime | None = None
    source_notion_id: str = ""

    def to_markdown(self) -> str:
        """Generate Obsidian markdown with YAML frontmatter."""
        lines = ["---"]

        # Title as alias if different from filename
        if self.aliases:
            lines.append(f"aliases: {self.aliases}")

        # Tags
        if self.tags:
            lines.append("tags:")
            for tag in self.tags:
                # Obsidian tags: 공백 -> _, 특수문자 제거
                clean_tag = tag.replace(" ", "_").replace("/", "_")
                lines.append(f"  - {clean_tag}")

        # Dates
        if self.created:
            lines.append(f"created: {self.created.strftime('%Y-%m-%d')}")
        if self.updated:
            lines.append(f"updated: {self.updated.strftime('%Y-%m-%d')}")

        # Source tracking
        if self.source_notion_id:
            lines.append(f"notion_id: {self.source_notion_id}")

        lines.append("---")
        lines.append("")
        lines.append(self.content)

        return "\n".join(lines)

    @property
    def filename(self) -> str:
        """Generate safe filename for Obsidian."""
        # 파일명에 사용 불가한 문자 제거
        safe_title = self.title
        for char in ["/", "\\", ":", "*", "?", '"', "<", ">", "|", "#"]:
            safe_title = safe_title.replace(char, "_")
        return f"{safe_title}.md"

    @property
    def relative_path(self) -> Path:
        """Get relative path including folder."""
        if self.folder:
            return Path(self.folder) / self.filename
        return Path(self.filename)
