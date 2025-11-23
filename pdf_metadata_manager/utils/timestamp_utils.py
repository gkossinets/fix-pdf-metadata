"""
Cross-platform timestamp preservation utilities.

This module provides utilities for preserving file timestamps across different
platforms (macOS, Linux, Windows).
"""

import os
import platform
import subprocess
import time
from typing import Dict, Optional


def get_timestamps(file_path: str) -> Dict[str, float]:
    """
    Get all timestamps for a file.

    Args:
        file_path: Path to the file

    Returns:
        Dict with 'mtime', 'atime', 'ctime' keys containing timestamp values

    Raises:
        FileNotFoundError: If the file doesn't exist
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    stat_info = os.stat(file_path)
    timestamps = {
        'mtime': stat_info.st_mtime,
        'atime': stat_info.st_atime,
        'ctime': stat_info.st_ctime
    }

    # On macOS, try to get birthtime if available
    if platform.system() == 'Darwin' and hasattr(stat_info, 'st_birthtime'):
        timestamps['birthtime'] = stat_info.st_birthtime

    return timestamps


def set_timestamps(file_path: str, timestamps: Dict[str, float]) -> bool:
    """
    Set timestamps on a file.

    Args:
        file_path: File to update
        timestamps: Dict with 'mtime', 'atime', and optionally 'ctime'/'birthtime' keys

    Returns:
        True if successful, False otherwise
    """
    if not os.path.exists(file_path):
        print(f"Warning: File not found: {file_path}")
        return False

    try:
        # Set modification and access time (works on all platforms)
        atime = timestamps.get('atime', time.time())
        mtime = timestamps.get('mtime', time.time())
        os.utime(file_path, (atime, mtime))

        # For macOS, try to preserve creation time using SetFile
        if platform.system() == 'Darwin':
            # Try birthtime first, fallback to ctime
            creation_time = timestamps.get('birthtime') or timestamps.get('ctime')
            if creation_time:
                _set_creation_date_macos(file_path, creation_time)

        return True

    except Exception as e:
        print(f"Warning: Could not set all timestamps: {e}")
        return False


def preserve_timestamps(target_path: str, source_path: str) -> bool:
    """
    Preserve file timestamps from source to target.

    This function copies modification time, access time, and (on macOS) creation
    time from the source file to the target file.

    Args:
        target_path: File to update timestamps on
        source_path: File to copy timestamps from

    Returns:
        True if all timestamps preserved, False if partial/failed

    Examples:
        >>> preserve_timestamps("output.pdf", "original.pdf")
        True
    """
    try:
        if not os.path.exists(source_path):
            print(f"Warning: Source file not found: {source_path}")
            return False

        if not os.path.exists(target_path):
            print(f"Warning: Target file not found: {target_path}")
            return False

        # Get timestamps from source
        timestamps = get_timestamps(source_path)

        # Apply timestamps to target
        return set_timestamps(target_path, timestamps)

    except Exception as e:
        print(f"Warning: Could not preserve timestamps: {e}")
        return False


def _set_creation_date_macos(file_path: str, creation_time: float) -> bool:
    """
    Set file creation date on macOS using SetFile command.

    This is a macOS-specific function that uses the SetFile command from
    Apple's Command Line Tools. If SetFile is not available, it will fail
    gracefully with a warning.

    Args:
        file_path: Path to the file
        creation_time: Unix timestamp for creation time

    Returns:
        True if successful, False otherwise
    """
    try:
        # Check if SetFile is available
        result = subprocess.run(
            ["which", "SetFile"],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            # SetFile not available, warn but don't fail
            print("  Note: SetFile not available. Creation time not preserved.")
            print("  Install Xcode Command Line Tools for full timestamp preservation.")
            return False

        # Convert Unix timestamp to format required by SetFile: MM/DD/YYYY HH:MM:SS
        date_str = time.strftime("%m/%d/%Y %H:%M:%S", time.localtime(creation_time))

        # Run SetFile command
        result = subprocess.run(
            ["SetFile", "-d", date_str, file_path],
            capture_output=True,
            text=True,
            check=True
        )

        return True

    except subprocess.CalledProcessError as e:
        print(f"  Warning: SetFile command failed: {e}")
        return False

    except Exception as e:
        print(f"  Warning: Could not set creation date: {e}")
        return False
