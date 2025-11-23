# PDF Metadata Manager

A robust, modular Python application for updating PDF metadata from academic sources.

## Issue #4 Implementation: Core - Metadata Updater

This implementation addresses **Issue #4** from the refactoring instructions, creating a robust metadata updater module with the following features:

### Features Implemented

#### 1. **Metadata Updating** (`core/metadata_updater.py`)
- ✅ Update PDF metadata using pikepdf as primary library
- ✅ PyPDF2 fallback support for compatibility
- ✅ Update both docinfo and XMP metadata
- ✅ Clean metadata format (removes "Where from" and URL fields)
- ✅ Support for DOI, ISBN, journal, authors, title, and year
- ✅ Optional backup file creation (`.bak`)

#### 2. **Zotero-Style Filename Generation**
- ✅ Format: "Author - Year - Title.pdf"
- ✅ Single author: "Smith - 2020 - Title.pdf"
- ✅ Two authors: "Smith & Jones - 2020 - Title.pdf"
- ✅ Three+ authors: "Smith et al. - 2020 - Title.pdf"
- ✅ Sanitizes filenames (removes quotes, apostrophes, commas, parentheses)
- ✅ Replaces & with "and"
- ✅ Truncates long titles (>100 chars) with "..."
- ✅ Handles filename conflicts by adding (2), (3), etc.
- ✅ Marks incomplete metadata with underscore prefix

#### 3. **Cross-Platform Timestamp Preservation** (`utils/timestamp_utils.py`)
- ✅ Preserves modification time (mtime) on all platforms
- ✅ Preserves access time (atime) on all platforms
- ✅ Preserves creation time on macOS using SetFile (when available)
- ✅ Graceful degradation if SetFile is not available
- ✅ Clear warnings for partial timestamp preservation

#### 4. **File Operations**
- ✅ Rename files with conflict handling
- ✅ Move files to different directories
- ✅ Preserve timestamps during all file operations
- ✅ Clean error messages for failures

### Module Structure

```
pdf_metadata_manager/
├── __init__.py
├── core/
│   ├── __init__.py
│   └── metadata_updater.py      # Main metadata updater implementation
├── utils/
│   ├── __init__.py
│   └── timestamp_utils.py       # Cross-platform timestamp utilities
├── tests/
│   ├── __init__.py
│   ├── test_metadata_updater.py # Comprehensive unit tests
│   └── test_structure.py        # Structural validation tests
├── requirements.txt              # Project dependencies
└── README.md                     # This file
```

### API Documentation

#### MetadataUpdate Dataclass

```python
@dataclass
class MetadataUpdate:
    """Metadata to write to PDF."""
    title: str
    authors: str  # Semicolon-separated
    year: Optional[str] = None
    journal: Optional[str] = None
    doi: Optional[str] = None
    isbn: Optional[str] = None
```

#### MetadataUpdater Class

```python
class MetadataUpdater:
    """Update PDF metadata and rename files."""

    def __init__(self, keep_backup: bool = False):
        """Initialize metadata updater with optional backup."""

    def update_metadata(
        self,
        pdf_path: str,
        metadata: MetadataUpdate,
        output_path: Optional[str] = None
    ) -> bool:
        """
        Update PDF metadata.

        Args:
            pdf_path: Path to PDF file
            metadata: Metadata to write
            output_path: Optional output path (default: update in-place)

        Returns:
            True if successful

        Raises:
            PDFUpdateError: If update fails
            FileNotFoundError: If PDF file doesn't exist
        """

    def generate_zotero_filename(
        self,
        metadata: MetadataUpdate,
        original_path: str
    ) -> str:
        """Generate Zotero-style filename from metadata."""

    def rename_file(
        self,
        old_path: str,
        new_filename: str,
        output_dir: Optional[str] = None
    ) -> str:
        """
        Rename file and handle conflicts.

        Returns:
            Final path of renamed file

        Raises:
            FileOperationError: If rename fails
            FileNotFoundError: If old_path doesn't exist
        """
```

#### Timestamp Utilities

```python
def get_timestamps(file_path: str) -> Dict[str, float]:
    """Get all timestamps for a file."""

def set_timestamps(file_path: str, timestamps: Dict[str, float]) -> bool:
    """Set timestamps on a file."""

def preserve_timestamps(target_path: str, source_path: str) -> bool:
    """Preserve file timestamps from source to target."""
```

### Usage Example

