#!/usr/bin/env python3
"""
PDF Metadata Manager - Main CLI Orchestrator

Update PDF metadata from academic sources like Crossref, with interactive
or batch processing modes.
"""

import argparse
import os
import sys
import signal
from pathlib import Path
from typing import List, Optional, Tuple

from pdf_metadata_manager.core import (
    PDFProcessor,
    PDFMetadata,
    PDFProcessingError,
    PDFNotFoundError,
    CrossrefClient,
    CrossrefMatch,
    CrossrefConnectionError,
    CrossrefAPIError,
    MetadataUpdater,
    MetadataUpdate,
    PDFUpdateError,
    FileOperationError,
    parse_filename,
    FilenameHints
)
from pdf_metadata_manager.ui import InteractiveUI, UserQuitError
from pdf_metadata_manager.utils import SessionLogger


class PDFMetadataManager:
    """Main orchestrator for PDF metadata processing."""

    def __init__(
        self,
        email: Optional[str] = None,
        use_ocr: bool = True,
        ocr_pages: int = 1,
        keep_backup: bool = False,
        retries: int = 3,
        verbose: bool = False,
        quiet: bool = False,
        batch_mode: bool = False,
        rename: bool = True,
        log_path: Optional[str] = None,
        from_filename: bool = False
    ):
        """
        Initialize PDF Metadata Manager.

        Args:
            email: Email for Crossref API (polite pool), not required for --from-filename
            use_ocr: Enable OCR fallback for scanned documents
            ocr_pages: Number of pages to OCR (default: 1)
            keep_backup: Keep .bak copy of original files
            retries: Number of retry attempts for Crossref API
            verbose: Show detailed information
            quiet: Minimal output (errors and summary only)
            batch_mode: Auto-accept high-confidence matches
            rename: Rename files to Zotero format
            log_path: Path to write a JSON session log to (default: no log file)
            from_filename: Extract metadata from Zotero-style filename (skip Crossref)
        """
        self.batch_mode = batch_mode
        self.rename = rename
        self.from_filename = from_filename

        # Initialize components
        self.pdf_processor = PDFProcessor(
            use_ocr=use_ocr,
            ocr_pages=ocr_pages,
            verbose=verbose
        )
        # Only initialize Crossref client if not using from_filename mode
        if not from_filename and email:
            self.crossref_client = CrossrefClient(
                email=email,
                retries=retries
            )
        else:
            self.crossref_client = None
        self.metadata_updater = MetadataUpdater(keep_backup=keep_backup)
        self.ui = InteractiveUI(verbose=verbose, quiet=quiet)

        # Settings for logging
        settings = {
            'use_ocr': use_ocr,
            'ocr_pages': ocr_pages,
            'keep_backup': keep_backup,
            'batch_mode': batch_mode,
            'rename': rename,
            'retries': retries
        }
        self.logger = SessionLogger(log_path=log_path, settings=settings)

        # Statistics
        self.stats = {
            'completed': 0,
            'skipped': 0,
            'failed': 0
        }

    def process_single_pdf(self, pdf_path: str) -> str:
        """
        Process a single PDF file.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            'completed', 'skipped', or 'failed'
        """
        try:
            # Convert to absolute path to avoid issues with relative paths
            pdf_path = str(Path(pdf_path).resolve())

            if not self.ui.quiet:
                print(f"\n{'='*60}")
                print(f"Processing: {Path(pdf_path).name}")
                print(f"{'='*60}")

            # Step 1: Parse filename hints
            filename_hints = parse_filename(Path(pdf_path).name)

            if self.ui.verbose:
                print(f"\nFilename hints: author={filename_hints.author}, "
                      f"year={filename_hints.year}, confidence={filename_hints.confidence:.2f}")

            # Handle --from-filename mode: extract metadata from filename only
            if self.from_filename:
                return self._process_from_filename(pdf_path, filename_hints)

            # Step 2: Extract PDF metadata
            if not self.ui.quiet:
                print("Extracting PDF metadata...")

            pdf_metadata = self.pdf_processor.extract_metadata(pdf_path)

            if self.ui.verbose:
                print(f"Extracted DOI: {pdf_metadata.doi or 'Not found'}")
                print(f"Extracted title: {pdf_metadata.title or 'Not found'}")
                print(f"Used OCR: {pdf_metadata.used_ocr}")

            # Display current PDF docinfo metadata (same fields we will update)
            if not self.ui.quiet:
                current = self.metadata_updater.read_metadata(pdf_path)
                print("\nCurrent PDF metadata:")
                print(f"  Title:   {current.title or '(none)'}")
                print(f"  Authors: {current.authors or '(none)'}")
                print(f"  Year:    {current.year or '(none)'}")
                print(f"  Journal: {current.journal or '(none)'}")
                print(f"  DOI:     {current.doi or '(none)'}")
                if current.isbn:
                    print(f"  ISBN:    {current.isbn}")
                print()

            # Step 3: Search Crossref
            if not self.ui.quiet:
                print("Searching Crossref API...")

            # Build search query from extracted metadata and filename hints
            search_title = pdf_metadata.title or filename_hints.title
            search_author = pdf_metadata.authors or filename_hints.author
            search_year = pdf_metadata.year or filename_hints.year

            if pdf_metadata.doi:
                # If we have a DOI, fetch metadata directly
                try:
                    metadata_dict = self.crossref_client.fetch_metadata(pdf_metadata.doi)
                    # Convert to CrossrefMatch for consistency
                    matches = [self._metadata_dict_to_match(metadata_dict, 1.0)]
                except (CrossrefConnectionError, CrossrefAPIError) as e:
                    if self.ui.verbose:
                        print(f"DOI lookup failed: {e}")
                    # Fall back to search
                    matches = self.crossref_client.search(
                        title=search_title,
                        author=search_author,
                        year=search_year,
                        max_results=5
                    )
            else:
                matches = self.crossref_client.search(
                    title=search_title,
                    author=search_author,
                    year=search_year,
                    max_results=5
                )

            if not matches:
                if not self.ui.quiet:
                    print("⚠️  No matches found in Crossref")
                self.logger.log_skip(pdf_path, "No Crossref matches found")
                return 'skipped'

            # Step 4: Select match (batch or interactive)
            selected_match = None
            # Whether the user picked a numbered candidate directly from the
            # list (as opposed to entering a manual DOI). A direct pick is
            # applied immediately, without a separate confirmation step.
            selected_directly = False

            if self.batch_mode:
                # Auto-accept if high confidence
                if matches[0].score >= 0.80:
                    selected_match = matches[0]
                    if not self.ui.quiet:
                        print(f"✓ Auto-selected (score: {matches[0].score:.2f})")
                else:
                    if not self.ui.quiet:
                        print(f"⚠️  Skipped - confidence too low ({matches[0].score:.2f} < 0.80)")
                    self.logger.log_skip(
                        pdf_path,
                        f"Confidence below threshold: {matches[0].score:.2f}"
                    )
                    return 'skipped'
            else:
                # Interactive mode
                selected_match = self.ui.display_matches(
                    matches,
                    Path(pdf_path).name,
                    filename_hints
                )

                # A CrossrefMatch here means the user chose a numbered option.
                selected_directly = isinstance(selected_match, CrossrefMatch)

                # Handle special return values from display_matches
                if selected_match is None:
                    self.logger.log_skip(pdf_path, "User skipped")
                    return 'skipped'
                elif selected_match == 'retry':
                    # User requested retry - recursive call
                    return self.process_single_pdf(pdf_path)
                elif selected_match == 'from_filename':
                    # User chose to use metadata from filename
                    return self._process_from_filename(pdf_path, filename_hints)
                elif isinstance(selected_match, tuple) and selected_match[0] == 'manual':
                    # User entered manual DOI
                    manual_doi = selected_match[1]
                    try:
                        metadata_dict = self.crossref_client.fetch_metadata(manual_doi)
                        selected_match = self._metadata_dict_to_match(metadata_dict, 1.0)
                    except (CrossrefConnectionError, CrossrefAPIError) as e:
                        if not self.ui.quiet:
                            print(f"❌ Failed to fetch metadata for DOI: {e}")
                        self.logger.log_failure(pdf_path, f"Invalid DOI: {manual_doi}")
                        return 'failed'

            # Step 5: Prepare metadata update
            metadata_update = self._match_to_metadata_update(selected_match)

            # Generate new filename
            if self.rename:
                new_filename = self.metadata_updater.generate_zotero_filename(
                    metadata_update,
                    pdf_path
                )
            else:
                new_filename = Path(pdf_path).name

            # Step 6: Confirm (skip for a direct numbered pick; the user has
            # already seen the candidate's details in the list)
            if not self.batch_mode and not selected_directly:
                confirmed = self.ui.confirm_metadata(
                    Path(pdf_path).name,
                    metadata_update,
                    new_filename
                )

                if not confirmed:
                    self.logger.log_skip(pdf_path, "User declined metadata")
                    return 'skipped'

            # Step 7: Update PDF metadata
            if not self.ui.quiet:
                print("Updating PDF metadata...")

            self.metadata_updater.update_metadata(pdf_path, metadata_update)

            # Step 8: Rename file
            new_path = pdf_path
            if self.rename:
                if not self.ui.quiet:
                    print(f"Renaming to: {new_filename}")

                new_path = self.metadata_updater.rename_file(
                    pdf_path,
                    new_filename
                )

            # Step 9: Log success
            self.logger.log_success(
                original_path=pdf_path,
                new_path=new_path,
                doi=selected_match.doi,
                confidence=selected_match.score,
                used_ocr=pdf_metadata.used_ocr
            )

            if not self.ui.quiet:
                print(f"✓ Successfully processed")

            return 'completed'

        except UserQuitError:
            raise  # Propagate quit signal

        except PDFNotFoundError as e:
            if not self.ui.quiet:
                print(f"❌ Error: {e}")
            self.logger.log_failure(pdf_path, str(e))
            return 'failed'

        except (PDFProcessingError, PDFUpdateError, FileOperationError) as e:
            # Handle errors interactively
            if self.batch_mode:
                if not self.ui.quiet:
                    print(f"❌ Error: {e}")
                self.logger.log_failure(pdf_path, str(e))
                return 'failed'
            else:
                choice = self.ui.handle_error(
                    Path(pdf_path).name,
                    e,
                    retryable=False
                )

                if choice == 'quit':
                    raise UserQuitError()

                self.logger.log_failure(pdf_path, str(e))
                return 'failed'

        except (CrossrefConnectionError, CrossrefAPIError) as e:
            # Connection errors can be retried
            if self.batch_mode:
                if not self.ui.quiet:
                    print(f"❌ Connection error: {e}")
                self.logger.log_failure(pdf_path, str(e))
                return 'failed'
            else:
                choice = self.ui.handle_error(
                    Path(pdf_path).name,
                    e,
                    retryable=True
                )

                if choice == 'retry':
                    # Recursive retry
                    return self.process_single_pdf(pdf_path)
                elif choice == 'quit':
                    raise UserQuitError()
                else:
                    self.logger.log_failure(pdf_path, str(e))
                    return 'failed'

        except Exception as e:
            if not self.ui.quiet:
                print(f"❌ Unexpected error: {e}")
            if self.ui.verbose:
                import traceback
                traceback.print_exc()
            self.logger.log_failure(pdf_path, f"Unexpected error: {e}")
            return 'failed'

    def _metadata_dict_to_match(self, metadata: dict, score: float) -> CrossrefMatch:
        """Convert Crossref metadata dict to CrossrefMatch.

        Handles both:
        - Raw Crossref API responses (uppercase 'DOI', 'author' as list of dicts)
        - Processed metadata from fetch_metadata() (lowercase 'doi', 'authors' as list of strings)
        """
        authors = []

        # Handle both raw API format and processed format
        if 'authors' in metadata and isinstance(metadata['authors'], list):
            # Processed format: already a list of formatted strings
            authors = metadata['authors']
        elif 'author' in metadata:
            # Raw API format: list of author dictionaries
            for author in metadata['author']:
                if 'family' in author:
                    given = author.get('given', '')
                    authors.append(f"{author['family']}, {given}" if given else author['family'])

        year = None
        if 'year' in metadata:
            # Processed format
            year = metadata['year']
        elif 'published-print' in metadata:
            year = str(metadata['published-print']['date-parts'][0][0])
        elif 'published-online' in metadata:
            year = str(metadata['published-online']['date-parts'][0][0])
        elif 'issued' in metadata:
            year = str(metadata['issued']['date-parts'][0][0])

        journal = None
        if 'journal' in metadata:
            # Processed format
            journal = metadata['journal']
        elif 'container-title' in metadata and metadata['container-title']:
            journal = metadata['container-title'][0]

        # Handle both 'doi' and 'DOI' keys
        doi = metadata.get('doi') or metadata.get('DOI', '')

        # Handle both title formats
        title = metadata.get('title', '')
        if isinstance(title, list):
            title = title[0] if title else ''

        return CrossrefMatch(
            doi=doi,
            title=title,
            authors=authors,
            year=year,
            journal=journal,
            score=score
        )

    def _match_to_metadata_update(self, match: CrossrefMatch) -> MetadataUpdate:
        """Convert CrossrefMatch to MetadataUpdate."""
        return MetadataUpdate(
            title=match.title,
            authors='; '.join(match.authors) if match.authors else '',
            year=match.year,
            journal=match.journal,
            doi=match.doi
        )

    def _process_from_filename(self, pdf_path: str, filename_hints: FilenameHints) -> str:
        """
        Process a PDF using metadata extracted from its filename.

        This mode is used with --from-filename to set PDF metadata based on
        Zotero-style filenames without querying Crossref.

        Args:
            pdf_path: Path to the PDF file
            filename_hints: Parsed hints from the filename

        Returns:
            'completed', 'skipped', or 'failed'
        """
        # Check if filename parsing was successful
        if filename_hints.confidence < 0.5:
            if not self.ui.quiet:
                print(f"⚠️  Filename doesn't match expected format (confidence: {filename_hints.confidence:.2f})")
                print(f"   Expected format: 'Author - Year - Title.pdf'")
            self.logger.log_skip(pdf_path, f"Filename format not recognized (confidence: {filename_hints.confidence:.2f})")
            return 'skipped'

        # Check for required fields
        missing_fields = []
        if not filename_hints.author:
            missing_fields.append('author')
        if not filename_hints.year:
            missing_fields.append('year')
        if not filename_hints.title:
            missing_fields.append('title')

        if missing_fields and not self.batch_mode:
            if not self.ui.quiet:
                print(f"⚠️  Missing fields from filename: {', '.join(missing_fields)}")

        # Create metadata update from filename hints
        metadata_update = MetadataUpdate(
            title=filename_hints.title or '',
            authors=filename_hints.author or '',
            year=filename_hints.year,
            journal=None,  # Not available from filename
            doi=None       # Not available from filename
        )

        if not self.ui.quiet:
            print(f"\nMetadata from filename:")
            print(f"  Title:  {metadata_update.title or '(not found)'}")
            print(f"  Author: {metadata_update.authors or '(not found)'}")
            print(f"  Year:   {metadata_update.year or '(not found)'}")

        # In interactive mode, confirm before applying
        if not self.batch_mode:
            # Generate new filename if renaming is enabled
            if self.rename:
                new_filename = self.metadata_updater.generate_zotero_filename(
                    metadata_update,
                    pdf_path
                )
            else:
                new_filename = Path(pdf_path).name

            confirmed = self.ui.confirm_metadata(
                Path(pdf_path).name,
                metadata_update,
                new_filename
            )

            if not confirmed:
                self.logger.log_skip(pdf_path, "User declined metadata")
                return 'skipped'

        # Update PDF metadata
        if not self.ui.quiet:
            print("Updating PDF metadata...")

        try:
            self.metadata_updater.update_metadata(pdf_path, metadata_update)
        except (PDFUpdateError, FileOperationError) as e:
            if not self.ui.quiet:
                print(f"❌ Error updating metadata: {e}")
            self.logger.log_failure(pdf_path, str(e))
            return 'failed'

        # Rename file if enabled
        new_path = pdf_path
        if self.rename:
            new_filename = self.metadata_updater.generate_zotero_filename(
                metadata_update,
                pdf_path
            )
            if not self.ui.quiet:
                print(f"Renaming to: {new_filename}")

            try:
                new_path = self.metadata_updater.rename_file(
                    pdf_path,
                    new_filename
                )
            except (FileOperationError, FileNotFoundError) as e:
                if not self.ui.quiet:
                    print(f"❌ Error renaming file: {e}")
                self.logger.log_failure(pdf_path, str(e))
                return 'failed'

        # Log success
        self.logger.log_success(
            original_path=pdf_path,
            new_path=new_path,
            doi=None,  # No DOI in from-filename mode
            confidence=filename_hints.confidence,
            used_ocr=False
        )

        if not self.ui.quiet:
            print(f"✓ Successfully processed")

        return 'completed'

    def process_files(self, files: List[str]) -> None:
        """
        Process multiple PDF files.

        Args:
            files: List of PDF file paths
        """
        total = len(files)

        if not self.ui.quiet:
            print(f"\nProcessing {total} PDF file{'s' if total != 1 else ''}...\n")

        try:
            for i, pdf_path in enumerate(files, 1):
                result = self.process_single_pdf(pdf_path)
                self.stats[result] += 1

                if not self.ui.quiet and total > 1:
                    self.ui.show_progress(
                        current=i,
                        total=total,
                        completed=self.stats['completed'],
                        skipped=self.stats['skipped'],
                        failed=self.stats['failed'],
                        current_file=Path(pdf_path).name
                    )

        except (KeyboardInterrupt, UserQuitError):
            if not self.ui.quiet:
                print("\n\n⚠️  Processing interrupted by user")

        finally:
            self.logger.close()
            if not self.ui.quiet:
                self.ui.print_summary(
                    total=total,
                    completed=self.stats['completed'],
                    skipped=self.stats['skipped'],
                    failed=self.stats['failed'],
                    log_path=self.logger.log_path
                )


