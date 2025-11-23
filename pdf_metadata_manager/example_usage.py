#!/usr/bin/env python3
"""
Example usage of the PDF Processor module.

This script demonstrates how to use the PDFProcessor to extract metadata from PDF files.
"""

import sys
from core.pdf_processor import PDFProcessor, PDFNotFoundError, PDFProcessingError


def main():
    """Main function to demonstrate PDF processing."""
    if len(sys.argv) < 2:
        print("Usage: python example_usage.py <pdf_file>")
        print("\nExample:")
        print("  python example_usage.py ../set-pdf-metadata.py")
        sys.exit(1)

    pdf_path = sys.argv[1]

    # Create a PDF processor with OCR enabled and verbose output
    processor = PDFProcessor(use_ocr=True, ocr_pages=2, verbose=True)

    try:
        # Extract metadata from the PDF
        print(f"\n{'='*60}")
        print(f"Processing PDF: {pdf_path}")
        print(f"{'='*60}\n")

        metadata = processor.extract_metadata(pdf_path)

        # Display the results
        print(f"\n{'='*60}")
        print("EXTRACTED METADATA")
        print(f"{'='*60}")
        print(f"Title:    {metadata.title or 'Not found'}")
        print(f"Authors:  {metadata.authors or 'Not found'}")
        print(f"Journal:  {metadata.journal or 'Not found'}")
        print(f"Year:     {metadata.year or 'Not found'}")
        print(f"DOI:      {metadata.doi or 'Not found'}")
        print(f"Used OCR: {metadata.used_ocr}")
        print(f"Text length: {len(metadata.extracted_text)} characters")
        print(f"{'='*60}\n")

        # Show first 500 characters of extracted text
        if metadata.extracted_text:
            print("First 500 characters of extracted text:")
            print("-" * 60)
            print(metadata.extracted_text[:500])
            print("-" * 60)

    except PDFNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except PDFProcessingError as e:
        print(f"Processing error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
