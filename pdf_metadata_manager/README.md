# PDF Metadata Manager

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
