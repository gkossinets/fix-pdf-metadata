# PDF Metadata Manager

A robust, modular Python CLI tool for updating PDF metadata from academic sources like Crossref.

**✅ Issue #8 Complete!** The main CLI orchestrator is now fully functional.

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

## Implementation Status

✅ All core features implemented (Issues #1-#8):

1. ✅ Filename Parser
2. ✅ PDF Processor with OCR
3. ✅ Crossref Client with retry logic
4. ✅ Metadata Updater with Zotero naming
5. ✅ Interactive UI
6. ✅ Logging System
7. ✅ Timestamp Utilities
8. ✅ **Main CLI Orchestrator** ⭐ NEW!

## Requirements

- Python 3.8+
- pikepdf, PyPDF2, requests, pathvalidate
- Optional: Tesseract OCR and Poppler (for scanned PDFs)

See [`pdf_metadata_manager/requirements.txt`](pdf_metadata_manager/requirements.txt) for complete list.

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

## Development

This project was developed following the refactoring plan in [`refactoring_instructions.md`](refactoring_instructions.md), which consolidates two original scripts into a clean, modular architecture.

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

## License

(To be determined)

## Contributing

See [`refactoring_instructions.md`](refactoring_instructions.md) for detailed implementation guidelines and architecture decisions.
