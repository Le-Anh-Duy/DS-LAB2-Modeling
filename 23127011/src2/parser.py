import re
import bibtexparser
from typing import List, Dict, Union, Any
from pylatexenc.latex2text import LatexNodes2Text

def parse_ref(path: str) -> List[Dict[str, Any]]:
    """
    Dispatches the parsing logic based on the file extension.

    Args:
        path (str): The path to the reference file (.bib, .tex, or .bbl).

    Returns:
        List[Dict[str, Any]]: A list of parsed references.
    """
    if path.endswith('.bib'):
        return parse_bib(path)
    elif path.endswith('.tex'):
        return parse_tex(path)
    elif path.endswith('.bbl'):
        return parse_bbl(path)
    return []

def parse_bib(bib_file_path: str) -> List[Dict[str, Any]]:
    """
    Parses a .bib file into structured data (title, authors, year).

    Args:
        bib_file_path (str): Path to the .bib file.

    Returns:
        List[Dict[str, Any]]: List of dictionaries containing structured fields.
    """
    latex_converter = LatexNodes2Text(keep_comments=False)

    try:
        with open(bib_file_path, 'r', encoding='utf-8') as bibtex_file:
            parser = bibtexparser.bparser.BibTexParser(common_strings=True)
            bib_database = bibtexparser.load(bibtex_file, parser=parser)
    except FileNotFoundError:
        print(f"Error: File {bib_file_path} not found.")
        return []

    parsed_refs = []

    for entry in bib_database.entries:
        ref_key = entry.get('ID')
        
        def clean_field(text):
            if not text: 
                return ""
            clean_text = latex_converter.latex_to_text(text)
            return " ".join(clean_text.split())

        # 1. Title
        title = clean_field(entry.get('title', ""))

        # 2. Authors
        raw_author = entry.get('author', "")
        clean_author_str = clean_field(raw_author)
        
        authors_list = []
        if clean_author_str:
            # Simple split by 'and'. Complex names might need humanfriends parsing
            parts = clean_author_str.split(' and ')
            authors_list = [p.strip() for p in parts]

        # 3. Year
        raw_year = entry.get('year', 0)
        try:
            year_int = int(clean_field(str(raw_year)))
        except ValueError:
            year_int = 0

        ref_item = {
            ref_key: {
                "title": title,
                "authors": authors_list,
                "year": year_int
            }
        }
        parsed_refs.append(ref_item)

    return parsed_refs

def parse_tex(tex_file_path: str) -> List[Dict[str, str]]:
    """
    Parses a .tex file to find the bibliography environment and extract items.

    Args:
        tex_file_path (str): Path to the .tex file.

    Returns:
        List[Dict[str, str]]: List of dicts mapping citation keys to clean text.
    """
    try:
        with open(tex_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: File {tex_file_path} not found.")
        return []

    # Find the bibliography environment block
    bib_env_pattern = r'\\begin\{thebibliography\}.*?([\s\S]*?)\\end\{thebibliography\}'
    match = re.search(bib_env_pattern, content)
    
    if not match:
        return []

    bib_content = match.group(1)
    return _extract_bib_items_from_text(bib_content)

def parse_bbl(bbl_file_path: str) -> List[Dict[str, str]]:
    """
    Parses a .bbl file to extract bibliography items. 
    Handles both standalone content and wrapped environments.

    Args:
        bbl_file_path (str): Path to the .bbl file.

    Returns:
        List[Dict[str, str]]: List of dicts mapping citation keys to clean text.
    """
    try:
        with open(bbl_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: File {bbl_file_path} not found.")
        return []

    # Check if content is wrapped in thebibliography env (common in .bbl)
    bib_env_pattern = r'\\begin\{thebibliography\}.*?([\s\S]*?)\\end\{thebibliography\}'
    match = re.search(bib_env_pattern, content)
    
    # If wrapped, extract inner content; otherwise use whole content
    bib_content = match.group(1) if match else content

    return _extract_bib_items_from_text(bib_content)

def _extract_bib_items_from_text(content: str) -> List[Dict[str, str]]:
    """
    Helper function to extract \bibitem entries from a raw latex string.

    Args:
        content (str): Raw latex string containing multiple \bibitem entries.

    Returns:
        List[Dict[str, str]]: List of {key: clean_text}.
    """
    # Regex to capture \bibitem{key} and its following content until next \bibitem
    bibitem_pattern = r'\\bibitem(?:\[.*?\])?\{([^}]+)\}\s*([\s\S]*?)(?=\\bibitem|$)'
    raw_refs = re.findall(bibitem_pattern, content)
    
    parsed_results = []
    latex_converter = LatexNodes2Text(keep_comments=False)

    for key, raw_text in raw_refs:
        # Clean latex macros to plain text
        clean_text = latex_converter.latex_to_text(raw_text)
        # Normalize whitespace
        clean_text = " ".join(clean_text.split())
        parsed_results.append({key: clean_text})

    return parsed_results