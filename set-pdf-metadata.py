#!/usr/bin/env python3
"""
PDF Metadata Updater with OCR

This script extracts the title and DOI from a PDF file using OCR if necessary,
searches for its DOI using Crossref, and updates the PDF's metadata.

Requirements:
    pip install PyPDF2 pikepdf requests pytesseract pdf2image
    
Optional dependencies for better functionality:
    pip install pathvalidate
    
You also need to install:
    - Tesseract OCR engine: https://github.com/tesseract-ocr/tesseract
    - Poppler (for pdf2image): https://github.com/oschwartz10612/poppler-windows/releases (Windows) 
      or via package manager on Linux/Mac
"""

import os
import re
import argparse
import time
import tempfile
import shutil
import platform
import subprocess
from PyPDF2 import PdfReader
import pikepdf
import requests
from urllib.parse import quote_plus

# Try to import pathvalidate for better filename sanitization
try:
    from pathvalidate import sanitize_filename
    PATHVALIDATE_AVAILABLE = True
except ImportError:
    PATHVALIDATE_AVAILABLE = False

# Import OCR-related libraries
try:
    import pytesseract
    from pdf2image import convert_from_path
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    print("Warning: OCR libraries not found. Install pytesseract and pdf2image for OCR support.")

def set_creation_date_macos(file_path, creation_time):
    """Set file creation date on macOS using SetFile command."""
    try:
        # Convert Unix timestamp to format required by SetFile: MM/DD/YYYY HH:MM:SS
        date_str = time.strftime("%m/%d/%Y %H:%M:%S", time.localtime(creation_time))
        subprocess.run(["SetFile", "-d", date_str, file_path], check=True)
        return True
    except Exception as e:
        print(f"  Warning: Could not set creation date with SetFile: {e}")
        return False
        
def preserve_timestamps(file_path, source_path, ctime=None, mtime=None, atime=None):
    """Preserve file timestamps from source to destination file."""
    try:
        # If specific timestamps are not provided, get them from source
        if ctime is None or mtime is None or atime is None:
            stat_info = os.stat(source_path)
            ctime = ctime or stat_info.st_ctime
            mtime = mtime or stat_info.st_mtime
            atime = atime or stat_info.st_atime
        
        # Update modification and access time
        os.utime(file_path, (atime, mtime))
        
        # For macOS, try to preserve creation time using platform-specific methods
        if platform.system() == 'Darwin':  # macOS
            set_creation_date_macos(file_path, ctime)
            
        return True
    except Exception as e:
        print(f"  Warning: Could not preserve all timestamps: {e}")
        return False
        
def extract_text_with_ocr(pdf_path, pages=1):
    """Extract text from PDF using OCR for the first few pages."""
    try:
        # Create a temporary directory for the image files
        with tempfile.TemporaryDirectory() as temp_dir:
            # Convert PDF pages to images
            images = convert_from_path(
                pdf_path, 
                first_page=1, 
                last_page=pages,
                dpi=300,
                output_folder=temp_dir
            )
            
            # Extract text from each image using OCR
            text = ""
            for i, image in enumerate(images):
                page_text = pytesseract.image_to_string(image)
                text += f"\n--- Page {i+1} ---\n{page_text}"
                
            return text
    except Exception as e:
        print(f"  OCR Error: {e}")
        return ""

def sanitize_doi(doi):
    """Sanitize DOI by removing trailing periods etc."""
    doi = doi.strip()
    # Remove trailing non-alphanumeric characters (must end in a number or letter)
    doi = re.sub(r'[^a-zA-Z0-9]+$', '', doi)
    return doi

