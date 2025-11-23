"""Interactive user interface for PDF processing.

This module provides user-friendly interactive prompts for match selection,
error handling, and confirmations during PDF metadata processing.
"""

import sys
from typing import List, Optional

# Import from core module - will be available when integrated
try:
    from ..core.crossref_client import CrossrefMatch
    from ..core.filename_parser import FilenameHints
    from ..core.metadata_updater import MetadataUpdate
except ImportError:
    # For standalone testing
    from dataclasses import dataclass

    @dataclass
    class CrossrefMatch:
        doi: str
        title: str
        authors: List[str]
        year: Optional[str]
        journal: Optional[str]
        score: float

        @property
        def confidence_level(self) -> str:
            if self.score >= 0.80:
                return "HIGH"
            elif self.score >= 0.65:
                return "MEDIUM"
            else:
                return "LOW"

    @dataclass
    class FilenameHints:
        author: Optional[str] = None
        year: Optional[str] = None
        title: Optional[str] = None
        confidence: float = 0.0

    @dataclass
    class MetadataUpdate:
        title: str
        authors: str
        year: Optional[str] = None
        journal: Optional[str] = None
        doi: Optional[str] = None
        isbn: Optional[str] = None


class UserQuitError(Exception):
    """Raised when user chooses to quit."""
    pass


