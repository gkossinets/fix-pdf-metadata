"""
Tests for CrossrefClient module.

Tests cover:
- Successful searches with mock responses
- Retry logic with simulated failures
- Timeout handling
- Scoring algorithm with known good/bad matches
- Rate limiting
- Metadata fetching
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import time
import requests

from pdf_metadata_manager.core.crossref_client import (
    CrossrefClient,
    CrossrefMatch,
    CrossrefConnectionError,
    CrossrefAPIError
)


class TestCrossrefMatch(unittest.TestCase):
    """Test CrossrefMatch dataclass."""

    def test_confidence_level_high(self):
        """Test HIGH confidence level."""
        match = CrossrefMatch(
            doi="10.1234/test",
            title="Test Title",
            authors=["Test Author"],
            year="2020",
            journal="Test Journal",
            score=0.85
        )
        self.assertEqual(match.confidence_level, "HIGH")

    def test_confidence_level_medium(self):
        """Test MEDIUM confidence level."""
        match = CrossrefMatch(
            doi="10.1234/test",
            title="Test Title",
            authors=["Test Author"],
            year="2020",
            journal="Test Journal",
            score=0.70
        )
        self.assertEqual(match.confidence_level, "MEDIUM")

    def test_confidence_level_low(self):
        """Test LOW confidence level."""
        match = CrossrefMatch(
            doi="10.1234/test",
            title="Test Title",
            authors=["Test Author"],
            year="2020",
            journal="Test Journal",
            score=0.50
        )
        self.assertEqual(match.confidence_level, "LOW")


class TestCrossrefClient(unittest.TestCase):
    """Test CrossrefClient functionality."""

    def setUp(self):
        """Set up test client."""
        self.client = CrossrefClient(
            email="test@example.com",
            retries=3,
            timeout=30,
            backoff_factor=0.1  # Shorter for tests
        )

    def test_initialization(self):
        """Test client initialization."""
        self.assertEqual(self.client.email, "test@example.com")
        self.assertEqual(self.client.retries, 3)
        self.assertEqual(self.client.timeout, 30)
        self.assertEqual(self.client.backoff_factor, 0.1)
        self.assertIn("test@example.com", self.client.headers['User-Agent'])

    def test_fuzzy_title_similarity_exact_match(self):
        """Test fuzzy title matching with exact match."""
        title1 = "Machine Learning Applications in Climate Science"
        title2 = "Machine Learning Applications in Climate Science"
        similarity = self.client._fuzzy_title_similarity(title1, title2)
        self.assertGreater(similarity, 0.95)

    def test_fuzzy_title_similarity_case_insensitive(self):
        """Test fuzzy title matching is case insensitive."""
        title1 = "Machine Learning Applications"
        title2 = "machine learning applications"
        similarity = self.client._fuzzy_title_similarity(title1, title2)
        self.assertGreater(similarity, 0.95)

    def test_fuzzy_title_similarity_with_punctuation(self):
        """Test fuzzy title matching ignores punctuation."""
        title1 = "Machine Learning: Applications"
        title2 = "Machine Learning Applications"
        similarity = self.client._fuzzy_title_similarity(title1, title2)
        self.assertGreater(similarity, 0.90)

    def test_fuzzy_title_similarity_different_titles(self):
        """Test fuzzy title matching with different titles."""
        title1 = "Machine Learning in Climate"
        title2 = "Deep Learning for Weather Prediction"
        similarity = self.client._fuzzy_title_similarity(title1, title2)
        # "learning" appears in both, so some similarity expected
        self.assertLess(similarity, 0.60)

    def test_extract_year(self):
        """Test year extraction from Crossref item."""
        item = {
            'published-print': {
                'date-parts': [[2020, 5, 15]]
            }
        }
        year = self.client._extract_year(item)
        self.assertEqual(year, "2020")

    def test_extract_year_fallback(self):
        """Test year extraction falls back to other date fields."""
        item = {
            'published-online': {
                'date-parts': [[2019, 12, 1]]
            }
        }
        year = self.client._extract_year(item)
        self.assertEqual(year, "2019")

    def test_extract_year_none(self):
        """Test year extraction returns None when no date available."""
        item = {}
        year = self.client._extract_year(item)
        self.assertIsNone(year)

    def test_extract_authors(self):
        """Test author extraction from Crossref item."""
        item = {
            'author': [
                {'given': 'John', 'family': 'Smith'},
                {'given': 'Jane', 'family': 'Doe'},
                {'family': 'OnlyLastName'}
            ]
        }
        authors = self.client._extract_authors(item)
        self.assertEqual(len(authors), 3)
        self.assertEqual(authors[0], "John Smith")
        self.assertEqual(authors[1], "Jane Doe")
        self.assertEqual(authors[2], "OnlyLastName")

    def test_calculate_match_score_perfect_match(self):
        """Test scoring with perfect match."""
        item = {
            'title': ['Machine Learning Applications in Climate Science'],
            'author': [
                {'given': 'John', 'family': 'Smith'}
            ],
            'published-print': {
                'date-parts': [[2020, 5, 15]]
            }
        }
        score = self.client._calculate_match_score(
            item,
            title="Machine Learning Applications in Climate Science",
            author="Smith",
            year="2020"
        )
        # Should be very high (title + year + author match)
        self.assertGreater(score, 0.85)

    def test_calculate_match_score_partial_match(self):
        """Test scoring with partial match."""
        item = {
            'title': ['Machine Learning in Science'],
            'author': [
                {'given': 'Jane', 'family': 'Doe'}
            ],
            'published-print': {
                'date-parts': [[2020, 5, 15]]
            }
        }
        score = self.client._calculate_match_score(
            item,
            title="Machine Learning Applications in Climate Science",
            author="Smith",
            year="2020"
        )
        # Should have some score (year + partial title, no author)
        self.assertGreater(score, 0.20)
        self.assertLess(score, 0.60)

    def test_calculate_match_score_year_tolerance(self):
        """Test scoring with ±1 year tolerance."""
        item = {
            'title': ['Test Title'],
            'published-print': {
                'date-parts': [[2020, 5, 15]]
            }
        }
        # Exact year match
        score_exact = self.client._calculate_match_score(
            item,
            title="Test Title",
            year="2020"
        )
        # ±1 year match
        score_close = self.client._calculate_match_score(
            item,
            title="Test Title",
            year="2019"
        )
        # Exact should be higher than close
        self.assertGreater(score_exact, score_close)
        # Both should give some year credit
        self.assertGreater(score_close, 0.0)

    @patch('pdf_metadata_manager.core.crossref_client.requests.request')
    def test_search_success(self, mock_request):
        """Test successful search."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'message': {
                'items': [
                    {
                        'DOI': '10.1234/test1',
                        'title': ['Machine Learning Applications'],
                        'author': [
                            {'given': 'John', 'family': 'Smith'}
                        ],
                        'published-print': {
                            'date-parts': [[2020, 5, 15]]
                        },
                        'container-title': ['Nature']
                    },
                    {
                        'DOI': '10.1234/test2',
                        'title': ['Deep Learning Methods'],
                        'author': [
                            {'given': 'Jane', 'family': 'Doe'}
                        ],
                        'published-print': {
                            'date-parts': [[2019, 3, 10]]
                        },
                        'container-title': ['Science']
                    }
                ]
            }
        }
        mock_request.return_value = mock_response

        # Perform search
        results = self.client.search(
            title="Machine Learning Applications",
            author="Smith",
            year="2020",
            max_results=5
        )

        # Verify results
        self.assertGreater(len(results), 0)
        self.assertIsInstance(results[0], CrossrefMatch)
        # Results should be sorted by score
        for i in range(len(results) - 1):
            self.assertGreaterEqual(results[i].score, results[i + 1].score)

    @patch('pdf_metadata_manager.core.crossref_client.requests.request')
    def test_search_no_results(self, mock_request):
        """Test search with no results."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'message': {
                'items': []
            }
        }
        mock_request.return_value = mock_response

        results = self.client.search(title="Nonexistent Paper")
        self.assertEqual(len(results), 0)

    @patch('pdf_metadata_manager.core.crossref_client.requests.request')
    def test_search_empty_query(self, mock_request):
        """Test search with empty query."""
        results = self.client.search()
        self.assertEqual(len(results), 0)
        # Should not make any API calls
        mock_request.assert_not_called()

    @patch('pdf_metadata_manager.core.crossref_client.requests.request')
    @patch('pdf_metadata_manager.core.crossref_client.time.sleep')
    def test_retry_on_connection_error(self, mock_sleep, mock_request):
        """Test retry logic on connection errors."""
        # First two attempts fail, third succeeds
        mock_request.side_effect = [
            requests.exceptions.ConnectionError("Connection failed"),
            requests.exceptions.ConnectionError("Connection failed"),
            Mock(status_code=200, json=lambda: {'message': {'items': []}})
        ]

        # Should succeed after retries
        results = self.client.search(title="Test")

        # Verify retries happened
        self.assertEqual(mock_request.call_count, 3)
        # Verify exponential backoff (includes rate limiting sleeps)
        self.assertGreaterEqual(mock_sleep.call_count, 2)

    @patch('pdf_metadata_manager.core.crossref_client.requests.request')
    @patch('pdf_metadata_manager.core.crossref_client.time.sleep')
    def test_retry_exhausted(self, mock_sleep, mock_request):
        """Test exception raised when all retries exhausted."""
        # All attempts fail
        mock_request.side_effect = requests.exceptions.ConnectionError("Connection failed")

        # Should raise CrossrefConnectionError
        with self.assertRaises(CrossrefConnectionError):
            self.client.search(title="Test")

        # Should have tried the configured number of times
        self.assertEqual(mock_request.call_count, self.client.retries)

    @patch('pdf_metadata_manager.core.crossref_client.requests.request')
    def test_no_retry_on_client_error(self, mock_request):
        """Test no retry on 4xx client errors."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_request.return_value = mock_response

        # Should raise CrossrefAPIError without retries
        with self.assertRaises(CrossrefAPIError):
            self.client.search(title="Test")

        # Should only try once (no retries on client errors)
        self.assertEqual(mock_request.call_count, 1)

    @patch('pdf_metadata_manager.core.crossref_client.requests.request')
    @patch('pdf_metadata_manager.core.crossref_client.time.sleep')
    def test_retry_on_server_error(self, mock_sleep, mock_request):
        """Test retry on 5xx server errors."""
        # First attempt returns 500, second succeeds
        mock_request.side_effect = [
            Mock(status_code=500, text="Server Error"),
            Mock(status_code=200, json=lambda: {'message': {'items': []}})
        ]

        # Should succeed after retry
        results = self.client.search(title="Test")

        # Verify retry happened
        self.assertEqual(mock_request.call_count, 2)

    @patch('pdf_metadata_manager.core.crossref_client.time.time')
    @patch('pdf_metadata_manager.core.crossref_client.time.sleep')
    @patch('pdf_metadata_manager.core.crossref_client.requests.request')
    def test_rate_limiting(self, mock_request, mock_sleep, mock_time):
        """Test rate limiting between requests."""
        # Mock time progression
        times = [0, 0.3, 0.6]  # Simulate requests coming faster than rate limit
        mock_time.side_effect = times + [1.0, 1.5, 2.0]

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'message': {'items': []}}
        mock_request.return_value = mock_response

        # Make two searches
        self.client.search(title="Test 1")
        self.client.search(title="Test 2")

        # Should have enforced rate limiting
        # First request: no sleep
        # Second request: should sleep because < 0.5s elapsed
        self.assertGreater(mock_sleep.call_count, 0)

    @patch('pdf_metadata_manager.core.crossref_client.requests.request')
    def test_fetch_metadata_success(self, mock_request):
        """Test fetching metadata by DOI."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'message': {
                'DOI': '10.1234/test',
                'title': ['Test Article'],
                'author': [
                    {'given': 'John', 'family': 'Smith'}
                ],
                'published-print': {
                    'date-parts': [[2020, 5, 15]]
                },
                'container-title': ['Nature'],
                'publisher': 'Nature Publishing Group',
                'type': 'journal-article'
            }
        }
        mock_request.return_value = mock_response

        metadata = self.client.fetch_metadata('10.1234/test')

        self.assertEqual(metadata['doi'], '10.1234/test')
        self.assertEqual(metadata['title'], 'Test Article')
        self.assertEqual(len(metadata['authors']), 1)
        self.assertEqual(metadata['year'], '2020')
        self.assertEqual(metadata['journal'], 'Nature')

    @patch('pdf_metadata_manager.core.crossref_client.requests.request')
    def test_fetch_metadata_clean_doi(self, mock_request):
        """Test fetching metadata cleans DOI from URL."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'message': {
                'DOI': '10.1234/test',
                'title': ['Test Article'],
                'author': []
            }
        }
        mock_request.return_value = mock_response

        # Pass DOI as URL
        metadata = self.client.fetch_metadata('https://doi.org/10.1234/test')

        # Should have extracted DOI from URL
        self.assertIn('10.1234/test', mock_request.call_args[0][1])

    @patch('pdf_metadata_manager.core.crossref_client.requests.request')
    def test_fetch_metadata_not_found(self, mock_request):
        """Test fetching metadata for non-existent DOI."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_request.return_value = mock_response

        with self.assertRaises(CrossrefAPIError):
            self.client.fetch_metadata('10.9999/nonexistent')


class TestCrossrefClientIntegration(unittest.TestCase):
    """
    Integration tests with real Crossref API.

    These tests are optional and can be slow. They make real API calls.
    Uncomment the @unittest.skip decorator to run them.
    """

    @unittest.skip("Integration test - makes real API calls")
    def test_real_search(self):
        """Test real search with Crossref API."""
        client = CrossrefClient(email="test@example.com")

        # Search for a well-known paper
        results = client.search(
            title="Deep Learning",
            author="LeCun",
            year="2015",
            max_results=5
        )

        # Should find results
        self.assertGreater(len(results), 0)
        # Top result should have reasonable score
        self.assertGreater(results[0].score, 0.5)

    @unittest.skip("Integration test - makes real API calls")
    def test_real_fetch_metadata(self):
        """Test real metadata fetch with Crossref API."""
        client = CrossrefClient(email="test@example.com")

        # Fetch metadata for a known DOI
        metadata = client.fetch_metadata('10.1038/nature14539')

        # Should have complete metadata
        self.assertIsNotNone(metadata['title'])
        self.assertGreater(len(metadata['authors']), 0)
        self.assertIsNotNone(metadata['year'])


if __name__ == '__main__':
    unittest.main()
