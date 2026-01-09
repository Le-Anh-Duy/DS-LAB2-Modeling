"""
Data Loading & Transformation Module.

Module chứa các hàm để load, merge, và transform dữ liệu
từ các file JSON/PKL phục vụ cho pipeline ML.
"""

import json
import os
import re
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from collections import defaultdict


# =============================================================================
# FILE I/O
# =============================================================================

def load_json(filepath: str) -> Any:
    """
    Load file JSON.
    
    Args:
        filepath: Đường dẫn tới file JSON
        
    Returns:
        Dữ liệu đã parse từ JSON
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Không tìm thấy file: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(data: Any, filepath: str, indent: int = 4) -> None:
    """
    Lưu dữ liệu ra file JSON.
    
    Args:
        data: Dữ liệu cần lưu
        filepath: Đường dẫn file output
        indent: Số spaces để indent
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)


def load_pickle(filepath: str) -> pd.DataFrame:
    """
    Load file Pickle thành DataFrame.
    
    Args:
        filepath: Đường dẫn tới file .pkl
        
    Returns:
        DataFrame
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Không tìm thấy file: {filepath}")
    
    return pd.read_pickle(filepath)


def save_pickle(df: pd.DataFrame, filepath: str) -> None:
    """
    Lưu DataFrame ra file Pickle.
    
    Args:
        df: DataFrame cần lưu
        filepath: Đường dẫn file output
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    df.to_pickle(filepath)


# =============================================================================
# DATA MERGING
# =============================================================================

