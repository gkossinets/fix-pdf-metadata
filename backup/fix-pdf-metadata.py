#!/usr/bin/env python3
"""
PDF Metadata Updater from Filename

This script parses Zotero-formatted filenames (Author - Year - Title.pdf),
searches for DOI using Crossref, and updates PDF metadata while preserving file timestamps.

Requirements:
    pip install pikepdf requests
"""

import os
import re
import argparse
import time
from pprint import pformat
import platform
import shutil
import subprocess
from urllib.parse import quote_plus
import requests
import pikepdf


def parse_zotero_filename(filename):
    """Extract author, year, and title from a Zotero-formatted filename."""
    # Pattern for "Author - Year - Title.pdf"
    pattern = r'^_*(.+?) - (\d{4}) - (.+?)\.pdf$'
    match = re.match(pattern, filename)
    
    if match:
        authors = match.group(1)
        year = match.group(2)
        title = match.group(3)
        return {
            'authors': authors,
            'year': year,
            'title': title
        }        
    else:
        print(f"Warning: Could not parse filename: {filename}")
        return None

def search_doi_from_crossref(metadata):
    """Search for a DOI using the Crossref API based on title, author, and year."""
    try:
        print(f"Searching Crossref with: {metadata['title']}, {metadata['authors']}, {metadata['year']}")
        
        # Build the query with the available information
        query_parts = []
        
        # Add title (most important)
        if 'title' in metadata and metadata['title']:
            query_parts.append(metadata['title'])
        # authors
        # Add author if available
        if 'authors' in metadata and metadata['authors']:
            # Extract last name if multiple words
            words = metadata['authors'].split()
            if len(words) > 1:
                # If format is "Last, First" get the part before the comma
                if ',' in metadata['authors']:
                    lastname = metadata['authors'].split(',')[0]
                else:
                    # Otherwise, assume the last word is the last name
                    lastname = words[-1]
                query_parts.append(lastname)
            else:
                query_parts.append(metadata['authors'])
        
        # Add year if available
        if 'year' in metadata and metadata['year']:
            query_parts.append(metadata['year'])
        
        if not query_parts:
            print("No usable search terms found")
            return None
            
        # Build the query with the most important parts
        query = " ".join(query_parts)
        print(f"Query string: {query}")
        encoded_query = quote_plus(query)
        
        url = f"https://api.crossref.org/works?query={encoded_query}&rows=5"
        headers = {
            'User-Agent': 'PdfMetadataUpdater/1.0 (mailto:user@example.com)'
        }
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            print(f"Crossref API error: {response.status_code}")
            return None
            
        data = response.json()
        
        if 'message' in data and 'items' in data['message'] and data['message']['items']:
            # Get the top results
            items = data['message']['items']
            
            # Find the best match by comparing titles and publication year
            best_match = None
            best_score = 0
            
            for item in items:
                score = 0
                
                # Check title similarity
                if 'title' in item and item['title']:
                    item_title = item['title'][0].lower()
                    search_title = metadata['title'].lower()
                    
                    # Simple score based on word overlap
                    words1 = set(re.findall(r'\b\w+\b', item_title))
                    words2 = set(re.findall(r'\b\w+\b', search_title))
                    common = words1.intersection(words2)
                    
                    if len(words1) > 0 and len(words2) > 0:
                        # Calculate title similarity score
                        title_score = len(common) / max(len(words1), len(words2))
                        score += title_score * 0.6  # Title is 60% of total score
                
                # Check year match
                if 'year' in metadata and metadata['year']:
                    pub_year = None
                    
                    # Try to get publication year from different fields
                    for date_field in ['published-print', 'published-online', 'created']:
                        if date_field in item and 'date-parts' in item[date_field]:
                            date_parts = item[date_field]['date-parts'][0]
                            if date_parts and len(date_parts) > 0:
                                pub_year = str(date_parts[0])
                                break
                    
                    if pub_year and pub_year == metadata['year']:
                        score += 0.3  # Year match is 30% of total score
                
                # Check author match
                if 'authors' in item and 'authors' in metadata and metadata['authors']:
                    author_words = set(re.findall(r'\b\w+\b', metadata['authors'].lower()))
                    for author in item['authors']:
                        if 'family' in author:
                            if author['family'].lower() in author_words:
                                score += 0.1  # Author match is 10% of total score
                                break
                
                if score > best_score:
                    best_score = score
                    best_match = item
            
            # If we have a reasonable match, return its data
            if best_match and best_score > 0.5:  # Require a good match
                print(f"Best match score: {best_score:.2f}")
                
                result = {}
                
                if 'title' in best_match and best_match['title']:
                    print(f"Matched title: {best_match['title'][0]}")
                    result['title'] = best_match['title'][0]
                
                # Extract DOI if available
                if 'DOI' in best_match:
                    result['doi'] = best_match['DOI']
                    print(f"Found DOI: {result['doi']}")
                
                # Extract ISBN if available
                if 'ISBN' in best_match:
                    result['isbn'] = best_match['ISBN'][0] if isinstance(best_match['ISBN'], list) else best_match['ISBN']
                    print(f"Found ISBN: {result['isbn']}")
                
                # Extract journal if available
                if 'container-title' in best_match and best_match['container-title']:
                    result['journal'] = best_match['container-title'][0]
                    print(f"Found journal: {result['journal']}")

                if 'author' in best_match:
                    authors = []
                    for author in best_match['author']:
                        if 'given' in author and 'family' in author:
                            authors.append(f"{author['given']} {author['family']}")
                        elif 'family' in author:
                            authors.append(author['family'])
                    result['authors'] = '; '.join(authors)
                    print(f"Found authors: {result['authors']}")

                # Return the complete result
                return result
            else:
                print(f"No good match found. Best score: {best_score:.2f}")
        
        return None
    
    except Exception as e:
        print(f"Error searching Crossref: {e}")
        return None

