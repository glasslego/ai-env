#!/usr/bin/env python3
"""CLI for Notion to Obsidian conversion."""

import argparse
import logging
import sys
from pathlib import Path

# Add src to path for direct execution
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ai_assistant.notion_to_obsidian import NotionToObsidianConverter


def setup_logging(verbose: bool = False, debug: bool = False) -> None:
    """Configure logging."""
    if debug:
        level = logging.DEBUG
    elif verbose:
        level = logging.INFO
    else:
        level = logging.WARNING

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Convert Notion export to Obsidian vault",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic conversion
  python -m ai_assistant.notion_to_obsidian.cli /path/to/notion/export /path/to/obsidian/vault
  
  # Dry run (preview without writing)
  python -m ai_assistant.notion_to_obsidian.cli /path/to/export /path/to/vault --dry-run
  
  # Flatten folder structure (all notes in root)
  python -m ai_assistant.notion_to_obsidian.cli /path/to/export /path/to/vault --flatten
  
  # Verbose output
  python -m ai_assistant.notion_to_obsidian.cli /path/to/export /path/to/vault -v
        """,
    )

    parser.add_argument(
        "source",
        type=Path,
        help="Path to Notion export directory",
    )
    parser.add_argument(
        "target",
        type=Path,
        help="Path to target Obsidian vault directory",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview conversion without writing files",
    )
    parser.add_argument(
        "--no-attachments",
        action="store_true",
        help="Skip copying attachments (images, PDFs)",
    )
    parser.add_argument(
        "--flatten",
        action="store_true",
        help="Flatten folder structure (all notes in root, use tags for hierarchy)",
    )
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Skip confirmation prompts",
    )

    args = parser.parse_args()
    setup_logging(args.verbose, args.debug)

    logger = logging.getLogger(__name__)

    # Validate source
    if not args.source.exists():
        logger.error(f"Source directory not found: {args.source}")
        return 1

    # Confirm if target exists
    if args.target.exists() and not args.dry_run and not args.yes:
        print(f"\n⚠️  Target directory exists: {args.target}")
        print("   Existing files may be overwritten.\n")
        response = input("Continue? [y/N]: ")
        if response.lower() != "y":
            logger.info("Aborted by user")
            return 0

    # Run conversion
    try:
        converter = NotionToObsidianConverter(
            source_dir=args.source,
            target_dir=args.target,
            copy_attachments=not args.no_attachments,
            flatten_structure=args.flatten,
            dry_run=args.dry_run,
        )
        stats = converter.convert()

        # Print summary
        print("\n" + "=" * 50)
        print("📊 Conversion Summary")
        print("=" * 50)
        print(f"  ✅ Pages converted: {stats['pages_converted']}")
        print(f"  ⏭️  Pages skipped:   {stats['pages_skipped']}")
        print(f"  📎 Attachments:     {stats['attachments_copied']}")
        if stats["errors"]:
            print(f"  ❌ Errors:          {len(stats['errors'])}")
            for err in stats["errors"][:5]:
                print(f"     - {Path(err['file']).name}: {err['error']}")
            if len(stats["errors"]) > 5:
                print(f"     ... and {len(stats['errors']) - 5} more")
        print("=" * 50)

        if args.dry_run:
            print("\n🔍 [DRY RUN] No files were written.")
        else:
            print(f"\n✨ Done! Open '{args.target}' in Obsidian.")

        return 0 if not stats["errors"] else 1

    except Exception as e:
        logger.exception(f"Conversion failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
