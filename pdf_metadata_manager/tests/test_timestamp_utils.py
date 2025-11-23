"""
Tests for timestamp_utils module.

Tests the cross-platform timestamp preservation utilities.
"""

import os
import platform
import tempfile
import time
import unittest
from unittest.mock import patch, MagicMock

from pdf_metadata_manager.utils.timestamp_utils import (
    get_timestamps,
    set_timestamps,
    preserve_timestamps,
    _set_creation_date_macos
)


class TestGetTimestamps(unittest.TestCase):
    """Test get_timestamps function."""

    def setUp(self):
        """Create a temporary file for testing."""
        self.temp_file = tempfile.NamedTemporaryFile(delete=False)
        self.temp_file.write(b"test content")
        self.temp_file.close()

    def tearDown(self):
        """Clean up temporary file."""
        if os.path.exists(self.temp_file.name):
            os.remove(self.temp_file.name)

    def test_get_timestamps_success(self):
        """Test getting timestamps from an existing file."""
        timestamps = get_timestamps(self.temp_file.name)

        # Check that all required keys are present
        self.assertIn('mtime', timestamps)
        self.assertIn('atime', timestamps)
        self.assertIn('ctime', timestamps)

        # Check that timestamps are valid (positive floats)
        self.assertIsInstance(timestamps['mtime'], float)
        self.assertIsInstance(timestamps['atime'], float)
        self.assertIsInstance(timestamps['ctime'], float)
        self.assertGreater(timestamps['mtime'], 0)
        self.assertGreater(timestamps['atime'], 0)
        self.assertGreater(timestamps['ctime'], 0)

    def test_get_timestamps_includes_birthtime_on_macos(self):
        """Test that birthtime is included on macOS."""
        timestamps = get_timestamps(self.temp_file.name)

        if platform.system() == 'Darwin':
            # On macOS, birthtime should be present
            self.assertIn('birthtime', timestamps)
            self.assertIsInstance(timestamps['birthtime'], float)
            self.assertGreater(timestamps['birthtime'], 0)
        else:
            # On other platforms, birthtime should not be present
            self.assertNotIn('birthtime', timestamps)

    def test_get_timestamps_nonexistent_file(self):
        """Test getting timestamps from a nonexistent file."""
        with self.assertRaises(FileNotFoundError):
            get_timestamps("/nonexistent/file.txt")


class TestSetTimestamps(unittest.TestCase):
    """Test set_timestamps function."""

    def setUp(self):
        """Create a temporary file for testing."""
        self.temp_file = tempfile.NamedTemporaryFile(delete=False)
        self.temp_file.write(b"test content")
        self.temp_file.close()

        # Wait a bit to ensure timestamps are different
        time.sleep(0.1)

    def tearDown(self):
        """Clean up temporary file."""
        if os.path.exists(self.temp_file.name):
            os.remove(self.temp_file.name)

    def test_set_timestamps_success(self):
        """Test setting timestamps on a file."""
        # Get original timestamps
        original = get_timestamps(self.temp_file.name)

        # Create new timestamps (1 day earlier)
        new_timestamps = {
            'mtime': original['mtime'] - 86400,  # 1 day in seconds
            'atime': original['atime'] - 86400,
            'ctime': original['ctime'] - 86400
        }

        # Set the new timestamps
        result = set_timestamps(self.temp_file.name, new_timestamps)
        self.assertTrue(result)

        # Verify that mtime and atime were updated
        updated = get_timestamps(self.temp_file.name)
        self.assertAlmostEqual(updated['mtime'], new_timestamps['mtime'], places=0)
        self.assertAlmostEqual(updated['atime'], new_timestamps['atime'], places=0)

    def test_set_timestamps_nonexistent_file(self):
        """Test setting timestamps on a nonexistent file."""
        timestamps = {
            'mtime': time.time(),
            'atime': time.time(),
            'ctime': time.time()
        }

        result = set_timestamps("/nonexistent/file.txt", timestamps)
        self.assertFalse(result)

    def test_set_timestamps_with_defaults(self):
        """Test setting timestamps with missing keys (should use defaults)."""
        # Only provide mtime, let function use defaults for atime
        timestamps = {
            'mtime': time.time() - 3600  # 1 hour ago
        }

        result = set_timestamps(self.temp_file.name, timestamps)
        self.assertTrue(result)

    @patch('platform.system')
    @patch('pdf_metadata_manager.utils.timestamp_utils._set_creation_date_macos')
    def test_set_timestamps_calls_macos_function(self, mock_macos_func, mock_platform):
        """Test that macOS-specific function is called on macOS."""
        mock_platform.return_value = 'Darwin'
        mock_macos_func.return_value = True

        timestamps = {
            'mtime': time.time(),
            'atime': time.time(),
            'birthtime': time.time() - 86400
        }

        result = set_timestamps(self.temp_file.name, timestamps)
        self.assertTrue(result)

        # Verify macOS function was called
        mock_macos_func.assert_called_once()

    @patch('platform.system')
    def test_set_timestamps_skips_macos_function_on_linux(self, mock_platform):
        """Test that macOS-specific function is not called on Linux."""
        mock_platform.return_value = 'Linux'

        timestamps = {
            'mtime': time.time(),
            'atime': time.time(),
            'ctime': time.time()
        }

        with patch('pdf_metadata_manager.utils.timestamp_utils._set_creation_date_macos') as mock_macos:
            result = set_timestamps(self.temp_file.name, timestamps)
            self.assertTrue(result)

            # Verify macOS function was NOT called on Linux
            mock_macos.assert_not_called()


