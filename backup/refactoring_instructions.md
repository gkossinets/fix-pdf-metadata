# PDF Metadata Manager - Implementation Instructions for Claude Code

## Project Overview

Refactor two existing PDF metadata scripts into a single, robust, interactive CLI tool following Unix philosophy: simple, focused, and composable.

**Goal**: Process academic PDF files by extracting metadata, searching Crossref API, presenting matches for user confirmation, updating PDF metadata, and renaming files in Zotero format.

---

## Project Structure

```
pdf_metadata_manager/
├── pdf_metadata_manager.py      # Main CLI entry point
├── core/
│   ├── __init__.py
│   ├── pdf_processor.py         # Text extraction, DOI detection
│   ├── crossref_client.py       # API client with retry logic
│   ├── metadata_updater.py      # PDF updates & renaming
│   └── filename_parser.py       # Parse filename hints
├── ui/
│   ├── __init__.py
│   └── interactive.py           # User prompts and display
├── utils/
│   ├── __init__.py
│   ├── timestamp_utils.py       # Cross-platform timestamps
│   └── logger.py                # Simple JSON logging
├── tests/
│   ├── __init__.py
│   ├── test_pdf_processor.py
│   ├── test_crossref_client.py
│   ├── test_filename_parser.py
│   └── test_metadata_updater.py
├── requirements.txt
└── README.md
```

---

## Dependencies (requirements.txt)

```
pikepdf>=8.0.0
PyPDF2>=3.0.0
requests>=2.31.0
pathvalidate>=3.0.0
pytesseract>=0.3.10
pdf2image>=1.16.3
```

---

# ISSUE #1: Core - Filename Parser

**Priority**: HIGH (no dependencies)  
**Estimated effort**: Small (~1-2 hours)

## Objective
Create a robust filename parser that extracts author, year, and title hints from various filename formats.

## Implementation Details

**File**: `core/filename_parser.py`

### Requirements

1. **Parse multiple filename formats**:
   ```python
   patterns = [
       r'^(.+?) - (\d{4}) - (.+)\.pdf$',           # Zotero: "Author - Year - Title"
       r'^([A-Za-z]+)_(\d{4})\.pdf$',              # "author_year"
       r'^([A-Za-z]+)(\d{4})\.pdf$',               # "authorYEAR"
       r'^([A-Za-z\s]+)\s+(\d{4})\.pdf$',          # "author year"
       r'^([A-Za-z\s]+)\((\d{4})\)\.pdf$',         # "author(year)"
       r'^(\d{4})_([A-Za-z]+)\.pdf$',              # "year_author"
   ]
   ```

2. **Return structured data**:
   ```python
   @dataclass
   class FilenameHints:
       author: Optional[str] = None
       year: Optional[str] = None
       title: Optional[str] = None
       confidence: float = 0.0  # 0.0 to 1.0
   ```

3. **Handle edge cases**:
   - Multiple authors: "Smith & Jones 2020.pdf"
   - Special characters: "O'Brien_2020.pdf"
   - Very long titles in Zotero format
   - No parseable information: "random_file.pdf" → return empty hints

### Public API

```python
def parse_filename(filename: str) -> FilenameHints:
    """
    Extract author, year, and title hints from a PDF filename.
    
    Args:
        filename: The PDF filename (with or without .pdf extension)
    
    Returns:
        FilenameHints object with extracted information and confidence score
    
    Examples:
        >>> parse_filename("Smith - 2020 - Machine Learning.pdf")
        FilenameHints(author="Smith", year="2020", title="Machine Learning", confidence=0.9)
        
        >>> parse_filename("jones_2019.pdf")
        FilenameHints(author="jones", year="2019", title=None, confidence=0.6)
        
        >>> parse_filename("random_file.pdf")
        FilenameHints(author=None, year=None, title=None, confidence=0.0)
    """
```

### Testing Requirements

Create `tests/test_filename_parser.py`:
- Test all supported formats
- Test edge cases (special chars, unicode, long names)
- Test invalid/unparseable filenames
- Test confidence scoring

---

# ISSUE #2: Core - PDF Processor