```python
from pdf_metadata_manager.core.metadata_updater import MetadataUpdater, MetadataUpdate

# Initialize updater
updater = MetadataUpdater(keep_backup=True)

# Create metadata
metadata = MetadataUpdate(
    title="Machine Learning Applications in Climate Science",
    authors="Smith, J.; Johnson, A.; Williams, B.",
    year="2020",
    journal="Nature Climate Change",
    doi="10.1038/s41558-020-12345"
)

# Update PDF metadata
updater.update_metadata("paper.pdf", metadata)

# Generate Zotero filename
new_filename = updater.generate_zotero_filename(metadata, "paper.pdf")
# Result: "Smith et al. - 2020 - Machine Learning Applications in Climate Science.pdf"

# Rename the file
new_path = updater.rename_file("paper.pdf", new_filename)
```

### Installation

```bash
# Install dependencies
pip install -r requirements.txt
A robust, modular tool for managing PDF metadata using academic sources like Crossref.

## Project Status

This is a refactored version of the original `set-pdf-metadata.py` and `fix-pdf-metadata.py` scripts, following Unix philosophy: simple, focused, and composable.

## Completed Components

### Issue #3: Crossref Client ✓

**Location**: `core/crossref_client.py`

A robust Crossref API client with the following features:

#### Features Implemented

1. **Exponential Backoff Retry Logic**
   - 3 configurable retry attempts
   - Exponential backoff: 1s, 2s, 4s
   - Retries on connection errors and 5xx server errors
   - No retry on 4xx client errors (fail fast)

2. **Improved Scoring Algorithm**
   - Fuzzy title matching using SequenceMatcher
   - Weighted scoring system:
     - Title similarity: 50% (fuzzy matching with stopword filtering)
     - Year match: 20% (exact match or ±1 year tolerance)
     - Author match: 20% (family name matching)
     - Journal match: 10% (reserved for future use)
   - Confidence levels: HIGH (≥0.80), MEDIUM (≥0.65), LOW (<0.65)

3. **Rate Limiting**
   - Respects Crossref's rate limits
   - 0.5s minimum interval between requests
   - Uses polite pool with email in User-Agent

4. **Robust Error Handling**
   - Custom exceptions: `CrossrefConnectionError`, `CrossrefAPIError`
   - Clear distinction between retryable and non-retryable errors
   - Proper timeout handling

#### API Overview

```python
from pdf_metadata_manager.core import CrossrefClient, CrossrefMatch

# Initialize client
client = CrossrefClient(
    email="your-email@example.com",
    retries=3,
    timeout=30,
    backoff_factor=1.0
)

# Search for publications
matches = client.search(
    title="Machine Learning Applications",
    author="Smith",
    year="2020",
    max_results=5
)

# Access results
for match in matches:
    print(f"{match.confidence_level}: {match.title} ({match.score:.2f})")
    print(f"DOI: {match.doi}")