def extract_info_from_pdf(pdf_path):
    """Extract title and DOI from PDF, using OCR as a fallback if necessary."""
    # First try normal text extraction
    try:
        reader = PdfReader(pdf_path)
        if len(reader.pages) == 0:
            return None, None
        
        # Try normal text extraction first
        text = reader.pages[0].extract_text()
        
        # If no text was extracted or text is too short, try OCR
        if not text or len(text.strip()) < 100:
            if OCR_AVAILABLE:
                print("  PDF has little or no extractable text. Using OCR...")
                text = extract_text_with_ocr(pdf_path, pages=2)
            else:
                print("  PDF has little or no extractable text and OCR is not available.")
                return None, None
        
        # Print the first 500 characters of text for debugging
        print(f"  First 500 chars of extracted text: {text[:500].replace(chr(10), ' ')}")
        
        # Improved DOI pattern matching to allow non-terminating period in the DOI
        # Pattern for DOI with or without https prefix
        doi_patterns = [
            r'(?:doi|DOI):?\s*(10\.\d{4,9}/[^\s"\'<>]+)',  # Standard DOI format with DOI prefix
            r'https?://doi\.org/(10\.\d{4,9}/[^\s"\'<>]+)',  # DOI with https://doi.org/ prefix
            r'https?://(doi\.org/10\.\d{4,9}/[^\s"\'<>]+)', # Alternative DOI URL format
            r'(?:^|\s|[^\w.])(10\.\d{4,9}/[^\s"\'<>]+)(?:$|\s|[^\w.])',  # Bare DOI format
            r'doi\.org/(10\.\d{4,9}/[^\s"\'<>]+)'  # doi.org/ without http/https
        ]
        
        # Try each DOI pattern
        for pattern in doi_patterns:
            doi_match = re.search(pattern, text)
            if doi_match:
                # Extract the DOI, ensure we're getting just the "10.xxxx/yyyy" part
                doi = doi_match.group(1)
                # If the DOI contains "doi.org/" prefix, remove it
                if "doi.org/" in doi:
                    doi = re.sub(r'doi\.org/', '', doi)
                doi = sanitize_doi(doi)
                print(f"  Found DOI directly in PDF: {doi}")
                return None, doi
        
        # If we didn't find a DOI with normal text extraction, try OCR if we haven't already
        if OCR_AVAILABLE and not text.strip().startswith("--- Page"):  # Check if we already used OCR
            print("  No DOI found in extracted text. Trying OCR as a fallback...")
            ocr_text = extract_text_with_ocr(pdf_path, pages=2)
            
            # Try each DOI pattern on the OCR text
            for pattern in doi_patterns:
                doi_match = re.search(pattern, ocr_text)
                if doi_match:
                    # Extract the DOI, ensure we're getting just the "10.xxxx/yyyy" part
                    doi = doi_match.group(1)
                    # If the DOI contains "doi.org/" prefix, remove it
                    if "doi.org/" in doi:
                        doi = re.sub(r'doi\.org/', '', doi)
                    doi = sanitize_doi(doi) 
                    print(f"  Found DOI in OCR text: {doi}")
                    return None, doi
        
        # Extract file name without extension - might be useful for fallback
        base_filename = os.path.basename(pdf_path)
        filename_without_ext = os.path.splitext(base_filename)[0]
        
        # Split into lines and filter out short lines
        lines = [line.strip() for line in text.split('\n') if len(line.strip()) > 3]  # Lower threshold to catch more lines
        
        # Print all lines for debugging
        print("  All lines extracted:")
        for i, line in enumerate(lines[:20]):  # Print first 20 lines
            print(f"  Line {i}: {line[:100]}")
        
        # Filter out common headers, footers, and copyright notices
        blacklist_patterns = [
            r'downloaded from',
            r'all rights reserved',
            r'copyright',
            r'reproduced with permission',
            r'used with permission',
            r'©',
            r'page \d+ of \d+',
            r'\d+\s*?\|\s*?page',
            r'http',
            r'www\.',
            r'@',
            r'volume \d+',
            r'issue \d+',
            r'doi:',
            r'isbn',
            r'issn',
            r'\d{4} by',
            r'Elsevier|Springer|Wiley|SAGE|IEEE|Oxford University Press|Cambridge University Press'
        ]
        
        filtered_lines = []
        for line in lines:
            # Skip lines that match blacklist patterns
            if any(re.search(pattern, line, re.IGNORECASE) for pattern in blacklist_patterns):
                continue
            filtered_lines.append(line)
        
        # Look for academic journal article patterns
        # In many journal PDFs, the title is in ALL CAPS or has more capital letters than usual
        title_candidates = []
        
        # Look for lines with typical title characteristics:
        # 1. Title case or all caps
        # 2. Appropriate length (not too short, not too long)
        # 3. No numerical prefix
        # 4. Often appears in the first third of the document
        for line in filtered_lines[:min(30, len(filtered_lines))]:  # Check more lines for academic articles
            # Skip very short lines and lines starting with numbers
            if len(line) < 10 or re.match(r'^\d', line):
                continue
                
            # Check for lines that might be titles (uppercase or title case)
            if line.isupper() or sum(1 for c in line if c.isupper()) >= 2:
                if len(line) < 200:  # Title shouldn't be too long
                    title_candidates.append((line, filtered_lines.index(line)))
        
        # Sort candidates by position (earlier in document more likely to be title)
        title_candidates.sort(key=lambda x: x[1])
        
        # Get journal information if available
        journal_info = None
        for line in lines:
            journal_match = re.search(r'(Journal of|Proceedings of|Transactions of|Review of).*', line, re.IGNORECASE)
            if journal_match:
                journal_info = journal_match.group(0)
                break
        
        # Look for volume/issue/date info
        pub_info = None
        for line in lines:
            vol_match = re.search(r'Vol\w*\.?\s*\d+.*', line, re.IGNORECASE)
            if vol_match:
                pub_info = vol_match.group(0)
                break
        
        # Select the best title candidate
        title = None
        author = None
        
        if title_candidates:
            # Prefer all-caps or mostly-caps titles, which are common in academic papers
            all_caps_candidates = [t for t, idx in title_candidates if t.isupper()]
            if all_caps_candidates:
                title = all_caps_candidates[0]
            else:
                # Otherwise take the first candidate
                title = title_candidates[0][0]
            
            # Look for author information after the title
            title_idx = -1
            for i, line in enumerate(lines):
                if title in line:
                    title_idx = i
                    break
            
            if title_idx >= 0:
                # Look at the next few lines for author information
                for i in range(title_idx + 1, min(title_idx + 10, len(lines))):
                    # Author lines often contain names (capitalized words)
                    name_pattern = r'([A-Z][a-z]+ [A-Z][a-z]+)'
                    if re.search(name_pattern, lines[i]) and not lines[i].isupper():
                        # Check it's not a blacklisted line
                        if not any(re.search(pattern, lines[i], re.IGNORECASE) for pattern in blacklist_patterns):
                            author = lines[i]
                            break
        
        # If we still don't have a title, use filename as fallback
        if not title:
            print("  Could not extract a reliable title, using filename as fallback")
            # Try to clean up the filename (remove underscores, hyphens, etc.)
            cleaned_filename = re.sub(r'[_\-]', ' ', filename_without_ext)
            # If filename has author_year pattern, extract just the author part
            if '_' in filename_without_ext:
                author_part = filename_without_ext.split('_')[0]
                author = author_part.replace('_', ' ').strip()
            title = cleaned_filename
        
        # Collect information for Crossref search
        result = {'title': title}
        if author:
            result['author'] = author
        if journal_info:
            result['journal'] = journal_info
        if pub_info:
            result['publication_info'] = pub_info
            
        print(f"  Extracted title: {title}")
        if author:
            print(f"  Extracted author: {author}")
        if journal_info:
            print(f"  Extracted journal: {journal_info}")
            
        return result, None
        
    except Exception as e:
        print(f"  Error extracting info from PDF: {e}")
        return None, None

