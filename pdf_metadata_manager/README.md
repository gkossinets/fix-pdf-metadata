# PDF Metadata Manager

A robust, modular Python CLI tool for updating PDF metadata from academic sources like Crossref.

## Project Overview

This project refactors the original `set-pdf-metadata.py` and `fix-pdf-metadata.py` scripts into a well-structured, maintainable codebase following Unix philosophy: simple, focused, and composable.

**Goal**: Process academic PDF files by extracting metadata, searching Crossref API, presenting matches for user confirmation, updating PDF metadata, and renaming files in Zotero format.

## Project Status

### Completed Components ✅

- **Issue #1**: Filename Parser (`core/filename_parser.py`)
- **Issue #2**: PDF Processor (`core/pdf_processor.py`)
- **Issue #3**: Crossref Client (`core/crossref_client.py`)
- **Issue #4**: Metadata Updater (`core/metadata_updater.py`)
- **Issue #5**: Interactive UI (`ui/interactive.py`)
- **Issue #6**: Logging System (`utils/logger.py`)
- **Issue #7**: Timestamp Utilities (`utils/timestamp_utils.py`)
- **Issue #8**: Main CLI Orchestrator (`pdf_metadata_manager.py`) ⭐ **NEW!**

### Completed ✅

All issues (#1-#9) are now complete!

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set your email for Crossref API
export CROSSREF_EMAIL="your-email@example.com"

# 3. Process a PDF file (from project root)
./pdf-metadata-manager path/to/paper.pdf

# 4. Or batch process a directory
./pdf-metadata-manager papers/ --batch --recursive
```

## Installation

```bash
pip install -r requirements.txt
```

### System Dependencies

For OCR support, you also need:

- **Tesseract OCR**: https://github.com/tesseract-ocr/tesseract
- **Poppler** (for pdf2image):
  - Windows: https://github.com/oschwartz10612/poppler-windows/releases
  - Linux: `sudo apt-get install poppler-utils`
  - macOS: `brew install poppler`

## Project Structure

```
pdf_metadata_manager/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── filename_parser.py         # ✅ Issue #1 - Parse filename hints
│   ├── pdf_processor.py           # ✅ Issue #2 - Extract text/metadata/DOI
│   ├── crossref_client.py         # ✅ Issue #3 - Crossref API client
│   └── metadata_updater.py        # ✅ Issue #4 - Update PDF metadata
├── ui/
│   ├── __init__.py
│   └── interactive.py             # 🚧 Issue #5 - Interactive prompts
├── utils/
│   ├── __init__.py
│   ├── timestamp_utils.py         # ✅ Used by Issue #4
│   └── logger.py                  # 📋 Issue #6 - JSON logging
├── tests/
│   ├── __init__.py
│   ├── test_filename_parser.py    # ✅ Comprehensive tests
│   ├── test_pdf_processor.py      # ✅ Comprehensive tests
│   ├── test_crossref_client.py    # ✅ Comprehensive tests
│   ├── test_metadata_updater.py   # ✅ Comprehensive tests
│   └── test_structure.py          # ✅ Structural validation
├── pdf_metadata_manager.py        # ✅ Issue #8 - Main CLI entry point
├── requirements.txt
└── README.md                      # This file
```

## Completed Features

### Issue #1: Filename Parser ✅

Extracts author, year, and title hints from various filename formats.

```python
from pdf_metadata_manager.core.filename_parser import parse_filename

hints = parse_filename("Smith - 2020 - Machine Learning.pdf")
# FilenameHints(author="Smith", year="2020", title="Machine Learning", confidence=0.9)
```

**Features:**
- Supports multiple filename patterns (Zotero, author_year, etc.)
- Confidence scoring (0.0 to 1.0)
- Handles edge cases (special chars, unicode, long names)

### Issue #2: PDF Processor ✅

Extracts text, metadata, and DOIs from PDF files with OCR fallback.

```python
from pdf_metadata_manager.core.pdf_processor import PDFProcessor

processor = PDFProcessor(use_ocr=True, ocr_pages=2)
metadata = processor.extract_metadata("paper.pdf")

print(f"Title: {metadata.title}")
print(f"DOI: {metadata.doi}")
print(f"Authors: {metadata.authors}")
```

**Features:**
- Multi-library text extraction (pikepdf → PyPDF2 fallback)
- Automatic OCR for scanned documents
- Multiple DOI pattern matching
- Academic metadata extraction (title, authors, journal)
- Robust error handling

### Issue #3: Crossref Client ✅

Robust Crossref API client with retry logic and improved scoring.

```python
from pdf_metadata_manager.core.crossref_client import CrossrefClient

client = CrossrefClient(email="your-email@example.com")
matches = client.search(
    title="Machine Learning Applications",
    author="Smith",
    year="2020",
    max_results=5
)

for match in matches:
    print(f"{match.confidence_level}: {match.title} ({match.score:.2f})")
```

**Features:**
- Exponential backoff retry logic (3 attempts: 1s, 2s, 4s)
- Improved fuzzy title matching with stopword filtering
- Weighted scoring: Title (50%), Year (20%), Author (20%), Journal (10%)
- Confidence levels: HIGH (≥0.80), MEDIUM (≥0.65), LOW (<0.65)
- Rate limiting (0.5s minimum between requests)
- Polite pool usage

### Issue #4: Metadata Updater ✅

Updates PDF metadata and renames files with timestamp preservation.

```python
from pdf_metadata_manager.core.metadata_updater import MetadataUpdater, MetadataUpdate

updater = MetadataUpdater(keep_backup=True)
metadata = MetadataUpdate(
    title="Machine Learning Applications",
    authors="Smith, J.; Johnson, A.; Williams, B.",
    year="2020",
    journal="Nature Climate Change",
    doi="10.1038/s41558-020-12345"
)

updater.update_metadata("paper.pdf", metadata)
new_filename = updater.generate_zotero_filename(metadata, "paper.pdf")
# Result: "Smith et al. - 2020 - Machine Learning Applications.pdf"

new_path = updater.rename_file("paper.pdf", new_filename)
```

**Features:**
- Update both docinfo and XMP metadata
- Zotero-style filename generation
- Author formatting: Single, "Author1 & Author2", "Author et al."
- Filename sanitization and truncation
- Conflict handling with (2), (3) suffixes
- Cross-platform timestamp preservation
- Optional backup (.bak) files

## Dependencies

```
pikepdf>=8.0.0
PyPDF2>=3.0.0
requests>=2.31.0
pathvalidate>=3.0.0
pytesseract>=0.3.10
pdf2image>=1.16.3
```

## Testing

```bash
# Run all tests
python -m unittest discover pdf_metadata_manager/tests

# Run specific module tests
python -m unittest pdf_metadata_manager/tests/test_filename_parser.py
python -m unittest pdf_metadata_manager/tests/test_pdf_processor.py
python -m unittest pdf_metadata_manager/tests/test_crossref_client.py
python -m unittest pdf_metadata_manager/tests/test_metadata_updater.py
```

## Code Quality

- ✅ Full type hints on all public APIs
- ✅ Comprehensive docstrings (Google style)
- ✅ Specific exception types with clear messages
- ✅ PEP 8 compliant
- ✅ No silent failures
- ✅ Extensive unit test coverage

## Platform Support

- **macOS**: Full support including creation time preservation
- **Linux**: Modification and access time preservation
- **Windows**: Modification and access time preservation

## Usage

The main CLI tool is now fully functional! Use the `pdf-metadata-manager` wrapper script in the root directory.

### Basic Usage

```bash
# Process a single PDF (interactive mode)
./pdf-metadata-manager paper.pdf --email "your-email@example.com"

# Or set email via environment variable
export CROSSREF_EMAIL="your-email@example.com"
./pdf-metadata-manager paper.pdf
```

### Batch Processing

```bash
# Process all PDFs in a directory (auto-accept high-confidence matches)
./pdf-metadata-manager papers/ --batch --email "me@example.com"

# Recursive processing with backups
./pdf-metadata-manager papers/ --batch --recursive --backup --email "me@example.com"
```

### Advanced Options

```bash
# Update metadata only (no renaming)
./pdf-metadata-manager *.pdf --no-rename --email "me@example.com"

# Disable OCR (faster, but won't work with scanned PDFs)
./pdf-metadata-manager paper.pdf --no-ocr --email "me@example.com"

# OCR first 3 pages (better accuracy for scanned documents)
./pdf-metadata-manager scanned.pdf --ocr-pages 3 --email "me@example.com"

# Verbose mode (see detailed processing info)
./pdf-metadata-manager paper.pdf --verbose --email "me@example.com"

# Quiet mode (only errors and summary)
./pdf-metadata-manager papers/ --batch --quiet --email "me@example.com"

# Custom log file location
./pdf-metadata-manager papers/ --batch --log ~/logs/processing.json --email "me@example.com"
```

### CLI Options

```
Required:
  input                 PDF file, directory, or glob pattern

Optional:
  --email, -e          Email for Crossref API (or set CROSSREF_EMAIL)
  --batch, -b          Auto-accept matches with confidence >= 0.80
  --recursive, -r      Search directories recursively
  --no-rename          Update metadata only, don't rename files
  --backup             Keep .bak copy of original files
  --no-ocr             Disable OCR for scanned documents
  --ocr-pages N        Number of pages to OCR (default: 1)
  --retries N          Crossref API retry attempts (default: 3)
  --log PATH           Custom log file path
  --verbose, -v        Show detailed information
  --quiet, -q          Minimal output (errors and summary only)
```

### Interactive Mode Features

When running without `--batch`, the tool provides:

- **Match selection**: Review multiple Crossref matches with confidence scores
- **Metadata preview**: Confirm metadata before applying
- **Error handling**: Choose to retry, skip, or quit on errors
- **Progress tracking**: See real-time progress for batch operations

### Batch Mode Behavior

With `--batch` flag:

- Automatically accepts matches with score >= 0.80 (HIGH confidence)
- Skips matches with score < 0.80
- No user interaction required
- Faster processing for large collections

### Log Files

Every session creates a JSON log file (default: `pdf_metadata_log_YYYYMMDD_HHMMSS.json`) containing:

- Session settings and timestamps
- Per-file results (success/skip/failure)
- Matched DOIs and confidence scores
- Error messages for failed files

Example log entry:
```json
{
  "original_path": "/path/to/paper.pdf",
  "status": "success",
  "matched_doi": "10.1038/s41558-020-12345",
  "confidence": 0.87,
  "new_filename": "Smith et al. - 2020 - Machine Learning Applications.pdf",
  "used_ocr": false,
  "timestamp": "2025-01-15T10:31:23"
}
```

## Troubleshooting

See the main [README.md](../README.md#troubleshooting) for comprehensive troubleshooting guides including:

- Dependency installation issues
- OCR and Tesseract problems
- Crossref API connection errors
- Permission and file access issues
- Platform-specific considerations

## License

MIT License - See [LICENSE](../README.md#license) for full text.

## Contributing

We welcome contributions! See the main [README.md](../README.md#contributing) for:

- How to contribute
- Development setup
- Coding standards
- Testing requirements
- Areas for contribution

For architecture details, consult [`../refactoring_instructions.md`](../refactoring_instructions.md).