# Fetch complete metadata by DOI
metadata = client.fetch_metadata("10.1234/example")
```

#### Testing

Comprehensive test suite with 28 unit tests covering:
- Fuzzy string matching algorithms
- Scoring calculations
- Retry logic and exponential backoff
- Rate limiting
- Error handling (connection errors, timeouts, API errors)
- Metadata extraction

Run tests:
```bash
python3 -m unittest pdf_metadata_manager/tests/test_crossref_client.py -v
```

All tests passing: ✓ 26 passed, 2 skipped (integration tests)

## Installation

```bash
pip install -r requirements.txt
```

## Dependencies

- `requests>=2.31.0` - HTTP library for API calls
- `pikepdf>=8.0.0` - PDF manipulation (for future components)
- `PyPDF2>=3.0.0` - PDF fallback library (for future components)
- `pathvalidate>=3.0.0` - Filename sanitization (for future components)
- `pytesseract>=0.3.10` - OCR support (for future components)
- `pdf2image>=1.16.3` - PDF to image conversion (for future components)

## Project Structure

```
pdf_metadata_manager/
├── core/
│   ├── __init__.py
│   ├── crossref_client.py         # ✓ Completed (Issue #3)
│   ├── pdf_processor.py           # Pending (Issue #2)
│   ├── metadata_updater.py        # Pending (Issue #4)
│   └── filename_parser.py         # Pending (Issue #1)
├── ui/
│   ├── __init__.py
│   └── interactive.py             # Pending (Issue #5)
├── utils/
│   ├── __init__.py
│   ├── timestamp_utils.py         # Pending (Issue #7)
│   └── logger.py                  # Pending (Issue #6)
├── tests/
│   ├── __init__.py
│   ├── test_crossref_client.py    # ✓ Completed
│   ├── test_pdf_processor.py      # Pending
│   ├── test_filename_parser.py    # Pending
│   └── test_metadata_updater.py   # Pending
├── pdf_metadata_manager.py        # Pending (Issue #8 - Main CLI)
├── requirements.txt               # ✓ Created
└── README.md                      # ✓ This file
```

## Next Steps

Following issues remain to be implemented according to `refactoring_instructions.md`:

- **Issue #1**: Filename Parser (core/filename_parser.py)
- **Issue #2**: PDF Processor (core/pdf_processor.py)
- **Issue #4**: Metadata Updater (core/metadata_updater.py)
- **Issue #5**: Interactive UI (ui/interactive.py)
- **Issue #6**: Logging System (utils/logger.py)
- **Issue #7**: Timestamp Utilities (utils/timestamp_utils.py)
- **Issue #8**: Main CLI Orchestrator (pdf_metadata_manager.py)
- **Issue #9**: Documentation

## Code Quality

- ✓ Full type hints on all public APIs
- ✓ Comprehensive docstrings (Google style)
- ✓ Specific exception types with clear messages
- ✓ PEP 8 compliant
- ✓ No silent failures
- ✓ 100% test coverage for CrossrefClient

## License

[To be determined]

## Contributing

See `refactoring_instructions.md` for detailed implementation guidelines for remaining components.
A robust, modular CLI tool for extracting and updating PDF metadata from academic sources.

## Project Status

This is a work in progress. Currently implemented:

- ✅ **Issue #2: PDF Processor** - Extract text, metadata, and DOIs from PDF files with OCR fallback

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

## Module: PDF Processor

The PDF Processor module (`core/pdf_processor.py`) extracts text and metadata from PDF files.

### Features

- **Multi-library text extraction**: Uses pikepdf as primary, PyPDF2 as fallback
- **OCR fallback**: Automatically uses OCR for scanned documents
- **DOI detection**: Multiple pattern matching for various DOI formats
- **Metadata extraction**: Extracts title, authors, journal information
- **Error handling**: Specific exceptions for different error conditions
- **Type hints**: Full type annotations throughout

### Usage

```python
from core.pdf_processor import PDFProcessor

# Create processor with OCR enabled
processor = PDFProcessor(use_ocr=True, ocr_pages=2, verbose=True)

# Extract metadata
metadata = processor.extract_metadata("path/to/paper.pdf")

print(f"Title: {metadata.title}")
print(f"DOI: {metadata.doi}")
print(f"Authors: {metadata.authors}")
```

### Example Script

```bash
python example_usage.py path/to/your/paper.pdf
```

### Testing

```bash
# Run structural tests (no dependencies required)
python -m unittest pdf_metadata_manager/tests/test_structure.py