def search_doi_from_crossref(query_data, pdf_path=None):
    """Search for a DOI using the Crossref API based on title and optionally author/journal."""
    try:
        # Print the data we're searching with
        print("  Searching Crossref with:")
        for key, value in query_data.items():
            print(f"    {key}: {value}")
        
        # Prepare the query
        query_parts = []
        
        # Add title to query (most important)
        if 'title' in query_data and query_data['title']:
            # For all-caps titles, convert to title case for better matching
            title = query_data['title']
            if title.isupper():
                title = title.title()
            query_parts.append(title)
        
        # Add author if available
        if 'author' in query_data and query_data['author']:
            # Extract last names from author string using common patterns
            # For academic papers, authors often appear as "Lastname, Firstname" or "Firstname Lastname"
            author_text = query_data['author']
            
            # Look for a pattern like "Lastname, Firstname"
            lastname_match = re.search(r'([A-Z][a-zA-Z\-]+),', author_text)
            if lastname_match:
                query_parts.append(lastname_match.group(1))
            else:
                # Try to extract a name in the format "Firstname Lastname"
                name_match = re.search(r'([A-Z][a-z]+ [A-Z][a-z]+)', author_text)
                if name_match:
                    # Add the last name (second word)
                    name_parts = name_match.group(1).split()
                    if len(name_parts) > 1:
                        query_parts.append(name_parts[-1])  # Last name is usually last
        
        # Add journal info if available - helps narrow search
        if 'journal' in query_data:
            # Extract just the journal name without "Journal of" for brevity
            journal = query_data['journal']
            journal_match = re.search(r'Journal of ([A-Za-z ]+)', journal)
            if journal_match:
                query_parts.append(journal_match.group(1))
            else:
                # Add a shorter version of the journal name
                words = journal.split()
                if len(words) > 3:
                    query_parts.append(' '.join(words[:3]))
                else:
                    query_parts.append(journal)
        
        if not query_parts:
            print("  No usable search terms found")
            return None
            
        # Build the query with the most important parts
        query = " ".join(query_parts[:3])  # Limit to first 3 parts to avoid over-constraining
        print(f"  Query string: {query}")
        encoded_query = quote_plus(query)
        
        url = f"https://api.crossref.org/works?query={encoded_query}&rows=10"  # Increase rows for better matches
        headers = {
            'User-Agent': 'PdfMetadataUpdater/1.0 (mailto:your-email@example.com)'
        }
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            print(f"  Crossref API error: {response.status_code}")
            return None
            
        data = response.json()
        
        if 'message' in data and 'items' in data['message'] and data['message']['items']:
            # Get the top results
            items = data['message']['items']
            
            # Debug: print top 3 results
            print(f"  Found {len(items)} results from Crossref")
            for i, item in enumerate(items[:3]):
                if 'title' in item and item['title']:
                    print(f"  Result {i+1}: {item['title'][0]}")
                    if 'author' in item and item['author']:
                        authors = []
                        for author in item['author'][:2]:  # Show first 2 authors
                            if 'family' in author:
                                authors.append(author['family'])
                        print(f"    Authors: {', '.join(authors)}")
            
            # Find the best match by comparing titles
            best_match = None
            best_score = 0
            
            for item in items:
                if 'title' in item and item['title']:
                    item_title = item['title'][0].lower()
                    search_title = query_data['title'].lower()
                    
                    # Special handling for all caps titles
                    if query_data['title'].isupper():
                        search_title = query_data['title'].lower()
                    
                    # Simple score based on word overlap
                    words1 = set(re.findall(r'\b\w+\b', item_title))
                    words2 = set(re.findall(r'\b\w+\b', search_title))
                    common = words1.intersection(words2)
                    
                    if len(words1) > 0 and len(words2) > 0:
                        # Calculate base score
                        base_score = len(common) / max(len(words1), len(words2))
                        score = base_score
                        
                        # Boost score if important title words match
                        # (ignore common words like "the", "of", "and", etc.)
                        important_words = [w for w in common 
                                         if len(w) > 3 and w not in 
                                         ['this', 'that', 'with', 'from', 'have', 'there']]
                        if len(important_words) >= 2:
                            score += 0.1
                            
                        # Boost score if author matches
                        if 'author' in item and 'author' in query_data and query_data['author']:
                            author_words = set(re.findall(r'\b\w+\b', query_data['author'].lower()))
                            for author in item['author']:
                                if 'family' in author:
                                    if author['family'].lower() in author_words:
                                        score += 0.2
                                        break
                        
                        # Boost score if journal matches
                        if 'journal' in query_data and 'container-title' in item and item['container-title']:
                            journal_words = set(re.findall(r'\b\w+\b', query_data['journal'].lower()))
                            item_journal = item['container-title'][0].lower()
                            item_journal_words = set(re.findall(r'\b\w+\b', item_journal))
                            journal_common = journal_words.intersection(item_journal_words)
                            if len(journal_common) > 0:
                                score += 0.2
                        
                        # Boost score if publication year is in the PDF filename
                        if pdf_path and '_' in os.path.basename(pdf_path):
                            # Extract year from filename if in author_year format
                            try:
                                filename = os.path.basename(pdf_path)
                                filename_year = filename.split('_')[1]
                                if filename_year.isdigit() and len(filename_year) == 4:
                                    # Check if publication year matches
                                    if 'published-print' in item and 'date-parts' in item['published-print']:
                                        pub_year = str(item['published-print']['date-parts'][0][0])
                                        if pub_year == filename_year:
                                            score += 0.3
                            except:
                                pass
                        
                        if score > best_score:
                            best_score = score
                            best_match = item
            
            # If we have a reasonable match, return its DOI
            if best_match and best_score > 0.3 and 'DOI' in best_match:  # Lower threshold for academic papers
                print(f"  Best match score: {best_score:.2f}")
                print(f"  Matched title: {best_match['title'][0]}")
                return best_match['DOI']
            else:
                print(f"  No good match found. Best score: {best_score:.2f}")
        
        return None
    
    except Exception as e:
        print(f"  Error searching Crossref: {e}")
        return None

