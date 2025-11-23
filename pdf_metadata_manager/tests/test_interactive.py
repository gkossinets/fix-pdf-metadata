"""Tests for the interactive UI module.

This module tests the InteractiveUI class functionality including
match display, confirmations, error handling, and progress display.
"""

import unittest
from unittest.mock import patch, MagicMock, call
from io import StringIO
import sys

# Import the module to test
try:
    from pdf_metadata_manager.ui.interactive import (
        InteractiveUI,
        UserQuitError,
        CrossrefMatch,
        FilenameHints,
        MetadataUpdate
    )
except ImportError:
    import sys
    import os
    # Add parent directory to path for testing
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from ui.interactive import (
        InteractiveUI,
        UserQuitError,
        CrossrefMatch,
        FilenameHints,
        MetadataUpdate
    )


class TestInteractiveUI(unittest.TestCase):
    """Test cases for InteractiveUI class."""

    def setUp(self):
        """Set up test fixtures."""
        self.ui = InteractiveUI(verbose=False, quiet=False)
        self.verbose_ui = InteractiveUI(verbose=True, quiet=False)
        self.quiet_ui = InteractiveUI(verbose=False, quiet=True)

        # Sample test data
        self.sample_matches = [
            CrossrefMatch(
                doi="10.1038/s41558-020-12345",
                title="Machine Learning Applications in Climate Science",
                authors=["Smith, J.", "Johnson, A.", "Williams, B."],
                year="2020",
                journal="Nature Climate Change",
                score=0.87
            ),
            CrossrefMatch(
                doi="10.1021/acs.est.9b12345",
                title="Machine Learning for Environmental Prediction",
                authors=["Smith, John"],
                year="2019",
                journal="Environmental Science & Technology",
                score=0.65
            ),
            CrossrefMatch(
                doi="10.1234/example.2018",
                title="Another ML Paper",
                authors=["Jones, A."],
                year="2018",
                journal="Example Journal",
                score=0.54
            )
        ]

        self.sample_hints = FilenameHints(
            author="Smith",
            year="2020",
            title=None,
            confidence=0.6
        )

        self.sample_metadata = MetadataUpdate(
            title="Machine Learning Applications in Climate Science",
            authors="Smith, J.; Johnson, A.; Williams, B.",
            year="2020",
            journal="Nature Climate Change",
            doi="10.1038/s41558-020-12345",
            isbn=None
        )

    def test_init(self):
        """Test UI initialization."""
        ui = InteractiveUI()
        self.assertFalse(ui.verbose)
        self.assertFalse(ui.quiet)
        self.assertEqual(ui._last_progress_lines, 0)

        ui_verbose = InteractiveUI(verbose=True)
        self.assertTrue(ui_verbose.verbose)

        ui_quiet = InteractiveUI(quiet=True)
        self.assertTrue(ui_quiet.quiet)

    @patch('builtins.input', side_effect=['1'])
    @patch('sys.stdout', new_callable=StringIO)
    def test_display_matches_select_first(self, mock_stdout, mock_input):
        """Test selecting the first match."""
        result = self.ui.display_matches(
            self.sample_matches,
            "smith_2020.pdf",
            self.sample_hints
        )

        self.assertEqual(result, self.sample_matches[0])
        output = mock_stdout.getvalue()
        self.assertIn("Found 3 potential matches", output)
        self.assertIn("Author: Smith", output)
        self.assertIn("Year: 2020", output)
        self.assertIn("HIGH CONFIDENCE", output)

    @patch('builtins.input', side_effect=['3'])
    @patch('sys.stdout', new_callable=StringIO)
    def test_display_matches_select_third(self, mock_stdout, mock_input):
        """Test selecting the third match."""
        result = self.ui.display_matches(
            self.sample_matches,
            "test.pdf",
            self.sample_hints
        )

        self.assertEqual(result, self.sample_matches[2])

    @patch('builtins.input', side_effect=['s'])
    @patch('sys.stdout', new_callable=StringIO)
    def test_display_matches_skip(self, mock_stdout, mock_input):
        """Test skipping match selection."""
        result = self.ui.display_matches(
            self.sample_matches,
            "test.pdf",
            self.sample_hints
        )

        self.assertIsNone(result)

    @patch('builtins.input', side_effect=['q'])
    @patch('sys.stdout', new_callable=StringIO)
    def test_display_matches_quit(self, mock_stdout, mock_input):
        """Test quitting from match selection."""
        with self.assertRaises(UserQuitError):
            self.ui.display_matches(
                self.sample_matches,
                "test.pdf",
                self.sample_hints
            )

    @patch('builtins.input', side_effect=['r'])
    @patch('sys.stdout', new_callable=StringIO)
    def test_display_matches_retry(self, mock_stdout, mock_input):
        """Test retry option."""
        result = self.ui.display_matches(
            self.sample_matches,
            "test.pdf",
            self.sample_hints
        )

        self.assertEqual(result, 'retry')

    @patch('builtins.input', side_effect=['m', '10.1234/manual'])
    @patch('sys.stdout', new_callable=StringIO)
    def test_display_matches_manual_doi(self, mock_stdout, mock_input):
        """Test manual DOI entry."""
        result = self.ui.display_matches(
            self.sample_matches,
            "test.pdf",
            self.sample_hints
        )

        self.assertEqual(result, ('manual', '10.1234/manual'))

    @patch('builtins.input', side_effect=['m', ''])
    @patch('sys.stdout', new_callable=StringIO)
    def test_display_matches_manual_doi_empty(self, mock_stdout, mock_input):
        """Test manual DOI entry with empty input."""
        result = self.ui.display_matches(
            self.sample_matches,
            "test.pdf",
            self.sample_hints
        )

        self.assertIsNone(result)
        output = mock_stdout.getvalue()
        self.assertIn("No DOI entered", output)

    @patch('builtins.input', side_effect=['99', '2'])
    @patch('sys.stdout', new_callable=StringIO)
    def test_display_matches_invalid_then_valid(self, mock_stdout, mock_input):
        """Test invalid selection followed by valid one."""
        result = self.ui.display_matches(
            self.sample_matches,
            "test.pdf",
            self.sample_hints
        )

        self.assertEqual(result, self.sample_matches[1])
        output = mock_stdout.getvalue()
        self.assertIn("Please enter a number between 1 and 3", output)

    @patch('builtins.input', side_effect=['invalid', 's'])
    @patch('sys.stdout', new_callable=StringIO)
    def test_display_matches_invalid_choice(self, mock_stdout, mock_input):
        """Test invalid choice followed by skip."""
        result = self.ui.display_matches(
            self.sample_matches,
            "test.pdf",
            self.sample_hints
        )

        self.assertIsNone(result)
        output = mock_stdout.getvalue()
        self.assertIn("Invalid choice", output)

    @patch('builtins.input', side_effect=EOFError())
    @patch('sys.stdout', new_callable=StringIO)
    def test_display_matches_eof(self, mock_stdout, mock_input):
        """Test EOF handling (Ctrl+D)."""
        result = self.ui.display_matches(
            self.sample_matches,
            "test.pdf",
            self.sample_hints
        )

        self.assertIsNone(result)
        output = mock_stdout.getvalue()
        self.assertIn("EOF detected", output)

    @patch('builtins.input', side_effect=KeyboardInterrupt())
    @patch('sys.stdout', new_callable=StringIO)
    def test_display_matches_keyboard_interrupt(self, mock_stdout, mock_input):
        """Test Ctrl+C handling."""
        result = self.ui.display_matches(
            self.sample_matches,
            "test.pdf",
            self.sample_hints
        )

        self.assertIsNone(result)
        output = mock_stdout.getvalue()
        self.assertIn("Interrupted", output)

    def test_display_matches_quiet_mode(self):
        """Test that quiet mode returns None immediately."""
        result = self.quiet_ui.display_matches(
            self.sample_matches,
            "test.pdf",
            self.sample_hints
        )

        self.assertIsNone(result)

    @patch('builtins.input', side_effect=['1'])
    @patch('sys.stdout', new_callable=StringIO)
    def test_display_matches_no_hints(self, mock_stdout, mock_input):
        """Test display with no filename hints."""
        empty_hints = FilenameHints()
        result = self.ui.display_matches(
            self.sample_matches,
            "test.pdf",
            empty_hints
        )

        output = mock_stdout.getvalue()
        self.assertNotIn("Current filename info:", output)

    @patch('builtins.input', side_effect=['1'])
    @patch('sys.stdout', new_callable=StringIO)
    def test_display_matches_many_authors(self, mock_stdout, mock_input):
        """Test display with many authors."""
        match_with_many_authors = CrossrefMatch(
            doi="10.1234/test",
            title="Test Paper",
            authors=[f"Author {i}" for i in range(10)],
            year="2020",
            journal="Test Journal",
            score=0.85
        )

        result = self.ui.display_matches(
            [match_with_many_authors],
            "test.pdf",
            self.sample_hints
        )

        output = mock_stdout.getvalue()
        self.assertIn("(10 total)", output)

    @patch('builtins.input', side_effect=['a'])
    @patch('sys.stdout', new_callable=StringIO)
    def test_confirm_metadata_apply(self, mock_stdout, mock_input):
        """Test applying metadata update."""
        result = self.ui.confirm_metadata(
            "test.pdf",
            self.sample_metadata,
            "Smith et al. - 2020 - Machine Learning.pdf"
        )

        self.assertTrue(result)
        output = mock_stdout.getvalue()
        self.assertIn("Review metadata update", output)
        self.assertIn("Machine Learning Applications", output)
        self.assertIn("Smith, J.; Johnson, A.; Williams, B.", output)

    @patch('builtins.input', side_effect=['s'])
    @patch('sys.stdout', new_callable=StringIO)
    def test_confirm_metadata_skip(self, mock_stdout, mock_input):
        """Test skipping metadata update."""
        result = self.ui.confirm_metadata(
            "test.pdf",
            self.sample_metadata,
            "new_name.pdf"
        )

        self.assertFalse(result)

    @patch('builtins.input', side_effect=['q'])
    @patch('sys.stdout', new_callable=StringIO)
    def test_confirm_metadata_quit(self, mock_stdout, mock_input):
        """Test quitting from metadata confirmation."""
        with self.assertRaises(UserQuitError):
            self.ui.confirm_metadata(
                "test.pdf",
                self.sample_metadata,
                "new_name.pdf"
            )

    @patch('builtins.input', side_effect=['invalid', 'a'])
    @patch('sys.stdout', new_callable=StringIO)
    def test_confirm_metadata_invalid_then_valid(self, mock_stdout, mock_input):
        """Test invalid choice then valid choice."""
        result = self.ui.confirm_metadata(
            "test.pdf",
            self.sample_metadata,
            "new_name.pdf"
        )

        self.assertTrue(result)
        output = mock_stdout.getvalue()
        self.assertIn("Invalid choice", output)

    @patch('builtins.input', side_effect=EOFError())
    @patch('sys.stdout', new_callable=StringIO)
    def test_confirm_metadata_eof(self, mock_stdout, mock_input):
        """Test EOF during confirmation."""
        result = self.ui.confirm_metadata(
            "test.pdf",
            self.sample_metadata,
            "new_name.pdf"
        )

        self.assertFalse(result)

    def test_confirm_metadata_quiet_mode(self):
        """Test that quiet mode returns True immediately."""
        result = self.quiet_ui.confirm_metadata(
            "test.pdf",
            self.sample_metadata,
            "new_name.pdf"
        )

        self.assertTrue(result)

    @patch('builtins.input', side_effect=['r'])
    @patch('sys.stdout', new_callable=StringIO)
    def test_handle_error_retry(self, mock_stdout, mock_input):
        """Test retry option for error handling."""
        error = Exception("Test error")
        result = self.ui.handle_error("test.pdf", error, retryable=True)

        self.assertEqual(result, 'retry')
        output = mock_stdout.getvalue()
        self.assertIn("Error processing: test.pdf", output)
        self.assertIn("Test error", output)

    @patch('builtins.input', side_effect=['s'])
    @patch('sys.stdout', new_callable=StringIO)
    def test_handle_error_skip(self, mock_stdout, mock_input):
        """Test skip option for error handling."""
        error = Exception("Test error")
        result = self.ui.handle_error("test.pdf", error, retryable=True)

        self.assertEqual(result, 'skip')

    @patch('builtins.input', side_effect=['q'])
    @patch('sys.stdout', new_callable=StringIO)
    def test_handle_error_quit(self, mock_stdout, mock_input):
        """Test quit option for error handling."""
        error = Exception("Test error")
        result = self.ui.handle_error("test.pdf", error, retryable=True)

        self.assertEqual(result, 'quit')

    @patch('builtins.input', side_effect=['r', 's'])
    @patch('sys.stdout', new_callable=StringIO)
    def test_handle_error_not_retryable(self, mock_stdout, mock_input):
        """Test error handling when retry is not available."""
        error = Exception("Test error")
        result = self.ui.handle_error("test.pdf", error, retryable=False)

        # 'r' should be invalid, so it should ask again and accept 's'
        self.assertEqual(result, 'skip')
        output = mock_stdout.getvalue()
        self.assertIn("Invalid choice", output)

    @patch('builtins.input', side_effect=EOFError())
    @patch('sys.stdout', new_callable=StringIO)
    def test_handle_error_eof(self, mock_stdout, mock_input):
        """Test EOF during error handling."""
        error = Exception("Test error")
        result = self.ui.handle_error("test.pdf", error, retryable=True)

        self.assertEqual(result, 'skip')

    @patch('builtins.input', side_effect=KeyboardInterrupt())
    @patch('sys.stdout', new_callable=StringIO)
    def test_handle_error_keyboard_interrupt(self, mock_stdout, mock_input):
        """Test Ctrl+C during error handling."""
        error = Exception("Test error")
        result = self.ui.handle_error("test.pdf", error, retryable=True)

        self.assertEqual(result, 'quit')

    @patch('sys.stdout', new_callable=StringIO)
    def test_show_progress(self, mock_stdout):
        """Test progress display."""
        self.ui.show_progress(
            current=23,
            total=47,
            completed=20,
            skipped=2,
            failed=1,
            current_file="smith_2020.pdf"
        )

        output = mock_stdout.getvalue()
        self.assertIn("Processing 47 PDFs", output)
        self.assertIn("23/47", output)
        self.assertIn("48.9%", output)
        self.assertIn("Completed: 20", output)
        self.assertIn("Skipped: 2", output)
        self.assertIn("Failed: 1", output)
        self.assertIn("Remaining: 24", output)
        self.assertIn("smith_2020.pdf", output)

    @patch('sys.stdout', new_callable=StringIO)
    def test_show_progress_long_filename(self, mock_stdout):
        """Test progress display with very long filename."""
        long_filename = "a" * 100 + ".pdf"
        self.ui.show_progress(
            current=1,
            total=10,
            completed=0,
            skipped=0,
            failed=0,
            current_file=long_filename
        )

        output = mock_stdout.getvalue()
        self.assertIn("...", output)

    def test_show_progress_quiet_mode(self):
        """Test that quiet mode doesn't show progress."""
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            self.quiet_ui.show_progress(
                current=1,
                total=10,
                completed=0,
                skipped=0,
                failed=0,
                current_file="test.pdf"
            )

            output = mock_stdout.getvalue()
            self.assertEqual(output, "")

    @patch('sys.stdout', new_callable=StringIO)
    def test_print_summary(self, mock_stdout):
        """Test summary printing."""
        self.ui.print_summary(
            total=47,
            completed=40,
            skipped=5,
            failed=2,
            log_path="/path/to/log.json"
        )

        output = mock_stdout.getvalue()
        self.assertIn("PROCESSING SUMMARY", output)
        self.assertIn("Total files:      47", output)
        self.assertIn("Completed:      40", output)
        self.assertIn("Skipped:        5", output)
        self.assertIn("Failed:         2", output)
        self.assertIn("Success rate:", output)
        self.assertIn("85.1%", output)
        self.assertIn("Log file:         /path/to/log.json", output)

    @patch('sys.stdout', new_callable=StringIO)
    def test_print_summary_no_completed(self, mock_stdout):
        """Test summary with no completed files."""
        self.ui.print_summary(
            total=10,
            completed=0,
            skipped=8,
            failed=2,
            log_path="/path/to/log.json"
        )

        output = mock_stdout.getvalue()
        self.assertNotIn("Success rate:", output)

    @patch('sys.stdout', new_callable=StringIO)
    def test_info(self, mock_stdout):
        """Test info message."""
        self.ui.info("Test message")
        output = mock_stdout.getvalue()
        self.assertIn("Test message", output)

    def test_info_quiet_mode(self):
        """Test info message in quiet mode."""
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            self.quiet_ui.info("Test message")
            output = mock_stdout.getvalue()
            self.assertEqual(output, "")

    @patch('sys.stdout', new_callable=StringIO)
    def test_verbose_info(self, mock_stdout):
        """Test verbose info message."""
        self.verbose_ui.verbose_info("Verbose message")
        output = mock_stdout.getvalue()
        self.assertIn("[VERBOSE]", output)
        self.assertIn("Verbose message", output)

    @patch('sys.stdout', new_callable=StringIO)
    def test_verbose_info_not_verbose(self, mock_stdout):
        """Test verbose message without verbose mode."""
        self.ui.verbose_info("Verbose message")
        output = mock_stdout.getvalue()
        self.assertEqual(output, "")

    @patch('sys.stderr', new_callable=StringIO)
    def test_error(self, mock_stderr):
        """Test error message."""
        self.ui.error("Error message")
        output = mock_stderr.getvalue()
        self.assertIn("ERROR:", output)
        self.assertIn("Error message", output)

    @patch('sys.stdout', new_callable=StringIO)
    def test_warning(self, mock_stdout):
        """Test warning message."""
        self.ui.warning("Warning message")
        output = mock_stdout.getvalue()
        self.assertIn("WARNING:", output)
        self.assertIn("Warning message", output)

    def test_warning_quiet_mode(self):
        """Test warning message in quiet mode."""
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            self.quiet_ui.warning("Warning message")
            output = mock_stdout.getvalue()
            self.assertEqual(output, "")


if __name__ == '__main__':
    unittest.main()
