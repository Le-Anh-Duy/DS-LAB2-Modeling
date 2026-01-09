"""
Data Augmentation Module - Negative Sampling.

Module chứa các hàm để sinh dữ liệu huấn luyện cho model ML
bằng cách tạo các cặp Positive và Negative samples.
"""

import random
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from tqdm import tqdm


def build_candidate_pools(df: pd.DataFrame) -> tuple:
    """
    Xây dựng Global Pool và Local Pool cho negative sampling.
    
    Args:
        df: DataFrame chứa dữ liệu training (đã clean)
        
    Returns:
        Tuple (global_candidates, local_pool)
        - global_candidates: List tất cả candidates
        - local_pool: Dict {paper_id: [candidates]}
    """
    # Global Pool: Tất cả candidates
    global_candidates = df[[
        'gt_id', 'gt_title', 'gt_authors', 'gt_year', 'paper_id'
    ]].to_dict('records')
    
    # Local Pool: Gom nhóm theo Paper ID
    local_pool = {}
    for item in global_candidates:
        pid = item['paper_id']
        if pid not in local_pool:
            local_pool[pid] = []
        local_pool[pid].append(item)
    
    return global_candidates, local_pool


def generate_positive_sample(row: pd.Series) -> Dict[str, Any]:
    """
    Tạo một positive sample từ row dữ liệu.
    
    Args:
        row: Một dòng dữ liệu từ DataFrame
        
    Returns:
        Dictionary chứa positive sample
    """
    return {
        'bib_title': row['clean_title'],
        'bib_authors': row['clean_authors'],
        'bib_id': row['clean_id'],
        'bib_year': row['clean_year'],
        'cand_id': row['gt_id'],
        'cand_title': row['gt_title'],
        'cand_authors': row['gt_authors'],
        'cand_year': row['gt_year'],
        'label': 1
    }


def generate_negative_samples(
    query_info: Dict[str, Any],
    true_gt_id: str,
    current_paper_id: str,
    local_pool: Dict[str, List],
    global_candidates: List[Dict],
    num_hard_negatives: int = 2,
    num_total_negatives: int = 4,
    max_attempts: int = 50
) -> List[Dict[str, Any]]:
    """
    Sinh negative samples cho một query.
    
    Args:
        query_info: Thông tin query (bib_title, bib_authors, etc.)
        true_gt_id: ID của ground truth thật
        current_paper_id: ID của paper hiện tại
        local_pool: Pool candidates theo paper_id
        global_candidates: Pool tất cả candidates
        num_hard_negatives: Số lượng hard negatives (cùng paper)
        num_total_negatives: Tổng số negatives cần sinh
        max_attempts: Số lần thử tối đa cho easy negatives
        
    Returns:
        List các negative samples
    """
    negatives = []
    
    # 1. Hard Negatives (Local - cùng paper)
    local_candidates = local_pool.get(current_paper_id, [])
    valid_local_cands = [c for c in local_candidates if c['gt_id'] != true_gt_id]
    
    if valid_local_cands:
        k_hard = min(num_hard_negatives, len(valid_local_cands))
        chosen_hard = random.sample(valid_local_cands, k_hard)
        
        for cand in chosen_hard:
            neg_row = query_info.copy()
            neg_row.update({
                'cand_id': cand['gt_id'],
                'cand_title': cand['gt_title'],
                'cand_authors': cand['gt_authors'],
                'cand_year': cand['gt_year'],
                'label': 0
            })
            negatives.append(neg_row)
    
    # 2. Easy Negatives (Global - khác paper)
    needed = num_total_negatives - len(negatives)
    attempts = 0
    
    while needed > 0 and attempts < max_attempts:
        attempts += 1
        cand = random.choice(global_candidates)
        
        if cand['gt_id'] != true_gt_id and cand['paper_id'] != current_paper_id:
            neg_row = query_info.copy()
            neg_row.update({
                'cand_id': cand['gt_id'],
                'cand_title': cand['gt_title'],
                'cand_authors': cand['gt_authors'],
                'cand_year': cand['gt_year'],
                'label': 0
            })
            negatives.append(neg_row)
            needed -= 1
    
    return negatives


def augment_dataset(
    df_source: pd.DataFrame,
    num_negatives: int = 4,
    num_hard_negatives: int = 2,
    random_seed: int = 42,
    verbose: bool = True
) -> pd.DataFrame:
    """
    Sinh dữ liệu augmented (Positive + Negative samples).
    
    Chiến lược:
    - Local Negatives (Hard): Chọn metadata sai từ cùng paper
    - Global Negatives (Easy): Chọn metadata sai từ paper khác
    
    Args:
        df_source: DataFrame nguồn (chứa clean_title, clean_authors, etc.)
        num_negatives: Tổng số negatives cho mỗi positive
        num_hard_negatives: Số hard negatives (cùng paper)
        random_seed: Random seed
        verbose: In thông tin progress
        
    Returns:
        DataFrame đã augmented
    """
    random.seed(random_seed)
    np.random.seed(random_seed)
    
    # Build pools
    global_candidates, local_pool = build_candidate_pools(df_source)
    
    if verbose:
        print(f"📊 Global Pool Size: {len(global_candidates)}")
        print(f"📊 Number of Papers: {len(local_pool)}")
    
    augmented_rows = []
    
    iterator = tqdm(df_source.iterrows(), total=len(df_source), 
                    desc="🚀 Generating samples") if verbose else df_source.iterrows()
    
    for idx, row in iterator:
        # Query info
        query_info = {
            'bib_title': row['clean_title'],
            'bib_authors': row['clean_authors'],
            'bib_id': row['clean_id'],
            'bib_year': row['clean_year']
        }
        
        true_gt_id = row['gt_id']
        current_paper_id = row['paper_id']
        
        # 1. Positive sample
        pos_row = generate_positive_sample(row)
        augmented_rows.append(pos_row)
        
        # 2. Negative samples
        neg_rows = generate_negative_samples(
            query_info=query_info,
            true_gt_id=true_gt_id,
            current_paper_id=current_paper_id,
            local_pool=local_pool,
            global_candidates=global_candidates,
            num_hard_negatives=num_hard_negatives,
            num_total_negatives=num_negatives
        )
        augmented_rows.extend(neg_rows)
    
    # Create DataFrame
    df_augmented = pd.DataFrame(augmented_rows)
    
    # Shuffle
    df_augmented = df_augmented.sample(frac=1, random_state=random_seed).reset_index(drop=True)
    
    if verbose:
        print(f"\n✅ Augmentation completed!")
        print(f"   - Original samples: {len(df_source)}")
        print(f"   - Augmented samples: {len(df_augmented)}")
        print(f"   - Label distribution:\n{df_augmented['label'].value_counts()}")
    
    return df_augmented


def split_by_partition(
    df: pd.DataFrame,
    train_partitions: List[str] = ['train', 'validation'],
    test_partitions: List[str] = ['test']
) -> tuple:
    """
    Chia dữ liệu theo partition.
    
    Args:
        df: DataFrame chứa cột 'partition'
        train_partitions: List partition names cho training
        test_partitions: List partition names cho testing
        
    Returns:
        Tuple (df_train, df_test)
    """
    df_train = df[df['partition'].isin(train_partitions)].copy()
    df_test = df[df['partition'].isin(test_partitions)].copy()
    
    return df_train, df_test
