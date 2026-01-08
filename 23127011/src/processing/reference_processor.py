"""
Reference Processor
===================

Xử lý và trích xuất references từ LaTeX content.
"""

import os
import re
import logging
import bibtexparser
from bibtexparser.bparser import BibTexParser

logger = logging.getLogger(__name__)


class ReferenceProcessor:
    """
    Trích xuất và xử lý references từ LaTeX content.
    
    Hỗ trợ:
    - File .bib (BibTeX database)
    - File .bbl (BibTeX output)
    - Embedded \\bibitem trong .tex
    
    Example:
        >>> processor = ReferenceProcessor(paper_id, version, version_dir)
        >>> content, refs = processor.process_references(flattened_latex)
        >>> print(f"Found {len(refs)} references")
    """
    
    def __init__(self, paper_id: str, version: str, root_dir: str):
        self.paper_id = paper_id
        self.version = version
        self.root_dir = root_dir
        
        self.raw_refs = {} 
        self.MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
        
        # --- PRE-COMPILED REGEX ---
        self.REGEX_CITE = re.compile(
            r'\\cite[a-zA-Z]*\s*(?:\[[^\]]*\])?\s*\{([^}]+)\}', 
            re.IGNORECASE | re.DOTALL
        )
        self.REGEX_THEBIB_BLOCK = re.compile(
            r'\\begin\s*\{thebibliography\}.*?\\end\s*\{thebibliography\}', 
            re.DOTALL | re.IGNORECASE
        )
        self.REGEX_BIBITEM_HEADER = re.compile(
            r'^\\bibitem\s*(?:\[(.*?)\])?\s*\{(.*?)\}\s*(.*)', 
            re.DOTALL | re.IGNORECASE
        )

    def process_references(self, flat_content: str):
        """
        Trích xuất references từ flattened LaTeX content.
        
        Args:
            flat_content: Nội dung LaTeX đã được flatten
            
        Returns:
            Tuple[str, List[dict]]: (content, list of reference dicts)
        """
        # 1. CHUẨN HÓA SƠ BỘ
        norm_content = re.sub(r'\s+', ' ', flat_content)
        
        logger.info(f"Scanning references for {self.version}...")

        # --- BƯỚC 1: TRÍCH XUẤT NHU CẦU (USED KEYS) ---
        used_keys = set()
        for match in self.REGEX_CITE.finditer(norm_content):
            keys_str = match.group(1)
            if keys_str:
                for k in keys_str.split(','):
                    k_clean = k.strip()
                    if k_clean:
                        used_keys.add(k_clean)

        logger.info(f"Found {len(used_keys)} cited keys (Regex engine).")

        # --- BƯỚC 2: VÉT CẠN FILE NGOÀI (.bib/.bbl) ---
        if os.path.exists(self.root_dir):
            with os.scandir(self.root_dir) as entries:
                for entry in entries:
                    if not entry.is_file(): continue
                    
                    fname_lower = entry.name.lower()
                    if fname_lower.endswith('.bib'):
                        self._try_parse_bib(entry.path, entry.name)
                    elif fname_lower.endswith('.bbl'):
                        self._try_parse_bbl(entry.path, entry.name)

        # --- BƯỚC 3: XỬ LÝ EMBEDDED ---
        block_match = self.REGEX_THEBIB_BLOCK.search(norm_content)
        if block_match:
            self._parse_bibitem_content_optimized(block_match.group(0), source_type="embedded_block")
        else:
            if r'\bibitem' in norm_content:
                self._parse_bibitem_content_optimized(norm_content, source_type="embedded_fullscan")

        # --- BƯỚC 4: FILTER ---
        final_refs = []
        if not used_keys:
            logger.warning("No citations found in text. Returning all parsed references as fallback.")
            final_refs = list(self.raw_refs.values())
        else:
            is_wildcard = '*' in used_keys
            for key, ref_obj in self.raw_refs.items():
                if is_wildcard or key in used_keys:
                    final_refs.append(ref_obj)
            
        logger.info(f"Matched {len(final_refs)} references out of {len(self.raw_refs)} total candidates.")
        return flat_content, final_refs

    # --- HELPER METHODS ---

    def _try_parse_bib(self, path: str, filename: str):
        """Parse file .bib"""
        try:
            file_size = os.path.getsize(path)
            if file_size > self.MAX_FILE_SIZE:
                logger.warning(f"Skipping large file: {filename} ({file_size/1024/1024:.2f} MB)")
                return
            
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                parser = BibTexParser(common_strings=True)
                parser.ignore_nonstandard_types = True
                parser.homogenise_fields = False
                db = bibtexparser.load(f, parser=parser)
                
            count_new = 0
            for entry in db.entries:
                key = entry.get('ID', '').strip()
                if key and key not in self.raw_refs:
                    self.raw_refs[key] = {
                        "key": key,
                        "raw_text": self._dict_to_bibtex_string(entry),
                        "type": f"bib_{entry.get('ENTRYTYPE', 'misc').lower()}",
                        "source": filename
                    }
                    count_new += 1
            if count_new > 0:
                logger.debug(f"Parsed {count_new} entries from {filename}")

        except Exception as e:
            logger.warning(f"Failed to parse .bib file {filename}: {str(e)}")

    def _try_parse_bbl(self, path: str, filename: str):
        """Parse file .bbl"""
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            norm_content = re.sub(r'\s+', ' ', content)
            self._parse_bibitem_content_optimized(norm_content, source_type=filename)
        except Exception as e:
            logger.warning(f"Failed to parse .bbl file {filename}: {str(e)}")

    def _parse_bibitem_content_optimized(self, text: str, source_type: str = "bibitem"):
        """Parse \\bibitem entries từ text."""
        chunks = re.split(r'\\bibitem', text, flags=re.IGNORECASE)
        if len(chunks) < 2: return 

        count = 0
        for chunk in chunks[1:]:
            reconstructed = r'\bibitem' + chunk 
            match = self.REGEX_BIBITEM_HEADER.match(reconstructed)
            if match:
                key = match.group(2).strip()
                content = match.group(3)
                if r'\end' in content:
                    content = content.split(r'\end')[0]
                content = content.strip()

                if key and key not in self.raw_refs:
                    self.raw_refs[key] = {
                        "key": key,
                        "raw_text": content,
                        "type": "bibitem",
                        "source": source_type
                    }
                    count += 1
        
        if count > 0:
             logger.debug(f"Parsed {count} items from {source_type}")

    def _dict_to_bibtex_string(self, entry: dict) -> str:
        """Chuyển dict entry thành BibTeX string."""
        lines = [f"@{entry.get('ENTRYTYPE', 'misc')}{{{entry.get('ID', '')},"]
        lines.extend([f"  {k} = {{{v}}}," for k, v in entry.items() if k not in ['ENTRYTYPE', 'ID']])
        lines.append("}")
        return "\n".join(lines)