def fetch_metadata_from_doi(doi):
    """Fetch complete metadata using the DOI."""
    try:
        print(f"  Fetching metadata from DOI: {doi}")
        url = f"https://api.crossref.org/works/{doi}"
        headers = {
            'User-Agent': 'PdfMetadataUpdater/1.0 (mailto:your-email@example.com)'
        }
        
        # Try to handle DOIs that might contain URL-encoded characters
        cleaned_doi = doi.strip()
        if cleaned_doi.startswith('http'):
            # Extract the DOI part from a URL
            doi_match = re.search(r'(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)', cleaned_doi)
            if doi_match:
                cleaned_doi = doi_match.group(1)
        
        # Make the request
        print(f"  Querying Crossref API at: {url}")
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            print(f"  DOI lookup error: {response.status_code}")
            # Try a second method with URL encoding
            url = f"https://api.crossref.org/works/{quote_plus(cleaned_doi)}"
            print(f"  Trying with URL encoding: {url}")
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                print(f"  DOI lookup error with encoding: {response.status_code}")
                return None
            
        data = response.json()
        
        if 'message' in data:
            message = data['message']
            metadata = {}
            
            # Extract basic metadata
            if 'title' in message and message['title']:
                metadata['title'] = message['title'][0]
            
            if 'author' in message:
                authors = []
                for author in message['author']:
                    if 'given' in author and 'family' in author:
                        authors.append(f"{author['given']} {author['family']}")
                    elif 'family' in author:
                        authors.append(author['family'])
                metadata['author'] = '; '.join(authors)
            
            # Try to get publication date from different fields
            for date_field in ['published-print', 'published-online', 'created']:
                if date_field in message and 'date-parts' in message[date_field]:
                    date_parts = message[date_field]['date-parts'][0]
                    if date_parts and len(date_parts) > 0:
                        metadata['year'] = str(date_parts[0])
                        break
            
            if 'container-title' in message and message['container-title']:
                metadata['journal'] = message['container-title'][0]
                
            metadata['doi'] = doi
            
            return metadata
        
        return None
    
    except Exception as e:
        print(f"  Error fetching metadata from DOI: {e}")
        return None

