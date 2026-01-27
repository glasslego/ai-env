#!/usr/bin/env python3
"""
Confluence Wiki Client for Kakao On-Premise Wiki

카카오 사내 온프레미스 Confluence 위키 REST API 클라이언트.
Personal Access Token 인증 사용.

Usage:
    python wiki_client.py read --page-id 815966617
    python wiki_client.py read --url "https://wiki.daumkakao.com/spaces/KCAI/pages/123/Title"
    python wiki_client.py search --space KCAI --title "Products"
    python wiki_client.py children --page-id 815966617
    python wiki_client.py create --space KCAI --title "New Page" --parent-id 815966617
    python wiki_client.py update --page-id 815966617 --body-file content.md
    python wiki_client.py delete --page-id 815966617
    python wiki_client.py parse-url "https://wiki.../pages/123/Title"

Environment:
    WIKI_BASE_URL: Wiki base URL (e.g., https://wiki.daumkakao.com)
    WIKI_TOKEN: Personal Access Token
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

# html2text for storage -> markdown conversion
try:
    import html2text

    HAS_HTML2TEXT = True
except ImportError:
    HAS_HTML2TEXT = False

# mistune for markdown -> storage conversion
try:
    import mistune

    HAS_MISTUNE = True
except ImportError:
    HAS_MISTUNE = False


def find_project_root() -> Path:
    """Find project root by looking for pyproject.toml"""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return Path.cwd()


class WikiClient:
    """Confluence REST API Client for on-premise wiki"""

    def __init__(self, base_url: str, token: str, dry_run: bool = False, timeout: float = 30.0):
        """
        Initialize WikiClient.

        Args:
            base_url: Wiki base URL (e.g., https://wiki.daumkakao.com)
            token: Personal Access Token
            dry_run: If True, don't make write operations
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.dry_run = dry_run
        self.timeout = timeout

        self._client = httpx.Client(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=timeout,
        )

    def close(self):
        """Close the HTTP client"""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    # =========================================================================
    # URL Utilities
    # =========================================================================

    @staticmethod
    def extract_page_id_from_url(url: str) -> str | None:
        """
        Extract page ID from Confluence URL.

        Supports formats:
        - https://wiki.../spaces/SPACE/pages/123456/Page+Title
        - https://wiki.../pages/viewpage.action?pageId=123456
        - https://wiki.../display/SPACE/Page+Title (no ID, returns None)

        Args:
            url: Confluence page URL

        Returns:
            Page ID string or None if not found
        """
        # Pattern 1: /pages/{pageId}/{title}
        match = re.search(r"/pages/(\d+)/", url)
        if match:
            return match.group(1)

        # Pattern 2: pageId=123456
        match = re.search(r"pageId=(\d+)", url)
        if match:
            return match.group(1)

        # Pattern 3: /pages/{pageId} (no title)
        match = re.search(r"/pages/(\d+)$", url)
        if match:
            return match.group(1)

        return None

    def get_page_web_url(self, page_id: str, space_key: str = None, title: str = None) -> str:
        """
        Build web URL for a page.

        Note: On-premise wiki may require full path with title.

        Args:
            page_id: Page ID
            space_key: Optional space key
            title: Optional page title

        Returns:
            Web URL for the page
        """
        if space_key and title:
            # URL-encode the title
            encoded_title = title.replace(" ", "+")
            return f"{self.base_url}/spaces/{space_key}/pages/{page_id}/{encoded_title}"
        return f"{self.base_url}/pages/viewpage.action?pageId={page_id}"

    # =========================================================================
    # CRUD Operations
    # =========================================================================

    def get_page(self, page_id: str, expand: list[str] | None = None) -> dict:
        """
        Get page by ID.

        Args:
            page_id: Page ID
            expand: Fields to expand (e.g., ['body.storage', 'version', 'ancestors'])

        Returns:
            Page data dict

        Raises:
            httpx.HTTPStatusError: On API errors
        """
        params = {}
        if expand:
            params["expand"] = ",".join(expand)

        response = self._client.get(f"/rest/api/content/{page_id}", params=params)
        response.raise_for_status()
        return response.json()

    def create_page(
        self, space_key: str, title: str, body: str, parent_id: str | None = None
    ) -> dict:
        """
        Create a new page.

        Args:
            space_key: Space key (e.g., 'KCAI')
            title: Page title
            body: Page body in storage format (XHTML)
            parent_id: Optional parent page ID

        Returns:
            Created page data

        Raises:
            httpx.HTTPStatusError: On API errors
        """
        data = {
            "type": "page",
            "title": title,
            "space": {"key": space_key},
            "body": {"storage": {"value": body, "representation": "storage"}},
        }

        if parent_id:
            data["ancestors"] = [{"id": parent_id}]

        if self.dry_run:
            print("[DRY-RUN] Would create page:")
            print(f"  Space: {space_key}")
            print(f"  Title: {title}")
            if parent_id:
                print(f"  Parent: {parent_id}")
            print(f"  Body length: {len(body)} chars")
            return {"id": "DRY-RUN", "title": title, "_dry_run": True}

        response = self._client.post("/rest/api/content/", json=data)
        response.raise_for_status()
        return response.json()

    def update_page(self, page_id: str, title: str, body: str, version: int) -> dict:
        """
        Update an existing page.

        Args:
            page_id: Page ID
            title: Page title
            body: Page body in storage format (XHTML)
            version: Current version number (will be incremented)

        Returns:
            Updated page data

        Raises:
            httpx.HTTPStatusError: On API errors
        """
        data = {
            "id": page_id,
            "type": "page",
            "title": title,
            "body": {"storage": {"value": body, "representation": "storage"}},
            "version": {"number": version + 1},
        }

        if self.dry_run:
            print("[DRY-RUN] Would update page:")
            print(f"  ID: {page_id}")
            print(f"  Title: {title}")
            print(f"  Version: {version} -> {version + 1}")
            print(f"  Body length: {len(body)} chars")
            return {"id": page_id, "title": title, "_dry_run": True}

        response = self._client.put(f"/rest/api/content/{page_id}", json=data)
        response.raise_for_status()
        return response.json()

    def delete_page(self, page_id: str) -> bool:
        """
        Delete a page.

        Args:
            page_id: Page ID

        Returns:
            True if deleted successfully

        Raises:
            httpx.HTTPStatusError: On API errors
        """
        if self.dry_run:
            print(f"[DRY-RUN] Would delete page: {page_id}")
            return True

        response = self._client.delete(f"/rest/api/content/{page_id}")
        response.raise_for_status()
        return True

    # =========================================================================
    # Search and Navigation
    # =========================================================================

    def search_by_title(self, space_key: str, title: str, limit: int = 25) -> list[dict]:
        """
        Search pages by title in a space.

        Args:
            space_key: Space key
            title: Title to search (partial match)
            limit: Max results

        Returns:
            List of matching pages
        """
        params = {"spaceKey": space_key, "title": title, "limit": limit, "expand": "version"}

        response = self._client.get("/rest/api/content", params=params)
        response.raise_for_status()
        return response.json().get("results", [])

    def get_children(self, page_id: str, limit: int = 25) -> list[dict]:
        """
        Get child pages of a page.

        Args:
            page_id: Parent page ID
            limit: Max results

        Returns:
            List of child pages
        """
        params = {"limit": limit, "expand": "version"}

        response = self._client.get(f"/rest/api/content/{page_id}/child/page", params=params)
        response.raise_for_status()
        return response.json().get("results", [])

    def scan_space(self, space_key: str, limit: int = 25, cursor: str | None = None) -> dict:
        """
        Scan all pages in a space.

        Uses the optimized scan endpoint (Confluence 7.18+).

        Args:
            space_key: Space key
            limit: Max results per page
            cursor: Pagination cursor

        Returns:
            Dict with 'results' and pagination info
        """
        params = {"spaceKey": space_key, "limit": limit}
        if cursor:
            params["cursor"] = cursor

        response = self._client.get("/rest/api/content/scan", params=params)
        response.raise_for_status()
        return response.json()

    def search_cql(self, cql: str, limit: int = 25, start: int = 0) -> dict:
        """
        Search using Confluence Query Language (CQL).

        CQL is more flexible than title search.
        Examples:
        - space = KCAI and title ~ "Products"
        - space = KCAI and text ~ "추천"
        - parent = 815966617

        Args:
            cql: CQL query string
            limit: Max results
            start: Start index for pagination

        Returns:
            Dict with 'results' and pagination info
        """
        params = {"cql": cql, "limit": limit, "start": start, "expand": "version,space"}

        response = self._client.get("/rest/api/content/search", params=params)
        response.raise_for_status()
        return response.json()

    # =========================================================================
    # Labels
    # =========================================================================

    def get_labels(self, page_id: str) -> list[dict]:
        """
        Get labels for a page.

        Args:
            page_id: Page ID

        Returns:
            List of label objects
        """
        response = self._client.get(f"/rest/api/content/{page_id}/label")
        response.raise_for_status()
        return response.json().get("results", [])

    def add_label(self, page_id: str, label: str) -> dict:
        """
        Add a label to a page.

        Args:
            page_id: Page ID
            label: Label name

        Returns:
            Added label object
        """
        if self.dry_run:
            print(f"[DRY-RUN] Would add label '{label}' to page {page_id}")
            return {"name": label, "_dry_run": True}

        data = [{"name": label}]
        response = self._client.post(f"/rest/api/content/{page_id}/label", json=data)
        response.raise_for_status()
        return response.json()

    def remove_label(self, page_id: str, label: str) -> bool:
        """
        Remove a label from a page.

        Args:
            page_id: Page ID
            label: Label name

        Returns:
            True if successful
        """
        if self.dry_run:
            print(f"[DRY-RUN] Would remove label '{label}' from page {page_id}")
            return True

        response = self._client.delete(f"/rest/api/content/{page_id}/label/{label}")
        response.raise_for_status()
        return True

    # =========================================================================
    # Version History
    # =========================================================================

    def get_history(self, page_id: str, limit: int = 10) -> list[dict]:
        """
        Get version history for a page.

        Args:
            page_id: Page ID
            limit: Max versions to return

        Returns:
            List of version objects
        """
        params = {"expand": "lastUpdated,previousVersion", "limit": limit}
        response = self._client.get(f"/rest/api/content/{page_id}/history", params=params)
        response.raise_for_status()
        return response.json()

    def get_version(self, page_id: str, version: int) -> dict:
        """
        Get a specific version of a page.

        Args:
            page_id: Page ID
            version: Version number

        Returns:
            Page data for that version
        """
        response = self._client.get(
            f"/rest/api/content/{page_id}",
            params={"status": "historical", "version": version, "expand": "body.storage,version"},
        )
        response.raise_for_status()
        return response.json()

    # =========================================================================
    # Attachments
    # =========================================================================

    def get_attachments(self, page_id: str, limit: int = 25) -> list[dict]:
        """
        Get attachments for a page.

        Args:
            page_id: Page ID
            limit: Max results

        Returns:
            List of attachment objects
        """
        params = {"limit": limit, "expand": "version"}
        response = self._client.get(f"/rest/api/content/{page_id}/child/attachment", params=params)
        response.raise_for_status()
        return response.json().get("results", [])

    def upload_attachment(self, page_id: str, file_path: str, comment: str = "") -> dict:
        """
        Upload an attachment to a page.

        Args:
            page_id: Page ID
            file_path: Path to the file to upload
            comment: Optional comment

        Returns:
            Uploaded attachment object
        """
        from pathlib import Path as FilePath

        file_path = FilePath(file_path)

        if self.dry_run:
            print(f"[DRY-RUN] Would upload '{file_path.name}' to page {page_id}")
            return {"title": file_path.name, "_dry_run": True}

        with open(file_path, "rb") as f:
            # Need to use multipart/form-data for file upload
            files = {"file": (file_path.name, f)}
            headers = {
                "Authorization": f"Bearer {self.token}",
                "X-Atlassian-Token": "nocheck",
            }
            if comment:
                headers["X-Atlassian-Comment"] = comment

            # Use a separate request without JSON content-type
            response = httpx.post(
                f"{self.base_url}/rest/api/content/{page_id}/child/attachment",
                files=files,
                headers=headers,
                timeout=self.timeout,
            )
        response.raise_for_status()
        return response.json()

    def download_attachment(self, page_id: str, attachment_id: str, output_path: str) -> str:
        """
        Download an attachment.

        Args:
            page_id: Page ID
            attachment_id: Attachment ID
            output_path: Path to save the file

        Returns:
            Path to downloaded file
        """
        from pathlib import Path as FilePath

        # Get attachment info to get download link
        response = self._client.get(f"/rest/api/content/{attachment_id}")
        response.raise_for_status()
        attachment = response.json()

        download_link = attachment.get("_links", {}).get("download")
        if not download_link:
            raise ValueError("No download link found for attachment")

        # Download the file
        response = self._client.get(download_link)
        response.raise_for_status()

        output_path = FilePath(output_path)
        output_path.write_bytes(response.content)
        return str(output_path)

    # =========================================================================
    # Comments
    # =========================================================================

    def get_comments(self, page_id: str, limit: int = 25) -> list[dict]:
        """
        Get comments for a page.

        Args:
            page_id: Page ID
            limit: Max results

        Returns:
            List of comment objects
        """
        params = {"limit": limit, "expand": "body.view,version"}
        response = self._client.get(f"/rest/api/content/{page_id}/child/comment", params=params)
        response.raise_for_status()
        return response.json().get("results", [])

    def add_comment(self, page_id: str, body: str) -> dict:
        """
        Add a comment to a page.

        Args:
            page_id: Page ID
            body: Comment body (HTML or plain text)

        Returns:
            Created comment object
        """
        if self.dry_run:
            print(f"[DRY-RUN] Would add comment to page {page_id}")
            print(f"  Body: {body[:100]}...")
            return {"id": "DRY-RUN", "_dry_run": True}

        data = {
            "type": "comment",
            "container": {"id": page_id, "type": "page"},
            "body": {"storage": {"value": body, "representation": "storage"}},
        }
        response = self._client.post("/rest/api/content", json=data)
        response.raise_for_status()
        return response.json()

    # =========================================================================
    # Page Copy and Move
    # =========================================================================

    def copy_page(
        self,
        page_id: str,
        destination_page_id: str,
        title: str | None = None,
        copy_attachments: bool = True,
    ) -> dict:
        """
        Copy a page to a new location.

        Args:
            page_id: Source page ID
            destination_page_id: Destination parent page ID
            title: New title (optional, uses original + "Copy" if not provided)
            copy_attachments: Whether to copy attachments

        Returns:
            Copied page object
        """
        if self.dry_run:
            print(f"[DRY-RUN] Would copy page {page_id} to under {destination_page_id}")
            if title:
                print(f"  New title: {title}")
            return {"id": "DRY-RUN", "_dry_run": True}

        data = {
            "copyAttachments": copy_attachments,
            "destination": {"type": "parent_page", "value": destination_page_id},
        }
        if title:
            data["pageTitle"] = title

        response = self._client.post(f"/rest/api/content/{page_id}/copy", json=data)
        response.raise_for_status()
        return response.json()

    def move_page(self, page_id: str, target_page_id: str, position: str = "append") -> dict:
        """
        Move a page to a new location.

        Args:
            page_id: Page to move
            target_page_id: Target page ID
            position: Position relative to target ('append', 'before', 'after')

        Returns:
            Moved page object
        """
        if self.dry_run:
            print(f"[DRY-RUN] Would move page {page_id} to {position} {target_page_id}")
            return {"id": page_id, "_dry_run": True}

        response = self._client.put(f"/rest/api/content/{page_id}/move/{position}/{target_page_id}")
        response.raise_for_status()
        return response.json()

    # =========================================================================
    # Watchers and Space Info
    # =========================================================================

    def get_watchers(self, page_id: str) -> list[dict]:
        """
        Get watchers (people watching) a page.

        Args:
            page_id: Page ID

        Returns:
            List of watcher objects
        """
        response = self._client.get(f"/rest/api/content/{page_id}/notification/child-pages")
        response.raise_for_status()
        return response.json().get("results", [])

    def get_space(self, space_key: str) -> dict:
        """
        Get space information.

        Args:
            space_key: Space key (e.g., 'KCAI')

        Returns:
            Space object with metadata
        """
        params = {"expand": "description.plain,homepage"}
        response = self._client.get(f"/rest/api/space/{space_key}", params=params)
        response.raise_for_status()
        return response.json()

    def get_space_homepage(self, space_key: str) -> str:
        """
        Get the homepage ID for a space.

        Args:
            space_key: Space key

        Returns:
            Homepage page ID
        """
        space = self.get_space(space_key)
        homepage = space.get("homepage", {})
        return homepage.get("id")

    # =========================================================================
    # PlantUML Conversion
    # =========================================================================

    @staticmethod
    def plantuml_to_macro(plantuml_code: str) -> str:
        """
        Convert PlantUML code to Confluence structured-macro format.

        Args:
            plantuml_code: PlantUML code (with or without @startuml/@enduml)

        Returns:
            Confluence storage format XML for PlantUML macro
        """
        # Ensure code has @startuml/@enduml tags
        code = plantuml_code.strip()
        if not code.startswith("@startuml"):
            code = "@startuml\n" + code
        if not code.endswith("@enduml"):
            code = code + "\n@enduml"

        return (
            '<ac:structured-macro ac:name="plantuml">'
            "<ac:plain-text-body><![CDATA["
            f"{code}"
            "]]></ac:plain-text-body>"
            "</ac:structured-macro>"
        )

    @staticmethod
    def macro_to_plantuml(macro_html: str) -> str:
        """
        Extract PlantUML code from Confluence macro.

        Args:
            macro_html: Confluence storage format containing PlantUML macro

        Returns:
            PlantUML code extracted from CDATA section
        """
        # Pattern to match PlantUML macro and extract CDATA content
        pattern = r'<ac:structured-macro[^>]*ac:name="plantuml"[^>]*>.*?<ac:plain-text-body><!\[CDATA\[(.*?)\]\]></ac:plain-text-body>.*?</ac:structured-macro>'
        match = re.search(pattern, macro_html, re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""

    # =========================================================================
    # Markdown Conversion
    # =========================================================================

    def storage_to_markdown(self, storage_html: str) -> str:
        """
        Convert Confluence storage format to Markdown.

        Handles special macros:
        - PlantUML macros are converted to ```plantuml code blocks

        Args:
            storage_html: HTML in Confluence storage format

        Returns:
            Markdown text
        """
        if not HAS_HTML2TEXT:
            raise ImportError(
                "html2text is required for Markdown conversion. Install with: pip install html2text"
            )

        # Pre-process: Extract PlantUML macros and replace with placeholders
        plantuml_blocks = []
        plantuml_pattern = r'<ac:structured-macro[^>]*ac:name="plantuml"[^>]*>.*?<ac:plain-text-body><!\[CDATA\[(.*?)\]\]></ac:plain-text-body>.*?</ac:structured-macro>'

        def replace_macro(match):
            plantuml_code = match.group(1).strip()
            placeholder = f"<!--PLANTUML_{len(plantuml_blocks)}-->"
            plantuml_blocks.append(plantuml_code)
            return placeholder

        processed_html = re.sub(plantuml_pattern, replace_macro, storage_html, flags=re.DOTALL)

        # Convert HTML to Markdown
        h = html2text.HTML2Text()
        h.body_width = 0  # No line wrapping
        h.ignore_links = False
        h.ignore_images = False
        h.ignore_emphasis = False

        markdown = h.handle(processed_html)

        # Post-process: Replace placeholders with Markdown PlantUML code blocks
        for i, plantuml_code in enumerate(plantuml_blocks):
            placeholder = f"<!--PLANTUML_{i}-->"
            markdown_block = f"```plantuml\n{plantuml_code}\n```"
            markdown = markdown.replace(placeholder, markdown_block)

        return markdown

    def markdown_to_storage(self, markdown: str) -> str:
        """
        Convert Markdown to Confluence storage format.

        Handles special blocks:
        - ```plantuml code blocks are converted to Confluence PlantUML macros

        Args:
            markdown: Markdown text

        Returns:
            HTML in Confluence storage format
        """
        if not HAS_MISTUNE:
            raise ImportError(
                "mistune is required for Markdown conversion. Install with: pip install mistune"
            )

        # Pre-process: Extract PlantUML blocks and replace with placeholders
        plantuml_blocks = []
        plantuml_pattern = r"```plantuml\s*\n(.*?)```"

        def replace_plantuml(match):
            plantuml_code = match.group(1).strip()
            placeholder = f"<!--PLANTUML_{len(plantuml_blocks)}-->"
            plantuml_blocks.append(plantuml_code)
            return placeholder

        processed_markdown = re.sub(plantuml_pattern, replace_plantuml, markdown, flags=re.DOTALL)

        # Convert markdown to HTML
        html = mistune.html(processed_markdown)

        # Post-process: Replace placeholders with Confluence PlantUML macros
        for i, plantuml_code in enumerate(plantuml_blocks):
            placeholder = f"<!--PLANTUML_{i}-->"
            macro = self.plantuml_to_macro(plantuml_code)
            # Handle various wrapping scenarios
            html = html.replace(f"<p>{placeholder}</p>", macro)
            html = html.replace(placeholder, macro)

        return html

    # =========================================================================
    # Convenience Methods
    # =========================================================================

    def get_page_as_markdown(self, page_id: str) -> tuple[dict, str]:
        """
        Get page and convert body to Markdown.

        Args:
            page_id: Page ID

        Returns:
            Tuple of (page_data, markdown_body)
        """
        page = self.get_page(page_id, expand=["body.storage", "version"])
        storage_body = page.get("body", {}).get("storage", {}).get("value", "")
        markdown_body = self.storage_to_markdown(storage_body)
        return page, markdown_body

    def update_page_from_markdown(
        self, page_id: str, markdown_body: str, title: str | None = None
    ) -> dict:
        """
        Update page from Markdown content.

        Args:
            page_id: Page ID
            markdown_body: Markdown content
            title: Optional new title (uses existing if not provided)

        Returns:
            Updated page data
        """
        # Get current page for version and title
        current = self.get_page(page_id, expand=["version"])
        current_title = title or current["title"]
        current_version = current["version"]["number"]

        # Convert markdown to storage format
        storage_body = self.markdown_to_storage(markdown_body)

        return self.update_page(
            page_id=page_id, title=current_title, body=storage_body, version=current_version
        )


# =============================================================================
# CLI Interface
# =============================================================================


def main():
    """CLI entry point"""
    # Load environment
    project_root = find_project_root()
    load_dotenv(project_root / ".env")

    base_url = os.getenv("WIKI_BASE_URL")
    token = os.getenv("WIKI_TOKEN")

    if not base_url or not token:
        print("Error: WIKI_BASE_URL and WIKI_TOKEN must be set in .env", file=sys.stderr)
        sys.exit(1)

    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Confluence Wiki Client", formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview changes without making them"
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # read command
    read_parser = subparsers.add_parser("read", help="Read a page")
    read_group = read_parser.add_mutually_exclusive_group(required=True)
    read_group.add_argument("--page-id", help="Page ID")
    read_group.add_argument("--url", help="Page URL")
    read_parser.add_argument("--format", choices=["json", "markdown", "storage"], default="json")

    # create command
    create_parser = subparsers.add_parser("create", help="Create a page")
    create_parser.add_argument("--space", required=True, help="Space key")
    create_parser.add_argument("--title", required=True, help="Page title")
    create_parser.add_argument("--parent-id", help="Parent page ID")
    create_parser.add_argument("--body", help="Page body (storage format)")
    create_parser.add_argument("--body-file", help="File containing page body (markdown)")

    # update command
    update_parser = subparsers.add_parser("update", help="Update a page")
    update_parser.add_argument("--page-id", required=True, help="Page ID")
    update_parser.add_argument("--title", help="New title")
    update_parser.add_argument("--body-file", help="File containing new body (markdown)")

    # delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a page")
    delete_parser.add_argument("--page-id", required=True, help="Page ID")

    # search command
    search_parser = subparsers.add_parser("search", help="Search pages by title")
    search_parser.add_argument("--space", required=True, help="Space key")
    search_parser.add_argument("--title", required=True, help="Title to search")
    search_parser.add_argument("--limit", type=int, default=25)

    # cql command (CQL search)
    cql_parser = subparsers.add_parser("cql", help="Search using CQL (Confluence Query Language)")
    cql_parser.add_argument(
        "query", help="CQL query (e.g., 'space = KCAI and title ~ \"Products\"')"
    )
    cql_parser.add_argument("--limit", type=int, default=25)

    # children command
    children_parser = subparsers.add_parser("children", help="List child pages")
    children_parser.add_argument("--page-id", required=True, help="Parent page ID")
    children_parser.add_argument("--limit", type=int, default=25)

    # ancestors command
    ancestors_parser = subparsers.add_parser("ancestors", help="Show parent pages (breadcrumb)")
    ancestors_parser.add_argument("--page-id", required=True, help="Page ID")

    # labels command
    labels_parser = subparsers.add_parser("labels", help="Manage page labels")
    labels_parser.add_argument("--page-id", required=True, help="Page ID")
    labels_parser.add_argument("--add", help="Add a label")
    labels_parser.add_argument("--remove", help="Remove a label")

    # history command
    history_parser = subparsers.add_parser("history", help="Show page version history")
    history_parser.add_argument("--page-id", required=True, help="Page ID")
    history_parser.add_argument("--version", type=int, help="Get specific version content")
    history_parser.add_argument("--limit", type=int, default=10)

    # attachments command
    attachments_parser = subparsers.add_parser("attachments", help="Manage page attachments")
    attachments_parser.add_argument("--page-id", required=True, help="Page ID")
    attachments_parser.add_argument("--upload", help="File path to upload")
    attachments_parser.add_argument("--download", help="Attachment ID to download")
    attachments_parser.add_argument("--output", help="Output path for download")

    # comments command
    comments_parser = subparsers.add_parser("comments", help="Manage page comments")
    comments_parser.add_argument("--page-id", required=True, help="Page ID")
    comments_parser.add_argument("--add", help="Add a comment (text)")

    # copy command
    copy_parser = subparsers.add_parser("copy", help="Copy a page")
    copy_parser.add_argument("--page-id", required=True, help="Source page ID")
    copy_parser.add_argument("--dest", required=True, help="Destination parent page ID")
    copy_parser.add_argument("--title", help="New title for copied page")

    # move command
    move_parser = subparsers.add_parser("move", help="Move a page")
    move_parser.add_argument("--page-id", required=True, help="Page ID to move")
    move_parser.add_argument("--target", required=True, help="Target page ID")
    move_parser.add_argument("--position", choices=["append", "before", "after"], default="append")

    # watchers command
    watchers_parser = subparsers.add_parser("watchers", help="Show page watchers")
    watchers_parser.add_argument("--page-id", required=True, help="Page ID")

    # space command
    space_parser = subparsers.add_parser("space", help="Get space information")
    space_parser.add_argument("space_key", help="Space key (e.g., KCAI)")

    # parse-url command
    parse_url_parser = subparsers.add_parser("parse-url", help="Extract page ID from URL")
    parse_url_parser.add_argument("url", help="Confluence page URL")

    args = parser.parse_args()

    # Handle parse-url (doesn't need client)
    if args.command == "parse-url":
        page_id = WikiClient.extract_page_id_from_url(args.url)
        if page_id:
            print(page_id)
        else:
            print("Could not extract page ID from URL", file=sys.stderr)
            sys.exit(1)
        return

    # Create client and execute command
    with WikiClient(base_url, token, dry_run=args.dry_run) as client:
        try:
            if args.command == "read":
                page_id = args.page_id or client.extract_page_id_from_url(args.url)
                if not page_id:
                    print("Could not determine page ID", file=sys.stderr)
                    sys.exit(1)

                if args.format == "markdown":
                    page, markdown = client.get_page_as_markdown(page_id)
                    print(f"# {page['title']}\n")
                    print(markdown)
                elif args.format == "storage":
                    page = client.get_page(page_id, expand=["body.storage"])
                    print(page.get("body", {}).get("storage", {}).get("value", ""))
                else:
                    page = client.get_page(page_id, expand=["body.storage", "version", "ancestors"])
                    print(json.dumps(page, indent=2, ensure_ascii=False))

            elif args.command == "create":
                body = args.body or ""
                if args.body_file:
                    body_content = Path(args.body_file).read_text()
                    body = client.markdown_to_storage(body_content)

                result = client.create_page(
                    space_key=args.space, title=args.title, body=body, parent_id=args.parent_id
                )
                print(json.dumps(result, indent=2, ensure_ascii=False))

            elif args.command == "update":
                if not args.body_file:
                    print("--body-file is required for update", file=sys.stderr)
                    sys.exit(1)

                body_content = Path(args.body_file).read_text()
                result = client.update_page_from_markdown(
                    page_id=args.page_id, markdown_body=body_content, title=args.title
                )
                print(json.dumps(result, indent=2, ensure_ascii=False))

            elif args.command == "delete":
                client.delete_page(args.page_id)
                print(f"Page {args.page_id} deleted successfully")

            elif args.command == "search":
                results = client.search_by_title(args.space, args.title, args.limit)
                for page in results:
                    print(f"{page['id']}: {page['title']}")

            elif args.command == "cql":
                result = client.search_cql(args.query, args.limit)
                for page in result.get("results", []):
                    space_key = page.get("space", {}).get("key", "?")
                    print(f"[{space_key}] {page['id']}: {page['title']}")

            elif args.command == "children":
                results = client.get_children(args.page_id, args.limit)
                for page in results:
                    print(f"{page['id']}: {page['title']}")

            elif args.command == "ancestors":
                page = client.get_page(args.page_id, expand=["ancestors"])
                ancestors = page.get("ancestors", [])
                if not ancestors:
                    print(f"{page['id']}: {page['title']} (root)")
                else:
                    # Print from root to current page
                    for ancestor in ancestors:
                        print(f"{ancestor['id']}: {ancestor['title']}")
                    print(f"{page['id']}: {page['title']} (current)")

            elif args.command == "labels":
                if args.add:
                    result = client.add_label(args.page_id, args.add)
                    print(f"Added label: {args.add}")
                elif args.remove:
                    client.remove_label(args.page_id, args.remove)
                    print(f"Removed label: {args.remove}")
                else:
                    labels = client.get_labels(args.page_id)
                    if labels:
                        for label in labels:
                            print(f"  - {label['name']}")
                    else:
                        print("No labels")

            elif args.command == "history":
                if args.version:
                    page = client.get_version(args.page_id, args.version)
                    print(f"Version {args.version}: {page['title']}")
                    print(
                        f"Body:\n{page.get('body', {}).get('storage', {}).get('value', '')[:500]}..."
                    )
                else:
                    history = client.get_history(args.page_id, args.limit)
                    print(f"Page: {history.get('title', 'Unknown')}")
                    print(f"Latest version: {history.get('lastUpdated', {}).get('number', '?')}")
                    print(f"Created: {history.get('createdDate', '?')}")
                    if history.get("lastUpdated"):
                        lu = history["lastUpdated"]
                        print(
                            f"Last updated by: {lu.get('by', {}).get('displayName', '?')} at {lu.get('when', '?')}"
                        )

            elif args.command == "attachments":
                if args.upload:
                    result = client.upload_attachment(args.page_id, args.upload)
                    print(f"Uploaded: {result.get('title', args.upload)}")
                elif args.download:
                    output = args.output or f"./{args.download}"
                    path = client.download_attachment(args.page_id, args.download, output)
                    print(f"Downloaded to: {path}")
                else:
                    attachments = client.get_attachments(args.page_id)
                    if attachments:
                        for att in attachments:
                            size = att.get("extensions", {}).get("fileSize", "?")
                            print(f"  {att['id']}: {att['title']} ({size} bytes)")
                    else:
                        print("No attachments")

            elif args.command == "comments":
                if args.add:
                    result = client.add_comment(args.page_id, args.add)
                    print(f"Added comment: {result.get('id', 'OK')}")
                else:
                    comments = client.get_comments(args.page_id)
                    if comments:
                        for c in comments:
                            author = c.get("version", {}).get("by", {}).get("displayName", "?")
                            body = c.get("body", {}).get("view", {}).get("value", "")[:100]
                            print(f"  [{author}] {body}...")
                    else:
                        print("No comments")

            elif args.command == "copy":
                result = client.copy_page(args.page_id, args.dest, args.title)
                print(f"Copied to: {result.get('id', 'OK')}")

            elif args.command == "move":
                result = client.move_page(args.page_id, args.target, args.position)
                print(f"Moved page {args.page_id} to {args.position} {args.target}")

            elif args.command == "watchers":
                watchers = client.get_watchers(args.page_id)
                if watchers:
                    for w in watchers:
                        print(f"  - {w.get('displayName', w.get('username', '?'))}")
                else:
                    print("No watchers")

            elif args.command == "space":
                space = client.get_space(args.space_key)
                print(f"Key: {space['key']}")
                print(f"Name: {space['name']}")
                print(f"Type: {space['type']}")
                homepage = space.get("homepage", {})
                if homepage:
                    print(f"Homepage: {homepage.get('id')} - {homepage.get('title', '?')}")
                desc = space.get("description", {}).get("plain", {}).get("value", "")
                if desc:
                    print(f"Description: {desc[:200]}")

        except httpx.HTTPStatusError as e:
            print(f"API Error: {e.response.status_code}", file=sys.stderr)
            print(e.response.text, file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