**Priority**: HIGH (depends on: none)  
**Estimated effort**: Large (~4-6 hours)

## Objective
Extract text, metadata, and DOIs from PDF files, with OCR fallback for scanned documents.

## Implementation Details

**File**: `core/pdf_processor.py`

### Requirements

1. **Combine best practices from both existing scripts**:
   - Use pikepdf as primary library
   - Fall back to PyPDF2 if pikepdf fails
   - OCR with Tesseract when text extraction yields insufficient text

2. **Multi-method DOI detection**:
   ```python
   doi_patterns = [
       r'(?:doi|DOI):?\s*(10\.\d{4,9}/[^\s"\'<>]+)',
       r'https?://doi\.org/(10\.\d{4,9}/[^\s"\'<>]+)',
       r'https?://(doi\.org/10\.\d{4,9}/[^\s"\'<>]+)',
       r'(?:^|\s|[^\w.])(10\.\d{4,9}/[^\s"\'<>]+)(?:$|\s|[^\w.])',
       r'doi\.org/(10\.\d{4,9}/[^\s"\'<>]+)'
   ]
   ```

3. **Extract academic metadata**:
   - Title (filter out headers, copyright notices)
   - Authors (look for name patterns after title)
   - Journal name
   - Publication info (volume, issue, pages)

4. **OCR Configuration**:
   - Configurable number of pages (default: 1)
   - Only use when needed (text extraction < 100 chars)
   - Show progress for OCR operations

### Public API

```python
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
    
    def __init__(self, use_ocr: bool = True, ocr_pages: int = 1):
        """
        Initialize PDF processor.
        
        Args:
            use_ocr: Enable OCR fallback for scanned documents
            ocr_pages: Number of pages to OCR (default: 1)
        """
    
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
            FileNotFoundError: If PDF file doesn't exist
            PDFProcessingError: If PDF cannot be read
        """
```

### Code Reuse Strategy

**From `set-pdf-metadata.py`**:
- `extract_text_with_ocr()` function
- `extract_info_from_pdf()` function (refactor and clean up)
- DOI pattern matching logic
- Title extraction with blacklist filtering
- Author detection logic

**Improvements needed**:
- Better error handling and specific exceptions
- Separate concerns (text extraction vs. metadata parsing)
- Type hints throughout
- Progress callbacks for OCR operations

### Testing Requirements

Create `tests/test_pdf_processor.py`:
- Test with real PDF samples (text-based, scanned, mixed)
- Test DOI detection with various formats
- Test OCR fallback trigger conditions
- Test error handling (corrupted PDFs, permission issues)
- Mock OCR for faster tests

---

# ISSUE #3: Core - Crossref Client

**Priority**: HIGH (depends on: none)  
**Estimated effort**: Medium (~3-4 hours)

## Objective
Robust Crossref API client with retry logic, better scoring, and connection error handling.

## Implementation Details

**File**: `core/crossref_client.py`

### Requirements

1. **Exponential backoff retry logic**:
   ```python
   - Retry on connection errors (ConnectionError, Timeout)
   - 3 attempts by default (configurable)
   - Backoff: 1s, 2s, 4s
   - Don't retry on 4xx errors (client errors)
   - Do retry on 5xx errors (server errors)
   ```

2. **Improved scoring algorithm**:
   ```python
   def calculate_match_score(crossref_item, query_data) -> float:
       """
       Score: 0.0 to 1.0
       
       Weights:
       - Title similarity: 0.5 (fuzzy matching, not just word overlap)
       - Year match: 0.2 (exact match or ±1 year)
       - Author match: 0.2 (family name in query)
       - Journal match: 0.1 (if journal info available)
       """
   ```

3. **Fuzzy string matching for titles**:
   - Use sequence matching or Levenshtein distance
   - Handle case insensitivity
   - Ignore common words (the, a, an, of, in, on, etc.)
   - Handle punctuation differences

4. **Rate limiting**:
   - Respect Crossref's rate limits
   - Add small delay between requests (0.5-1s)
   - Use polite pool with email in User-Agent

### Public API