def create_zotero_filename(metadata, original_path):
    """Create a filename in the Zotero format: Author - Year - Title.pdf."""
    try:
        # Check if this file should be marked with an underscore due to incomplete metadata
        mark_incomplete = False
        if 'year' not in metadata or not metadata['year'] or metadata['year'] == 'Unknown':
            mark_incomplete = True
        if 'title' not in metadata or not metadata['title'] or 'author' not in metadata or not metadata['author']:
            mark_incomplete = True
            
        # Extract author
        authors = []
        if 'author' in metadata and metadata['author']:
            # Split author string by common delimiters
            author_list = re.split(r'[;,]', metadata['author'])
            for author in author_list[:3]:  # Limit to first 3 authors
                # Extract last name
                author = author.strip()
                if ' ' in author:
                    # For "Firstname Lastname" format
                    last_name = author.split(' ')[-1]
                    authors.append(last_name)
                else:
                    # Just use what we have
                    authors.append(author)
            
            if len(authors) == 0:
                authors = ['Unknown']
                mark_incomplete = True
        else:
            authors = ['Unknown']
            mark_incomplete = True
        
        # Format the author part of the filename
        if len(authors) == 1:
            author_part = authors[0]
        elif len(authors) == 2:
            author_part = f"{authors[0]} & {authors[1]}"
        else:
            author_part = f"{authors[0]} et al."
        
        # Extract year
        year = metadata.get('year', 'Unknown')
        if year == 'Unknown':
            mark_incomplete = True
        
        # Extract title and shorten if needed
        title = metadata.get('title', os.path.splitext(os.path.basename(original_path))[0])
        if not title or title == os.path.splitext(os.path.basename(original_path))[0]:
            mark_incomplete = True
            
        # Truncate title if too long (max 100 chars)
        if len(title) > 100:
            title = title[:97] + "..."
        
        # Create raw filename
        raw_filename = f"{author_part} - {year} - {title}"
        
        # Sanitize filename - use pathvalidate if available, otherwise use regex
        if PATHVALIDATE_AVAILABLE:
            # Use pathvalidate's built-in sanitization (handles all OS-specific rules)
            filename = sanitize_filename(raw_filename)
            # Additional sanitization for characters we specifically want to remove
            filename = re.sub(r'[\'",;()]', '', filename)  # Remove quotes, parentheses, etc.
            filename = re.sub(r'[&]', 'and', filename)     # Replace & with 'and'
        else:
            # Manual sanitization with regex
            filename = re.sub(r'[<>:"/\\|?*\'(),;"]', '', raw_filename)  # Remove apostrophes, quotes, parentheses, etc.
            filename = re.sub(r"[&]", 'and', filename)  # Replace & with 'and'
            filename = re.sub(r"\s+", ' ', filename).strip()  # Remove extra spaces
        
        # Add extension
        filename = f"{filename}.pdf"
        
        # Handle cases where the generated filename is too long for the filesystem
        if len(filename) > 240:  # Leave some margin for the path
            # Truncate the filename
            base_name = filename[:-4]  # Remove .pdf
            base_name = base_name[:236]  # Truncate to 236 chars (240-4 for .pdf)
            filename = f"{base_name}.pdf"
        
        # If metadata is incomplete, prepend an underscore
        if mark_incomplete:
            filename = f"_{filename}"
            
        return filename
        
    except Exception as e:
        print(f"  Error creating Zotero filename: {e}")
        # Return original filename as fallback
        return os.path.basename(original_path)