class TestPreserveTimestamps(unittest.TestCase):
    """Test preserve_timestamps function."""

    def setUp(self):
        """Create temporary files for testing."""
        # Create source file
        self.source_file = tempfile.NamedTemporaryFile(delete=False)
        self.source_file.write(b"source content")
        self.source_file.close()

        # Wait a bit to ensure different timestamps
        time.sleep(0.1)

        # Create target file
        self.target_file = tempfile.NamedTemporaryFile(delete=False)
        self.target_file.write(b"target content")
        self.target_file.close()

    def tearDown(self):
        """Clean up temporary files."""
        for f in [self.source_file.name, self.target_file.name]:
            if os.path.exists(f):
                os.remove(f)

    def test_preserve_timestamps_success(self):
        """Test preserving timestamps from source to target."""
        # Get source timestamps
        source_timestamps = get_timestamps(self.source_file.name)

        # Preserve timestamps
        result = preserve_timestamps(self.target_file.name, self.source_file.name)
        self.assertTrue(result)

        # Verify timestamps were copied
        target_timestamps = get_timestamps(self.target_file.name)
        self.assertAlmostEqual(
            target_timestamps['mtime'],
            source_timestamps['mtime'],
            places=0
        )
        self.assertAlmostEqual(
            target_timestamps['atime'],
            source_timestamps['atime'],
            places=0
        )

    def test_preserve_timestamps_nonexistent_source(self):
        """Test preserving timestamps when source doesn't exist."""
        result = preserve_timestamps(self.target_file.name, "/nonexistent/source.txt")
        self.assertFalse(result)

    def test_preserve_timestamps_nonexistent_target(self):
        """Test preserving timestamps when target doesn't exist."""
        result = preserve_timestamps("/nonexistent/target.txt", self.source_file.name)
        self.assertFalse(result)

    def test_preserve_timestamps_both_nonexistent(self):
        """Test preserving timestamps when both files don't exist."""
        result = preserve_timestamps("/nonexistent/target.txt", "/nonexistent/source.txt")
        self.assertFalse(result)


class TestSetCreationDateMacOS(unittest.TestCase):
    """Test _set_creation_date_macos function."""

    def setUp(self):
        """Create a temporary file for testing."""
        self.temp_file = tempfile.NamedTemporaryFile(delete=False)
        self.temp_file.write(b"test content")
        self.temp_file.close()

    def tearDown(self):
        """Clean up temporary file."""
        if os.path.exists(self.temp_file.name):
            os.remove(self.temp_file.name)

    @patch('subprocess.run')
    def test_setfile_available(self, mock_run):
        """Test when SetFile command is available."""
        # Mock successful 'which SetFile' check
        mock_which = MagicMock()
        mock_which.returncode = 0

        # Mock successful SetFile command
        mock_setfile = MagicMock()
        mock_setfile.returncode = 0

        # Return different mocks for different calls
        mock_run.side_effect = [mock_which, mock_setfile]

        creation_time = time.time() - 86400  # 1 day ago
        result = _set_creation_date_macos(self.temp_file.name, creation_time)

        self.assertTrue(result)
        self.assertEqual(mock_run.call_count, 2)

    @patch('subprocess.run')
    def test_setfile_not_available(self, mock_run):
        """Test when SetFile command is not available."""
        # Mock failed 'which SetFile' check
        mock_which = MagicMock()
        mock_which.returncode = 1
        mock_run.return_value = mock_which

        creation_time = time.time()
        result = _set_creation_date_macos(self.temp_file.name, creation_time)

        # Should return False but not raise an exception
        self.assertFalse(result)
        mock_run.assert_called_once()

    @patch('subprocess.run')
    def test_setfile_command_fails(self, mock_run):
        """Test when SetFile command fails."""
        # Mock successful 'which' but failed SetFile
        mock_which = MagicMock()
        mock_which.returncode = 0

        # Second call should raise an exception
        import subprocess
        mock_run.side_effect = [
            mock_which,
            subprocess.CalledProcessError(1, 'SetFile', stderr="SetFile failed")
        ]

        creation_time = time.time()
        result = _set_creation_date_macos(self.temp_file.name, creation_time)

        # Should return False and handle the exception gracefully
        self.assertFalse(result)

    @patch('subprocess.run')
    def test_setfile_date_format(self, mock_run):
        """Test that date is formatted correctly for SetFile."""
        mock_which = MagicMock()
        mock_which.returncode = 0

        mock_setfile = MagicMock()
        mock_setfile.returncode = 0

        mock_run.side_effect = [mock_which, mock_setfile]

        # Use a specific timestamp
        creation_time = 1609459200.0  # 2021-01-01 00:00:00 UTC
        result = _set_creation_date_macos(self.temp_file.name, creation_time)

        self.assertTrue(result)

        # Check that SetFile was called with correct format
        # The format should be MM/DD/YYYY HH:MM:SS
        setfile_call = mock_run.call_args_list[1]
        self.assertEqual(setfile_call[0][0][0], "SetFile")
        self.assertEqual(setfile_call[0][0][1], "-d")
        # Date string should match the format (exact value depends on timezone)
        self.assertRegex(setfile_call[0][0][2], r'\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}')


