"""Core modules for PDF metadata management."""

from .crossref_client import (
    CrossrefClient,
    CrossrefMatch,
    CrossrefConnectionError,
    CrossrefAPIError
)
from .filename_parser import FilenameHints, parse_filename
from .metadata_updater import (
    MetadataUpdater,
    MetadataUpdate,
    PDFUpdateError,
    FileOperationError
)
from .pdf_processor import (
    PDFProcessor,
    PDFMetadata,
    PDFProcessingError,
    PDFNotFoundError,
    PDFReadError,
    OCRNotAvailableError
)

__all__ = [
    'CrossrefClient',
    'CrossrefMatch',
    'CrossrefConnectionError',
    'CrossrefAPIError',
    'FilenameHints',
    'parse_filename',
    'MetadataUpdater',
    'MetadataUpdate',
    'PDFUpdateError',
    'FileOperationError',
    'PDFProcessor',
    'PDFMetadata',
    'PDFProcessingError',
    'PDFNotFoundError',
    'PDFReadError',
    'OCRNotAvailableError'
]