def merge_partition_files(
    partition_path: str,
    output_filename: str = 'labels.json'
) -> Tuple[int, int]:
    """
    Gộp manual.json và auto.json thành labels.json cho một partition.
    
    Args:
        partition_path: Đường dẫn tới thư mục partition (train/validation/test)
        output_filename: Tên file output
        
    Returns:
        Tuple (count_manual, count_auto)
    """
    manual_path = os.path.join(partition_path, 'manual.json')
    auto_path = os.path.join(partition_path, 'auto.json')
    target_path = os.path.join(partition_path, output_filename)
    
    merged_data = []
    count_manual = 0
    count_auto = 0
    
    # Đọc Manual Data (Ưu tiên)
    if os.path.exists(manual_path):
        try:
            with open(manual_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    merged_data.extend(data)
                    count_manual = len(data)
        except Exception as e:
            print(f"❌ Lỗi đọc file Manual: {e}")

    # Đọc Auto Data
    if os.path.exists(auto_path):
        try:
            with open(auto_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    merged_data.extend(data)
                    count_auto = len(data)
        except Exception as e:
            print(f"❌ Lỗi đọc file Auto: {e}")
    
    # Ghi output
    if merged_data:
        with open(target_path, 'w', encoding='utf-8') as f:
            json.dump(merged_data, f, ensure_ascii=False, indent=4)
    
    return count_manual, count_auto


def merge_all_partitions(
    dataset_dir: str,
    partitions: List[str] = ['train', 'validation', 'test']
) -> Dict[str, Dict[str, int]]:
    """
    Gộp files cho tất cả các partitions.
    
    Args:
        dataset_dir: Thư mục gốc chứa dataset
        partitions: Danh sách các partition names
        
    Returns:
        Dictionary thống kê kết quả
    """
    stats = {}
    
    for partition in partitions:
        partition_path = os.path.join(dataset_dir, partition)
        
        if not os.path.exists(partition_path):
            print(f"⚠️ Không tìm thấy: {partition_path}")
            stats[partition] = {'manual': 0, 'auto': 0}
            continue
        
        manual_count, auto_count = merge_partition_files(partition_path)
        stats[partition] = {'manual': manual_count, 'auto': auto_count}
        
        print(f"✅ [{partition.upper()}] Manual: {manual_count}, Auto: {auto_count}")
    
    return stats


# =============================================================================
# DATA LOADING FOR ML
# =============================================================================

def deduplicate_list(input_list: List) -> List:
    """
    Loại bỏ duplicate trong list, giữ nguyên thứ tự.
    
    Args:
        input_list: List đầu vào
        
    Returns:
        List đã dedupe
    """
    if not isinstance(input_list, list) or not input_list:
        return []
    return list(dict.fromkeys([str(x).strip() for x in input_list if str(x).strip()]))


def load_dataset_raw(
    dataset_dir: str,
    partitions: List[str] = ['train', 'validation', 'test'],
    file_types: List[str] = ['manual.json', 'auto.json']
) -> pd.DataFrame:
    """
    Load raw dataset từ các file JSON.
    
    Args:
        dataset_dir: Thư mục gốc chứa dataset
        partitions: Danh sách các partition names
        file_types: Danh sách các file types cần load
        
    Returns:
        DataFrame chứa tất cả samples
    """
    all_samples = []
    
    for partition in partitions:
        partition_path = os.path.join(dataset_dir, partition)
        
        for file_type in file_types:
            file_path = os.path.join(partition_path, file_type)
            
            if not os.path.exists(file_path):
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for item in data:
                    gt = item.get('ground_truth')
                    if not gt:
                        continue
                    
                    gt_authors = gt.get('authors', [])
                    if not isinstance(gt_authors, list):
                        gt_authors = []
                    
                    gt_authors = deduplicate_list(gt_authors)
                    if not gt_authors:
                        continue
                    
                    # Extract year from submission_date
                    gt_date = gt.get('submission_date', '')
                    gt_year = str(gt_date)[:4] if gt_date and len(str(gt_date)) >= 4 else ''
                    
                    all_samples.append({
                        'partition': partition,
                        'source_type': file_type.replace('.json', ''),
                        'key': item.get('key'),
                        'paper_id': item.get('source_paper_id', gt.get('id', 'unknown')),
                        'bib_content': item.get('content', ''),
                        'gt_id': gt.get('id'),
                        'gt_title': gt.get('title', ''),
                        'gt_authors': gt_authors,
                        'gt_year': gt_year
                    })
                    
            except Exception as e:
                print(f"❌ Lỗi đọc {file_path}: {e}")
    
    return pd.DataFrame(all_samples)


def load_cleaned_data(filepath: str) -> pd.DataFrame:
    """
    Load dữ liệu đã cleaned từ file pickle.
    
    Args:
        filepath: Đường dẫn tới file .pkl
        
    Returns:
        DataFrame
    """
    return load_pickle(filepath)


# =============================================================================
# DATA TRANSFORMATION FOR RANKING
# =============================================================================

def transform_to_paper_based(
    raw_data: List[Dict],
    parse_func: callable
) -> Dict[str, Dict]:
    """
    Chuyển đổi dữ liệu từ flat list sang cấu trúc Paper-based.
    
    Args:
        raw_data: List các entries từ labels.json
        parse_func: Hàm parse BibTeX content
        
    Returns:
        Dictionary {paper_id: {'queries': [...], 'candidates': {...}}}
    """
    papers_db = defaultdict(lambda: {'queries': [], 'candidates': {}})
    
    for item in raw_data:
        paper_id = item.get('source_paper_id', 'unknown_paper')
        
        # Parse BibTeX
        bib_content = item.get('content', '')
        p_data = parse_func(bib_content)
        
        # Query object
        query_obj = {
            'key': item.get('key'),
            'bib_title': p_data.get('title', ''),
            'bib_authors': p_data.get('authors', []),
            'bib_id': p_data.get('extracted_id', ''),
            'bib_year': p_data.get('year', ''),
            'true_id': item.get('ground_truth', {}).get('id')
        }
        papers_db[paper_id]['queries'].append(query_obj)
        
        # Candidate pool
        gt = item.get('ground_truth', {})
        cand_id = gt.get('id')
        
        if cand_id and cand_id not in papers_db[paper_id]['candidates']:
            cand_authors = gt.get('authors', [])
            gt_date = gt.get('submission_date', '')
            gt_year = str(gt_date)[:4] if gt_date and len(str(gt_date)) >= 4 else ''
            
            papers_db[paper_id]['candidates'][cand_id] = {
                'cand_id': cand_id,
                'cand_title': gt.get('title', '').lower().strip(),
                'cand_authors': [str(a).lower().strip() for a in cand_authors],
                'cand_year': gt_year
            }
    
    return dict(papers_db)


# =============================================================================
# DATA QUALITY CHECKS
# =============================================================================

def check_data_quality(df: pd.DataFrame) -> Dict[str, int]:
    """
    Kiểm tra chất lượng dữ liệu.
    
    Args:
        df: DataFrame cần kiểm tra
        
    Returns:
        Dictionary chứa các thống kê quality
    """
    stats = {}
    
    # Ground Truth checks
    if 'gt_title' in df.columns:
        stats['missing_gt_title'] = df[df['gt_title'].str.strip() == ''].shape[0]
    
    if 'gt_authors' in df.columns:
        stats['empty_gt_authors'] = df[df['gt_authors'].apply(
            lambda x: len(x) == 0 if isinstance(x, list) else True
        )].shape[0]
    
    # BibTeX checks
    if 'bib_title' in df.columns:
        stats['missing_bib_title'] = df[df['bib_title'].str.strip() == ''].shape[0]
    
    if 'bib_author' in df.columns:
        stats['missing_bib_author'] = df[df['bib_author'].str.strip() == ''].shape[0]
    
    if 'clean_title' in df.columns:
        stats['missing_clean_title'] = df[df['clean_title'].str.strip() == ''].shape[0]
    
    return stats


def print_data_quality_report(df: pd.DataFrame) -> None:
    """
    In báo cáo chất lượng dữ liệu.
    
    Args:
        df: DataFrame cần kiểm tra
    """
    stats = check_data_quality(df)
    
    print("=== BÁO CÁO CHẤT LƯỢNG DỮ LIỆU ===")
    for key, value in stats.items():
        print(f"  {key}: {value} mẫu")
    print(f"  Total samples: {len(df)}")
