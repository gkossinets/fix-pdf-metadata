# PDF Metadata Manager

A robust, modular Python CLI tool for updating PDF metadata from academic sources like Crossref.

## Quick Start

```bash
# 1. Install dependencies
pip install -r pdf_metadata_manager/requirements.txt

# 2. Set your email for Crossref API
export CROSSREF_EMAIL="your-email@example.com"

# 3. Process a PDF file
./pdf-metadata-manager path/to/paper.pdf

# 4. Or batch process a directory
./pdf-metadata-manager papers/ --batch --recursive
```

## What This Tool Does

1. **Extracts metadata** from PDF files (title, authors, DOI)
2. **Searches Crossref API** for matching publications
3. **Presents matches** for user confirmation (or auto-accepts in batch mode)
4. **Updates PDF metadata** with correct bibliographic information
5. **Renames files** in Zotero format: "Author - Year - Title.pdf"
6. **Preserves timestamps** across platforms (macOS, Linux, Windows)
7. **Logs everything** to JSON for tracking and debugging

## Features

- 🔍 **Smart metadata extraction** with OCR fallback for scanned PDFs
- 🎯 **Fuzzy matching** with confidence scores (HIGH/MEDIUM/LOW)
- 🤖 **Batch mode** for processing large collections automatically
- 💬 **Interactive mode** for careful, one-by-one review
- 📝 **Comprehensive logging** in JSON format
- 🔄 **Retry logic** for network errors
- ⚡ **Cross-platform** timestamp preservation

## Documentation

Full documentation is available in [`pdf_metadata_manager/README.md`](pdf_metadata_manager/README.md), including:

- Detailed usage examples
- All CLI options
- Interactive vs batch mode comparison
- Log file format
- Module APIs for programmatic use

## Project Structure

```
pdf_metadata_manager/
├── core/                   # Core processing modules
│   ├── filename_parser.py      # Parse filename hints
│   ├── pdf_processor.py        # Extract text/metadata/DOI
│   ├── crossref_client.py      # Crossref API client
│   └── metadata_updater.py     # Update PDFs and rename
├── ui/
│   └── interactive.py          # Interactive user interface
├── utils/
│   ├── logger.py               # JSON session logging
│   └── timestamp_utils.py      # Cross-platform timestamps
└── pdf_metadata_manager.py     # Main CLI entry point
```

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

### Python Dependencies

Install all required Python packages:

```bash
pip install -r pdf_metadata_manager/requirements.txt
```

This installs:
- `pikepdf>=8.0.0` - Primary PDF manipulation library
- `PyPDF2>=3.0.0` - Fallback PDF library
- `requests>=2.31.0` - HTTP client for Crossref API
- `pathvalidate>=3.0.0` - Filename sanitization
- `pytesseract>=0.3.10` - OCR wrapper (optional)
- `pdf2image>=1.16.3` - PDF to image conversion (optional)

### System Dependencies (Optional)

For OCR support with scanned PDFs, install:

**Tesseract OCR**

