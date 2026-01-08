"""
Reference Matcher
=================

TF-IDF based reference matching với ground truth.
"""

import numpy as np
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from typing import Dict, Any, Optional


class ReferenceMatcher:
    """
    So khớp extracted references với ground truth sử dụng TF-IDF cosine similarity.
    
    Attributes:
        threshold: Ngưỡng score tối thiểu để chấp nhận match (mặc định: 0.55)
        
    Example:
        >>> matcher = ReferenceMatcher(threshold=0.55)
        >>> matcher.fit(ground_truth_refs)
        >>> result = matcher.match(extracted_ref_text)
        >>> print(result['score'], result['id'])
    """
    
    def __init__(self, threshold: float = 0.55):
        self.threshold = threshold
        self.vectorizer = TfidfVectorizer(
            analyzer='word', 
            ngram_range=(1, 2), 
            stop_words='english',
            token_pattern=r'(?u)\b\w\w+\b' 
        )
        self.candidates_meta = [] 
        self.title_lookup = {}
        self.is_fitted = False
        self.tfidf_matrix = None

    def _clean_text(self, text: str) -> str:
        """Làm sạch text chuyên dụng cho BibTeX."""
        if not text: return ""
        text = text.lower()
        
        bibtex_keys = [
            r'text\s*=', r'title\s*=', r'author\s*=', r'year\s*=', r'journal\s*=', 
            r'volume\s*=', r'pages\s*=', r'doi\s*=', r'eprint\s*=', 
            r'archiveprefix\s*=', r'primaryclass\s*=', r'month\s*=', 
            r'number\s*=', r'publisher\s*=', r'abstract\s*=', 
            r'address\s*=', r'url\s*=', r'urldate\s*=', r'issn\s*=',
            r'keywords\s*=', r'copyright\s*=', r'language\s*=',
            r'@article', r'@misc', r'@book', r'@inproceedings', 
            r'@unpublished', r'@techreport'
        ]
        for key in bibtex_keys:
            text = re.sub(key, ' ', text)

        text = re.sub(r'[\{\}\"\'\\=\,\:\;\(\)\[\]]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _extract_year(self, text: str) -> Optional[int]:
        """Trích xuất năm từ text."""
        match = re.search(r'\b(19|20)\d{2}\b', text)
        if match:
            return int(match.group(0))
        return None

    def _extract_bibtex_title(self, raw_text: str) -> Optional[str]:
        """Trích xuất title từ BibTeX entry."""
        match = re.search(r'title\s*=\s*[\{\"](.*?)(?=}?,|[\}\"]\s*$)', raw_text, re.IGNORECASE | re.DOTALL)
        if match:
            raw_title = match.group(1)
            clean = raw_title.replace('{', '').replace('}', '').replace('\n', ' ').strip()
            return clean
        return None

    def fit(self, ground_truth_refs: Dict[str, Any]):
        """
        Index ground truth references để chuẩn bị matching.
        
        Args:
            ground_truth_refs: Dict với key là arxiv_id và value là metadata dict
        """
        corpus = []
        self.candidates_meta = []
        self.title_lookup = {} 

        if not ground_truth_refs:
            return

        for arxiv_id, meta in ground_truth_refs.items():
            raw_title = meta.get('title', '') or ''
            clean_title = self._clean_text(raw_title)
            
            authors_list = meta.get('authors', [])
            authors = " ".join(authors_list) if isinstance(authors_list, list) else str(authors_list or '')
            clean_authors = self._clean_text(authors)
            
            raw_date = meta.get('submission_date', '') or meta.get('year', '')
            year = self._extract_year(str(raw_date))
            
            # Metadata object để trả về
            meta_obj = {"id": arxiv_id, "meta": meta, "year": year}

            # 1. Exact Match Lookup
            if len(clean_title) > 5:
                self.title_lookup[clean_title] = meta_obj

            # 2. TF-IDF Corpus
            text_rep = f"{clean_title} {clean_title} {clean_authors} {year if year else ''}"
            corpus.append(text_rep)
            self.candidates_meta.append(meta_obj)

        if corpus:
            try:
                self.tfidf_matrix = self.vectorizer.fit_transform(corpus)
                self.is_fitted = True
            except ValueError:
                pass

    def match(self, raw_ref_text: str) -> Optional[Dict[str, Any]]:
        """
        Match một extracted reference với ground truth.
        
        Args:
            raw_ref_text: Raw text của reference cần match
            
        Returns:
            Dict với keys: 'id', 'meta', 'year', 'score'
            Hoặc None nếu không tìm thấy match phù hợp
        """
        if not self.is_fitted:
            return None
        
        # --- BƯỚC 1: EXACT TITLE MATCH ---
        extracted_title = self._extract_bibtex_title(raw_ref_text)
        if extracted_title:
            clean_extracted_title = self._clean_text(extracted_title)
            if clean_extracted_title in self.title_lookup:
                result = self.title_lookup[clean_extracted_title].copy()
                result['score'] = 1.0 
                return result

        # --- BƯỚC 2: TF-IDF MATCH ---
        clean_raw_text = self._clean_text(raw_ref_text)
        query_vec = self.vectorizer.transform([clean_raw_text])
        
        scores = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
        top_k_indices = np.argsort(scores)[::-1][:3]
        
        raw_year = self._extract_year(raw_ref_text)

        for idx in top_k_indices:
            score = float(scores[idx])
            candidate = self.candidates_meta[idx]
            cand_year = candidate['year']

            if score < self.threshold:
                continue

            # Year Validation
            if raw_year and cand_year:
                if abs(raw_year - cand_year) > 2:
                    continue 

            result = candidate.copy()
            result['score'] = score
            return result

        return None