def update_pdf_metadata(pdf_path, metadata, output_path=None):
    """Update PDF metadata and preserve timestamps."""
    if not output_path:
        output_path = pdf_path
    
    # Get original file stats for timestamp preservation
    original_stat = os.stat(pdf_path)
    
    try:
        # Create temp output path if updating in place
        temp_output = output_path + ".tmp" if output_path == pdf_path else output_path
        
        # Use pikepdf for metadata update
        with pikepdf.open(pdf_path) as pdf:
            # Create a new metadata dictionary
            new_docinfo = pikepdf.Dictionary()
            
            # Add metadata fields
            if 'title' in metadata:
                new_docinfo['/Title'] = metadata['title']
            if 'authors' in metadata:
                new_docinfo['/Authors'] = metadata['authors']
            
            # Add subject field with journal, year, and DOI/ISBN
            subject = ""
            if 'journal' in metadata and metadata['journal']:
                subject = metadata['journal']
                # Add year to journal if available
                if 'year' in metadata and metadata['year']:
                    subject += f", {metadata['year']}"
                
            if 'doi' in metadata and metadata['doi']:
                if subject:
                    subject += f" | DOI: {metadata['doi']}"
                else:
                    subject = f"DOI: {metadata['doi']}"
            elif 'isbn' in metadata and metadata['isbn']:
                if subject:
                    subject += f" | ISBN: {metadata['isbn']}"
                else:
                    subject = f"ISBN: {metadata['isbn']}"
                
            if subject:
                new_docinfo['/Subject'] = subject
            
            # Add year to appropriate field
            if 'year' in metadata:
                try:
                    new_docinfo['/CreationDate'] = f"D:{metadata['year']}0101000000Z"
                except Exception as year_err:
                    print(f"Warning: Could not set year: {year_err}")
            
            # Make the dictionary an indirect object
            new_docinfo = pdf.make_indirect(new_docinfo)
            
            # Replace the document info
            pdf.docinfo = new_docinfo
            
            # Update XMP metadata too
            try:
                with pdf.open_metadata() as xmp_meta:
                    if 'title' in metadata:
                        xmp_meta['dc:title'] = metadata['title']
                    if 'authors' in metadata:
                        xmp_meta['dc:creator'] = [metadata['authors']]
                    
                    description = ""
                    if 'journal' in metadata:
                        description = metadata['journal']
                        # Add year to journal in description if available
                        if 'year' in metadata and metadata['year']:
                            description += f", {metadata['year']}"
                    
                    if 'doi' in metadata:
                        if description:
                            description += f" | DOI: {metadata['doi']}"
                        else:
                            description = f"DOI: {metadata['doi']}"
                    elif 'isbn' in metadata:
                        if description:
                            description += f" | ISBN: {metadata['isbn']}"
                        else:
                            description = f"ISBN: {metadata['isbn']}"
                            
                    if description:
                        xmp_meta['dc:description'] = description
                    
                    # Add DOI/ISBN to identifier field
                    if 'doi' in metadata:
                        xmp_meta['dc:identifier'] = metadata['doi']
                    elif 'isbn' in metadata:
                        xmp_meta['dc:identifier'] = metadata['isbn']
            except Exception as xmp_err:
                print(f"Warning: Could not update XMP metadata: {xmp_err}")
            
            # Save the PDF
            pdf.save(temp_output)
        
        # If updating in place, replace original with temp file
        if output_path == pdf_path:
            #os.replace(temp_output, output_path)
            shutil.copy2(temp_output, output_path)
            os.remove(temp_output)
        
        # Preserve timestamps
        # preserve_timestamps(output_path, pdf_path)
        
        try:
            # Update modification and access time
            print(f"Preserving file timestampes")
            os.utime(output_path, (original_stat.st_atime, original_stat.st_mtime))
        
        except Exception as e:
            print(f"Warning: Could not preserve all timestamps: {e}")
        
        return True
    
    except Exception as e:
        print(f"Error updating PDF metadata: {e}")
        # Try to clean up temp file if it exists
        if 'temp_output' in locals() and os.path.exists(temp_output):
            os.remove(temp_output)
        return False


