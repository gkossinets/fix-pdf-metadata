"""
Filename parser for extracting metadata hints from PDF filenames.

This module provides functionality to parse various academic PDF filename formats
and extract author, year, and title information that can be used to search
for metadata in academic databases like Crossref.
"""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class FilenameHints:
    """
    Structured metadata hints extracted from a PDF filename.

    Attributes:
        author: Author name or hint (may include multiple authors)
        year: Publication year (as string)
        title: Article title hint
        confidence: Confidence score from 0.0 to 1.0 indicating how well
                   the filename matched a known pattern
    """
    author: Optional[str] = None
    year: Optional[str] = None
    title: Optional[str] = None
    confidence: float = 0.0


def parse_filename(filename: str) -> FilenameHints:
    """
    Extract author, year, and title hints from a PDF filename.

    This function attempts to match the filename against various common
    academic PDF naming conventions, from most structured (Zotero format)
    to least structured formats.

    Args:
        filename: The PDF filename (with or without .pdf extension)

    Returns:
        FilenameHints object with extracted information and confidence score

    Examples:
        >>> parse_filename("Smith - 2020 - Machine Learning.pdf")
        FilenameHints(author="Smith", year="2020", title="Machine Learning", confidence=0.9)

        >>> parse_filename("jones_2019.pdf")
        FilenameHints(author="jones", year="2019", title=None, confidence=0.6)

        >>> parse_filename("random_file.pdf")
        FilenameHints(author=None, year=None, title=None, confidence=0.0)
    """
    # Remove .pdf extension if present (case-insensitive)
    clean_name = filename
    if clean_name.lower().endswith('.pdf'):
        clean_name = clean_name[:-4]

    # Define patterns in order of confidence (most specific first)
    # Each pattern is (regex, confidence_score, (author_group, year_group, title_group))
    patterns = [
        # Zotero format: "Author - Year - Title"
        # Highest confidence as it's the most structured
        (r'^(.+?)\s*-\s*(\d{4})\s*-\s*(.+)$', 0.9, (1, 2, 3)),

        # "Author (Year) Title" or "Author (Year)"
        (r'^([A-Za-z\s&]+)\s*\((\d{4})\)\s*(.*)$', 0.85, (1, 2, 3)),

        # "Author Year Title" with spaces
        (r'^([A-Za-z\s&]+?)\s+(\d{4})\s+(.+)$', 0.75, (1, 2, 3)),

        # "Author_Year_Title" with underscores
        (r'^([A-Za-z]+)_(\d{4})_(.+)$', 0.75, (1, 2, 3)),

        # "Author_Year" with underscore (no title)
        (r'^([A-Za-z]+)_(\d{4})$', 0.6, (1, 2, None)),

        # "AuthorYEAR" concatenated (no title)
        (r'^([A-Za-z]+)(\d{4})$', 0.6, (1, 2, None)),

        # "Author Year" with space (no title)
        (r'^([A-Za-z\s&]+)\s+(\d{4})$', 0.65, (1, 2, None)),

        # "Year_Author" reversed format
        (r'^(\d{4})_([A-Za-z]+)$', 0.55, (2, 1, None)),

        # Just year in filename
        (r'^.*?(\d{4}).*?$', 0.3, (None, 1, None)),
    ]

    for pattern, confidence, groups in patterns:
        match = re.match(pattern, clean_name)
        if match:
            author_group, year_group, title_group = groups

            author = match.group(author_group).strip() if author_group else None
            year = match.group(year_group).strip() if year_group else None
            title = None

            # Handle title extraction
            if title_group:
                title = match.group(title_group).strip()
                # Empty title should be treated as None
                if not title:
                    title = None
                    # Lower confidence if title was expected but missing
                    confidence *= 0.9

            # Clean up author field
            if author:
                # Handle multiple authors with & or "et al"
                if ' & ' in author or ' and ' in author.lower():
                    # Keep as is - indicates multiple authors
                    pass
                elif 'et al' in author.lower():
                    # Keep as is
                    pass

                # Clean up extra whitespace
                author = ' '.join(author.split())

            # Validate year is reasonable (between 1800 and 2100)
            if year:
                try:
                    year_int = int(year)
                    if year_int < 1800 or year_int > 2100:
                        # Probably not a real year, continue to next pattern
                        continue
                except ValueError:
                    continue

            return FilenameHints(
                author=author,
                year=year,
                title=title,
                confidence=confidence
            )

    # No pattern matched
    return FilenameHints(confidence=0.0)
