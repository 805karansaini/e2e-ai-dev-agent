"""File conversion utilities for converting various file formats to markdown."""

from pathlib import Path
from typing import Optional

from markitdown import MarkItDown


class FileConverter:
    """Convert various file formats to markdown using Markitdown."""

    # File extensions that should be converted to markdown
    CONVERTIBLE_EXTENSIONS = {".pdf", ".docx", ".pptx"}

    def should_convert(self, file_path: Path) -> bool:
        """Check if a file should be converted to markdown."""
        return file_path.suffix.lower() in self.CONVERTIBLE_EXTENSIONS

    def convert_to_markdown(self, file_path: Path) -> Optional[str]:
        """Convert a file to markdown format.

        Args:
            file_path: Path to the file to convert

        Returns:
            Markdown content as string, or None if conversion fails
        """
        try:
            # MarkItDown is not documented as thread-safe; build per call when run in threads
            result = MarkItDown().convert(str(file_path))
            return result.text_content
        except Exception as e:
            # Log the error but don't fail the entire import
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to convert {file_path} to markdown: {e}")
            return None

    def convert_and_save(self, source_path: Path, target_dir: Path) -> Optional[Path]:
        """Convert a file to markdown and save it with .md extension.

        Args:
            source_path: Path to the original file
            target_dir: Directory to save the converted file

        Returns:
            Path to the converted markdown file, or None if conversion fails
        """
        if not self.should_convert(source_path):
            return None

        markdown_content = self.convert_to_markdown(source_path)
        if markdown_content is None:
            return None

        # Create markdown filename by replacing extension with .md
        md_filename = source_path.stem + ".md"
        md_path = target_dir / md_filename

        try:
            md_path.write_text(markdown_content, encoding="utf-8")
            return md_path
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to save converted markdown for {source_path}: {e}")
            return None


# Global instance for reuse
file_converter = FileConverter()
