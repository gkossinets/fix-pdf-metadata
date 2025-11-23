"""
Tests for the filename parser module.

This test suite covers all supported filename formats, edge cases,
and ensures proper confidence scoring.
"""

import unittest
from pdf_metadata_manager.core.filename_parser import parse_filename, FilenameHints


class TestFilenameParser(unittest.TestCase):
    """Test cases for filename parsing functionality."""

    def test_zotero_format_basic(self):
        """Test standard Zotero format: 'Author - Year - Title'"""
        result = parse_filename("Smith - 2020 - Machine Learning.pdf")
        self.assertEqual(result.author, "Smith")
        self.assertEqual(result.year, "2020")
        self.assertEqual(result.title, "Machine Learning")
        self.assertGreaterEqual(result.confidence, 0.85)

    def test_zotero_format_long_title(self):
        """Test Zotero format with very long title"""
        result = parse_filename(
            "Jones - 2019 - A Comprehensive Study of Deep Learning Applications in Climate Science.pdf"
        )
        self.assertEqual(result.author, "Jones")
        self.assertEqual(result.year, "2019")
        self.assertEqual(
            result.title,
            "A Comprehensive Study of Deep Learning Applications in Climate Science"
        )
        self.assertGreaterEqual(result.confidence, 0.85)

    def test_zotero_format_multiple_authors(self):
        """Test Zotero format with multiple authors"""
        result = parse_filename("Smith & Jones - 2020 - Neural Networks.pdf")
        self.assertEqual(result.author, "Smith & Jones")
        self.assertEqual(result.year, "2020")
        self.assertEqual(result.title, "Neural Networks")
        self.assertGreaterEqual(result.confidence, 0.85)

    def test_zotero_format_et_al(self):
        """Test Zotero format with 'et al'"""
        result = parse_filename("Smith et al - 2018 - Climate Models.pdf")
        self.assertEqual(result.author, "Smith et al")
        self.assertEqual(result.year, "2018")
        self.assertEqual(result.title, "Climate Models")
        self.assertGreaterEqual(result.confidence, 0.85)

    def test_author_year_parentheses_with_title(self):
        """Test format: 'Author (Year) Title'"""
        result = parse_filename("Smith (2020) Machine Learning.pdf")
        self.assertEqual(result.author, "Smith")
        self.assertEqual(result.year, "2020")
        self.assertEqual(result.title, "Machine Learning")
        self.assertGreaterEqual(result.confidence, 0.8)

    def test_author_year_parentheses_no_title(self):
        """Test format: 'Author (Year)' without title"""
        result = parse_filename("Jones (2019).pdf")
        self.assertEqual(result.author, "Jones")
        self.assertEqual(result.year, "2019")
        self.assertIsNone(result.title)
        self.assertGreater(result.confidence, 0.5)

    def test_author_underscore_year(self):
        """Test format: 'author_year'"""
        result = parse_filename("jones_2019.pdf")
        self.assertEqual(result.author, "jones")
        self.assertEqual(result.year, "2019")
        self.assertIsNone(result.title)
        self.assertGreater(result.confidence, 0.5)

    def test_author_underscore_year_title(self):
        """Test format: 'author_year_title'"""
        result = parse_filename("smith_2020_MachineLearning.pdf")
        self.assertEqual(result.author, "smith")
        self.assertEqual(result.year, "2020")
        self.assertEqual(result.title, "MachineLearning")
        self.assertGreaterEqual(result.confidence, 0.7)

    def test_author_year_concatenated(self):
        """Test format: 'authorYEAR'"""
        result = parse_filename("smith2020.pdf")
        self.assertEqual(result.author, "smith")
        self.assertEqual(result.year, "2020")
        self.assertIsNone(result.title)
        self.assertGreater(result.confidence, 0.5)

    def test_author_space_year(self):
        """Test format: 'author year'"""
        result = parse_filename("Smith 2020.pdf")
        self.assertEqual(result.author, "Smith")
        self.assertEqual(result.year, "2020")
        self.assertIsNone(result.title)
        self.assertGreater(result.confidence, 0.5)

    def test_author_space_year_title(self):
        """Test format: 'Author Year Title' with spaces"""
        result = parse_filename("Smith 2020 Machine Learning.pdf")
        self.assertEqual(result.author, "Smith")
        self.assertEqual(result.year, "2020")
        self.assertEqual(result.title, "Machine Learning")
        self.assertGreaterEqual(result.confidence, 0.7)

    def test_year_underscore_author(self):
        """Test reversed format: 'year_author'"""
        result = parse_filename("2020_Smith.pdf")
        self.assertEqual(result.author, "Smith")
        self.assertEqual(result.year, "2020")
        self.assertIsNone(result.title)
        self.assertGreater(result.confidence, 0.5)

    def test_special_characters_apostrophe(self):
        """Test handling of special characters like apostrophes"""
        result = parse_filename("O'Brien - 2020 - Neural Networks.pdf")
        # Apostrophes in names might not match letter-only patterns
        # Should still extract year at minimum
        self.assertIsNotNone(result.year)

    def test_special_characters_ampersand(self):
        """Test handling of ampersand in multiple authors"""
        result = parse_filename("Smith & Jones - 2021 - Deep Learning.pdf")
        self.assertEqual(result.author, "Smith & Jones")
        self.assertEqual(result.year, "2021")
        self.assertEqual(result.title, "Deep Learning")

    def test_unicode_characters(self):
        """Test handling of Unicode characters in names"""
        result = parse_filename("Müller - 2020 - Machine Learning.pdf")
        # Pattern might not match non-ASCII, should still get year
        self.assertIsNotNone(result.year)

    def test_no_extension(self):
        """Test parsing filename without .pdf extension"""
        result = parse_filename("Smith - 2020 - Machine Learning")
        self.assertEqual(result.author, "Smith")
        self.assertEqual(result.year, "2020")
        self.assertEqual(result.title, "Machine Learning")

    def test_uppercase_extension(self):
        """Test parsing with uppercase .PDF extension"""
        result = parse_filename("Smith - 2020 - Machine Learning.PDF")
        self.assertEqual(result.author, "Smith")
        self.assertEqual(result.year, "2020")
        self.assertEqual(result.title, "Machine Learning")

    def test_unparseable_filename(self):
        """Test completely random/unparseable filename"""
        result = parse_filename("random_file.pdf")
        self.assertIsNone(result.author)
        self.assertIsNone(result.title)
        # Might extract year if digits happen to look like year
        self.assertEqual(result.confidence, 0.0)

    def test_unparseable_no_year(self):
        """Test filename with no year information"""
        result = parse_filename("document.pdf")
        self.assertIsNone(result.author)
        self.assertIsNone(result.year)
        self.assertIsNone(result.title)
        self.assertEqual(result.confidence, 0.0)

    def test_invalid_year_too_old(self):
        """Test that very old years are rejected"""
        result = parse_filename("Smith - 1799 - Old Paper.pdf")
        # Should not match due to year validation
        self.assertNotEqual(result.year, "1799")

    def test_invalid_year_future(self):
        """Test that far future years are rejected"""
        result = parse_filename("Smith - 2101 - Future Paper.pdf")
        # Should not match due to year validation
        self.assertNotEqual(result.year, "2101")

    def test_valid_year_range(self):
        """Test valid year range"""
        # Test lower bound
        result = parse_filename("Smith - 1800 - Historical Paper.pdf")
        self.assertEqual(result.year, "1800")

        # Test upper bound
        result = parse_filename("Smith - 2100 - Future Paper.pdf")
        self.assertEqual(result.year, "2100")

        # Test modern year
        result = parse_filename("Smith - 2023 - Recent Paper.pdf")
        self.assertEqual(result.year, "2023")

    def test_year_only_in_filename(self):
        """Test filename with only year extractable"""
        result = parse_filename("some_random_2020_document.pdf")
        self.assertIsNone(result.author)
        self.assertIsNone(result.title)
        self.assertEqual(result.year, "2020")
        self.assertLess(result.confidence, 0.5)  # Low confidence

    def test_multiple_years_first_match(self):
        """Test that first valid year pattern is matched"""
        result = parse_filename("Smith - 2020 - Study from 2019.pdf")
        # Should match the Zotero pattern and extract 2020
        self.assertEqual(result.year, "2020")

    def test_confidence_scoring_zotero(self):
        """Test that Zotero format has highest confidence"""
        result = parse_filename("Smith - 2020 - Title.pdf")
        self.assertGreaterEqual(result.confidence, 0.85)

    def test_confidence_scoring_simple(self):
        """Test that simple formats have lower confidence"""
        result = parse_filename("smith2020.pdf")
        self.assertLess(result.confidence, 0.7)

    def test_confidence_scoring_year_only(self):
        """Test that year-only extraction has lowest confidence"""
        result = parse_filename("file123_copy_2020.pdf")
        self.assertLess(result.confidence, 0.5)

    def test_empty_title_handling(self):
        """Test handling of patterns that expect title but get empty string"""
        result = parse_filename("Smith - 2020 - .pdf")
        self.assertEqual(result.author, "Smith")
        self.assertEqual(result.year, "2020")
        self.assertIsNone(result.title)

    def test_whitespace_variations(self):
        """Test handling of various whitespace patterns"""
        # Extra spaces
        result = parse_filename("Smith  -  2020  -  Title.pdf")
        self.assertEqual(result.author, "Smith")
        self.assertEqual(result.year, "2020")
        self.assertEqual(result.title, "Title")

    def test_multiple_authors_and_keyword(self):
        """Test 'and' keyword for multiple authors"""
        result = parse_filename("Smith and Jones (2020) Title.pdf")
        self.assertIn("and", result.author.lower())
        self.assertEqual(result.year, "2020")

    def test_dataclass_defaults(self):
        """Test FilenameHints dataclass defaults"""
        hints = FilenameHints()
        self.assertIsNone(hints.author)
        self.assertIsNone(hints.year)
        self.assertIsNone(hints.title)
        self.assertEqual(hints.confidence, 0.0)

    def test_dataclass_partial_data(self):
        """Test FilenameHints with partial data"""
        hints = FilenameHints(author="Smith", year="2020", confidence=0.8)
        self.assertEqual(hints.author, "Smith")
        self.assertEqual(hints.year, "2020")
        self.assertIsNone(hints.title)
        self.assertEqual(hints.confidence, 0.8)


if __name__ == '__main__':
    unittest.main()