```python
@dataclass
class CrossrefMatch:
    """A potential match from Crossref."""
    doi: str
    title: str
    authors: List[str]
    year: Optional[str]
    journal: Optional[str]
    score: float  # 0.0 to 1.0
    
    @property
    def confidence_level(self) -> str:
        """Return HIGH/MEDIUM/LOW based on score."""
        if self.score >= 0.80:
            return "HIGH"
        elif self.score >= 0.65:
            return "MEDIUM"
        else:
            return "LOW"

class CrossrefClient:
    """Client for Crossref API with retry logic and rate limiting."""
    
    def __init__(
        self,
        email: str,
        retries: int = 3,
        timeout: int = 30,
        backoff_factor: float = 1.0
    ):
        """
        Initialize Crossref client.
        
        Args:
            email: Your email (for polite pool and contact)
            retries: Number of retry attempts for failed requests
            timeout: Request timeout in seconds
            backoff_factor: Base delay for exponential backoff
        """
    
    def search(
        self,
        title: Optional[str] = None,
        author: Optional[str] = None,
        year: Optional[str] = None,
        max_results: int = 5
    ) -> List[CrossrefMatch]:
        """
        Search Crossref for matching publications.
        
        Args:
            title: Article title (most important)
            author: Author name or hint
            year: Publication year
            max_results: Maximum number of results to return
        
        Returns:
            List of CrossrefMatch objects sorted by score (highest first)
        
        Raises:
            CrossrefConnectionError: After all retries exhausted
            CrossrefAPIError: For non-retryable API errors
        """
    
    def fetch_metadata(self, doi: str) -> dict:
        """
        Fetch complete metadata for a given DOI.
        
        Args:
            doi: The DOI to look up
        
        Returns:
            Dictionary with complete metadata
        
        Raises:
            CrossrefConnectionError: After all retries exhausted
            CrossrefAPIError: For non-retryable API errors (404, etc.)
        """
```

### Code Reuse Strategy

**From `set-pdf-metadata.py`**:
- `search_doi_from_crossref()` function - refactor significantly
- `fetch_metadata_from_doi()` function - refactor
- Basic scoring logic - improve significantly

**From `fix-pdf-metadata.py`**:
- Better scoring with year/author matching

**New additions**:
- Retry/backoff decorator or context manager
- Fuzzy string matching for titles
- Connection error classification

### Testing Requirements

Create `tests/test_crossref_client.py`:
- Test successful searches with mock responses
- Test retry logic with simulated failures
- Test timeout handling
- Test scoring algorithm with known good/bad matches
- Test rate limiting (mock time.sleep)
- Integration test with real API (optional, slow)

---

# ISSUE #4: Core - Metadata Updater

**Priority**: HIGH (depends on: none)  
**Estimated effort**: Medium (~3-4 hours)

## Objective
Update PDF metadata and rename files while preserving timestamps across platforms.

## Implementation Details

**File**: `core/metadata_updater.py`

### Requirements

1. **Update PDF metadata**:
   - Use pikepdf primarily, PyPDF2 as fallback
   - Update both docinfo and XMP metadata
   - Clean format: no "Where from" or URL fields (macOS issue)
   - Handle DOI, ISBN, journal, authors, title, year

2. **Generate Zotero-style filenames**:
   ```python
   Format: "Author - Year - Title.pdf"
   
   Rules:
   - Single author: "Smith - 2020 - Title.pdf"
   - Two authors: "Smith & Jones - 2020 - Title.pdf"
   - Three+ authors: "Smith et al. - 2020 - Title.pdf"
   - Sanitize: remove quotes, apostrophes, commas, parentheses
   - Replace & with "and"
   - Truncate long titles (>100 chars) with "..."
   - Handle conflicts: add "(2)", "(3)" suffix
   ```

3. **Timestamp preservation**:
   - Cross-platform support (macOS, Linux, Windows)
   - Preserve modification time, access time
   - Preserve creation time on macOS (using SetFile if available)
   - Fallback gracefully if SetFile unavailable

4. **Optional backup**:
   - Create .bak copy before modifications
   - Preserve .bak timestamps too

### Public API

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

