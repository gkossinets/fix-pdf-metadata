"""
Unit tests for the metadata_updater module.
"""

import os
import tempfile
import unittest
from pathlib import Path

try:
    import pikepdf
    PIKEPDF_AVAILABLE = True
except ImportError:
    PIKEPDF_AVAILABLE = False

from ..core.metadata_updater import (
    MetadataUpdater,
    MetadataUpdate,
    PDFUpdateError,
    FileOperationError
)


class TestMetadataUpdate(unittest.TestCase):
    """Test the MetadataUpdate dataclass."""

    def test_metadata_update_creation(self):
        """Test creating a MetadataUpdate object."""
        metadata = MetadataUpdate(
            title="Test Title",
            authors="Smith, J.; Jones, A.",
            year="2020",
            journal="Test Journal",
            doi="10.1234/test",
            isbn="978-0-123456-78-9"
        )

        self.assertEqual(metadata.title, "Test Title")
        self.assertEqual(metadata.authors, "Smith, J.; Jones, A.")
        self.assertEqual(metadata.year, "2020")
        self.assertEqual(metadata.journal, "Test Journal")
        self.assertEqual(metadata.doi, "10.1234/test")
        self.assertEqual(metadata.isbn, "978-0-123456-78-9")

    def test_metadata_update_optional_fields(self):
        """Test MetadataUpdate with only required fields."""
        metadata = MetadataUpdate(
            title="Test Title",
            authors="Smith, J."
        )

        self.assertEqual(metadata.title, "Test Title")
        self.assertEqual(metadata.authors, "Smith, J.")
        self.assertIsNone(metadata.year)
        self.assertIsNone(metadata.journal)
        self.assertIsNone(metadata.doi)
        self.assertIsNone(metadata.isbn)


class TestZoteroFilenameGeneration(unittest.TestCase):
    """Test Zotero filename generation."""

    def setUp(self):
        """Set up test fixtures."""
        self.updater = MetadataUpdater()

    def test_single_author(self):
        """Test filename generation with single author."""
        metadata = MetadataUpdate(
            title="Machine Learning Applications",
            authors="Smith, John",
            year="2020"
        )

        filename = self.updater.generate_zotero_filename(metadata, "original.pdf")
        self.assertEqual(filename, "Smith - 2020 - Machine Learning Applications.pdf")

    def test_two_authors(self):
        """Test filename generation with two authors."""
        metadata = MetadataUpdate(
            title="Deep Learning",
            authors="Smith, John; Jones, Alice",
            year="2021"
        )

        filename = self.updater.generate_zotero_filename(metadata, "original.pdf")
        self.assertEqual(filename, "Smith & Jones - 2021 - Deep Learning.pdf")

    def test_three_or_more_authors(self):
        """Test filename generation with three or more authors."""
        metadata = MetadataUpdate(
            title="Neural Networks",
            authors="Smith, John; Jones, Alice; Brown, Bob",
            year="2019"
        )

        filename = self.updater.generate_zotero_filename(metadata, "original.pdf")
        self.assertEqual(filename, "Smith et al. - 2019 - Neural Networks.pdf")

    def test_long_title_truncation(self):
        """Test that long titles are truncated."""
        long_title = "A" * 150  # Title longer than 100 chars
        metadata = MetadataUpdate(
            title=long_title,
            authors="Smith, John",
            year="2020"
        )

        filename = self.updater.generate_zotero_filename(metadata, "original.pdf")
        # Should be truncated to 97 chars + "..."
        self.assertIn("...", filename)
        self.assertLess(len(filename), 150)

    def test_special_characters_removed(self):
        """Test that special characters are removed from filename."""
        metadata = MetadataUpdate(
            title='Test "Title" with: Special* Chars?',
            authors="O'Brien, John",
            year="2020"
        )

        filename = self.updater.generate_zotero_filename(metadata, "original.pdf")
        # Should not contain special characters
        self.assertNotIn('"', filename)
        self.assertNotIn(':', filename)
        self.assertNotIn('*', filename)
        self.assertNotIn('?', filename)

    def test_ampersand_replacement(self):
        """Test that & is replaced with 'and'."""
        metadata = MetadataUpdate(
            title="Data & Analytics",
            authors="Smith, John",
            year="2020"
        )

        filename = self.updater.generate_zotero_filename(metadata, "original.pdf")
        # & should be replaced with 'and'
        self.assertIn("and", filename)
        self.assertNotIn("&", filename.split(" - ")[2])  # Check title part

    def test_incomplete_metadata_marked(self):
        """Test that incomplete metadata gets underscore prefix."""
        metadata = MetadataUpdate(
            title="Test Title",
            authors="Unknown"
        )

        filename = self.updater.generate_zotero_filename(metadata, "original.pdf")
        # Should start with underscore due to missing year
        self.assertTrue(filename.startswith("_"))

    def test_missing_title_uses_original(self):
        """Test fallback to original filename when title is missing."""
        metadata = MetadataUpdate(
            title="",
            authors="Smith, John",
            year="2020"
        )

        filename = self.updater.generate_zotero_filename(metadata, "/path/to/original.pdf")
        # Should use original filename and be marked incomplete
        self.assertTrue(filename.startswith("_"))
        self.assertIn("original", filename)