def update_pdf_metadata_old(pdf_path, metadata, output_path=None):
    """Update PDF metadata and preserve timestamps."""
    if not output_path:
        output_path = pdf_path
    
    # Get original file stats for timestamp preservation
    original_stat = os.stat(pdf_path)
    
    try:
        # Create temp output path if updating in place
        temp_output = output_path + ".tmp" if output_path == pdf_path else output_path
        
        # Use pikepdf for metadata update
        with pikepdf.open(pdf_path) as pdf:
            # Create a new metadata dictionary
            new_docinfo = pikepdf.Dictionary()
            
            # Add metadata fields
            if 'title' in metadata:
                new_docinfo['/Title'] = metadata['title']
            if 'authors' in metadata:
                new_docinfo['/Authors'] = metadata['authors']
            
            # Add subject field with journal and DOI/ISBN
            subject = ""
            if 'journal' in metadata and metadata['journal']:
                subject = metadata['journal']
                
            if 'doi' in metadata and metadata['doi']:
                if subject:
                    subject += f" | DOI: {metadata['doi']}"
                else:
                    subject = f"DOI: {metadata['doi']}"
            elif 'isbn' in metadata and metadata['isbn']:
                if subject:
                    subject += f" | ISBN: {metadata['isbn']}"
                else:
                    subject = f"ISBN: {metadata['isbn']}"
                
            if subject:
                new_docinfo['/Subject'] = subject
            
            # Add year to appropriate field
            if 'year' in metadata:
                try:
                    new_docinfo['/CreationDate'] = f"D:{metadata['year']}0101000000Z"
                except Exception as year_err:
                    print(f"Warning: Could not set year: {year_err}")
            
            # Make the dictionary an indirect object
            new_docinfo = pdf.make_indirect(new_docinfo)
            
            # Replace the document info
            pdf.docinfo = new_docinfo
            
            # Update XMP metadata too
            try:
                with pdf.open_metadata() as xmp_meta:
                    if 'title' in metadata:
                        xmp_meta['dc:title'] = metadata['title']
                    if 'authors' in metadata:
                        xmp_meta['dc:creator'] = [metadata['authors']]
                    
                    description = ""
                    if 'journal' in metadata:
                        description = metadata['journal']
                    if 'doi' in metadata:
                        if description:
                            description += f" | DOI: {metadata['doi']}"
                        else:
                            description = f"DOI: {metadata['doi']}"
                    elif 'isbn' in metadata:
                        if description:
                            description += f" | ISBN: {metadata['isbn']}"
                        else:
                            description = f"ISBN: {metadata['isbn']}"
                            
                    if description:
                        xmp_meta['dc:description'] = description
                    
                    # Add DOI/ISBN to identifier field
                    if 'doi' in metadata:
                        xmp_meta['dc:identifier'] = metadata['doi']
                    elif 'isbn' in metadata:
                        xmp_meta['dc:identifier'] = metadata['isbn']
            except Exception as xmp_err:
                print(f"Warning: Could not update XMP metadata: {xmp_err}")
            
            # Save the PDF
            pdf.save(temp_output)
        
        # If updating in place, replace original with temp file
        if output_path == pdf_path:
            #os.replace(temp_output, output_path)
            shutil.copy2(temp_output, output_path)
            os.remove(temp_output)
        
        # Preserve timestamps
        # preserve_timestamps(output_path, pdf_path)
        
        try:
            # Update modification and access time
            # print(f"Preserving file timestampes")
            
            # atime_date_str = t2s(original_stat.st_atime)
            # mtime_date_str = t2s(original_stat.st_mtime)
            # ctime_date_str = t2s(original_stat.st_ctime)
            # btime_date_str = t2s(original_stat.st_birthtime)
            # print(f"Original atime {atime_date_str}, mtime {mtime_date_str}, ctime {ctime_date_str}, btime {btime_date_str}")
            #
            # temp_stat = os.stat(output_path)
            # atime_date_str = t2s(temp_stat.st_atime)
            # mtime_date_str = t2s(temp_stat.st_mtime)
            # ctime_date_str = t2s(temp_stat.st_ctime)
            # btime_date_str = t2s(temp_stat.st_birthtime)
            # print(f"Temp atime     {atime_date_str}, mtime {mtime_date_str}, ctime {ctime_date_str}, btime {btime_date_str}")

            os.utime(output_path, (original_stat.st_atime, original_stat.st_mtime))

            # temp_stat = os.stat(output_path)
            # atime_date_str = t2s(temp_stat.st_atime)
            # mtime_date_str = t2s(temp_stat.st_mtime)
            # ctime_date_str = t2s(temp_stat.st_ctime)
            # btime_date_str = t2s(temp_stat.st_birthtime)
            # print(f"New atime      {atime_date_str}, mtime {mtime_date_str}, ctime {ctime_date_str}, btime {btime_date_str}")

            # # For creation time, use platform-specific methods
            # print("Running set_creation_date_macos()")
            # set_creation_date_macos(output_path, original_stat.st_birthtime)
            #
            # temp_stat = os.stat(output_path)
            # atime_date_str = t2s(temp_stat.st_atime)
            # mtime_date_str = t2s(temp_stat.st_mtime)
            # ctime_date_str = t2s(temp_stat.st_ctime)
            # btime_date_str = t2s(temp_stat.st_birthtime)
            # print(f"New atime      {atime_date_str}, mtime {mtime_date_str}, ctime {ctime_date_str}, btime {btime_date_str}")
        
        except Exception as e:
            print(f"Warning: Could not preserve all timestamps: {e}")
        
        return True
    
    except Exception as e:
        print(f"Error updating PDF metadata: {e}")
        # Try to clean up temp file if it exists
        if 'temp_output' in locals() and os.path.exists(temp_output):
            os.remove(temp_output)
        return False
        
