"""Tests for the PDFMetadataManager orchestration logic.

These focus on the interactive selection flow: a numbered pick from the
candidate list is applied immediately, while a manual DOI entry still goes
through the confirmation step.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

from pdf_metadata_manager.pdf_metadata_manager import PDFMetadataManager
from pdf_metadata_manager.core import CrossrefMatch

# Use an absolute path so process_single_pdf's Path(...).resolve() does not
# depend on the current working directory. Other test modules chdir into a
# TemporaryDirectory that is later deleted, which would otherwise make a
# relative path unresolvable and cause spurious order-dependent failures.
PDF_PATH = "/tmp/pmm_test_paper.pdf"


def _extracted(**overrides):
    """Build a fake extracted-PDF-metadata object."""
    base = dict(doi=None, title="T", authors="A", year="2020", used_ocr=False)
    base.update(overrides)
    return SimpleNamespace(**base)


def _current_metadata():
    """Build a fake current-docinfo metadata object (all empty)."""
    return SimpleNamespace(
        title=None, authors=None, year=None, journal=None, doi=None, isbn=None
    )


def _manager_with_mocks():
    """Create a manager with all external components replaced by mocks."""
    mgr = PDFMetadataManager(email="x@y.com")
    mgr.ui = MagicMock()
    mgr.ui.quiet = False
    mgr.ui.verbose = False
    mgr.pdf_processor = MagicMock()
    mgr.pdf_processor.extract_metadata.return_value = _extracted()
    mgr.metadata_updater = MagicMock()
    mgr.metadata_updater.read_metadata.return_value = _current_metadata()
    mgr.metadata_updater.generate_zotero_filename.return_value = "new.pdf"
    mgr.metadata_updater.rename_file.return_value = "/tmp/new.pdf"
    mgr.crossref_client = MagicMock()
    mgr.logger = MagicMock()
    return mgr


def test_numbered_pick_skips_confirmation():
    """Selecting a numbered candidate applies metadata without confirmation."""
    mgr = _manager_with_mocks()
    match = CrossrefMatch(
        doi="10.1/x", title="T", authors=["A, B"], year="2020",
        journal="J", score=0.9,
    )
    mgr.crossref_client.search.return_value = [match]
    # display_matches returns a CrossrefMatch => a direct numbered pick.
    mgr.ui.display_matches.return_value = match

    result = mgr.process_single_pdf(PDF_PATH)

    assert result == "completed"
    mgr.ui.confirm_metadata.assert_not_called()
    mgr.metadata_updater.update_metadata.assert_called_once()


def test_manual_doi_still_confirms():
    """Entering a manual DOI still goes through the confirmation step."""
    mgr = _manager_with_mocks()
    mgr.crossref_client.search.return_value = [
        CrossrefMatch(
            doi="10.1/y", title="T2", authors=["C"], year="2019",
            journal="J", score=0.7,
        )
    ]
    # display_matches signals a manual DOI entry, not a numbered pick.
    mgr.ui.display_matches.return_value = ("manual", "10.1/x")
    mgr.ui.confirm_metadata.return_value = True
    mgr.crossref_client.fetch_metadata.return_value = {
        "doi": "10.1/x", "title": "Manual", "authors": ["A, B"],
        "year": "2020", "journal": "J",
    }

    result = mgr.process_single_pdf(PDF_PATH)

    assert result == "completed"
    mgr.ui.confirm_metadata.assert_called_once()