- **macOS**: `brew install tesseract`
- **Ubuntu/Debian**: `sudo apt-get install tesseract-ocr`
- **Windows**: Download from [GitHub](https://github.com/tesseract-ocr/tesseract) or use installer

**Poppler** (required for pdf2image)

- **macOS**: `brew install poppler`
- **Ubuntu/Debian**: `sudo apt-get install poppler-utils`
- **Windows**: Download from [oschwartz10612's releases](https://github.com/oschwartz10612/poppler-windows/releases), extract, and add to PATH

### Verify Installation

```bash
# Check if Tesseract is installed
tesseract --version

# Check if Poppler is installed
pdfinfo -v

# Run a quick test
./pdf-metadata-manager --help
```

## Usage Examples

### Interactive Mode (default)

```bash
./pdf-metadata-manager paper.pdf --email "me@example.com"
```

You'll be able to:
- Review multiple Crossref matches
- See confidence scores
- Confirm metadata before applying
- Handle errors interactively

### Batch Mode

```bash
./pdf-metadata-manager papers/ --batch --recursive --email "me@example.com"
```

- Auto-accepts matches with score >= 0.80
- Skips low-confidence matches
- No user interaction needed
- Perfect for processing large collections

### Advanced Options

```bash
# Keep backups of original files
./pdf-metadata-manager papers/ --backup --email "me@example.com"

# Update metadata only (don't rename)
./pdf-metadata-manager *.pdf --no-rename --email "me@example.com"

# Increase OCR pages for better accuracy
./pdf-metadata-manager scanned.pdf --ocr-pages 3 --email "me@example.com"

# Quiet mode for automation
./pdf-metadata-manager papers/ --batch --quiet --email "me@example.com"
```

## Common Workflows

### Workflow 1: Organize Downloaded Papers

You've just downloaded a bunch of academic papers with random filenames. You want to organize them with proper metadata and Zotero-style naming.

```bash
# Set your email once
export CROSSREF_EMAIL="your-email@example.com"

# Process all PDFs in Downloads folder (interactive mode)
./pdf-metadata-manager ~/Downloads/*.pdf

# The tool will:
# 1. Extract metadata from each PDF
# 2. Search Crossref for matches
# 3. Show you the top matches with confidence scores
# 4. Let you confirm before applying changes
# 5. Update metadata and rename to "Author - Year - Title.pdf"
# 6. Create a log file with all actions taken
```

### Workflow 2: Clean Up Existing Library

You have a large collection of PDFs with inconsistent metadata. You want to batch process them with high confidence matches only.

```bash
# Batch mode: auto-accept HIGH confidence matches (≥0.80), skip low confidence
./pdf-metadata-manager ~/Papers/ --batch --recursive --backup

# The --backup flag keeps .bak copies of originals
# The --recursive flag processes subdirectories
# Low confidence matches are skipped and logged
```

### Workflow 3: Process Scanned Papers

You have scanned PDF papers without searchable text. You need OCR to extract metadata.

```bash
# Process with OCR enabled (scans first 3 pages for better accuracy)
./pdf-metadata-manager scanned_papers/ --ocr-pages 3 --batch

# The tool will:
# 1. Detect that PDFs lack searchable text
# 2. Use OCR to extract text from first 3 pages
# 3. Search for DOI and metadata in OCR'd text
# 4. Proceed with normal workflow
```

### Workflow 4: Update Metadata Only

You like your current filenames but want to fix the PDF metadata for better organization in reference managers.

```bash
# Update metadata without renaming files
./pdf-metadata-manager my_papers/ --no-rename --recursive

# Files keep their current names
# But PDF metadata (title, authors, DOI, etc.) is updated
```

### Workflow 5: Automation Pipeline

You want to automatically process papers in a watched directory (e.g., for a research group).

```bash
# Create a cron job or scheduled task
./pdf-metadata-manager /shared/new_papers/ \
    --batch \
    --backup \
    --quiet \
    --log /shared/logs/metadata_$(date +%Y%m%d).json

# --quiet: minimal output (good for cron)
# --log: custom log location with date
# Combine with inotify (Linux) or fswatch (macOS) for real-time processing
```

### Workflow 6: Review and Retry

After a batch run, you want to review the log and retry failed files.

```bash
# First run (batch mode)
./pdf-metadata-manager papers/ --batch

# Check the log file
cat pdf_metadata_log_*.json | jq '.results[] | select(.status=="failed")'

# Extract failed files and retry interactively
# (manual step - extract paths from JSON, create a list)
./pdf-metadata-manager failed_file1.pdf failed_file2.pdf

# Or retry with more aggressive OCR
./pdf-metadata-manager failed_file1.pdf --ocr-pages 5 --verbose
```

## Development

This project follows a clean, modular architecture that consolidates functionality into well-organized modules.

All modules have:
- Full type hints
- Comprehensive docstrings
- Extensive unit tests
- Specific exception types
- PEP 8 compliance

Run tests:
```bash
python -m unittest discover pdf_metadata_manager/tests
```

## Troubleshooting

### Common Issues

#### 1. "No module named 'pikepdf'" or other import errors

**Problem**: Python dependencies not installed.

**Solution**:
```bash
pip install -r pdf_metadata_manager/requirements.txt
```

If you're using a virtual environment, make sure it's activated first.

#### 2. "CROSSREF_EMAIL environment variable not set"

**Problem**: The Crossref API requires an email address.

**Solution**: Either set the environment variable or use the `--email` flag:
```bash
export CROSSREF_EMAIL="your-email@example.com"
# Or
./pdf-metadata-manager paper.pdf --email "your-email@example.com"
```

#### 3. OCR not working ("pytesseract.TesseractNotFoundError")

**Problem**: Tesseract is not installed or not in PATH.

**Solution**:
- **macOS**: `brew install tesseract`
- **Linux**: `sudo apt-get install tesseract-ocr`
- **Windows**: Install Tesseract and add to PATH, or disable OCR with `--no-ocr`

#### 4. "Unable to get page count" or pdf2image errors

**Problem**: Poppler is not installed.

**Solution**:
- **macOS**: `brew install poppler`
- **Linux**: `sudo apt-get install poppler-utils`
- **Windows**: Download Poppler binaries and add to PATH, or disable OCR with `--no-ocr`

#### 5. Connection timeout errors

**Problem**: Network issues or Crossref API is slow/unavailable.

**Solution**:
- Check your internet connection
- Try again later (Crossref may be experiencing high load)
- Increase retry attempts: `--retries 5`
- The tool will automatically retry with exponential backoff (1s, 2s, 4s)

#### 6. No matches found for PDFs

**Problem**: Crossref might not have metadata, or filename/PDF content doesn't match.

**Solution**:
- Ensure the PDF is an academic paper (Crossref focuses on scholarly content)
- Try renaming the file to include author and year (e.g., "Smith_2020.pdf")
- If you know the DOI, you could manually add it to the PDF metadata
- Check if the PDF has searchable text (not a scanned image)

#### 7. Permission denied when writing files

**Problem**: Insufficient permissions to modify files or create backups.

**Solution**:
- Ensure you have write permissions for the directory
- On Unix systems: `chmod u+w directory/`
- Try running from a directory you own

#### 8. File timestamp not preserved on macOS

**Problem**: Creation time preservation requires `SetFile` (part of Xcode Command Line Tools).

**Solution**:
```bash
xcode-select --install
```

This is optional - the tool will continue without creation time preservation if `SetFile` is unavailable.

### Getting Help

If you encounter issues not listed here:

1. Check the log file (`pdf_metadata_log_*.json`) for detailed error messages
2. Run with `--verbose` flag to see detailed processing information
3. Open an issue on the project repository with:
   - Error message and stack trace
   - Operating system and Python version
   - Steps to reproduce the issue
   - Sample PDF (if possible and appropriate)

## License

MIT License

Copyright (c) 2025 PDF Metadata Manager Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Contributing

We welcome contributions! This project follows a clean, modular architecture with well-defined module responsibilities.

### How to Contribute

1. **Fork the repository** and create a feature branch
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Follow the coding standards**:
   - Use type hints on all function signatures
   - Write docstrings for all public APIs (Google style)
   - Follow PEP 8 style guidelines
   - Add unit tests for new functionality
   - Ensure all tests pass before submitting

3. **Write tests** for your changes:
   ```bash
   python -m unittest discover pdf_metadata_manager/tests
   ```

4. **Update documentation** if you're adding new features or changing behavior

5. **Submit a pull request** with:
   - Clear description of the changes
   - Reference to any related issues
   - Screenshots/examples for UI changes
   - Test results

### Development Setup

```bash
# Clone the repository
git clone <repository-url>
cd pdf-metadata-manager

# Install dependencies
pip install -r pdf_metadata_manager/requirements.txt

# Install development dependencies (optional)
pip install pytest pytest-cov black flake8 mypy

# Run tests
python -m unittest discover pdf_metadata_manager/tests

# Run type checking (optional)
mypy pdf_metadata_manager/

# Run linting (optional)
flake8 pdf_metadata_manager/
```

### Areas for Contribution

- **Additional filename patterns** for the filename parser
- **Improved fuzzy matching** algorithms
- **Support for other metadata sources** (e.g., PubMed, arXiv)
- **GUI interface** using tkinter or PyQt
- **Performance optimizations** for batch processing
- **Additional test coverage**
- **Documentation improvements**

### Code Review Process

All submissions require review. We use GitHub pull requests for this purpose. Consult [GitHub Help](https://help.github.com/articles/about-pull-requests/) for more information on using pull requests.

### Reporting Issues

When reporting bugs, please include:

- Operating system and Python version
- Complete error message and stack trace
- Steps to reproduce the issue
- Expected vs. actual behavior
- Sample PDF file (if appropriate and not confidential)
