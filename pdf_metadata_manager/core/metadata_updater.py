"""
PDF metadata updater and file renaming utilities.

This module provides functionality to update PDF metadata and rename files
in Zotero format while preserving file timestamps.
"""

import os
import re
import shutil
from dataclasses import dataclass
from typing import Optional

import pikepdf

try:
    from PyPDF2 import PdfReader, PdfWriter
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False
    print("Warning: PyPDF2 not available. Only pikepdf will be used for PDF operations.")

try:
    from pathvalidate import sanitize_filename as pathvalidate_sanitize
    PATHVALIDATE_AVAILABLE = True
except ImportError:
    PATHVALIDATE_AVAILABLE = False

from ..utils.timestamp_utils import preserve_timestamps, get_timestamps, set_timestamps


# Custom exceptions
class PDFUpdateError(Exception):
    """Raised when PDF metadata update fails."""
    pass


class FileOperationError(Exception):
    """Raised when file operations fail."""
    pass


@dataclass
class MetadataUpdate:
    """Metadata to write to PDF."""
    title: str
    authors: str  # Semicolon-separated
    year: Optional[str] = None
    journal: Optional[str] = None
    doi: Optional[str] = None
    isbn: Optional[str] = None


class MetadataUpdater:
    """Update PDF metadata and rename files."""

    def __init__(self, keep_backup: bool = False):
        """
        Initialize metadata updater.

        Args:
            keep_backup: Keep .bak copy of original files
        """
        self.keep_backup = keep_backup

    def update_metadata(
        self,
        pdf_path: str,
        metadata: MetadataUpdate,
        output_path: Optional[str] = None
    ) -> bool:
        """
        Update PDF metadata.

        Updates both docinfo and XMP metadata in the PDF file. Uses pikepdf
        as the primary library with PyPDF2 as a fallback if available.

        Args:
            pdf_path: Path to PDF file
            metadata: Metadata to write
            output_path: Optional output path (default: update in-place)

        Returns:
            True if successful, False otherwise

        Raises:
            PDFUpdateError: If update fails with all methods
            FileNotFoundError: If PDF file doesn't exist
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        # Default to in-place update
        if not output_path:
            output_path = pdf_path

        # Get original timestamps for preservation
        original_timestamps = get_timestamps(pdf_path)

        # Create backup if requested
        if self.keep_backup and output_path == pdf_path:
            backup_path = f"{pdf_path}.bak"
            shutil.copy2(pdf_path, backup_path)
            print(f"  Created backup: {backup_path}")

        # Try to update with pikepdf first
        try:
            return self._update_with_pikepdf(pdf_path, metadata, output_path, original_timestamps)
        except Exception as e:
            print(f"  pikepdf update failed: {e}")

            # Try PyPDF2 fallback if available
            if PYPDF2_AVAILABLE:
                print("  Trying PyPDF2 fallback...")
                try:
                    return self._update_with_pypdf2(pdf_path, metadata, output_path, original_timestamps)
                except Exception as e2:
                    print(f"  PyPDF2 fallback also failed: {e2}")
                    raise PDFUpdateError(f"All metadata update methods failed. Last error: {e2}")
            else:
                raise PDFUpdateError(f"Metadata update failed: {e}")

    def _update_with_pikepdf(
        self,
        pdf_path: str,
        metadata: MetadataUpdate,
        output_path: str,
        original_timestamps: dict
    ) -> bool:
        """Update PDF metadata using pikepdf."""
        # Create temp output if updating in-place
        temp_output = output_path + ".tmp" if output_path == pdf_path else output_path

        try:
            with pikepdf.open(pdf_path, allow_overwriting_input=True) as pdf:
                # Create a new docinfo dictionary (removes unwanted fields)
                new_docinfo = pikepdf.Dictionary()

                # Add only the metadata we want
                if metadata.title:
                    new_docinfo['/Title'] = metadata.title

                if metadata.authors:
                    new_docinfo['/Author'] = metadata.authors

                if metadata.year:
                    try:
                        # Set creation date to January 1st of the publication year
                        new_docinfo['/CreationDate'] = f"D:{metadata.year}0101000000Z"
                    except Exception as year_err:
                        print(f"  Warning: Could not set CreationDate: {year_err}")

                # Handle journal and DOI in Subject field
                subject_parts = []
                if metadata.journal:
                    subject_parts.append(metadata.journal)

                if metadata.doi:
                    subject_parts.append(f"DOI: {metadata.doi}")
                elif metadata.isbn:
                    subject_parts.append(f"ISBN: {metadata.isbn}")

                if subject_parts:
                    new_docinfo['/Subject'] = " | ".join(subject_parts)

                # Set Keywords field with DOI or ISBN
                if metadata.doi:
                    new_docinfo['/Keywords'] = f"DOI: {metadata.doi}"
                elif metadata.isbn:
                    new_docinfo['/Keywords'] = f"ISBN: {metadata.isbn}"

                # Preserve some standard metadata fields if they exist
                standard_fields = ['/Creator', '/Producer']
                for field in standard_fields:
                    if hasattr(pdf, 'docinfo') and pdf.docinfo and field in pdf.docinfo:
                        if field not in new_docinfo:
                            new_docinfo[field] = pdf.docinfo[field]

                # Make the dictionary an indirect object
                new_docinfo = pdf.make_indirect(new_docinfo)

                # Replace the entire docinfo dictionary
                pdf.docinfo = new_docinfo

                # Update XMP metadata as well
                try:
                    with pdf.open_metadata() as xmp_meta:
                        # Remove URL-related or "where from" related properties
                        keys_to_remove = []
                        for key in xmp_meta.keys():
                            key_lower = str(key).lower()
                            if any(term in key_lower for term in ['where', 'url', 'source', 'link', 'from', 'uri']):
                                keys_to_remove.append(key)

                        # Remove identified keys
                        for key in keys_to_remove:
                            try:
                                del xmp_meta[key]
                            except:
                                pass

                        # Add our metadata in XMP format
                        if metadata.title:
                            xmp_meta['dc:title'] = metadata.title

                        if metadata.authors:
                            # Split authors and convert to list
                            author_list = [author.strip() for author in re.split(r'[;,]', metadata.authors)]
                            xmp_meta['dc:creator'] = author_list

                        # Add journal and DOI to description
                        description_parts = []
                        if metadata.journal:
                            description_parts.append(metadata.journal)

                        if metadata.doi:
                            description_parts.append(f"DOI: {metadata.doi}")
                        elif metadata.isbn:
                            description_parts.append(f"ISBN: {metadata.isbn}")

                        if description_parts:
                            xmp_meta['dc:description'] = " | ".join(description_parts)

                        # Add DOI/ISBN to identifier field
                        if metadata.doi:
                            xmp_meta['dc:identifier'] = metadata.doi
                        elif metadata.isbn:
                            xmp_meta['dc:identifier'] = metadata.isbn

                except Exception as xmp_error:
                    print(f"  Warning: Could not update XMP metadata: {xmp_error}")

                # Save the PDF
                pdf.save(temp_output)

            # If updating in-place, replace original with temp file
            if output_path == pdf_path:
                os.replace(temp_output, output_path)

            # Preserve timestamps
            set_timestamps(output_path, original_timestamps)

            return True

        except Exception as e:
            # Clean up temp file if it exists
            if os.path.exists(temp_output) and temp_output != output_path:
                try:
                    os.remove(temp_output)
                except:
                    pass
            raise

    def _update_with_pypdf2(
        self,
        pdf_path: str,
        metadata: MetadataUpdate,
        output_path: str,
        original_timestamps: dict
    ) -> bool:
        """Update PDF metadata using PyPDF2 as fallback."""
        reader = PdfReader(pdf_path)
        writer = PdfWriter()

        # Add all pages from the original PDF
        for page in reader.pages:
            writer.add_page(page)

        # Create metadata dictionary
        metadata_dict = {}

        if metadata.title:
            metadata_dict["/Title"] = metadata.title

        if metadata.authors:
            metadata_dict["/Author"] = metadata.authors

        # Handle journal and DOI in Subject field
        subject_parts = []
        if metadata.journal:
            subject_parts.append(metadata.journal)

        if metadata.doi:
            subject_parts.append(f"DOI: {metadata.doi}")
        elif metadata.isbn:
            subject_parts.append(f"ISBN: {metadata.isbn}")

        if subject_parts:
            metadata_dict["/Subject"] = " | ".join(subject_parts)

        # Add Keywords field
        if metadata.doi:
            metadata_dict["/Keywords"] = f"DOI: {metadata.doi}"
        elif metadata.isbn:
            metadata_dict["/Keywords"] = f"ISBN: {metadata.isbn}"

        # Try to add metadata (PyPDF2 version compatibility)
        try:
            writer.add_metadata(metadata_dict)
        except AttributeError:
            try:
                writer.addMetadata(metadata_dict)
            except:
                print("  Warning: Could not add metadata with PyPDF2")

        # Save the PDF
        with open(output_path, "wb") as output_file:
            writer.write(output_file)

        # Preserve timestamps
        set_timestamps(output_path, original_timestamps)

        return True

    def generate_zotero_filename(
        self,
        metadata: MetadataUpdate,
        original_path: str
    ) -> str:
        """
        Generate Zotero-style filename from metadata.

        Format: "Author - Year - Title.pdf"

        Rules:
        - Single author: "Smith - 2020 - Title.pdf"
        - Two authors: "Smith & Jones - 2020 - Title.pdf"
        - Three+ authors: "Smith et al. - 2020 - Title.pdf"
        - Sanitize: remove quotes, apostrophes, commas, parentheses
        - Replace & with "and"
        - Truncate long titles (>100 chars) with "..."

        Args:
            metadata: Metadata to use for filename
            original_path: Original file path (for fallback)

        Returns:
            Sanitized filename in format "Author - Year - Title.pdf"

        Examples:
            >>> metadata = MetadataUpdate(
            ...     title="Machine Learning",
            ...     authors="Smith, J.; Johnson, A.",
            ...     year="2020"
            ... )
            >>> updater.generate_zotero_filename(metadata, "original.pdf")
            'Smith & Johnson - 2020 - Machine Learning.pdf'
        """
        try:
            # Check if metadata is incomplete
            mark_incomplete = False

            # Extract authors
            authors = []
            if metadata.authors:
                # Split author string by common delimiters
                author_list = re.split(r'[;,]', metadata.authors)

                for author in author_list[:3]:  # Limit to first 3 authors
                    author = author.strip()
                    if ' ' in author:
                        # For "Firstname Lastname" format, extract last name
                        last_name = author.split()[-1]
                        authors.append(last_name)
                    else:
                        authors.append(author)

            if not authors:
                authors = ['Unknown']
                mark_incomplete = True

            # Format the author part
            if len(authors) == 1:
                author_part = authors[0]
            elif len(authors) == 2:
                author_part = f"{authors[0]} & {authors[1]}"
            else:
                author_part = f"{authors[0]} et al."

            # Extract year
            year = metadata.year or 'Unknown'
            if year == 'Unknown':
                mark_incomplete = True

            # Extract title
            title = metadata.title or os.path.splitext(os.path.basename(original_path))[0]
            if not metadata.title:
                mark_incomplete = True

            # Truncate title if too long
            if len(title) > 100:
                title = title[:97] + "..."

            # Create raw filename
            raw_filename = f"{author_part} - {year} - {title}"

            # Sanitize filename
            if PATHVALIDATE_AVAILABLE:
                # Use pathvalidate's built-in sanitization
                filename = pathvalidate_sanitize(raw_filename)
                # Additional sanitization for specific characters
                filename = re.sub(r'[\'",;()]', '', filename)
                filename = re.sub(r'&', 'and', filename)
            else:
                # Manual sanitization with regex
                filename = re.sub(r'[<>:"/\\|?*\'(),;"]', '', raw_filename)
                filename = re.sub(r'&', 'and', filename)
                filename = re.sub(r'\s+', ' ', filename).strip()

            # Add extension
            filename = f"{filename}.pdf"

            # Handle long filenames
            if len(filename) > 240:
                base_name = filename[:-4]  # Remove .pdf
                base_name = base_name[:236]  # Truncate
                filename = f"{base_name}.pdf"

            # Prepend underscore if metadata is incomplete
            if mark_incomplete:
                filename = f"_{filename}"

            return filename

        except Exception as e:
            print(f"  Error creating Zotero filename: {e}")
            # Return original filename as fallback
            return os.path.basename(original_path)

    def rename_file(
        self,
        old_path: str,
        new_filename: str,
        output_dir: Optional[str] = None
    ) -> str:
        """
        Rename file and handle conflicts.

        If a file with the new name already exists, appends (2), (3), etc.
        to the filename until a unique name is found.

        Args:
            old_path: Current file path
            new_filename: New filename (not full path)
            output_dir: Optional output directory (default: same dir as old_path)

        Returns:
            Final path of renamed file

        Raises:
            FileOperationError: If rename fails
            FileNotFoundError: If old_path doesn't exist

        Examples:
            >>> updater.rename_file(
            ...     "/path/to/old.pdf",
            ...     "New Name.pdf",
            ...     "/path/to/output"
            ... )
            '/path/to/output/New Name.pdf'
        """
        if not os.path.exists(old_path):
            raise FileNotFoundError(f"File not found: {old_path}")

        try:
            # Determine output directory
            if output_dir:
                target_dir = output_dir
            else:
                target_dir = os.path.dirname(old_path)

            # Create output directory if it doesn't exist
            os.makedirs(target_dir, exist_ok=True)

            # Build new path
            new_path = os.path.join(target_dir, new_filename)

            # Handle conflicts by adding (2), (3), etc.
            counter = 1
            base_path = new_path
            while os.path.exists(new_path) and os.path.abspath(new_path) != os.path.abspath(old_path):
                name_parts = os.path.splitext(base_path)
                new_path = f"{name_parts[0]} ({counter}){name_parts[1]}"
                counter += 1

            # If the new path is the same as old path, no rename needed
            if os.path.abspath(new_path) == os.path.abspath(old_path):
                return new_path

            # Get timestamps before moving
            timestamps = get_timestamps(old_path)

            # Move/rename the file
            shutil.move(old_path, new_path)

            # Preserve timestamps
            set_timestamps(new_path, timestamps)

            return new_path

        except Exception as e:
            raise FileOperationError(f"Failed to rename file: {e}")
