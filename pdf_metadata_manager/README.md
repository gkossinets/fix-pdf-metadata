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