def update_pdf_metadata(pdf_path, metadata, output_path=None):
    """Update PDF metadata and save to a new file if output_path is provided."""
    if not output_path:
        output_path = output_path or pdf_path
        
    try:
        # Use pikepdf for metadata update
        with pikepdf.open(pdf_path, allow_overwriting_input=True) as pdf:
            # Create an entirely new docinfo dictionary rather than modifying the existing one
            # This is the most effective way to ensure unwanted fields are removed
            new_docinfo = pikepdf.Dictionary()
            
            # Add only the metadata we want
            if 'title' in metadata:
                new_docinfo['/Title'] = metadata['title']
            if 'author' in metadata:
                new_docinfo['/Author'] = metadata['author']
            if 'year' in metadata:
                try:
                    new_docinfo['/CreationDate'] = f"D:{metadata['year']}0101000000Z"
                except:
                    print("  Warning: Couldn't set CreationDate")
            
            # Handle journal and DOI - make DOI more visible in macOS
            if 'journal' in metadata and 'doi' in metadata:
                # Include DOI in Subject field for better visibility in macOS
                new_docinfo['/Subject'] = f"{metadata['journal']} | DOI: {metadata['doi']}"
            elif 'journal' in metadata:
                new_docinfo['/Subject'] = metadata['journal']
            elif 'doi' in metadata:
                new_docinfo['/Subject'] = f"DOI: {metadata['doi']}"
                
            # Still set Keywords for compatibility with other PDF readers
            if 'doi' in metadata:
                new_docinfo['/Keywords'] = f"DOI: {metadata['doi']}"
            elif 'publication_info' in metadata:
                new_docinfo['/Keywords'] = f"Publication Info: {metadata['publication_info']}"
            
            # Add DOI to more fields for better discovery
            if 'doi' in metadata:
                # Some PDF viewers check these fields
                new_docinfo['/CustomField1'] = f"DOI: {metadata['doi']}"
            
            # Copy some standard metadata fields if they exist and we don't have replacements
            standard_fields = ['/Creator', '/Producer']
            for field in standard_fields:
                if field in pdf.docinfo and field not in new_docinfo:
                    new_docinfo[field] = pdf.docinfo[field]
            
            # Make the dictionary an indirect object - this fixes the "docinfo must be an indirect object" error
            new_docinfo = pdf.make_indirect(new_docinfo)
            
            # Replace the entire docinfo dictionary
            pdf.docinfo = new_docinfo
            
            # Handle XMP metadata which macOS may use for the "Where from" field
            try:
                with pdf.open_metadata() as xmp_meta:
                    # Remove any URL-related or "where from" related properties in XMP
                    keys_to_remove = []
                    for key in xmp_meta.keys():
                        key_lower = str(key).lower()
                        if ('where' in key_lower or 
                            'url' in key_lower or 
                            'source' in key_lower or 
                            'link' in key_lower or
                            'from' in key_lower or
                            'uri' in key_lower):
                            keys_to_remove.append(key)
                    
                    # Remove the identified keys
                    for key in keys_to_remove:
                        try:
                            del xmp_meta[key]
                        except:
                            pass
                    
                    # Also try to rebuild key XMP namespaces that might contain the "Where from" field
                    if 'pdf:custom_metadata' in xmp_meta:
                        del xmp_meta['pdf:custom_metadata']
                    
                    # Add our metadata in XMP format as well for consistency
                    # For XMP, creator needs to be a list of strings
                    if 'title' in metadata:
                        xmp_meta['dc:title'] = metadata['title']
                    if 'author' in metadata:
                        # Split authors by semicolons or commas and convert to a proper list
                        author_list = [author.strip() for author in re.split(r'[;,]', metadata['author'])]
                        xmp_meta['dc:creator'] = author_list
                    
                    # Add journal and DOI to description
                    if 'journal' in metadata:
                        if 'doi' in metadata:
                            xmp_meta['dc:description'] = f"{metadata['journal']} | DOI: {metadata['doi']}"
                        else:
                            xmp_meta['dc:description'] = metadata['journal']
                    elif 'doi' in metadata:
                        xmp_meta['dc:description'] = f"DOI: {metadata['doi']}"
                        
                    # Add DOI to identifier field if available
                    if 'doi' in metadata:
                        xmp_meta['dc:identifier'] = metadata['doi']
            except Exception as xmp_error:
                print(f"  Warning: Could not update XMP metadata: {xmp_error}")
            
            # For macOS specific metadata, we need to remove all potentially related keys
            # Try to access macOS specific metadata methods if available
            try:
                # Check if there's any extended metadata that might contain "Where from"
                for meta_key in list(pdf.Root.keys()):
                    if str(meta_key).lower() in ['/metadata', '/privatedata', '/info']:
                        try:
                            # If it's a metadata container we can't easily edit, try to replace it
                            if meta_key != '/Info':  # Don't touch the standard Info dictionary we just set
                                # This is more aggressive, only do this for PDFs with persistent "Where from" issues
                                del pdf.Root[meta_key]
                        except:
                            pass
            except Exception as ext_error:
                print(f"  Warning: Could not clean extended metadata: {ext_error}")
                
            # Save the PDF
            try:
                # Ensure the output directory exists
                os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
                
                # Save without the unsupported parameter
                pdf.save(output_path)
    
            except Exception as save_err:
                print(f"  Warning: Error saving PDF: {save_err}")
                raise
        
        return True
        
    except Exception as e:
        print(f"  Error updating PDF metadata: {e}")
        # Try an alternative approach if the first method fails
        try:
            print("  Trying alternative metadata update method...")
            # Create a completely new PDF file with the same content but new metadata
            temp_output = output_path + ".tmp"
            
            # First, try with pikepdf in a different way
            with pikepdf.open(pdf_path) as pdf_in:
                # Create a new PDF with the same content
                pdf_out = pikepdf.new()
                
                # Copy all pages and content
                for page in pdf_in.pages:
                    pdf_out.pages.append(pdf_out.copy_foreign(page))
                
                # Copy necessary keys from the Root object, but be selective
                for key in pdf_in.Root.keys():
                    if key not in ['/Info', '/Metadata', '/AcroForm', '/OCProperties']:
                        try:
                            pdf_out.Root[key] = pdf_out.copy_foreign(pdf_in.Root[key])
                        except:
                            print(f"  Warning: Could not copy Root key: {key}")
                
                # Create a new clean metadata dictionary
                new_info = pikepdf.Dictionary()
                if 'title' in metadata:
                    new_info['/Title'] = metadata['title']
                if 'author' in metadata:
                    new_info['/Author'] = metadata['author']
                if 'year' in metadata:
                    try:
                        new_info['/CreationDate'] = f"D:{metadata['year']}0101000000Z"
                    except:
                        pass
                
                # Handle journal and DOI - append DOI to journal in Subject field
                if 'journal' in metadata:
                    if 'doi' in metadata:
                        # Include DOI after the journal name
                        new_info['/Subject'] = f"{metadata['journal']} | DOI: {metadata['doi']}"
                    else:
                        new_info['/Subject'] = metadata['journal']
                elif 'doi' in metadata:
                    # No journal, just show DOI
                    new_info['/Subject'] = f"DOI: {metadata['doi']}"
                    
                # Add publication info to Keywords if available
                if 'publication_info' in metadata:
                    new_info['/Keywords'] = f"Publication Info: {metadata['publication_info']}"
                
                # Make the dictionary an indirect object
                new_info = pdf_out.make_indirect(new_info)
                
                # Set the new docinfo
                pdf_out.docinfo = new_info
                
                # Save the file
                pdf_out.save(temp_output)
                
                # Preserve the original file's timestamps
                if original_creation_time is not None:
                    preserve_timestamps(temp_output, pdf_path,
                                       ctime=original_creation_time,
                                       mtime=original_modification_time,
                                       atime=original_access_time)
            
            # Check if the file was created successfully
            if os.path.exists(temp_output) and os.path.getsize(temp_output) > 0:
                # Replace the original/target file with the temporary one
                os.replace(temp_output, output_path)
                print("  Alternative method successful")
                return True
            else:
                raise Exception("Failed to create valid PDF file")
                
        except Exception as e2:
            print(f"  Alternative method also failed: {e2}")
            if os.path.exists(temp_output):
                os.remove(temp_output)
            
            # Last resort: try with PyPDF2
            try:
                print("  Trying PyPDF2 as fallback...")
                from PyPDF2 import PdfReader, PdfWriter
                
                reader = PdfReader(pdf_path)
                writer = PdfWriter()
                
                # Add all pages from the original PDF
                for page in reader.pages:
                    writer.add_page(page)
                
                # Ensure no "Where from" type fields make it into the metadata
                metadata_dict = {}
                if 'title' in metadata:
                    metadata_dict["/Title"] = metadata['title']
                if 'author' in metadata:
                    metadata_dict["/Author"] = metadata['author']
                
                # Handle journal and DOI - append DOI to journal in Subject field
                if 'journal' in metadata:
                    if 'doi' in metadata:
                        # Include DOI after the journal name
                        metadata_dict["/Subject"] = f"{metadata['journal']} | DOI: {metadata['doi']}"
                    else:
                        metadata_dict["/Subject"] = metadata['journal']
                elif 'doi' in metadata:
                    # No journal, just show DOI
                    metadata_dict["/Subject"] = f"DOI: {metadata['doi']}"
                    
                # Add publication info to Keywords if available
                if 'publication_info' in metadata:
                    metadata_dict["/Keywords"] = f"Publication Info: {metadata['publication_info']}"
                
                # Use addMetadata instead of add_metadata (for newer PyPDF2 versions)
                try:
                    writer.add_metadata(metadata_dict)
                except AttributeError:
                    try:
                        writer.addMetadata(metadata_dict)
                    except:
                        print("  Warning: Could not add metadata with PyPDF2")
                
                # Save the PDF
                with open(output_path, "wb") as output:
                    writer.write(output)
                
                # Preserve the original file's timestamps
                if original_creation_time is not None:
                    preserve_timestamps(output_path, pdf_path,
                                       ctime=original_creation_time,
                                       mtime=original_modification_time,
                                       atime=original_access_time)
                
                print("  PyPDF2 fallback successful")
                return True
            except Exception as e3:
                print(f"  All metadata update methods failed. Last error: {e3}")
                return False

