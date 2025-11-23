# PDF Metadata Manager

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
