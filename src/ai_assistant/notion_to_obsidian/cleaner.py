"""Notion markdown cleaner - removes Notion-specific artifacts."""

import re
from datetime import datetime
from urllib.parse import unquote


class NotionCleaner:
    """Clean Notion export markdown for Obsidian compatibility."""

    # Notion ID pattern: 32자리 hex (8-4-4-4-12 또는 연속)
    NOTION_ID_PATTERN = re.compile(
        r"[a-f0-9]{8}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{12}|"
        r"[a-f0-9]{32}"
    )

    # URL encoded Korean + Notion ID in links
    NOTION_LINK_PATTERN = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

    # Notion metadata patterns
    METADATA_PATTERNS = {
        "tags": re.compile(r"^Tags:\s*(.+)$", re.MULTILINE),
        "created": re.compile(r"^Created:\s*(.+)$", re.MULTILINE),
        "updated": re.compile(r"^Updated:\s*(.+)$", re.MULTILINE),
    }

    def __init__(self):
        self.reset()

    def reset(self):
        """Reset extracted metadata."""
        self.extracted_tags: list[str] = []
        self.extracted_created: datetime | None = None
        self.extracted_updated: datetime | None = None

    def clean(self, content: str) -> str:
        """Main cleaning pipeline."""
        self.reset()

        # 1. Extract and remove metadata
        content = self._extract_metadata(content)

        # 2. Clean Notion links
        content = self._clean_links(content)

        # 3. Clean image links
        content = self._clean_images(content)

        # 4. Remove Notion callout remnants
        content = self._clean_callouts(content)

        # 5. Remove empty lines at start/end
        content = content.strip()

        # 6. Normalize multiple blank lines
        content = re.sub(r"\n{3,}", "\n\n", content)

        return content

    def _extract_metadata(self, content: str) -> str:
        """Extract Tags, Created, Updated from Notion metadata block."""
        # Extract Tags
        tags_match = self.METADATA_PATTERNS["tags"].search(content)
        if tags_match:
            tags_str = tags_match.group(1).strip()
            self.extracted_tags = [t.strip() for t in tags_str.split(",") if t.strip()]
            content = content.replace(tags_match.group(0), "")

        # Extract Created
        created_match = self.METADATA_PATTERNS["created"].search(content)
        if created_match:
            self.extracted_created = self._parse_notion_date(
                created_match.group(1).strip()
            )
            content = content.replace(created_match.group(0), "")

        # Extract Updated
        updated_match = self.METADATA_PATTERNS["updated"].search(content)
        if updated_match:
            self.extracted_updated = self._parse_notion_date(
                updated_match.group(1).strip()
            )
            content = content.replace(updated_match.group(0), "")

        return content

    def _parse_notion_date(self, date_str: str) -> datetime | None:
        """Parse Notion date format: 'January 14, 2022 6:02 PM'."""
        formats = [
            "%B %d, %Y %I:%M %p",  # January 14, 2022 6:02 PM
            "%B %d, %Y",  # January 14, 2022
            "%Y-%m-%d %H:%M:%S",  # 2022-01-14 18:02:00
            "%Y-%m-%d",  # 2022-01-14
            "%Y년 %m월 %d일 %p %I:%M",  # 2022년 1월 14일 오후 6:02
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return None

    def _clean_links(self, content: str) -> str:
        """Clean Notion-style links to Obsidian wiki links."""

        def replace_link(match: re.Match) -> str:
            text = match.group(1)
            url = match.group(2)

            # Skip image links
            if url.startswith("http") and any(
                ext in url.lower() for ext in [".png", ".jpg", ".jpeg", ".gif", ".webp"]
            ):
                return match.group(0)

            # External http links - keep as is
            if url.startswith("http"):
                return match.group(0)

            # URL decode for internal links
            decoded_url = unquote(url)

            # CSV link -> convert to wiki link (database page)
            if decoded_url.endswith(".csv"):
                clean_name = self._extract_clean_name(decoded_url)
                return f"[[{clean_name}]]"

            # MD link -> convert to wiki link
            if decoded_url.endswith(".md"):
                clean_name = self._extract_clean_name(decoded_url)
                return f"[[{clean_name}]]"

            # Other internal links (folder references, etc.)
            if "/" in decoded_url or "%" in url:
                clean_name = self._extract_clean_name(decoded_url)
                if clean_name:
                    return f"[[{clean_name}]]"

            return match.group(0)

        return self.NOTION_LINK_PATTERN.sub(replace_link, content)

    def _clean_images(self, content: str) -> str:
        """Clean image paths for Obsidian."""
        # ![alt](encoded_path.png) -> ![[filename.png]]
        img_pattern = re.compile(r"!\[([^\]]*)\]\(([^)]+\.(png|jpg|jpeg|gif|webp|svg))\)", re.IGNORECASE)

        def replace_image(match: re.Match) -> str:
            alt = match.group(1)
            path = unquote(match.group(2))

            # Extract filename
            filename = path.split("/")[-1]
            # Remove Notion ID from filename
            filename = self.remove_notion_id_from_title(filename)

            # Obsidian image embed
            if alt:
                return f"![[{filename}|{alt}]]"
            return f"![[{filename}]]"

        return img_pattern.sub(replace_image, content)

    def _clean_callouts(self, content: str) -> str:
        """Convert Notion callouts to Obsidian callouts."""
        # Notion: > ℹ️ Info text or > 💡 Tip
        # Obsidian: > [!info] Info text

        callout_icons = {
            "ℹ️": "info",
            "💡": "tip",
            "⚠️": "warning",
            "❗": "danger",
            "📌": "note",
            "✅": "success",
            "❌": "failure",
            "❓": "question",
            "📝": "note",
            "🔥": "important",
        }

        for icon, callout_type in callout_icons.items():
            pattern = re.compile(rf"^>\s*{re.escape(icon)}\s*(.*)$", re.MULTILINE)
            content = pattern.sub(rf"> [!{callout_type}] \1", content)

        return content

    def _extract_clean_name(self, path: str) -> str:
        """Extract clean name from Notion path."""
        from pathlib import Path

        # URL decode
        path = unquote(path)

        # Get filename without extension
        name = Path(path).stem

        # Remove Notion ID suffix (32 hex chars)
        name = self.remove_notion_id_from_title(name)

        return name.strip()

    def remove_notion_id_from_title(self, title: str) -> str:
        """Remove Notion ID suffix from title."""
        # "trino 사용하기 9b305ba1e3e582c9aa2f8121ac069c86" -> "trino 사용하기"
        # Also handles: "title 9b305ba1e3e582c9aa2f8121ac069c86.md"
        cleaned = re.sub(r"\s+[a-f0-9]{32}(?:\.\w+)?$", "", title)
        return cleaned.strip()
