"""
BibTeX Parser Module - Smart Parsing for Reference Matching.

Module chứa các hàm để parse và clean BibTeX content
từ các định dạng khác nhau (structured @article, flat text, etc.)
"""

import re
from typing import Dict, Tuple, List, Any, Optional

# Optional imports
try:
    import bibtexparser
    HAS_BIBTEXPARSER = True
except ImportError:
    HAS_BIBTEXPARSER = False

try:
    from pylatexenc.latex2text import LatexNodes2Text
    latex_decoder = LatexNodes2Text()
    HAS_PYLATEXENC = True
except ImportError:
    latex_decoder = None
    HAS_PYLATEXENC = False


# =============================================================================
# PRE-COMPILED REGEX PATTERNS
# =============================================================================

# Pattern: Tìm year chuẩn: year = {2020} hoặc year = "2020"
P_YEAR_KEY = re.compile(r'year\s*=\s*[\{\"]?\s*([12]\d{3})\s*[\}\"]?', re.IGNORECASE)

# Pattern: Tìm số năm 4 chữ số (fallback)
P_YEAR_SIMPLE = re.compile(r'\b(19|20)\d{2}\b')

# Pattern: Parse title từ BibTeX
P_TITLE = re.compile(r'title\s*=\s*[\{"](.*?)(?<!\\)[\}"]', re.IGNORECASE | re.DOTALL)

# Pattern: Parse author từ BibTeX
P_AUTHOR = re.compile(r'author\s*=\s*[\{"](.*?)(?<!\\)[\}"]', re.IGNORECASE | re.DOTALL)

# Pattern: Clean braces và spaces
P_CLEAN_BRACES = re.compile(r'[\{\}]')
P_CLEAN_SPACES = re.compile(r'\s+')


# =============================================================================
# TEXT CLEANING FUNCTIONS
# =============================================================================

def clean_latex(text: str) -> str:
    """
    Clean LaTeX markup từ text.
    
    Args:
        text: Văn bản có thể chứa LaTeX commands
        
    Returns:
        Văn bản đã clean
    """
    if not isinstance(text, str) or not text:
        return ""
    
    try:
        if HAS_PYLATEXENC and latex_decoder:
            text = latex_decoder.latex_to_text(text)
        
        # Remove braces
        text = text.replace('{', '').replace('}', '')
        # Normalize whitespace
        text = " ".join(text.split())
        return text
    except:
        return text


def normalize_id(text: str) -> str:
    """
    Chuẩn hóa ID (DOI, arXiv ID, etc.) để so sánh.
    
    Args:
        text: ID string
        
    Returns:
        ID đã chuẩn hóa
    """
    if not text:
        return ""
    return re.sub(r'[\.\-\/]', '', str(text).lower())


# =============================================================================
# BIBTEX PARSING FUNCTIONS
# =============================================================================

def parse_bibtex_fast(bib_string: str) -> Tuple[str, str]:
    """
    Parse nhanh BibTeX chỉ dùng Regex (không dependency).
    
    Args:
        bib_string: Chuỗi BibTeX raw
        
    Returns:
        Tuple (title, author_string)
    """
    if not isinstance(bib_string, str) or not bib_string:
        return '', ''

    # Tìm Title
    m_title = P_TITLE.search(bib_string)
    raw_title = m_title.group(1) if m_title else ''
    
    # Tìm Author
    m_author = P_AUTHOR.search(bib_string)
    raw_author = m_author.group(1) if m_author else ''
    
    # Clean
    parsed_title = " ".join(raw_title.replace('{', '').replace('}', '').split()) if raw_title else ''
    parsed_author = " ".join(raw_author.replace('{', '').replace('}', '').split()) if raw_author else ''
        
    return parsed_title, parsed_author


