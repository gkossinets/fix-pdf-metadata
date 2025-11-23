"""
Crossref API client with retry logic, fuzzy matching, and improved scoring.

This module provides a robust client for searching and fetching metadata from
the Crossref API, with exponential backoff retry logic, rate limiting, and
sophisticated matching algorithms.
"""

import re
import time
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import List, Optional, Dict, Any
from urllib.parse import quote_plus

import requests


# Custom exceptions
class CrossrefConnectionError(Exception):
    """Raised when connection to Crossref API fails after all retries."""
    pass


class CrossrefAPIError(Exception):
    """Raised for non-retryable API errors (e.g., 404, malformed requests)."""
    pass


@dataclass
class CrossrefMatch:
    """A potential match from Crossref."""
    doi: str
    title: str
    authors: List[str]
    year: Optional[str]
    journal: Optional[str]
    score: float  # 0.0 to 1.0

    @property
    def confidence_level(self) -> str:
        """Return HIGH/MEDIUM/LOW based on score."""
        if self.score >= 0.80:
            return "HIGH"
        elif self.score >= 0.65:
            return "MEDIUM"
        else:
            return "LOW"


class CrossrefClient:
    """Client for Crossref API with retry logic and rate limiting."""

    # Common words to ignore in title matching
    STOPWORDS = {
        'the', 'a', 'an', 'of', 'in', 'on', 'at', 'to', 'for', 'with',
        'from', 'by', 'and', 'or', 'but', 'is', 'are', 'was', 'were',
        'this', 'that', 'these', 'those', 'have', 'has', 'had', 'there'
    }

    def __init__(
        self,
        email: str,
        retries: int = 3,
        timeout: int = 30,
        backoff_factor: float = 1.0
    ):
        """
        Initialize Crossref client.

        Args:
            email: Your email (for polite pool and contact)
            retries: Number of retry attempts for failed requests
            timeout: Request timeout in seconds
            backoff_factor: Base delay for exponential backoff (seconds)
        """
        self.email = email
        self.retries = retries
        self.timeout = timeout
        self.backoff_factor = backoff_factor
        self.last_request_time = 0
        self.min_request_interval = 0.5  # Rate limiting: 0.5s between requests

        # User-Agent for polite pool
        self.headers = {
            'User-Agent': f'PdfMetadataManager/1.0 (mailto:{email})'
        }

    def _wait_for_rate_limit(self):
        """Ensure we respect rate limiting between requests."""
        time_since_last = time.time() - self.last_request_time
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        self.last_request_time = time.time()

    def _make_request(self, url: str, method: str = 'GET') -> Dict[str, Any]:
        """
        Make HTTP request with retry logic and exponential backoff.

        Args:
            url: The URL to request
            method: HTTP method (default: GET)

        Returns:
            Response JSON as dictionary

        Raises:
            CrossrefConnectionError: After all retries exhausted
            CrossrefAPIError: For non-retryable API errors
        """
        last_exception = None

        for attempt in range(self.retries):
            try:
                self._wait_for_rate_limit()

                response = requests.request(
                    method,
                    url,
                    headers=self.headers,
                    timeout=self.timeout
                )

                # Handle different HTTP status codes
                if response.status_code == 200:
                    return response.json()
                elif 400 <= response.status_code < 500:
                    # Client error - don't retry
                    raise CrossrefAPIError(
                        f"API error {response.status_code}: {response.text}"
                    )
                elif response.status_code >= 500:
                    # Server error - retry
                    raise requests.exceptions.RequestException(
                        f"Server error {response.status_code}"
                    )

            except (requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout,
                    requests.exceptions.RequestException) as e:
                last_exception = e

                if attempt < self.retries - 1:
                    # Exponential backoff: 1s, 2s, 4s
                    delay = self.backoff_factor * (2 ** attempt)
                    time.sleep(delay)
                    continue
                else:
                    # All retries exhausted
                    raise CrossrefConnectionError(
                        f"Connection failed after {self.retries} attempts: {str(e)}"
                    ) from e

        # Should not reach here, but just in case
        raise CrossrefConnectionError(
            f"Connection failed: {str(last_exception)}"
        ) from last_exception

    def _fuzzy_title_similarity(self, title1: str, title2: str) -> float:
        """
        Calculate fuzzy similarity between two titles.

        Uses sequence matching after normalizing the titles (lowercase,
        removing punctuation, filtering stopwords).

        Args:
            title1: First title
            title2: Second title

        Returns:
            Similarity score between 0.0 and 1.0
        """
        # Normalize titles
        def normalize(text: str) -> str:
            # Convert to lowercase
            text = text.lower()
            # Remove punctuation
            text = re.sub(r'[^\w\s]', ' ', text)
            # Extract words
            words = text.split()
            # Filter stopwords and short words
            words = [w for w in words if w not in self.STOPWORDS and len(w) > 2]
            return ' '.join(words)

        norm1 = normalize(title1)
        norm2 = normalize(title2)

        if not norm1 or not norm2:
            return 0.0

        # Use SequenceMatcher for fuzzy matching
        matcher = SequenceMatcher(None, norm1, norm2)
        return matcher.ratio()

    def _calculate_match_score(
        self,
        item: Dict[str, Any],
        title: Optional[str] = None,
        author: Optional[str] = None,
        year: Optional[str] = None
    ) -> float:
        """
        Calculate match score for a Crossref item.

        Weights:
        - Title similarity: 0.5 (fuzzy matching)
        - Year match: 0.2 (exact match or ±1 year)
        - Author match: 0.2 (family name in query)
        - Journal match: 0.1 (if journal info available)

        Args:
            item: Crossref API result item
            title: Query title
            author: Query author
            year: Query year

        Returns:
            Score between 0.0 and 1.0
        """
        score = 0.0

        # Title similarity (weight: 0.5)
        if title and 'title' in item and item['title']:
            item_title = item['title'][0]
            title_similarity = self._fuzzy_title_similarity(title, item_title)
            score += title_similarity * 0.5

        # Year match (weight: 0.2)
        if year:
            item_year = self._extract_year(item)
            if item_year:
                # Exact match
                if item_year == year:
                    score += 0.2
                # ±1 year tolerance
                elif abs(int(item_year) - int(year)) == 1:
                    score += 0.1

        # Author match (weight: 0.2)
        if author and 'author' in item and item['author']:
            author_lower = author.lower()
            for item_author in item['author']:
                if 'family' in item_author:
                    family_name = item_author['family'].lower()
                    if family_name in author_lower or author_lower in family_name:
                        score += 0.2
                        break

        # Journal match (weight: 0.1) - currently not used in search
        # This is kept for potential future use when journal info is available

        return min(score, 1.0)  # Cap at 1.0

    def _extract_year(self, item: Dict[str, Any]) -> Optional[str]:
        """Extract publication year from Crossref item."""
        # Try different date fields in order of preference
        for date_field in ['published-print', 'published-online', 'created']:
            if date_field in item and 'date-parts' in item[date_field]:
                date_parts = item[date_field]['date-parts']
                if date_parts and len(date_parts) > 0 and len(date_parts[0]) > 0:
                    return str(date_parts[0][0])
        return None

    def _extract_authors(self, item: Dict[str, Any]) -> List[str]:
        """Extract author names from Crossref item."""
        authors = []
        if 'author' in item:
            for author in item['author']:
                if 'given' in author and 'family' in author:
                    authors.append(f"{author['given']} {author['family']}")
                elif 'family' in author:
                    authors.append(author['family'])
        return authors

    def search(
        self,
        title: Optional[str] = None,
        author: Optional[str] = None,
        year: Optional[str] = None,
        max_results: int = 5
    ) -> List[CrossrefMatch]:
        """
        Search Crossref for matching publications.

        Args:
            title: Article title (most important)
            author: Author name or hint
            year: Publication year
            max_results: Maximum number of results to return

        Returns:
            List of CrossrefMatch objects sorted by score (highest first)

        Raises:
            CrossrefConnectionError: After all retries exhausted
            CrossrefAPIError: For non-retryable API errors
        """
        # Build query string
        query_parts = []

        if title:
            # Handle all-caps titles
            if title.isupper():
                title = title.title()
            query_parts.append(title)

        if author:
            # Extract last name if possible
            lastname_match = re.search(r'([A-Z][a-zA-Z\-]+),', author)
            if lastname_match:
                query_parts.append(lastname_match.group(1))
            else:
                # Try to extract last name from "First Last" format
                words = author.split()
                if len(words) > 1:
                    query_parts.append(words[-1])
                else:
                    query_parts.append(author)

        if year:
            query_parts.append(year)

        if not query_parts:
            return []

        # Limit query to most important parts
        query = " ".join(query_parts[:3])
        encoded_query = quote_plus(query)

        # Make API request
        url = f"https://api.crossref.org/works?query={encoded_query}&rows={max_results * 2}"

        try:
            data = self._make_request(url)
        except (CrossrefConnectionError, CrossrefAPIError):
            raise

        # Extract and score results
        matches = []
        if 'message' in data and 'items' in data['message']:
            items = data['message']['items']

            for item in items:
                # Must have DOI and title
                if 'DOI' not in item or 'title' not in item or not item['title']:
                    continue

                # Calculate match score
                score = self._calculate_match_score(item, title, author, year)

                # Create match object
                match = CrossrefMatch(
                    doi=item['DOI'],
                    title=item['title'][0],
                    authors=self._extract_authors(item),
                    year=self._extract_year(item),
                    journal=item.get('container-title', [None])[0],
                    score=score
                )

                matches.append(match)

        # Sort by score (highest first) and limit results
        matches.sort(key=lambda m: m.score, reverse=True)
        return matches[:max_results]

    def fetch_metadata(self, doi: str) -> dict:
        """
        Fetch complete metadata for a given DOI.

        Args:
            doi: The DOI to look up

        Returns:
            Dictionary with complete metadata

        Raises:
            CrossrefConnectionError: After all retries exhausted
            CrossrefAPIError: For non-retryable API errors (404, etc.)
        """
        # Clean DOI
        cleaned_doi = doi.strip()
        if cleaned_doi.startswith('http'):
            # Extract DOI from URL
            doi_match = re.search(r'(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)', cleaned_doi)
            if doi_match:
                cleaned_doi = doi_match.group(1)

        # Make API request
        url = f"https://api.crossref.org/works/{cleaned_doi}"

        try:
            data = self._make_request(url)
        except (CrossrefConnectionError, CrossrefAPIError):
            raise

        # Extract metadata
        if 'message' in data:
            item = data['message']
            metadata = {
                'doi': item.get('DOI'),
                'title': item.get('title', [None])[0],
                'authors': self._extract_authors(item),
                'year': self._extract_year(item),
                'journal': item.get('container-title', [None])[0],
                'publisher': item.get('publisher'),
                'type': item.get('type'),
            }

            # Add ISBN if available
            if 'ISBN' in item:
                metadata['isbn'] = item['ISBN'][0] if isinstance(item['ISBN'], list) else item['ISBN']

            return metadata

        return {}