class TestFileRenaming(unittest.TestCase):
    """Test file renaming functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.updater = MetadataUpdater()
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test files."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_rename_file_same_directory(self):
        """Test renaming file in the same directory."""
        # Create a test file
        old_path = os.path.join(self.temp_dir, "old_name.pdf")
        with open(old_path, 'w') as f:
            f.write("test content")

        new_filename = "new_name.pdf"
        new_path = self.updater.rename_file(old_path, new_filename)

        # Check that file was renamed
        self.assertEqual(new_path, os.path.join(self.temp_dir, "new_name.pdf"))
        self.assertTrue(os.path.exists(new_path))
        self.assertFalse(os.path.exists(old_path))

    def test_rename_file_different_directory(self):
        """Test renaming file to a different directory."""
        # Create source and target directories
        source_dir = os.path.join(self.temp_dir, "source")
        target_dir = os.path.join(self.temp_dir, "target")
        os.makedirs(source_dir, exist_ok=True)

        # Create a test file
        old_path = os.path.join(source_dir, "old_name.pdf")
        with open(old_path, 'w') as f:
            f.write("test content")

        new_filename = "new_name.pdf"
        new_path = self.updater.rename_file(old_path, new_filename, output_dir=target_dir)

        # Check that file was moved and renamed
        self.assertEqual(new_path, os.path.join(target_dir, "new_name.pdf"))
        self.assertTrue(os.path.exists(new_path))
        self.assertFalse(os.path.exists(old_path))

    def test_rename_file_conflict_handling(self):
        """Test that conflicts are handled by adding (2), (3), etc."""
        # Create initial file
        file1 = os.path.join(self.temp_dir, "test.pdf")
        with open(file1, 'w') as f:
            f.write("content1")

        # Create file to rename
        file2 = os.path.join(self.temp_dir, "other.pdf")
        with open(file2, 'w') as f:
            f.write("content2")

        # Try to rename to existing name
        new_path = self.updater.rename_file(file2, "test.pdf")

        # Should have added (2) to avoid conflict
        self.assertEqual(new_path, os.path.join(self.temp_dir, "test (2).pdf"))
        self.assertTrue(os.path.exists(new_path))
        self.assertTrue(os.path.exists(file1))  # Original should still exist

    def test_rename_nonexistent_file_raises_error(self):
        """Test that renaming a nonexistent file raises error."""
        nonexistent = os.path.join(self.temp_dir, "nonexistent.pdf")

        with self.assertRaises(FileNotFoundError):
            self.updater.rename_file(nonexistent, "new_name.pdf")


@unittest.skipIf(not PIKEPDF_AVAILABLE, "pikepdf not available")
class TestPDFMetadataUpdate(unittest.TestCase):
    """Test PDF metadata update functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.updater = MetadataUpdater()
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test files."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def _create_test_pdf(self, filename: str) -> str:
        """Create a simple test PDF file."""
        pdf_path = os.path.join(self.temp_dir, filename)

        # Create a minimal PDF
        pdf = pikepdf.new()
        pdf.add_blank_page(page_size=(612, 792))  # Letter size
        pdf.save(pdf_path)

        return pdf_path

    def test_update_metadata_in_place(self):
        """Test updating PDF metadata in place."""
        pdf_path = self._create_test_pdf("test.pdf")

        metadata = MetadataUpdate(
            title="Test Title",
            authors="Smith, John; Jones, Alice",
            year="2020",
            journal="Test Journal",
            doi="10.1234/test"
        )

        result = self.updater.update_metadata(pdf_path, metadata)
        self.assertTrue(result)

        # Verify metadata was updated
        with pikepdf.open(pdf_path) as pdf:
            self.assertEqual(str(pdf.docinfo.get('/Title', '')), "Test Title")
            self.assertEqual(str(pdf.docinfo.get('/Author', '')), "Smith, John; Jones, Alice")
            self.assertIn("Test Journal", str(pdf.docinfo.get('/Subject', '')))
            self.assertIn("DOI: 10.1234/test", str(pdf.docinfo.get('/Subject', '')))

    def test_update_metadata_to_new_file(self):
        """Test updating PDF metadata to a new file."""
        pdf_path = self._create_test_pdf("original.pdf")
        output_path = os.path.join(self.temp_dir, "updated.pdf")

        metadata = MetadataUpdate(
            title="Updated Title",
            authors="Brown, Bob",
            year="2021"
        )

        result = self.updater.update_metadata(pdf_path, metadata, output_path)
        self.assertTrue(result)

        # Both files should exist
        self.assertTrue(os.path.exists(pdf_path))
        self.assertTrue(os.path.exists(output_path))

        # Verify new file has updated metadata
        with pikepdf.open(output_path) as pdf:
            self.assertEqual(str(pdf.docinfo.get('/Title', '')), "Updated Title")

    def test_update_metadata_with_backup(self):
        """Test that backup is created when requested."""
        updater = MetadataUpdater(keep_backup=True)
        pdf_path = self._create_test_pdf("test.pdf")

        metadata = MetadataUpdate(
            title="Test Title",
            authors="Smith, John"
        )

        updater.update_metadata(pdf_path, metadata)

        # Backup should exist
        backup_path = f"{pdf_path}.bak"
        self.assertTrue(os.path.exists(backup_path))

    def test_update_nonexistent_pdf_raises_error(self):
        """Test that updating nonexistent PDF raises error."""
        nonexistent = os.path.join(self.temp_dir, "nonexistent.pdf")

        metadata = MetadataUpdate(
            title="Test",
            authors="Test"
        )

        with self.assertRaises(FileNotFoundError):
            self.updater.update_metadata(nonexistent, metadata)


if __name__ == '__main__':
    unittest.main()