class MetadataUpdater:
    """Update PDF metadata and rename files."""
    
    def __init__(self, keep_backup: bool = False):
        """
        Initialize metadata updater.
        
        Args:
            keep_backup: Keep .bak copy of original files
        """
    
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
            True if successful, False otherwise
        
        Raises:
            PDFUpdateError: If update fails
        """
    
    def generate_zotero_filename(
        self,
        metadata: MetadataUpdate,
        original_path: str
    ) -> str:
        """
        Generate Zotero-style filename from metadata.
        
        Args:
            metadata: Metadata to use for filename
            original_path: Original file path (for fallback)
        
        Returns:
            Sanitized filename in format "Author - Year - Title.pdf"
        """
    
    def rename_file(
        self,
        old_path: str,
        new_filename: str,
        output_dir: Optional[str] = None
    ) -> str:
        """
        Rename file and handle conflicts.
        
        Args:
            old_path: Current file path
            new_filename: New filename (not full path)
            output_dir: Optional output directory (default: same dir)
        
        Returns:
            Final path of renamed file
        
        Raises:
            FileOperationError: If rename fails
        """
```

### Code Reuse Strategy

**From `set-pdf-metadata.py`**:
- `update_pdf_metadata()` function - combine both attempts
- `create_zotero_filename()` function - refactor
- `preserve_timestamps()` function
- `set_creation_date_macos()` function
- Filename sanitization logic with pathvalidate

**From `fix-pdf-metadata.py`**:
- Simplified metadata update approach
- Subject field formatting with DOI/ISBN

### Testing Requirements

Create `tests/test_metadata_updater.py`:
- Test metadata writing with real PDFs
- Test filename generation with various metadata
- Test conflict resolution (existing files)
- Test timestamp preservation (may need platform-specific tests)
- Test backup creation
- Test both pikepdf and PyPDF2 fallback

---

# ISSUE #5: UI - Interactive Interface

**Priority**: MEDIUM (depends on: #3 Crossref Client)  
**Estimated effort**: Medium (~2-3 hours)

## Objective
User-friendly interactive prompts for match selection, error handling, and confirmations.

## Implementation Details

**File**: `ui/interactive.py`

### Requirements

1. **Display match options**:
   ```
   Found 5 potential matches for: smith_2020.pdf
   
   Current filename info: Smith, 2020
   
   1. ★★★ HIGH CONFIDENCE (0.87)
      Title: Machine Learning Applications in Climate Science
      Authors: Smith, J.; Johnson, A.; Williams, B.
      Year: 2020
      Journal: Nature Climate Change
      DOI: 10.1038/s41558-020-12345
   
   2. ★★ MEDIUM CONFIDENCE (0.65)
      Title: Machine Learning for Environmental Prediction
      Authors: Smith, John
      Year: 2019
      Journal: Environmental Science & Technology
      DOI: 10.1021/acs.est.9b12345
   
   3. ★ LOW CONFIDENCE (0.54)
      ...
   
   Choose: [1-5] Select match | [s]kip | [r]etry | [m]anual DOI | [q]uit
   > 
   ```

2. **Handle user input**:
   - Validate input (1-N, s, r, m, q)
   - Handle EOF (Ctrl+D) gracefully
   - Case-insensitive commands
   - Clear error messages for invalid input

3. **Progress display** (batch processing):
   ```
   Processing 47 PDFs...
   [=========>              ] 23/47 (48.9%)
   
   ✓ Completed: 20
   ⚠ Skipped: 2
   ❌ Failed: 1
   ⏳ Remaining: 24
   
   Current: analyzing smith_2020.pdf...
   ```

4. **Error prompts**:
   ```
   ❌ Connection error for: smith_2020.pdf
   Error: Connection timeout after 3 attempts
   
   Options:
   [r] Retry now | [s] Skip and continue | [q] Quit
   > 
   ```

5. **Confirmation prompt**:
   ```
   📝 Review metadata update:
   
   File: smith_2020.pdf
   
   Metadata to write:
   ┌─────────────────────────────────────────────────────┐
   │ Title:   Machine Learning Applications...          │
   │ Authors: Smith, J.; Johnson, A.; Williams, B.      │
   │ Year:    2020                                       │
   │ Journal: Nature Climate Change                     │
   │ DOI:     10.1038/s41558-020-12345                  │
   └─────────────────────────────────────────────────────┘
   
   New filename: Smith et al - 2020 - Machine Learning Applications.pdf
   
   [a]pply | [s]kip | [q]uit
   > 
   ```

### Public API

```python
class InteractiveUI:
    """Interactive user interface for PDF processing."""
    
    def __init__(self, verbose: bool = False, quiet: bool = False):
        """
        Initialize UI.
        
        Args:
            verbose: Show detailed information
            quiet: Minimal output (errors and summary only)
        """
    
    def display_matches(
        self,
        matches: List[CrossrefMatch],
        filename: str,
        filename_hints: FilenameHints
    ) -> Optional[CrossrefMatch]:
        """
        Display matches and get user selection.
        
        Args:
            matches: List of potential matches
            filename: Original PDF filename
            filename_hints: Parsed filename information
        
        Returns:
            Selected CrossrefMatch, or None if skipped/quit
        
        Raises:
            UserQuitError: If user chooses to quit
        """
    
    def confirm_metadata(
        self,
        filename: str,
        metadata: MetadataUpdate,
        new_filename: str
    ) -> bool:
        """
        Show metadata and confirm with user.
        
        Args:
            filename: Original filename
            metadata: Metadata to write
            new_filename: Proposed new filename
        
        Returns:
            True if user approves, False if skip
        
        Raises:
            UserQuitError: If user chooses to quit
        """
    
    def handle_error(
        self,
        filename: str,
        error: Exception,
        retryable: bool = True
    ) -> str:
        """
        Display error and get user choice.
        
        Args:
            filename: File that caused error
            error: The exception
            retryable: Whether retry is an option
        
        Returns:
            User choice: 'retry', 'skip', or 'quit'
        """
    
    def show_progress(
        self,
        current: int,
        total: int,
        completed: int,
        skipped: int,
        failed: int,
        current_file: str
    ):
        """
        Display progress bar and statistics.
        
        Args:
            current: Current file number (1-indexed)
            total: Total files to process
            completed: Number of successfully completed files
            skipped: Number of skipped files
            failed: Number of failed files
            current_file: Name of file currently being processed
        """
    
    def print_summary(
        self,
        total: int,
        completed: int,
        skipped: int,
        failed: int,
        log_path: str
    ):
        """
        Print final summary.
        
        Args:
            total: Total files processed
            completed: Number successfully completed
            skipped: Number skipped
            failed: Number failed
            log_path: Path to log file
        """
```

### Testing Requirements

- Test match display formatting
- Test user input validation
- Test progress bar updates
- Mock input for automated testing

---

# ISSUE #6: Utils - Logging System

**Priority**: LOW (depends on: none)  
**Estimated effort**: Small (~1-2 hours)

## Objective
Simple JSON logging for session tracking and debugging.

## Implementation Details

**File**: `utils/logger.py`

### Requirements

1. **Session tracking**:
   ```json
   {
     "session": {
       "start_time": "2024-01-15T10:30:00",
       "end_time": "2024-01-15T10:45:23",
       "total_files": 47,
       "settings": {
         "use_ocr": true,
         "ocr_pages": 1,
         "keep_backup": false,
         "batch_mode": false
       }
     },
     "results": [...]
   }
   ```

2. **Per-file results**:
   ```json
   {
     "original_path": "/path/to/smith_2020.pdf",
     "status": "success",
     "matched_doi": "10.1038/...",
     "confidence": 0.87,
     "new_filename": "Smith et al - 2020 - Machine Learning.pdf",
     "metadata_updated": true,
     "renamed": true,
     "used_ocr": false,
     "timestamp": "2024-01-15T10:31:23"
   }
   ```

3. **Auto-generate log filename**:
   - Format: `pdf_metadata_log_YYYYMMDD_HHMMSS.json`
   - Place in current directory or custom path

### Public API

```python
class SessionLogger:
    """Log PDF processing session to JSON file."""
    
    def __init__(self, log_path: Optional[str] = None, settings: dict = None):
        """
        Initialize logger.
        
        Args:
            log_path: Custom log file path (default: auto-generate)
            settings: Settings dict to include in session metadata
        """
    
    def log_success(
        self,
        original_path: str,
        new_path: str,
        doi: str,
        confidence: float,
        used_ocr: bool = False
    ):
        """Log successful processing."""
    
    def log_skip(
        self,
        original_path: str,
        reason: str
    ):
        """Log skipped file."""
    
    def log_failure(
        self,
        original_path: str,
        error: str,
        attempts: int = 1
    ):
        """Log failed processing."""
    
    def close(self):
        """Finalize and write log file."""
```

---

# ISSUE #7: Utils - Timestamp Utilities

**Priority**: LOW (depends on: none)  
**Estimated effort**: Small (~1 hour)

## Objective
Cross-platform timestamp preservation utilities.

## Implementation Details

**File**: `utils/timestamp_utils.py`

### Requirements

1. **Preserve all timestamps**:
   - Modification time (mtime) - all platforms
   - Access time (atime) - all platforms
   - Creation time (birthtime/ctime) - macOS only

2. **Platform detection**:
   - Use `platform.system()` to detect OS
   - macOS: Try SetFile command if available
   - Windows: Use ctypes or similar
   - Linux: Best effort (no creation time)

3. **Graceful degradation**:
   - If SetFile not available, warn but continue
   - If any timestamp preservation fails, warn but don't fail entire operation

### Public API

```python
def preserve_timestamps(
    target_path: str,
    source_path: str
) -> bool:
    """
    Preserve file timestamps from source to target.
    
    Args:
        target_path: File to update timestamps on
        source_path: File to copy timestamps from
    
    Returns:
        True if all timestamps preserved, False if partial/failed
    """

def get_timestamps(file_path: str) -> dict:
    """
    Get all timestamps for a file.
    
    Returns:
        Dict with 'mtime', 'atime', 'ctime' keys
    """

def set_timestamps(
    file_path: str,
    timestamps: dict
) -> bool:
    """
    Set timestamps on a file.
    
    Args:
        file_path: File to update
        timestamps: Dict with 'mtime', 'atime', 'ctime' keys
    
    Returns:
        True if successful
    """
```

### Code Reuse

Extract and refactor from `set-pdf-metadata.py`:
- `preserve_timestamps()` function
- `set_creation_date_macos()` function

---

# ISSUE #8: Main - CLI Orchestrator

**Priority**: HIGH (depends on: #1-#7)  
**Estimated effort**: Medium (~3-4 hours)

## Objective
Main entry point that orchestrates all components and provides CLI interface.

## Implementation Details

**File**: `pdf_metadata_manager.py`

### Requirements

1. **CLI argument parsing**:
   ```python
   parser = argparse.ArgumentParser(
       description='Update PDF metadata from academic sources',
       formatter_class=argparse.RawDescriptionHelpFormatter,
       epilog='''
   Examples:
     %(prog)s paper.pdf --email "me@example.com"
     %(prog)s papers/ --batch --backup --recursive
     %(prog)s *.pdf --no-rename
     %(prog)s input/ -o organized/ --recursive
       '''
   )
   ```

2. **Environment variable support**:
   - Check `CROSSREF_EMAIL` env var
   - Warn if not set

3. **Processing pipeline**:
   ```python
   for each PDF:
       1. Parse filename hints
       2. Extract PDF metadata (with OCR if needed)
       3. Search Crossref (with retry)
       4. If batch mode:
          - Auto-accept if confidence > 0.80
          - Skip if confidence < 0.80
       5. Else interactive mode:
          - Display matches
          - Get user selection
       6. Confirm metadata (if not batch)
       7. Update PDF metadata
       8. Rename file
       9. Log result
   ```

4. **Error handling**:
   - Catch and handle specific exceptions
   - Fatal errors: stop processing, show clear message
   - Non-fatal: skip file, continue with next
   - Always finalize log before exit

5. **Signal handling**:
   - Catch Ctrl+C gracefully
   - Finalize log and show partial summary

### Main Function Structure

```python
def main():
    """Main entry point."""
    # 1. Parse arguments
    args = parse_arguments()
    
    # 2. Validate configuration
    validate_config(args)
    
    # 3. Initialize components
    pdf_processor = PDFProcessor(use_ocr=args.use_ocr, ocr_pages=args.ocr_pages)
    crossref_client = CrossrefClient(email=args.email, retries=args.retries)
    metadata_updater = MetadataUpdater(keep_backup=args.backup)
    ui = InteractiveUI(verbose=args.verbose, quiet=args.quiet)
    logger = SessionLogger(log_path=args.log, settings=vars(args))
    
    # 4. Collect files to process
    files = collect_pdf_files(args.input, recursive=args.recursive)
    
    # 5. Process each file
    stats = {'completed': 0, 'skipped': 0, 'failed': 0}
    try:
        for i, pdf_path in enumerate(files, 1):
            result = process_single_pdf(
                pdf_path=pdf_path,
                processor=pdf_processor,
                crossref=crossref_client,
                updater=metadata_updater,
                ui=ui,
                logger=logger,
                batch_mode=args.batch,
                rename=args.rename
            )
            stats[result] += 1
            
            if not args.quiet:
                ui.show_progress(i, len(files), **stats, current_file=pdf_path)
    
    except KeyboardInterrupt:
        print("\n⚠️  Processing interrupted by user")
    
    finally:
        logger.close()
        ui.print_summary(len(files), **stats, log_path=logger.log_path)

def process_single_pdf(...) -> str:
    """
    Process a single PDF file.
    
    Returns:
        'completed', 'skipped', or 'failed'
    """
```

### Testing Requirements

- Integration tests with mock components
- Test argument parsing
- Test file collection (directories, recursive, patterns)
- Test error handling and recovery
- Test signal handling (Ctrl+C)

---

# ISSUE #9: Documentation

**Priority**: LOW (depends on: all)  
**Estimated effort**: Small (~1-2 hours)

## Objective
Clear documentation for users and developers.

## Requirements

### README.md

Include:
1. **Project description** and goals
2. **Installation instructions** (pip install -r requirements.txt)
3. **System dependencies** (Tesseract, Poppler)
4. **Usage examples** with common scenarios
5. **CLI reference** (all flags explained)
6. **Troubleshooting** section
7. **Contributing** guidelines (if open source)
8. **License** information

### Inline Documentation

- All public functions/classes have docstrings
- Complex algorithms have explanation comments
- Type hints on all function signatures

---

# Implementation Order

## Phase 1: Core Components (Parallel)
- **ISSUE #1**: Filename Parser (start first, no dependencies)
- **ISSUE #2**: PDF Processor (start first, no dependencies)
- **ISSUE #3**: Crossref Client (start first, no dependencies)
- **ISSUE #4**: Metadata Updater (start first, no dependencies)

## Phase 2: Support Systems (Parallel)
- **ISSUE #6**: Logging System
- **ISSUE #7**: Timestamp Utilities

## Phase 3: User Interface (Sequential)
- **ISSUE #5**: Interactive Interface (needs Crossref Client)

## Phase 4: Integration (Sequential)
- **ISSUE #8**: Main CLI Orchestrator (needs everything)

## Phase 5: Polish
- **ISSUE #9**: Documentation

---

# Testing Strategy

1. **Unit tests** for each module (priority: HIGH)
2. **Integration tests** for main orchestrator (priority: MEDIUM)
3. **Manual testing** with real PDFs (priority: HIGH)
4. **CI/CD** setup optional (future enhancement)

---

# Code Quality Standards

- **Type hints**: All public APIs and complex functions
- **Docstrings**: Google or NumPy style
- **Error handling**: Specific exception types, clear messages
- **Logging**: Use Python's logging module for debug output
- **No silent failures**: Always inform user of problems
- **PEP 8**: Follow Python style guide

---

# Success Criteria

✅ Single command processes PDFs with metadata updates and renaming  
✅ Interactive mode allows user to confirm matches  
✅ Batch mode auto-accepts high-confidence matches (>0.80)  
✅ Connection errors handled with retry and clear messaging  
✅ Timestamps preserved across platforms  
✅ Comprehensive JSON logging  
✅ Clean, maintainable code with tests  
✅ Good documentation