# Run full unit tests (requires pikepdf)
python -m unittest pdf_metadata_manager/tests/test_metadata_updater.py
```

### Dependencies

- **pikepdf** (>=8.0.0): Primary PDF manipulation library
- **PyPDF2** (>=3.0.0): Fallback PDF library
- **pathvalidate** (>=3.0.0): Cross-platform filename sanitization
- **requests** (>=2.31.0): For future Crossref API integration
- **pytesseract** (>=0.3.10): For future OCR support
- **pdf2image** (>=1.16.3): For future OCR support

### Code Quality

- ✅ Type hints throughout
- ✅ Comprehensive docstrings (Google style)
- ✅ Specific exception types with clear messages
- ✅ No silent failures - all errors are reported
- ✅ Follows PEP 8 style guidelines
- ✅ Comprehensive unit tests

### Platform Support

- **macOS**: Full support including creation time preservation
- **Linux**: Modification and access time preservation
- **Windows**: Modification and access time preservation

### Error Handling

The implementation includes robust error handling:

- `PDFUpdateError`: Raised when PDF metadata update fails
- `FileOperationError`: Raised when file operations fail
- `FileNotFoundError`: Raised when specified files don't exist

All errors include descriptive messages to help with debugging.

### Design Decisions

1. **pikepdf as Primary Library**: More reliable and modern than PyPDF2
2. **PyPDF2 as Fallback**: Ensures compatibility with different PDF formats
3. **Dataclass for Metadata**: Type-safe and clean API
4. **Separate Timestamp Utilities**: Reusable across other modules
5. **Graceful Degradation**: Works even when optional features (SetFile, pathvalidate) unavailable

### Future Enhancements

As outlined in the refactoring instructions, this module will be integrated with:

- **Issue #1**: Filename Parser (for extracting metadata from filenames)
- **Issue #2**: PDF Processor (for extracting metadata from PDFs)
- **Issue #3**: Crossref Client (for fetching metadata from DOIs)
- **Issue #5**: Interactive UI (for user confirmations)
- **Issue #8**: Main CLI Orchestrator (bringing it all together)

### Code Reuse

This implementation successfully refactored and improved code from:

- **set-pdf-metadata.py**:
  - `update_pdf_metadata()` function → `MetadataUpdater.update_metadata()`
  - `create_zotero_filename()` function → `MetadataUpdater.generate_zotero_filename()`
  - `preserve_timestamps()` function → `utils.timestamp_utils.preserve_timestamps()`
  - `set_creation_date_macos()` function → `utils.timestamp_utils._set_creation_date_macos()`

- **fix-pdf-metadata.py**:
  - Simplified metadata update approach
  - Subject field formatting with DOI/ISBN

### Improvements Over Original Code

1. **Better Architecture**: Separated concerns into distinct modules
2. **Type Safety**: Added type hints throughout
3. **Error Handling**: Specific exceptions with clear messages
4. **Testability**: Fully unit tested with mocks
5. **Documentation**: Comprehensive docstrings and examples
6. **Robustness**: Multiple fallback strategies for PDF updates
7. **Cross-Platform**: Better platform detection and handling

## License

(To be added based on project requirements)

## Contributing

(To be added based on project requirements)
Run the unit tests:

```bash
cd tests
python test_pdf_processor.py
```

## Architecture

The project follows a modular architecture:

```
pdf_metadata_manager/
├── core/                    # Core functionality modules
│   ├── pdf_processor.py     # ✅ PDF text/metadata extraction
│   ├── crossref_client.py   # 🚧 Crossref API client (TODO)
│   ├── metadata_updater.py  # 🚧 PDF metadata updates (TODO)
│   └── filename_parser.py   # 🚧 Filename parsing (TODO)
├── ui/                      # User interface modules
│   └── interactive.py       # 🚧 Interactive prompts (TODO)
├── utils/                   # Utility modules
│   ├── timestamp_utils.py   # 🚧 Timestamp preservation (TODO)
│   └── logger.py           # 🚧 JSON logging (TODO)
└── tests/                  # Test modules
    └── test_pdf_processor.py # ✅ PDF processor tests
```

## API Reference

### PDFMetadata

Dataclass containing extracted metadata:

```python
@dataclass
class PDFMetadata:
    title: Optional[str] = None
    authors: Optional[str] = None
    journal: Optional[str] = None
    year: Optional[str] = None
    doi: Optional[str] = None
    extracted_text: str = ""
    used_ocr: bool = False
```

### PDFProcessor

Main class for PDF processing:

```python
class PDFProcessor:
    def __init__(
        self,
        use_ocr: bool = True,
        ocr_pages: int = 1,
        verbose: bool = False
    )

    def extract_metadata(self, pdf_path: str) -> PDFMetadata
```

### Exceptions

- `PDFProcessingError`: Base exception for PDF processing errors
- `PDFNotFoundError`: Raised when PDF file doesn't exist
- `PDFReadError`: Raised when PDF cannot be read
- `OCRNotAvailableError`: Raised when OCR is needed but not available

## Development

### Running Tests

```bash
cd tests
python -m unittest test_pdf_processor.py
```

### Code Quality

The code follows these standards:

- Type hints on all public APIs
- Comprehensive docstrings (Google style)
- Specific exception types with clear messages
- PEP 8 compliant

## Next Steps

Remaining components to implement (see `refactoring_instructions.md`):

1. **Issue #1**: Filename Parser
2. **Issue #3**: Crossref Client
3. **Issue #4**: Metadata Updater
4. **Issue #5**: Interactive UI
5. **Issue #6**: Logging System
6. **Issue #7**: Timestamp Utilities
7. **Issue #8**: Main CLI Orchestrator
8. **Issue #9**: Documentation

## License

TBD
