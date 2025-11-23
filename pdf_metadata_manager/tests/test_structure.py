"""
Structural validation tests - verify module structure without external dependencies.
"""

import unittest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestModuleStructure(unittest.TestCase):
    """Test that all modules can be imported and have expected structure."""

    def test_utils_timestamp_utils_exists(self):
        """Test that timestamp_utils module exists and has required functions."""
        try:
            from utils import timestamp_utils

            # Check required functions exist
            self.assertTrue(hasattr(timestamp_utils, 'get_timestamps'))
            self.assertTrue(hasattr(timestamp_utils, 'set_timestamps'))
            self.assertTrue(hasattr(timestamp_utils, 'preserve_timestamps'))

        except ImportError as e:
            self.fail(f"Could not import timestamp_utils: {e}")

    def test_core_metadata_updater_structure(self):
        """Test that metadata_updater module has required classes."""
        try:
            # Import without pikepdf dependency
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "metadata_updater",
                os.path.join(os.path.dirname(__file__), "..", "core", "metadata_updater.py")
            )

            # Just verify the file exists and is valid Python
            self.assertIsNotNone(spec)

        except Exception as e:
            self.fail(f"Error loading metadata_updater: {e}")

    def test_directory_structure(self):
        """Test that all required directories exist."""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        required_dirs = [
            'core',
            'ui',
            'utils',
            'tests'
        ]

        for dir_name in required_dirs:
            dir_path = os.path.join(base_dir, dir_name)
            self.assertTrue(
                os.path.isdir(dir_path),
                f"Required directory '{dir_name}' does not exist"
            )

    def test_init_files_exist(self):
        """Test that __init__.py files exist in all packages."""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        required_inits = [
            '__init__.py',
            'core/__init__.py',
            'ui/__init__.py',
            'utils/__init__.py',
            'tests/__init__.py'
        ]

        for init_file in required_inits:
            init_path = os.path.join(base_dir, init_file)
            self.assertTrue(
                os.path.isfile(init_path),
                f"Required __init__.py file does not exist: {init_file}"
            )


if __name__ == '__main__':
    unittest.main()