class InteractiveUI:
    """Interactive user interface for PDF processing."""

    def __init__(self, verbose: bool = False, quiet: bool = False):
        """
        Initialize UI.

        Args:
            verbose: Show detailed information
            quiet: Minimal output (errors and summary only)
        """
        self.verbose = verbose
        self.quiet = quiet
        self._last_progress_lines = 0

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
        if self.quiet:
            return None

        # Display header
        print(f"\nFound {len(matches)} potential match{'es' if len(matches) != 1 else ''} for: {filename}")
        print()

        # Display filename hints if available
        hint_parts = []
        if filename_hints.author:
            hint_parts.append(f"Author: {filename_hints.author}")
        if filename_hints.year:
            hint_parts.append(f"Year: {filename_hints.year}")
        if filename_hints.title:
            hint_parts.append(f"Title: {filename_hints.title}")

        if hint_parts:
            print("Current filename info: " + ", ".join(hint_parts))
            print()

        # Display matches
        for i, match in enumerate(matches, 1):
            # Confidence indicator
            if match.confidence_level == "HIGH":
                stars = "★★★"
            elif match.confidence_level == "MEDIUM":
                stars = "★★"
            else:
                stars = "★"

            print(f"{i}. {stars} {match.confidence_level} CONFIDENCE ({match.score:.2f})")
            print(f"   Title: {match.title}")

            # Format authors
            if match.authors:
                if len(match.authors) <= 3:
                    authors_str = "; ".join(match.authors)
                else:
                    authors_str = "; ".join(match.authors[:3]) + f"; ... ({len(match.authors)} total)"
                print(f"   Authors: {authors_str}")

            if match.year:
                print(f"   Year: {match.year}")
            if match.journal:
                print(f"   Journal: {match.journal}")
            print(f"   DOI: {match.doi}")
            print()

        # Get user choice
        while True:
            try:
                prompt = f"Choose: [1-{len(matches)}] Select match | [s]kip | [r]etry | [m]anual DOI | [q]uit\n> "
                choice = input(prompt).strip().lower()

                if choice == 'q':
                    raise UserQuitError("User chose to quit")
                elif choice == 's':
                    return None
                elif choice == 'r':
                    # Return a special marker for retry
                    return 'retry'  # type: ignore
                elif choice == 'm':
                    # Get manual DOI
                    doi = input("Enter DOI: ").strip()
                    if doi:
                        # Return a marker for manual DOI entry
                        return ('manual', doi)  # type: ignore
                    else:
                        print("No DOI entered, skipping...")
                        return None
                else:
                    # Try to parse as number
                    try:
                        idx = int(choice)
                        if 1 <= idx <= len(matches):
                            return matches[idx - 1]
                        else:
                            print(f"Please enter a number between 1 and {len(matches)}")
                    except ValueError:
                        print(f"Invalid choice: {choice}")

            except EOFError:
                # Handle Ctrl+D
                print("\nEOF detected, skipping...")
                return None
            except KeyboardInterrupt:
                # Handle Ctrl+C
                print("\nInterrupted, skipping...")
                return None

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
        if self.quiet:
            return True

        print("\n📝 Review metadata update:")
        print()
        print(f"File: {filename}")
        print()
        print("Metadata to write:")
        print("┌" + "─" * 70 + "┐")

        # Format metadata nicely
        self._print_boxed_line(f"Title:   {metadata.title}")
        self._print_boxed_line(f"Authors: {metadata.authors}")
        if metadata.year:
            self._print_boxed_line(f"Year:    {metadata.year}")
        if metadata.journal:
            self._print_boxed_line(f"Journal: {metadata.journal}")
        if metadata.doi:
            self._print_boxed_line(f"DOI:     {metadata.doi}")
        if metadata.isbn:
            self._print_boxed_line(f"ISBN:    {metadata.isbn}")

        print("└" + "─" * 70 + "┘")
        print()
        print(f"New filename: {new_filename}")
        print()

        # Get confirmation
        while True:
            try:
                choice = input("[a]pply | [s]kip | [q]uit\n> ").strip().lower()

                if choice == 'q':
                    raise UserQuitError("User chose to quit")
                elif choice == 's':
                    return False
                elif choice == 'a':
                    return True
                else:
                    print(f"Invalid choice: {choice}")

            except EOFError:
                print("\nEOF detected, skipping...")
                return False
            except KeyboardInterrupt:
                print("\nInterrupted, skipping...")
                return False

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
        print(f"\n❌ Error processing: {filename}")
        print(f"Error: {str(error)}")
        print()

        if retryable:
            prompt = "[r]etry | [s]kip | [q]uit\n> "
            valid_choices = ['r', 's', 'q']
        else:
            prompt = "[s]kip | [q]uit\n> "
            valid_choices = ['s', 'q']

        while True:
            try:
                choice = input(prompt).strip().lower()

                if choice == 'q':
                    return 'quit'
                elif choice == 's':
                    return 'skip'
                elif choice == 'r' and retryable:
                    return 'retry'
                else:
                    print(f"Invalid choice: {choice}")

            except EOFError:
                print("\nEOF detected, skipping...")
                return 'skip'
            except KeyboardInterrupt:
                print("\nInterrupted, quitting...")
                return 'quit'

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
        if self.quiet:
            return

        # Clear previous progress lines
        if self._last_progress_lines > 0:
            # Move cursor up and clear lines
            for _ in range(self._last_progress_lines):
                sys.stdout.write('\033[F\033[K')

        # Calculate progress
        percentage = (current / total) * 100 if total > 0 else 0

        # Create progress bar
        bar_width = 30
        filled = int(bar_width * current / total) if total > 0 else 0
        bar = "=" * filled + ">" + " " * (bar_width - filled - 1)

        print(f"\nProcessing {total} PDFs...")
        print(f"[{bar}] {current}/{total} ({percentage:.1f}%)")
        print()
        print(f"✓ Completed: {completed}")
        print(f"⚠ Skipped: {skipped}")
        print(f"❌ Failed: {failed}")
        print(f"⏳ Remaining: {total - current}")
        print()

        # Truncate filename if too long
        if len(current_file) > 60:
            current_file = current_file[:57] + "..."
        print(f"Current: {current_file}")

        self._last_progress_lines = 9

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
        print("\n" + "=" * 70)
        print("PROCESSING SUMMARY")
        print("=" * 70)
        print()
        print(f"Total files:      {total}")
        print(f"✓ Completed:      {completed}")
        print(f"⚠ Skipped:        {skipped}")
        print(f"❌ Failed:         {failed}")
        print()

        if completed > 0:
            success_rate = (completed / total) * 100
            print(f"Success rate:     {success_rate:.1f}%")
            print()

        if log_path:
            print(f"Log file:         {log_path}")
            print()

        print("=" * 70)

    def _print_boxed_line(self, text: str):
        """Helper to print a line inside a box."""
        # Truncate if too long
        max_width = 68
        if len(text) > max_width:
            text = text[:max_width - 3] + "..."

        # Pad to width
        padded = text + " " * (max_width - len(text))
        print(f"│ {padded} │")

    def info(self, message: str):
        """Print informational message."""
        if not self.quiet:
            print(message)

    def verbose_info(self, message: str):
        """Print verbose informational message."""
        if self.verbose and not self.quiet:
            print(f"[VERBOSE] {message}")

    def error(self, message: str):
        """Print error message (always shown)."""
        print(f"ERROR: {message}", file=sys.stderr)

    def warning(self, message: str):
        """Print warning message."""
        if not self.quiet:
            print(f"WARNING: {message}")
