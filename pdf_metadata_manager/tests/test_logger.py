"""Tests for the SessionLogger module."""

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from pdf_metadata_manager.utils.logger import SessionLogger


class TestSessionLogger:
    """Test SessionLogger functionality."""

    def test_auto_generated_filename(self):
        """Test that logger auto-generates filename with timestamp."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            logger = SessionLogger()

            # Should match format: pdf_metadata_log_YYYYMMDD_HHMMSS.json
            assert logger.log_path.startswith("pdf_metadata_log_")
            assert logger.log_path.endswith(".json")
            assert len(logger.log_path) == len("pdf_metadata_log_YYYYMMDD_HHMMSS.json")

    def test_custom_log_path(self):
        """Test using custom log path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_path = os.path.join(tmpdir, "custom_log.json")
            logger = SessionLogger(log_path=custom_path)
            assert logger.log_path == custom_path

    def test_log_path_with_subdirectory(self):
        """Test that subdirectories are created if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "logs", "subdir", "test.json")
            logger = SessionLogger(log_path=log_path)
            assert logger.log_path == log_path
            assert os.path.exists(os.path.join(tmpdir, "logs", "subdir"))

    def test_log_success(self):
        """Test logging successful processing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "test.json")
            logger = SessionLogger(log_path=log_path)

            logger.log_success(
                original_path="/path/to/original.pdf",
                new_path="/path/to/new.pdf",
                doi="10.1234/test",
                confidence=0.87,
                used_ocr=True
            )

            assert len(logger.results) == 1
            result = logger.results[0]
            assert result["status"] == "success"
            assert result["original_path"] == "/path/to/original.pdf"
            assert result["matched_doi"] == "10.1234/test"
            assert result["confidence"] == 0.87
            assert result["new_filename"] == "new.pdf"
            assert result["metadata_updated"] is True
            assert result["renamed"] is True
            assert result["used_ocr"] is True
            assert "timestamp" in result

    def test_log_success_no_rename(self):
        """Test logging success when file wasn't renamed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "test.json")
            logger = SessionLogger(log_path=log_path)

            logger.log_success(
                original_path="/path/to/same.pdf",
                new_path="/path/to/same.pdf",
                doi="10.1234/test",
                confidence=0.92
            )

            result = logger.results[0]
            assert result["renamed"] is False
            assert result["used_ocr"] is False

    def test_log_skip(self):
        """Test logging skipped file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "test.json")
            logger = SessionLogger(log_path=log_path)

            logger.log_skip(
                original_path="/path/to/skipped.pdf",
                reason="User chose to skip"
            )

            assert len(logger.results) == 1
            result = logger.results[0]
            assert result["status"] == "skipped"
            assert result["original_path"] == "/path/to/skipped.pdf"
            assert result["reason"] == "User chose to skip"
            assert "timestamp" in result

    def test_log_failure(self):
        """Test logging failed processing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "test.json")
            logger = SessionLogger(log_path=log_path)

            logger.log_failure(
                original_path="/path/to/failed.pdf",
                error="Connection timeout",
                attempts=3
            )

            assert len(logger.results) == 1
            result = logger.results[0]
            assert result["status"] == "failed"
            assert result["original_path"] == "/path/to/failed.pdf"
            assert result["error"] == "Connection timeout"
            assert result["attempts"] == 3
            assert "timestamp" in result

    def test_get_stats(self):
        """Test statistics calculation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "test.json")
            logger = SessionLogger(log_path=log_path)

            # Log various results
            logger.log_success("/path/1.pdf", "/path/new1.pdf", "10.1/1", 0.9)
            logger.log_success("/path/2.pdf", "/path/new2.pdf", "10.1/2", 0.85)
            logger.log_skip("/path/3.pdf", "Low confidence")
            logger.log_failure("/path/4.pdf", "Network error")
            logger.log_skip("/path/5.pdf", "User skipped")

            stats = logger.get_stats()
            assert stats["success"] == 2
            assert stats["skipped"] == 2
            assert stats["failed"] == 1

    def test_close_writes_json(self):
        """Test that close() writes valid JSON file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "test.json")
            settings = {"use_ocr": True, "batch_mode": False}
            logger = SessionLogger(log_path=log_path, settings=settings)

            # Add some results
            logger.log_success("/path/1.pdf", "/path/new1.pdf", "10.1/1", 0.9)
            logger.log_skip("/path/2.pdf", "User skipped")
            logger.log_failure("/path/3.pdf", "Error", attempts=2)

            # Close and write
            logger.close()

            # Verify file exists and is valid JSON
            assert os.path.exists(log_path)

            with open(log_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Check session data
            assert "session" in data
            assert "results" in data

            session = data["session"]
            assert "start_time" in session
            assert "end_time" in session
            assert "duration_seconds" in session
            assert session["total_files"] == 3
            assert session["successful"] == 1
            assert session["skipped"] == 1
            assert session["failed"] == 1
            assert session["settings"] == settings

            # Check results
            assert len(data["results"]) == 3
            assert data["results"][0]["status"] == "success"
            assert data["results"][1]["status"] == "skipped"
            assert data["results"][2]["status"] == "failed"

    def test_session_timestamps(self):
        """Test that session timestamps are valid ISO format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "test.json")
            logger = SessionLogger(log_path=log_path)
            logger.log_success("/path/1.pdf", "/path/new1.pdf", "10.1/1", 0.9)
            logger.close()

            with open(log_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Verify timestamps are valid ISO format
            start_time = datetime.fromisoformat(data["session"]["start_time"])
            end_time = datetime.fromisoformat(data["session"]["end_time"])
            assert end_time >= start_time

            # Duration should be positive
            assert data["session"]["duration_seconds"] >= 0

    def test_context_manager(self):
        """Test using SessionLogger as context manager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "test.json")

            with SessionLogger(log_path=log_path) as logger:
                logger.log_success("/path/1.pdf", "/path/new1.pdf", "10.1/1", 0.9)

            # Log should be written automatically
            assert os.path.exists(log_path)

            with open(log_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            assert data["session"]["total_files"] == 1
            assert len(data["results"]) == 1

    def test_context_manager_with_exception(self):
        """Test that log is written even if exception occurs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "test.json")

            try:
                with SessionLogger(log_path=log_path) as logger:
                    logger.log_success("/path/1.pdf", "/path/new1.pdf", "10.1/1", 0.9)
                    raise ValueError("Test exception")
            except ValueError:
                pass

            # Log should still be written
            assert os.path.exists(log_path)

            with open(log_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            assert data["session"]["total_files"] == 1

    def test_empty_session(self):
        """Test logging session with no results."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "test.json")
            logger = SessionLogger(log_path=log_path)
            logger.close()

            with open(log_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            assert data["session"]["total_files"] == 0
            assert data["session"]["successful"] == 0
            assert data["session"]["skipped"] == 0
            assert data["session"]["failed"] == 0
            assert len(data["results"]) == 0

    def test_unicode_handling(self):
        """Test that logger handles unicode characters correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "test.json")
            logger = SessionLogger(log_path=log_path)

            logger.log_success(
                original_path="/path/to/café_文档.pdf",
                new_path="/path/to/Smith et al - 2020 - Über München.pdf",
                doi="10.1234/test",
                confidence=0.9
            )

            logger.close()

            with open(log_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            result = data["results"][0]
            assert "café_文档.pdf" in result["original_path"]
            assert "Über München.pdf" in result["new_filename"]

    def test_multiple_sessions_different_filenames(self):
        """Test that multiple loggers create different filenames."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            logger1 = SessionLogger()
            # Need to wait 1 second since timestamp has second precision
            import time
            time.sleep(1.1)
            logger2 = SessionLogger()

            # Filenames should be different (different timestamps)
            assert logger1.log_path != logger2.log_path

    def test_settings_preservation(self):
        """Test that settings dict is preserved correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "test.json")
            settings = {
                "use_ocr": True,
                "ocr_pages": 3,
                "keep_backup": False,
                "batch_mode": True,
                "email": "test@example.com"
            }

            logger = SessionLogger(log_path=log_path, settings=settings)
            logger.close()

            with open(log_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            assert data["session"]["settings"] == settings