def parse_bibtex_smart(bib_string: str) -> Dict[str, Any]:
    """
    Parser thông minh V3: Lấy đủ Title, Author, Year, ID.
    
    Ưu tiên:
    1. Tìm year từ key-value trước
    2. Parse cấu trúc BibTeX (@article, etc.)
    3. Xử lý flat text (\\newblock)
    4. Fallback regex
    
    Args:
        bib_string: Chuỗi BibTeX raw
        
    Returns:
        Dictionary với keys: title, authors, year, extracted_id
    """
    if not bib_string:
        return {"title": "", "authors": [], "year": "", "extracted_id": ""}
    
    parsed_data = {
        "title": "",
        "authors": [],
        "year": "",
        "extracted_id": ""
    }
    
    # --- BƯỚC 1: TÌM NĂM DỰA TRÊN KEY-VALUE ---
    year_match = P_YEAR_KEY.search(bib_string)
    if year_match:
        parsed_data['year'] = year_match.group(1)

    # --- BƯỚC 2: PARSE CẤU TRÚC BIBTEX ---
    if bib_string.strip().startswith('@') and HAS_BIBTEXPARSER:
        try:
            parser = bibtexparser.bparser.BibTexParser(common_strings=True)
            bib_db = bibtexparser.loads(bib_string, parser=parser)
            
            if bib_db.entries:
                entry = bib_db.entries[0]
                
                # Title
                parsed_data['title'] = clean_latex(entry.get('title', ''))
                
                # Author
                raw_authors = entry.get('author', '')
                if raw_authors:
                    parsed_data['authors'] = [
                        clean_latex(a.strip()) 
                        for a in raw_authors.split(' and ')
                    ]
                
                # ID (eprint hoặc doi)
                raw_id = entry.get('eprint', entry.get('doi', ''))
                parsed_data['extracted_id'] = normalize_id(raw_id)
                
                # Year fallback
                if not parsed_data['year']:
                    parsed_data['year'] = entry.get('year', '')
                
                return parsed_data
        except:
            pass

    # --- BƯỚC 3: XỬ LÝ FLAT TEXT (\\newblock) ---
    if r'\newblock' in bib_string:
        try:
            parts = bib_string.split(r'\newblock')
            
            # Author (phần đầu)
            raw_author_str = parts[0].strip()
            if raw_author_str.endswith('.'):
                raw_author_str = raw_author_str[:-1]
            parsed_data['authors'] = [
                clean_latex(a.strip()) 
                for a in raw_author_str.split(',')
            ]

            # Title (phần thứ 2)
            if len(parts) > 1:
                parsed_data['title'] = clean_latex(parts[1].strip())
            
            # Year (từ phần cuối)
            if not parsed_data['year']:
                simple_match = P_YEAR_SIMPLE.search(parts[-1])
                if simple_match:
                    parsed_data['year'] = simple_match.group(0)

            return parsed_data
        except:
            pass
            
    # --- BƯỚC 4: FALLBACK REGEX ---
    if not parsed_data['title']:
        title_match = P_TITLE.search(bib_string)
        if title_match:
            parsed_data['title'] = clean_latex(title_match.group(1))
    
    if not parsed_data['authors']:
        author_match = P_AUTHOR.search(bib_string)
        if author_match:
            raw_authors = author_match.group(1)
            parsed_data['authors'] = [
                clean_latex(a.strip()) 
                for a in raw_authors.split(' and ')
            ]

    # --- BƯỚC 5: LAST RESORT FOR YEAR ---
    if not parsed_data['year']:
        fallback_match = P_YEAR_SIMPLE.search(bib_string)
        if fallback_match:
            parsed_data['year'] = fallback_match.group(0)

    return parsed_data


def parse_bibtex_content(bib_content: str) -> Tuple[str, List[str]]:
    """
    Trích xuất Title và Authors từ chuỗi BibTeX raw.
    
    Args:
        bib_content: Chuỗi BibTeX
        
    Returns:
        Tuple (title, authors_list)
    """
    # Extract Title
    title_match = re.search(r'title\s*=\s*[\{"](.*?)(?<!\\)[\}"]', bib_content, re.I | re.S)
    title = title_match.group(1) if title_match else ""
    title = title.lower().strip() if title else ""
    
    # Extract Authors
    author_match = re.search(r'author\s*=\s*[\{"](.*?)(?<!\\)[\}"]', bib_content, re.I | re.S)
    authors_str = author_match.group(1) if author_match else ""
    
    # Tách author bằng 'and'
    authors = [a.lower().strip() for a in authors_str.split(' and ')] if authors_str else []
    
    return title, authors


# =============================================================================
# BATCH PROCESSING
# =============================================================================

def process_dataframe_bibtex(
    df,
    bib_column: str = 'bib_content',
    prefix: str = 'clean_'
) -> None:
    """
    Parse BibTeX cho toàn bộ DataFrame (inplace).
    
    Args:
        df: DataFrame chứa cột BibTeX content
        bib_column: Tên cột chứa BibTeX
        prefix: Prefix cho các cột output
        
    Side effects:
        Thêm các cột: {prefix}title, {prefix}authors, {prefix}id, {prefix}year, parse_method
    """
    from tqdm import tqdm
    
    results = []
    methods = []
    
    for bib_string in tqdm(df[bib_column], desc="Parsing BibTeX"):
        data = parse_bibtex_smart(bib_string)
        results.append(data)
        
        # Determine parse method
        if bib_string and bib_string.strip().startswith('@'):
            methods.append('bibtex_struct')
        elif r'\newblock' in str(bib_string):
            methods.append('flat_text')
        else:
            methods.append('regex_fallback')
    
    # Add columns
    df[f'{prefix}title'] = [r['title'] for r in results]
    df[f'{prefix}authors'] = [r['authors'] for r in results]
    df[f'{prefix}id'] = [r['extracted_id'] for r in results]
    df[f'{prefix}year'] = [r['year'] for r in results]
    df['parse_method'] = methods
