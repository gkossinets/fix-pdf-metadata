"""Core modules for PDF processing."""
"""Core modules for PDF metadata management."""

from .crossref_client import (
    CrossrefClient,
    CrossrefMatch,
    CrossrefConnectionError,
    CrossrefAPIError
)

__all__ = [
    'CrossrefClient',
    'CrossrefMatch',
    'CrossrefConnectionError',
    'CrossrefAPIError'
]
