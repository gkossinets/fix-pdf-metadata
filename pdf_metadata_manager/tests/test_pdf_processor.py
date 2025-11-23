"""
Unit tests for PDF Processor

Tests the PDFProcessor class with various scenarios.
"""

import os
import sys
import unittest
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.pdf_processor import (
    PDFProcessor,
    PDFMetadata,
    PDFNotFoundError,
    PDFReadError,
    OCRNotAvailableError
)


class TestPDFProcessor(unittest.TestCase):
    """Test cases for PDFProcessor class."""

    def setUp(self):
        """Set up test fixtures."""
        self.processor = PDFProcessor(use_ocr=False, verbose=False)

    def test_initialization(self):
        """Test PDFProcessor initialization."""
        processor = PDFProcessor(use_ocr=True, ocr_pages=2, verbose=True)
        self.assertEqual(processor.ocr_pages, 2)
        self.assertTrue(processor.verbose)

    def test_sanitize_doi(self):
        """Test DOI sanitization."""
        # Test trailing period removal
        doi = self.processor._sanitize_doi("10.1234/test...")
        self.assertEqual(doi, "10.1234/test")

        # Test whitespace removal
        doi = self.processor._sanitize_doi("  10.1234/test  ")
        self.assertEqual(doi, "10.1234/test")

    def test_extract_doi_from_text(self):
        """Test DOI extraction from text."""
        # Test standard DOI format
        text = "This paper DOI: 10.1234/test.5678 is interesting"
        doi = self.processor._extract_doi(text)
        self.assertEqual(doi, "10.1234/test.5678")

        # Test DOI with URL
        text = "Available at https://doi.org/10.1234/test.5678"
        doi = self.processor._extract_doi(text)
        self.assertEqual(doi, "10.1234/test.5678")

        # Test bare DOI
        text = "The DOI is 10.1234/test.5678 for this work"
        doi = self.processor._extract_doi(text)
        self.assertEqual(doi, "10.1234/test.5678")

        # Test no DOI
        text = "This text has no DOI"
        doi = self.processor._extract_doi(text)
        self.assertIsNone(doi)

    def test_pdf_not_found(self):
        """Test handling of non-existent PDF files."""
        with self.assertRaises(PDFNotFoundError):
            self.processor.extract_metadata("/nonexistent/file.pdf")

    def test_extract_title_from_lines(self):
        """Test title extraction from filtered lines."""
        # Test with all-caps title
        lines = [
            "Some header",
            "MACHINE LEARNING FOR CLIMATE SCIENCE",
            "Some other text",
            "More content"
        ]
        title = self.processor._extract_title(lines)
        self.assertEqual(title, "MACHINE LEARNING FOR CLIMATE SCIENCE")

        # Test with no valid title
        lines = ["short", "abc", "12"]
        title = self.processor._extract_title(lines)
        self.assertIsNone(title)

    def test_extract_journal(self):
        """Test journal name extraction."""
        lines = [
            "Some text",
            "Journal of Climate Science, Vol. 10",
            "More text"
        ]
        journal = self.processor._extract_journal(lines)
        self.assertIsNotNone(journal)
        self.assertIn("Journal of Climate Science", journal)

        # Test with no journal
        lines = ["No journal here", "Just text"]
        journal = self.processor._extract_journal(lines)
        self.assertIsNone(journal)

    @patch('core.pdf_processor.PdfReader')
    def test_extract_text_with_pypdf2(self, mock_reader):
        """Test text extraction using PyPDF2."""
        # Mock PdfReader
        mock_page = Mock()
        mock_page.extract_text.return_value = "Sample extracted text from PDF"

        mock_pdf = Mock()
        mock_pdf.pages = [mock_page]

        mock_reader.return_value = mock_pdf

        # Create a temporary test file
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            tmp_path = tmp.name

        try:
            # Extract text (will use mocked PyPDF2)
            text = self.processor._extract_text(tmp_path)
            self.assertEqual(text, "Sample extracted text from PDF")
        finally:
            # Clean up
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


class TestPDFMetadata(unittest.TestCase):
    """Test cases for PDFMetadata dataclass."""

    def test_metadata_initialization(self):
        """Test PDFMetadata initialization."""
        metadata = PDFMetadata()
        self.assertIsNone(metadata.title)
        self.assertIsNone(metadata.authors)
        self.assertIsNone(metadata.journal)
        self.assertIsNone(metadata.year)
        self.assertIsNone(metadata.doi)
        self.assertEqual(metadata.extracted_text, "")
        self.assertFalse(metadata.used_ocr)

    def test_metadata_with_values(self):
        """Test PDFMetadata with values."""
        metadata = PDFMetadata(
            title="Test Title",
            authors="John Doe",
            doi="10.1234/test",
            used_ocr=True
        )
        self.assertEqual(metadata.title, "Test Title")
        self.assertEqual(metadata.authors, "John Doe")
        self.assertEqual(metadata.doi, "10.1234/test")
        self.assertTrue(metadata.used_ocr)


if __name__ == '__main__':
    unittest.main()
