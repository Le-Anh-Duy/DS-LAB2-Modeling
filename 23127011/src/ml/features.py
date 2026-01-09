"""
Feature Engineering Module cho Reference Matching.

Module chứa các hàm trích xuất đặc trưng từ cặp (Query, Candidate)
để phục vụ cho việc huấn luyện và đánh giá mô hình ML.
"""

import re
import numpy as np
import pandas as pd
from fuzzywuzzy import fuzz
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from typing import Dict, List, Any, Optional, Set


# =============================================================================
# TEXT NORMALIZATION HELPERS
# =============================================================================

def normalize_text_basic(text: Any) -> str:
    """
    Chuẩn hóa cơ bản text để tính toán khoảng cách.
    
    Args:
        text: Văn bản đầu vào (có thể là bất kỳ kiểu nào)
        
    Returns:
        Chuỗi đã được lowercase và strip
    """
    if not isinstance(text, str):
        return ""
    return str(text).lower().strip()


def get_tokens(text_list_or_str: Any) -> Set[str]:
    """
    Chuyển đổi text hoặc list text thành set các từ đơn (tokens).
    
    Args:
        text_list_or_str: Có thể là string hoặc list of strings
        
    Returns:
        Set các tokens đã được chuẩn hóa
    """
    if isinstance(text_list_or_str, list):
        text = " ".join([str(t) for t in text_list_or_str])
    else:
        text = str(text_list_or_str)
    
    # Bỏ dấu câu, giữ lại chữ số và chữ cái
    text = re.sub(r'[^\w\s]', '', text.lower())
    return set(text.split())


def safe_year_diff(y1: Any, y2: Any) -> int:
    """
    Tính khoảng cách năm, xử lý lỗi nếu thiếu dữ liệu.
    
    Args:
        y1: Năm thứ nhất
        y2: Năm thứ hai
        
    Returns:
        Khoảng cách năm (0-10), hoặc -1 nếu không xác định được
    """
    try:
        # Lấy 4 số đầu tiên tìm thấy làm năm
        m1 = re.search(r'\d{4}', str(y1))
        m2 = re.search(r'\d{4}', str(y2))
        
        if m1 and m2:
            val1 = int(m1.group(0))
            val2 = int(m2.group(0))
            diff = abs(val1 - val2)
            # Clip khoảng cách để tránh outlier quá lớn
            return min(diff, 10)
        return -1  # Giá trị missing indicator
    except:
        return -1


# =============================================================================
# FEATURE EXTRACTION
# =============================================================================

def compute_pairwise_features(row: Dict[str, Any]) -> Dict[str, float]:
    """
    Tính toán các features cho một cặp (Query, Candidate).
    
    Args:
        row: Dictionary chứa thông tin của cặp với các key:
            - bib_title, bib_authors, bib_id, bib_year (Query)
            - cand_title, cand_authors, cand_id, cand_year (Candidate)
            
    Returns:
        Dictionary chứa các feature values
    """
    feats = {}
    
    # --- A. UNPACK DATA ---
    q_tit = normalize_text_basic(row.get('bib_title', ''))
    q_auth_list = row.get('bib_authors', [])
    q_id = normalize_text_basic(row.get('bib_id', ''))
    q_year = str(row.get('bib_year', ''))
    
    c_tit = normalize_text_basic(row.get('cand_title', ''))
    c_auth_list = row.get('cand_authors', [])
    c_id = normalize_text_basic(row.get('cand_id', ''))
    c_year = str(row.get('cand_year', ''))
    
    # Chuyển list author thành string để dùng fuzzy match
    q_auth_str = " ".join(q_auth_list) if isinstance(q_auth_list, list) else str(q_auth_list)
    c_auth_str = " ".join(c_auth_list) if isinstance(c_auth_list, list) else str(c_auth_list)

    # --- B. ID FEATURES (GOLDEN FEATURE) ---
    id_score = 0.0
    if q_id and c_id:
        clean_q = re.sub(r'[^a-z0-9]', '', q_id)
        clean_c = re.sub(r'[^a-z0-9]', '', c_id)
        if clean_q == clean_c:
            id_score = 1.0
        elif clean_q in clean_c or clean_c in clean_q:
            id_score = 0.8
    feats['feat_id_match'] = id_score

    # --- C. TITLE FEATURES ---
    feats['feat_title_fuzzy'] = fuzz.ratio(q_tit, c_tit) / 100.0
    feats['feat_title_sort'] = fuzz.token_sort_ratio(q_tit, c_tit) / 100.0
    feats['feat_title_partial'] = fuzz.partial_ratio(q_tit, c_tit) / 100.0
    
    # Feature: Kiểm tra xem Title query có nằm trọn trong Candidate không
    feats['feat_title_contain'] = 1.0 if (q_tit and c_tit and (q_tit in c_tit or c_tit in q_tit)) else 0.0

    len_q = len(q_tit)
    len_c = len(c_tit)
    feats['feat_title_len_diff'] = abs(len_q - len_c) / max(len_q, len_c, 1)

    # --- D. AUTHOR FEATURES ---
    q_tokens = get_tokens(q_auth_list)
    c_tokens = get_tokens(c_auth_list)
    
    # Jaccard similarity
    if q_tokens and c_tokens:
        inter = len(q_tokens.intersection(c_tokens))
        union = len(q_tokens.union(c_tokens))
        feats['feat_auth_jaccard'] = inter / union
        feats['feat_auth_overlap'] = inter
    else:
        feats['feat_auth_jaccard'] = 0.0
        feats['feat_auth_overlap'] = 0
        
    # Author Fuzzy Sort (xử lý: "Bengio, Y." vs "Yoshua Bengio")
    feats['feat_auth_token_sort'] = fuzz.token_sort_ratio(q_auth_str, c_auth_str) / 100.0
        
    # First Author Match
    try:
        a1_q = str(q_auth_list[0]).split()[0].lower() if len(q_auth_list) > 0 else ""
        a1_c = str(c_auth_list[0]).split()[0].lower() if len(c_auth_list) > 0 else ""
        feats['feat_first_auth_match'] = 1.0 if (a1_q and a1_c and a1_q[:3] == a1_c[:3]) else 0.0
    except:
        feats['feat_first_auth_match'] = 0.0
        
    # --- E. YEAR FEATURES ---
    feats['feat_year_diff'] = safe_year_diff(q_year, c_year)
    feats['feat_year_match'] = 1.0 if (feats['feat_year_diff'] == 0) else 0.0

    return feats


