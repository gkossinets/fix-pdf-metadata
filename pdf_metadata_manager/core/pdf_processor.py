"""
PDF Processor Module

Extracts text, metadata, and DOIs from PDF files with OCR fallback for scanned documents.
"""

import os
import re
import tempfile
from dataclasses import dataclass
from typing import Optional, Tuple

# PDF libraries
from PyPDF2 import PdfReader
import pikepdf

# OCR libraries (optional)
try:
    import pytesseract
    from pdf2image import convert_from_path
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


# Custom exceptions
class PDFProcessingError(Exception):
    """Base exception for PDF processing errors."""
    pass


class PDFNotFoundError(PDFProcessingError):
    """Raised when PDF file doesn't exist."""
    pass


class PDFReadError(PDFProcessingError):
    """Raised when PDF cannot be read."""
    pass


class OCRNotAvailableError(PDFProcessingError):
    """Raised when OCR is needed but not available."""
    pass


@dataclass
class PDFMetadata:
    """Metadata extracted from a PDF file."""
    title: Optional[str] = None
    authors: Optional[str] = None
    journal: Optional[str] = None
    year: Optional[str] = None
    doi: Optional[str] = None
    extracted_text: str = ""
    used_ocr: bool = False


class PDFProcessor:
    """Extract text and metadata from PDF files."""

    # DOI detection patterns
    DOI_PATTERNS = [
        r'(?:doi|DOI):?\s*(10\.\d{4,9}/[^\s"\'<>]+)',
        r'https?://doi\.org/(10\.\d{4,9}/[^\s"\'<>]+)',
        r'https?://(doi\.org/10\.\d{4,9}/[^\s"\'<>]+)',
        r'(?:^|\s|[^\w.])(10\.\d{4,9}/[^\s"\'<>]+)(?:$|\s|[^\w.])',
        r'doi\.org/(10\.\d{4,9}/[^\s"\'<>]+)'
    ]

    # Blacklist patterns for filtering out non-title lines
    TITLE_BLACKLIST_PATTERNS = [
        r'downloaded from',
        r'all rights reserved',
        r'copyright',
        r'reproduced with permission',
        r'used with permission',
        r'©',
        r'page \d+ of \d+',
        r'\d+\s*?\|\s*?page',
        r'http',
        r'www\.',
        r'@',
        r'volume \d+',
        r'issue \d+',
        r'doi:',
        r'isbn',
        r'issn',
        r'\d{4} by',
        r'Elsevier|Springer|Wiley|SAGE|IEEE|Oxford University Press|Cambridge University Press'
    ]

    def __init__(self, use_ocr: bool = True, ocr_pages: int = 1, verbose: bool = False):
        """
        Initialize PDF processor.

        Args:
            use_ocr: Enable OCR fallback for scanned documents
            ocr_pages: Number of pages to OCR (default: 1)
            verbose: Print detailed processing information
        """
        self.use_ocr = use_ocr and OCR_AVAILABLE
        self.ocr_pages = ocr_pages
        self.verbose = verbose

        if use_ocr and not OCR_AVAILABLE:
            print("Warning: OCR requested but pytesseract and pdf2image are not installed.")

    def extract_metadata(self, pdf_path: str) -> PDFMetadata:
        """
        Extract metadata from a PDF file.

        Tries multiple methods in order:
        1. Standard text extraction (pikepdf → PyPDF2)
        2. OCR if text is insufficient (optional)
        3. Search for DOI in extracted text
        4. Extract title, authors, journal from text

        Args:
            pdf_path: Path to the PDF file

        Returns:
            PDFMetadata object with extracted information

        Raises:
            PDFNotFoundError: If PDF file doesn't exist
            PDFProcessingError: If PDF cannot be read
        """
        # Validate file exists
        if not os.path.exists(pdf_path):
            raise PDFNotFoundError(f"PDF file not found: {pdf_path}")

        if self.verbose:
            print(f"Processing: {pdf_path}")

        # Initialize metadata object
        metadata = PDFMetadata()

        # Extract text from PDF
        text = self._extract_text(pdf_path)

        # If text is insufficient, try OCR
        if len(text.strip()) < 100:
            if self.use_ocr:
                if self.verbose:
                    print("  PDF has little or no extractable text. Using OCR...")
                text = self._extract_text_with_ocr(pdf_path)
                metadata.used_ocr = True
            else:
                if self.verbose:
                    print("  PDF has little or no extractable text and OCR is disabled.")

        metadata.extracted_text = text

        if self.verbose and text:
            print(f"  Extracted {len(text)} characters of text")

        # Extract DOI from text
        doi = self._extract_doi(text)
        if doi:
            metadata.doi = doi
            if self.verbose:
                print(f"  Found DOI: {doi}")

        # Extract other metadata from text
        if text:
            title, authors, journal = self._extract_metadata_from_text(text)
            metadata.title = title
            metadata.authors = authors
            metadata.journal = journal

            if self.verbose:
                if title:
                    print(f"  Extracted title: {title}")
                if authors:
                    print(f"  Extracted authors: {authors}")
                if journal:
                    print(f"  Extracted journal: {journal}")

        return metadata

    def _extract_text(self, pdf_path: str) -> str:
        """
        Extract text from PDF using standard methods.

        Tries pikepdf first, then falls back to PyPDF2.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Extracted text

        Raises:
            PDFReadError: If PDF cannot be read by any method
        """
        # Try pikepdf first
        try:
            with pikepdf.open(pdf_path) as pdf:
                text = ""
                # Extract text from first page only (for performance)
                if len(pdf.pages) > 0:
                    page = pdf.pages[0]
                    try:
                        text = page.extract_text()
                    except:
                        pass  # Fall back to PyPDF2

                if text and len(text.strip()) >= 100:
                    return text
        except Exception as e:
            if self.verbose:
                print(f"  pikepdf extraction failed: {e}")

        # Fall back to PyPDF2
        try:
            reader = PdfReader(pdf_path)
            if len(reader.pages) == 0:
                raise PDFReadError("PDF has no pages")

            # Extract from first page
            text = reader.pages[0].extract_text()
            return text if text else ""

        except Exception as e:
            raise PDFReadError(f"Failed to read PDF with both pikepdf and PyPDF2: {e}")

    def _extract_text_with_ocr(self, pdf_path: str, pages: Optional[int] = None) -> str:
        """
        Extract text from PDF using OCR.

        Args:
            pdf_path: Path to PDF file
            pages: Number of pages to OCR (default: self.ocr_pages)

        Returns:
            Extracted text from OCR

        Raises:
            OCRNotAvailableError: If OCR libraries are not available
        """
        if not OCR_AVAILABLE:
            raise OCRNotAvailableError("OCR libraries (pytesseract, pdf2image) are not installed")

        if pages is None:
            pages = self.ocr_pages

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Convert PDF pages to images
                images = convert_from_path(
                    pdf_path,
                    first_page=1,
                    last_page=pages,
                    dpi=300,
                    output_folder=temp_dir
                )

                # Extract text from each image using OCR
                text = ""
                for i, image in enumerate(images):
                    if self.verbose:
                        print(f"  OCR processing page {i+1}/{len(images)}...")
                    page_text = pytesseract.image_to_string(image)
                    text += f"\n--- Page {i+1} ---\n{page_text}"

                return text

        except Exception as e:
            if self.verbose:
                print(f"  OCR Error: {e}")
            return ""

    def _sanitize_doi(self, doi: str) -> str:
        """
        Sanitize DOI by removing trailing periods and invalid characters.

        Args:
            doi: Raw DOI string

        Returns:
            Sanitized DOI
        """
        doi = doi.strip()
        # Remove trailing non-alphanumeric characters
        doi = re.sub(r'[^a-zA-Z0-9]+$', '', doi)
        return doi

    def _extract_doi(self, text: str) -> Optional[str]:
        """
        Extract DOI from text using multiple patterns.

        Args:
            text: Text to search for DOI

        Returns:
            DOI if found, None otherwise
        """
        for pattern in self.DOI_PATTERNS:
            match = re.search(pattern, text)
            if match:
                # Extract the DOI
                doi = match.group(1)

                # Remove "doi.org/" prefix if present
                if "doi.org/" in doi:
                    doi = re.sub(r'doi\.org/', '', doi)

                doi = self._sanitize_doi(doi)
                return doi

        return None

    def _extract_metadata_from_text(self, text: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Extract title, authors, and journal from PDF text.

        Args:
            text: Extracted text from PDF

        Returns:
            Tuple of (title, authors, journal)
        """
        # Split into lines and filter out short lines
        lines = [line.strip() for line in text.split('\n') if len(line.strip()) > 3]

        # Filter out headers, footers, and copyright notices
        filtered_lines = []
        for line in lines:
            # Skip lines that match blacklist patterns
            if any(re.search(pattern, line, re.IGNORECASE) for pattern in self.TITLE_BLACKLIST_PATTERNS):
                continue
            filtered_lines.append(line)

        # Extract title
        title = self._extract_title(filtered_lines)

        # Extract authors
        authors = self._extract_authors(lines, title)

        # Extract journal
        journal = self._extract_journal(lines)

        return title, authors, journal

    def _extract_title(self, filtered_lines: list) -> Optional[str]:
        """
        Extract title from filtered lines.

        Args:
            filtered_lines: Lines with blacklisted content removed

        Returns:
            Title if found, None otherwise
        """
        title_candidates = []

        # Look for lines with typical title characteristics
        for line in filtered_lines[:min(30, len(filtered_lines))]:
            # Skip very short lines and lines starting with numbers
            if len(line) < 10 or re.match(r'^\d', line):
                continue

            # Check for lines that might be titles (uppercase or title case)
            if line.isupper() or sum(1 for c in line if c.isupper()) >= 2:
                if len(line) < 200:  # Title shouldn't be too long
                    title_candidates.append((line, filtered_lines.index(line)))

        # Sort candidates by position (earlier in document more likely to be title)
        title_candidates.sort(key=lambda x: x[1])

        if title_candidates:
            # Prefer all-caps titles, which are common in academic papers
            all_caps_candidates = [t for t, idx in title_candidates if t.isupper()]
            if all_caps_candidates:
                return all_caps_candidates[0]
            else:
                return title_candidates[0][0]

        return None

    def _extract_authors(self, lines: list, title: Optional[str]) -> Optional[str]:
        """
        Extract authors from lines.

        Args:
            lines: All extracted lines
            title: Extracted title (used to find author position)

        Returns:
            Authors if found, None otherwise
        """
        if not title:
            return None

        # Find title position
        title_idx = -1
        for i, line in enumerate(lines):
            if title in line:
                title_idx = i
                break

        if title_idx < 0:
            return None

        # Look at the next few lines for author information
        for i in range(title_idx + 1, min(title_idx + 10, len(lines))):
            # Author lines often contain names (capitalized words)
            name_pattern = r'([A-Z][a-z]+ [A-Z][a-z]+)'
            if re.search(name_pattern, lines[i]) and not lines[i].isupper():
                # Check it's not a blacklisted line
                if not any(re.search(pattern, lines[i], re.IGNORECASE)
                          for pattern in self.TITLE_BLACKLIST_PATTERNS):
                    return lines[i]

        return None

    def _extract_journal(self, lines: list) -> Optional[str]:
        """
        Extract journal name from lines.

        Args:
            lines: All extracted lines

        Returns:
            Journal name if found, None otherwise
        """
        for line in lines:
            journal_match = re.search(
                r'(Journal of|Proceedings of|Transactions of|Review of).*',
                line,
                re.IGNORECASE
            )
            if journal_match:
                return journal_match.group(0)

        return None