def process_pdf(pdf_path, output_path=None, rename=False):
    """Process a single PDF file."""
    print(f"\nProcessing: {pdf_path}")
    
    # Track whether any major errors occurred
    had_error = False

    # Get the file's original creation time and modification time
    original_stat = os.stat(pdf_path)
    creation_time = original_stat.st_ctime
    modification_time = original_stat.st_mtime
    access_time = original_stat.st_atime
    
    # 1. Extract info and check for embedded DOI
    info, doi = extract_info_from_pdf(pdf_path)
    
    if not doi:
        if not info or not info.get('title'):
            print("  Could not extract title from PDF")
            had_error = True
            
        # 2. Search for DOI using extracted info
        doi = search_doi_from_crossref(info, pdf_path)
    
    # Initialize metadata
    metadata = {}
    
    if doi:
        print(f"  Found DOI: {doi}")
        
        # 3. Fetch complete metadata from DOI
        doi_metadata = fetch_metadata_from_doi(doi)
        if doi_metadata:
            print("\n  Fetched metadata from DOI:")
            for key, value in doi_metadata.items():
                print(f"    {key}: {value}")
            metadata = doi_metadata
        else:
            print("  Could not fetch metadata from DOI, using extracted info")
            metadata = info if info else {}
            metadata['doi'] = doi
            had_error = True  # Mark as error since we couldn't get complete metadata
    else:
        print("  Could not find DOI for this paper. Using extracted metadata.")
        metadata = info if info else {}
        had_error = True  # Mark as error since we couldn't find a DOI
    
    # Print the metadata we're going to use
    print("\n  Metadata that will be used to update PDF:")
    if metadata:
        for key, value in metadata.items():
            print(f"    {key}: {value}")
    else:
        print("    No metadata available")
        had_error = True
        
    # 3. Handle file renaming if requested
    new_filename = os.path.basename(pdf_path)
        
    if rename:
        if metadata:
            try:
                # Generate new filename based on metadata
                new_filename = create_zotero_filename(metadata, pdf_path)
                print(f"  Renaming to: {os.path.basename(new_filename)}")
            except Exception as e:
                print(f"  Error preparing Zotero file name: {e}")
                had_error = True
                                
        # If no metadata extracted, mark the file with _ 
        # If there was an error in the process, flag with an underscore
        if had_error and not new_filename.startswith('_'):
            new_filename = f"_{new_filename}"         
             
    # 4. Handle moving to output directory if requested
    new_path = None
    output_dir = None

    # Determine the output directory
    if output_path:
        if os.path.isdir(output_path):
           # Output is a directory
            output_dir = output_path
        else:
            # Output is a file path
            output_dir = os.path.dirname(output_path)
                    
        # Create the new path with metadata-based filename in the output directory
        new_path = os.path.join(output_dir, new_filename)
        
    else:
        # No output path specified, use original directory
        original_dir = os.path.dirname(pdf_path)
        new_path = os.path.join(original_dir, new_filename)
        
    if new_path:        
        # Check if the target file already exists
        counter = 1
        base_path = new_path
        while os.path.exists(new_path) and os.path.abspath(new_path) != os.path.abspath(pdf_path):
            # Add a counter to the filename
            name_parts = os.path.splitext(base_path)
            new_path = f"{name_parts[0]} ({counter}){name_parts[1]}"
            counter += 1
   
        try:
            print(f"  Moving to: {os.path.basename(new_path)}")
            shutil.copy2(pdf_path, new_path)
            os.remove(pdf_path)
            print(f"  File moved to: {os.path.basename(new_path)}")                                
        except Exception as e:
            print(f"  Error moving file: {e}")
            had_error = True
    else:
        print("  Failed to move file")
        had_error = True

        
    # 4. Update PDF metadata with whatever information we have
    if metadata:
        try:
            print(f"  Updating metadata in: {new_path}")
            result = update_pdf_metadata(new_path, metadata)
            # print(f"  Updater returned: {result}")
            
            if result:
                # print(f"  Successfully updated metadata in: {new_path}")
                print(f"  Resetting original timestamps")
                os.utime(new_path, (access_time, modification_time))
                return True
        except Exception as e:
            print(f"  Unexpected error during metadata update: {e}")
            had_error = True
            return False
                
    else:
        print("  No metadata available to update PDF")
        had_error = True
        return False

