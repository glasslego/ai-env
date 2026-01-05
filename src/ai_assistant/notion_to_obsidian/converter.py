"""Main converter: Notion export -> Obsidian vault."""

import logging
import re
import shutil
from pathlib import Path
from urllib.parse import unquote

from .cleaner import NotionCleaner
from .models import NotionPage, ObsidianNote

logger = logging.getLogger(__name__)


class NotionToObsidianConverter:
    """Convert Notion export directory to Obsidian vault structure."""

    def __init__(
        self,
        source_dir: str | Path,
        target_dir: str | Path,
        *,
        skip_csv: bool = True,
        skip_html: bool = True,
        copy_attachments: bool = True,
        flatten_structure: bool = False,
        dry_run: bool = False,
    ):
        self.source_dir = Path(source_dir)
        self.target_dir = Path(target_dir)
        self.skip_csv = skip_csv
        self.skip_html = skip_html
        self.copy_attachments = copy_attachments
        self.flatten_structure = flatten_structure
        self.dry_run = dry_run
        self.cleaner = NotionCleaner()

        # Statistics
        self.stats = {
            "pages_converted": 0,
            "pages_skipped": 0,
            "attachments_copied": 0,
            "errors": [],
        }

        # Track all pages for link resolution
        self._page_map: dict[str, str] = {}  # notion_id -> clean_title

    def convert(self) -> dict:
        """Run the conversion process."""
        logger.info(f"Converting Notion export: {self.source_dir}")
        logger.info(f"Target Obsidian vault: {self.target_dir}")

        if not self.source_dir.exists():
            raise FileNotFoundError(f"Source directory not found: {self.source_dir}")

        if not self.dry_run:
            self.target_dir.mkdir(parents=True, exist_ok=True)

        # First pass: build page map
        self._build_page_map()

        # Second pass: process all markdown files
        for md_file in self.source_dir.rglob("*.md"):
            try:
                self._process_file(md_file)
            except Exception as e:
                logger.error(f"Error processing {md_file}: {e}")
                self.stats["errors"].append({"file": str(md_file), "error": str(e)})

        # Copy attachments (images, pdfs, etc.)
        if self.copy_attachments:
            self._copy_attachments()

        logger.info(f"Conversion complete: {self.stats}")
        return self.stats

    def _build_page_map(self) -> None:
        """Build mapping from Notion IDs to clean titles."""
        for md_file in self.source_dir.rglob("*.md"):
            # Extract Notion ID from filename
            id_match = re.search(r"([a-f0-9]{32})\.md$", md_file.name)
            if id_match:
                notion_id = id_match.group(1)
                # Get clean title
                raw_title = md_file.stem
                clean_title = self.cleaner.remove_notion_id_from_title(raw_title)
                self._page_map[notion_id] = clean_title

    def _process_file(self, md_file: Path) -> None:
        """Process a single markdown file."""
        # Read content
        content = md_file.read_text(encoding="utf-8")

        # Parse Notion page
        notion_page = self._parse_notion_page(md_file, content)

        # Skip index/navigation pages
        if self._is_index_page(content):
            logger.debug(f"Skipping index page: {md_file.name}")
            self.stats["pages_skipped"] += 1
            return

        # Skip very short pages (likely empty or navigation only)
        content_lines = [l for l in content.split("\n") if l.strip() and not l.startswith("#")]
        if len(content_lines) < 2:
            logger.debug(f"Skipping empty page: {md_file.name}")
            self.stats["pages_skipped"] += 1
            return

        # Convert to Obsidian note
        obsidian_note = self._convert_to_obsidian(notion_page)

        # Write to target
        if not self.dry_run:
            self._write_note(obsidian_note)

        self.stats["pages_converted"] += 1
        logger.info(f"Converted: {notion_page.title} -> {obsidian_note.relative_path}")

    def _parse_notion_page(self, file_path: Path, content: str) -> NotionPage:
        """Parse Notion markdown file into NotionPage model."""
        # Extract title from first H1 or filename
        title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if title_match:
            raw_title = title_match.group(1).strip()
        else:
            raw_title = file_path.stem

        # Clean title (remove Notion ID)
        clean_title = self.cleaner.remove_notion_id_from_title(raw_title)

        # Extract Notion ID from filename
        notion_id = ""
        id_match = re.search(r"([a-f0-9]{32})\.md$", file_path.name)
        if id_match:
            notion_id = id_match.group(1)

        # Get relative folder path
        relative_path = file_path.relative_to(self.source_dir)
        parent_folder = str(relative_path.parent) if relative_path.parent != Path(".") else ""

        # Clean parent folder name (remove Notion IDs)
        if parent_folder:
            parent_folder = self._clean_folder_name(parent_folder)

        return NotionPage(
            source_path=file_path,
            title=clean_title,
            content=content,
            notion_id=notion_id,
            parent_folder=parent_folder,
        )

    def _clean_folder_name(self, folder: str) -> str:
        """Remove Notion IDs from folder path."""
        parts = folder.split("/")
        clean_parts = []
        for part in parts:
            # URL decode
            part = unquote(part)
            # Remove Notion ID suffix
            clean = re.sub(r"\s+[a-f0-9]{32}$", "", part)
            clean = re.sub(r"\s+[a-f0-9-]{20,}$", "", clean)
            clean_parts.append(clean.strip())
        return "/".join(clean_parts)

    def _is_index_page(self, content: str) -> bool:
        """Check if page is just an index (links to CSV files)."""
        lines = [l for l in content.strip().split("\n") if l.strip()]
        if len(lines) < 2:
            return True

        # Count CSV links
        csv_link_count = len(re.findall(r"\]\([^)]+\.csv\)", content))
        total_links = len(re.findall(r"\]\([^)]+\)", content))

        # If most links are CSV files, it's an index page
        if total_links > 0 and csv_link_count / total_links > 0.7:
            return True

        return False

    def _convert_to_obsidian(self, notion_page: NotionPage) -> ObsidianNote:
        """Convert NotionPage to ObsidianNote."""
        # Clean content
        clean_content = self.cleaner.clean(notion_page.content)

        # Remove the H1 title (will be filename)
        clean_content = re.sub(r"^#\s+.+\n+", "", clean_content)

        # Build tags from folder hierarchy + extracted tags
        tags = self.cleaner.extracted_tags.copy()
        if notion_page.parent_folder:
            # Add folder hierarchy as tags
            folder_parts = notion_page.parent_folder.split("/")
            for part in folder_parts:
                tag = part.replace(" ", "_").replace("&", "and")
                tag = re.sub(r"[^\w가-힣_-]", "", tag)
                if tag and tag not in tags:
                    tags.append(tag)

        # Determine folder
        folder = "" if self.flatten_structure else notion_page.parent_folder

        return ObsidianNote(
            title=notion_page.title,
            content=clean_content,
            folder=folder,
            tags=tags,
            created=self.cleaner.extracted_created,
            updated=self.cleaner.extracted_updated,
            source_notion_id=notion_page.notion_id,
        )

    def _write_note(self, note: ObsidianNote) -> None:
        """Write ObsidianNote to target directory."""
        target_path = self.target_dir / note.relative_path
        target_path.parent.mkdir(parents=True, exist_ok=True)

        markdown = note.to_markdown()
        target_path.write_text(markdown, encoding="utf-8")

    def _copy_attachments(self) -> None:
        """Copy non-markdown files (images, PDFs) to attachments folder."""
        attachment_extensions = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".webp", ".svg"}
        attachments_dir = self.target_dir / "attachments"

        for file in self.source_dir.rglob("*"):
            if file.is_file() and file.suffix.lower() in attachment_extensions:
                # Clean filename
                clean_name = self.cleaner.remove_notion_id_from_title(file.stem)
                clean_name = f"{clean_name}{file.suffix}"

                if not self.dry_run:
                    attachments_dir.mkdir(parents=True, exist_ok=True)
                    target = attachments_dir / clean_name

                    # Handle duplicates
                    counter = 1
                    while target.exists():
                        name_part = clean_name.rsplit(".", 1)[0]
                        ext_part = clean_name.rsplit(".", 1)[1]
                        target = attachments_dir / f"{name_part}_{counter}.{ext_part}"
                        counter += 1

                    shutil.copy2(file, target)
                    self.stats["attachments_copied"] += 1
                    logger.debug(f"Copied attachment: {file.name} -> {target.name}")