def compute_tfidf_cosine_batch(
    df: pd.DataFrame,
    query_col: str = 'bib_title',
    cand_col: str = 'cand_title'
) -> np.ndarray:
    """
    Tính TF-IDF Cosine Similarity cho batch dữ liệu.
    
    Args:
        df: DataFrame chứa các cặp
        query_col: Tên cột chứa query title
        cand_col: Tên cột chứa candidate title
        
    Returns:
        Array các giá trị cosine similarity
    """
    # Chuẩn bị Corpus
    all_titles = pd.concat([df[query_col], df[cand_col]]).astype(str).unique()
    
    # Sử dụng n-gram ký tự để bắt được cả lỗi chính tả nhỏ
    tfidf_vec = TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 4), min_df=2)
    tfidf_vec.fit(all_titles)
    
    # Transform dữ liệu
    q_matrix = tfidf_vec.transform(df[query_col].astype(str))
    c_matrix = tfidf_vec.transform(df[cand_col].astype(str))
    
    # Tính Cosine Similarity (Row-to-Row)
    cosine_sims = np.array(q_matrix.multiply(c_matrix).sum(axis=1)).flatten()
    
    return cosine_sims


def compute_tfidf_cosine_single(query: str, candidate: str) -> float:
    """
    Tính TF-IDF Cosine Similarity cho một cặp đơn lẻ.
    
    Args:
        query: Query title
        candidate: Candidate title
        
    Returns:
        Cosine similarity score
    """
    try:
        if query and candidate:
            vec = TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 4))
            tfidf = vec.fit_transform([query, candidate])
            return cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0]
        return 0.0
    except:
        return 0.0


def extract_features_batch(
    df: pd.DataFrame,
    include_tfidf: bool = True
) -> pd.DataFrame:
    """
    Trích xuất features cho toàn bộ DataFrame.
    
    Args:
        df: DataFrame chứa các cặp (Query, Candidate)
        include_tfidf: Có tính TF-IDF cosine hay không
        
    Returns:
        DataFrame chỉ chứa các cột feature
    """
    from tqdm import tqdm
    tqdm.pandas()
    
    # Tính features cơ bản (row-by-row)
    print("🚀 Đang tính toán các Features cơ bản...")
    basic_features_df = df.progress_apply(
        lambda row: pd.Series(compute_pairwise_features(row)), 
        axis=1
    )
    
    # Tính TF-IDF Cosine Similarity (Vectorized)
    if include_tfidf:
        print("🚀 Đang tính toán TF-IDF Cosine Similarity...")
        basic_features_df['feat_title_tfidf_cosine'] = compute_tfidf_cosine_batch(df)
    
    return basic_features_df


# =============================================================================
# FEATURE ANALYSIS
# =============================================================================

def analyze_feature_correlation(
    df_features: pd.DataFrame,
    label_col: str = 'label'
) -> pd.Series:
    """
    Phân tích tương quan giữa features và label.
    
    Args:
        df_features: DataFrame chứa features và label
        label_col: Tên cột label
        
    Returns:
        Series chứa correlation với label, sorted descending
    """
    feature_cols = [c for c in df_features.columns if c.startswith('feat_')]
    
    if label_col not in df_features.columns:
        raise ValueError(f"Column '{label_col}' not found in DataFrame")
    
    corr_matrix = df_features[feature_cols + [label_col]].corr()
    return corr_matrix[label_col].sort_values(ascending=False)


def get_feature_columns(df: pd.DataFrame) -> List[str]:
    """
    Lấy danh sách các cột feature từ DataFrame.
    
    Args:
        df: DataFrame chứa features
        
    Returns:
        List tên các cột feature
    """
    return [c for c in df.columns if c.startswith('feat_')]
