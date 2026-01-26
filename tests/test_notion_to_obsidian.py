"""Tests for Notion to Obsidian converter."""

import tempfile
from pathlib import Path

from ai_assistant.notion_to_obsidian import NotionCleaner, NotionToObsidianConverter


class TestNotionCleaner:
    """Test NotionCleaner class."""

    def test_remove_notion_id_from_title(self):
        cleaner = NotionCleaner()

        assert (
            cleaner.remove_notion_id_from_title("spark 튜닝 a4405ba1e3e5833da2d30149003acead")
            == "spark 튜닝"
        )

        assert cleaner.remove_notion_id_from_title("Simple Title") == "Simple Title"

        assert (
            cleaner.remove_notion_id_from_title("file 9b305ba1e3e582c9aa2f8121ac069c86.md")
            == "file"
        )

    def test_extract_metadata(self):
        cleaner = NotionCleaner()
        content = """# Test Page

Tags: spark, 튜닝
Created: June 17, 2022 6:38 PM
Updated: June 17, 2022 6:38 PM

Some content here.
"""
        result = cleaner.clean(content)

        assert "Tags:" not in result
        assert "Created:" not in result
        assert "Updated:" not in result
        assert cleaner.extracted_tags == ["spark", "튜닝"]
        assert cleaner.extracted_created is not None
        assert cleaner.extracted_created.year == 2022

    def test_clean_links(self):
        cleaner = NotionCleaner()

        # CSV link should become wiki link
        content = "[hadoop](hadoop%201c605ba1e3e5802da78eeab9359f4aa1.csv)"
        result = cleaner.clean(content)
        assert "[[hadoop]]" in result

        # External link should stay
        content = "[Google](https://google.com)"
        result = cleaner.clean(content)
        assert "[Google](https://google.com)" in result

    def test_clean_callouts(self):
        cleaner = NotionCleaner()

        content = "> 💡 This is a tip"
        result = cleaner.clean(content)
        assert "> [!tip]" in result


class TestNotionToObsidianConverter:
    """Test NotionToObsidianConverter class."""

    def test_is_index_page(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            target = Path(tmp) / "target"
            source.mkdir()

            converter = NotionToObsidianConverter(source, target)

            # Index page with mostly CSV links
            index_content = """# Index
[link1](file1.csv)
[link2](file2.csv)
[link3](file3.csv)
"""
            assert converter._is_index_page(index_content) is True

            # Regular page
            regular_content = """# Regular Page
This is some content.
More content here.
[link](other.md)
"""
            assert converter._is_index_page(regular_content) is False

    def test_clean_folder_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            target = Path(tmp) / "target"
            source.mkdir()

            converter = NotionToObsidianConverter(source, target)

            assert (
                converter._clean_folder_name(
                    "02_%EB%8D%B0%EC%9D%B4%ED%84%B0%EA%B8%B0%EC%88%A0/spark 1c605ba1e3e580729fa8d2df7bd40dc6"
                )
                == "02_데이터기술/spark"
            )

    def test_dry_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            target = Path(tmp) / "target"
            source.mkdir()

            # Create test file with enough content
            test_file = source / "test 1234567890abcdef1234567890abcdef.md"
            test_file.write_text("# Test\n\nContent here.\nMore content.\nEven more.")

            converter = NotionToObsidianConverter(source, target, dry_run=True)
            stats = converter.convert()

            assert stats["pages_converted"] == 1
            assert not target.exists()  # Should not create target in dry run

    def test_full_conversion(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            target = Path(tmp) / "target"
            source.mkdir()

            # Create test file with metadata
            test_file = source / "spark 튜닝 a4405ba1e3e5833da2d30149003acead.md"
            test_file.write_text("""# spark 튜닝

Tags: spark, 튜닝
Created: June 17, 2022 6:38 PM

This is test content.
""")

            converter = NotionToObsidianConverter(source, target)
            stats = converter.convert()

            assert stats["pages_converted"] == 1

            # Check output
            output_file = target / "spark 튜닝.md"
            assert output_file.exists()

            content = output_file.read_text()
            assert "tags:" in content
            assert "spark" in content
            assert "created: 2022-06-17" in content