def main():
    parser = argparse.ArgumentParser(description='Update PDF metadata using OCR and Crossref')
    parser.add_argument('pdf_paths', nargs='+', help='Path(s) to PDF file(s) or directory')
    parser.add_argument('--output', '-o', help='Output directory (for directory/batch processing) or file (for single file)')
    parser.add_argument('--recursive', '-r', action='store_true', help='Process directories recursively')
    parser.add_argument('--tesseract-path', help='Path to Tesseract executable')
    parser.add_argument('--rename', action='store_true', help='Rename the files using the format "Author - Year - Title.pdf" (Zotero style)')
    
    args = parser.parse_args()
    
    # Set custom Tesseract path if provided
    if args.tesseract_path:
        if OCR_AVAILABLE:
            pytesseract.pytesseract.tesseract_cmd = args.tesseract_path
        else:
            print("Warning: Tesseract path provided but OCR libraries not installed")
    
    # Handle all provided paths
    all_files = []
    
    # Process each provided path
    for path in args.pdf_paths:
        if os.path.isfile(path):
            # It's a single file
            if path.lower().endswith('.pdf'):
                all_files.append(path)
        elif os.path.isdir(path):
            # It's a directory
            if args.recursive:
                for root, _, files in os.walk(path):
                    for file in files:
                        if file.lower().endswith('.pdf'):
                            all_files.append(os.path.join(root, file))
            else:
                for file in os.listdir(path):
                    if file.lower().endswith('.pdf') and os.path.isfile(os.path.join(path, file)):
                        all_files.append(os.path.join(path, file))
        else:
            print(f"Warning: {path} is not a valid file or directory, skipping")
    
    if not all_files:
        print("No PDF files found to process")
        return
    
    num_files = len(all_files)
    print(f"Found {num_files} PDF files to process")
    
    # Process all files
    for (counter, pdf_file) in enumerate(all_files):
        if args.output:
            if len(all_files) == 1 and not os.path.isdir(args.output):
                # Single file, output is a file path
                output_path = args.output
            else:
                # Multiple files or output is a directory
                if os.path.isdir(args.output):
                    # Create the same directory structure in the output directory for files from directories
                    if any(os.path.isdir(p) for p in args.pdf_paths):
                        # Find the common base directory
                        base_dir = os.path.commonpath([os.path.abspath(p) for p in args.pdf_paths if os.path.isdir(p)])
                        rel_path = os.path.relpath(pdf_file, base_dir)
                        output_path = os.path.join(args.output, rel_path)
                    else:
                        # Just use the filename
                        output_path = os.path.join(args.output, os.path.basename(pdf_file))
                else:
                    # Create directory if it doesn't exist
                    os.makedirs(args.output, exist_ok=True)
                    output_path = os.path.join(args.output, os.path.basename(pdf_file))
                
                # Create any intermediate directories
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
        else:
            output_path = None
    
        c = counter + 1
        print(f"\nProcessing: {c} of {num_files}")
        process_pdf(pdf_file, output_path, rename=args.rename)
        
        # Add a small delay between requests to avoid rate limiting
        if len(all_files) > 1:
            time.sleep(1)

if __name__ == "__main__":
    main()