def collect_pdf_files(input_path: str, recursive: bool = False) -> List[str]:
    """
    Collect PDF files from input path.

    Args:
        input_path: File or directory path, or glob pattern
        recursive: Search directories recursively

    Returns:
        List of PDF file paths
    """
    path = Path(input_path)
    files = []

    if path.is_file():
        if path.suffix.lower() == '.pdf':
            files.append(str(path))
    elif path.is_dir():
        if recursive:
            files.extend(str(p) for p in path.rglob('*.pdf'))
        else:
            files.extend(str(p) for p in path.glob('*.pdf'))
    else:
        # Try as glob pattern
        import glob
        files.extend(glob.glob(input_path, recursive=recursive))

    return sorted(files)


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Update PDF metadata from academic sources',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s paper.pdf --email "me@example.com"
  %(prog)s papers/ --batch --backup --recursive
  %(prog)s *.pdf --no-rename --email "me@example.com"
  %(prog)s "Smith - 2020 - Title.pdf" --from-filename
  %(prog)s papers/ --from-filename --batch

Environment Variables:
  CROSSREF_EMAIL    Email for Crossref API (can be used instead of --email)
        '''
    )

    # Required arguments
    parser.add_argument(
        'input',
        help='PDF file, directory, or glob pattern to process'
    )

    # Optional arguments
    parser.add_argument(
        '--email', '-e',
        help='Email for Crossref API (or set CROSSREF_EMAIL env var)'
    )

    parser.add_argument(
        '--batch', '-b',
        action='store_true',
        help='Batch mode: auto-accept matches with confidence >= 0.80'
    )

    parser.add_argument(
        '--recursive', '-r',
        action='store_true',
        help='Search directories recursively'
    )

    parser.add_argument(
        '--no-rename',
        action='store_true',
        help='Do not rename files (only update metadata)'
    )

    parser.add_argument(
        '--from-filename',
        action='store_true',
        help='Set metadata from Zotero-style filename (Author - Year - Title.pdf). Skips Crossref lookup.'
    )

    parser.add_argument(
        '--backup',
        action='store_true',
        help='Keep .bak copy of original files'
    )

    parser.add_argument(
        '--no-ocr',
        action='store_true',
        help='Disable OCR for scanned documents'
    )

    parser.add_argument(
        '--ocr-pages',
        type=int,
        default=1,
        metavar='N',
        help='Number of pages to OCR (default: 1)'
    )

    parser.add_argument(
        '--retries',
        type=int,
        default=3,
        metavar='N',
        help='Number of retry attempts for Crossref API (default: 3)'
    )

    parser.add_argument(
        '--log',
        metavar='PATH',
        help='Write a JSON session log to PATH (default: no log file)'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed information'
    )

    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Minimal output (errors and summary only)'
    )

    return parser.parse_args()


def validate_config(args: argparse.Namespace) -> Tuple[bool, Optional[str]]:
    """
    Validate configuration.

    Returns:
        Tuple of (valid, error_message)
    """
    # Check for email (not required for --from-filename mode)
    if not args.from_filename:
        if not args.email:
            args.email = os.environ.get('CROSSREF_EMAIL')

            if not args.email:
                return False, (
                    "Error: Email required for Crossref API.\n"
                    "Provide via --email or set CROSSREF_EMAIL environment variable.\n"
                    "Or use --from-filename to set metadata from the filename without Crossref."
                )

    # Check input exists
    input_path = Path(args.input)
    if not input_path.exists() and not any(c in args.input for c in ['*', '?']):
        return False, f"Error: Input path does not exist: {args.input}"

    # Validate numeric arguments
    if args.ocr_pages < 1:
        return False, "Error: --ocr-pages must be >= 1"

    if args.retries < 1:
        return False, "Error: --retries must be >= 1"

    return True, None


def main():
    """Main entry point."""
    # Parse arguments
    args = parse_arguments()

    # Validate configuration
    valid, error_msg = validate_config(args)
    if not valid:
        print(error_msg, file=sys.stderr)
        sys.exit(1)

    # Collect files to process
    files = collect_pdf_files(args.input, recursive=args.recursive)

    if not files:
        print(f"Error: No PDF files found at: {args.input}", file=sys.stderr)
        sys.exit(1)

    # Initialize manager
    manager = PDFMetadataManager(
        email=args.email,
        use_ocr=not args.no_ocr,
        ocr_pages=args.ocr_pages,
        keep_backup=args.backup,
        retries=args.retries,
        verbose=args.verbose,
        quiet=args.quiet,
        batch_mode=args.batch,
        rename=not args.no_rename,
        log_path=args.log,
        from_filename=args.from_filename
    )

    # Set up signal handler for graceful shutdown
    def signal_handler(sig, frame):
        raise KeyboardInterrupt()

    signal.signal(signal.SIGINT, signal_handler)

    # Process files
    manager.process_files(files)


if __name__ == '__main__':
    main()
