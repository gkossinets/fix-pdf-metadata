"""JSON logging system for PDF processing sessions."""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any


class SessionLogger:
    """Log PDF processing session to JSON file."""

    def __init__(self, log_path: Optional[str] = None, settings: Optional[dict] = None):
        """
        Initialize logger.

        Args:
            log_path: Custom log file path (default: auto-generate)
            settings: Settings dict to include in session metadata
        """
        self.start_time = datetime.now()
        self.settings = settings or {}
        self.results: List[Dict[str, Any]] = []

        # Auto-generate log filename if not provided
        if log_path is None:
            timestamp = self.start_time.strftime("%Y%m%d_%H%M%S")
            self.log_path = f"pdf_metadata_log_{timestamp}.json"
        else:
            self.log_path = log_path

        # Ensure parent directory exists
        log_dir = Path(self.log_path).parent
        if log_dir != Path('.'):
            log_dir.mkdir(parents=True, exist_ok=True)

    def log_success(
        self,
        original_path: str,
        new_path: str,
        doi: str,
        confidence: float,
        used_ocr: bool = False
    ):
        """
        Log successful processing.

        Args:
            original_path: Original file path
            new_path: New file path after renaming
            doi: Matched DOI
            confidence: Match confidence score (0.0-1.0)
            used_ocr: Whether OCR was used for text extraction
        """
        result = {
            "original_path": original_path,
            "status": "success",
            "matched_doi": doi,
            "confidence": confidence,
            "new_filename": Path(new_path).name,
            "metadata_updated": True,
            "renamed": original_path != new_path,
            "used_ocr": used_ocr,
            "timestamp": datetime.now().isoformat()
        }
        self.results.append(result)

    def log_skip(
        self,
        original_path: str,
        reason: str
    ):
        """
        Log skipped file.

        Args:
            original_path: Original file path
            reason: Reason for skipping
        """
        result = {
            "original_path": original_path,
            "status": "skipped",
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        }
        self.results.append(result)

    def log_failure(
        self,
        original_path: str,
        error: str,
        attempts: int = 1
    ):
        """
        Log failed processing.

        Args:
            original_path: Original file path
            error: Error message
            attempts: Number of attempts made
        """
        result = {
            "original_path": original_path,
            "status": "failed",
            "error": error,
            "attempts": attempts,
            "timestamp": datetime.now().isoformat()
        }
        self.results.append(result)

    def get_stats(self) -> Dict[str, int]:
        """
        Get summary statistics for the session.

        Returns:
            Dictionary with counts by status
        """
        stats = {"success": 0, "skipped": 0, "failed": 0}
        for result in self.results:
            status = result.get("status")
            if status in stats:
                stats[status] += 1
        return stats

    def close(self):
        """Finalize and write log file."""
        end_time = datetime.now()
        stats = self.get_stats()

        log_data = {
            "session": {
                "start_time": self.start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_seconds": (end_time - self.start_time).total_seconds(),
                "total_files": len(self.results),
                "successful": stats["success"],
                "skipped": stats["skipped"],
                "failed": stats["failed"],
                "settings": self.settings
            },
            "results": self.results
        }

        # Write JSON file with nice formatting
        with open(self.log_path, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures log is written."""
        self.close()
        return False