class TestTimestampPreservationIntegration(unittest.TestCase):
    """Integration tests for timestamp preservation workflow."""

    def setUp(self):
        """Create temporary files for testing."""
        self.source_file = tempfile.NamedTemporaryFile(delete=False)
        self.source_file.write(b"source content")
        self.source_file.close()

        self.target_file = tempfile.NamedTemporaryFile(delete=False)
        self.target_file.write(b"target content")
        self.target_file.close()

    def tearDown(self):
        """Clean up temporary files."""
        for f in [self.source_file.name, self.target_file.name]:
            if os.path.exists(f):
                os.remove(f)

    def test_full_workflow(self):
        """Test complete workflow: get -> modify -> set -> verify."""
        # Step 1: Get original timestamps
        original = get_timestamps(self.source_file.name)

        # Step 2: Modify timestamps (simulate a file operation)
        time.sleep(0.1)
        with open(self.target_file.name, 'a') as f:
            f.write(" modified")

        # Step 3: Restore timestamps
        success = preserve_timestamps(self.target_file.name, self.source_file.name)
        self.assertTrue(success)

        # Step 4: Verify timestamps were preserved
        restored = get_timestamps(self.target_file.name)
        self.assertAlmostEqual(
            restored['mtime'],
            original['mtime'],
            places=0
        )

    def test_backup_and_restore_workflow(self):
        """Test backup file creation with timestamp preservation."""
        # Create a backup
        backup_path = self.source_file.name + ".bak"

        try:
            # Copy file to backup
            import shutil
            shutil.copy2(self.source_file.name, backup_path)

            # Verify backup exists
            self.assertTrue(os.path.exists(backup_path))

            # Preserve timestamps
            result = preserve_timestamps(backup_path, self.source_file.name)
            self.assertTrue(result)

            # Verify timestamps match
            source_ts = get_timestamps(self.source_file.name)
            backup_ts = get_timestamps(backup_path)

            self.assertAlmostEqual(source_ts['mtime'], backup_ts['mtime'], places=0)

        finally:
            if os.path.exists(backup_path):
                os.remove(backup_path)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""

    def test_empty_timestamps_dict(self):
        """Test set_timestamps with empty dictionary."""
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        temp_file.write(b"test")
        temp_file.close()

        try:
            # Should use defaults
            result = set_timestamps(temp_file.name, {})
            self.assertTrue(result)
        finally:
            os.remove(temp_file.name)

    def test_very_old_timestamp(self):
        """Test with very old timestamp (Unix epoch)."""
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        temp_file.write(b"test")
        temp_file.close()

        try:
            timestamps = {
                'mtime': 0,  # Unix epoch
                'atime': 0
            }
            result = set_timestamps(temp_file.name, timestamps)
            self.assertTrue(result)
        finally:
            os.remove(temp_file.name)

    def test_future_timestamp(self):
        """Test with future timestamp."""
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        temp_file.write(b"test")
        temp_file.close()

        try:
            timestamps = {
                'mtime': time.time() + 86400,  # Tomorrow
                'atime': time.time() + 86400
            }
            result = set_timestamps(temp_file.name, timestamps)
            self.assertTrue(result)
        finally:
            os.remove(temp_file.name)


if __name__ == '__main__':
    unittest.main()