def t2s(t):
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t))

def process_pdf(pdf_path, output_path=None):
    """Process a single PDF file."""
    filename = os.path.basename(pdf_path)
    print(f"\nProcessing: {filename}")
    
    # Parse the filename
    metadata = parse_zotero_filename(filename)
    if not metadata:
        print(f"Skipping {filename} - not in Zotero format")
        return False
    
    print(f"Extracted from filename: Authors: {metadata['authors']}, Year: {metadata['year']}, Title: {metadata['title']}")
    
    # Search for additional metadata from Crossref
    crossref_data = search_doi_from_crossref(metadata)
    if crossref_data:
        # Merge Crossref data with filename data
        metadata.update(crossref_data)
    
    # Update PDF metadata
    result = update_pdf_metadata(pdf_path, metadata, output_path)
    if result:
        print(f"Successfully updated metadata for {filename}")
        print(f"{pformat(metadata)}")
    else:
        print(f"Failed to update metadata for {filename}")
    
    return result

def main():
    parser = argparse.ArgumentParser(description='Update PDF metadata from Zotero-formatted filenames')
    parser.add_argument('pdf_paths', nargs='+', help='Path(s) to PDF file(s) or directory')
    parser.add_argument('--output', '-o', help='Output directory (for directory/batch processing) or file (for single file)')
    parser.add_argument('--recursive', '-r', action='store_true', help='Process directories recursively')
    
    args = parser.parse_args()
    
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
    
    print(f"Found {len(all_files)} PDF files to process")
    
    # Process all files
    for pdf_file in all_files:
        if args.output:
            if len(all_files) == 1 and not os.path.isdir(args.output):
                # Single file, output is a file path
                output_path = args.output
            else:
                # Multiple files or output is a directory
                if not os.path.isdir(args.output):
                    os.makedirs(args.output, exist_ok=True)
                output_path = os.path.join(args.output, os.path.basename(pdf_file))
        else:
            output_path = None
            
        process_pdf(pdf_file, output_path)
        
        # Add a small delay between requests to avoid rate limiting
        if len(all_files) > 1:
            time.sleep(1)

if __name__ == "__main__":
    main()
