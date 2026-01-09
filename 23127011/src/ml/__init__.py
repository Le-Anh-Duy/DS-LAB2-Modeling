"""
ML Module - Machine Learning Pipeline for Reference Matching.

Submodule này chứa các utilities cho pipeline ML:
- Feature Engineering
- Data Loading & Transformation
- Data Augmentation (Negative Sampling)
- BibTeX Parsing
"""

# Feature Engineering
from .features import (
    # Text helpers
    normalize_text_basic,
    get_tokens,
    safe_year_diff,
    # Feature extraction
    compute_pairwise_features,
    compute_tfidf_cosine_batch,
    compute_tfidf_cosine_single,
    extract_features_batch,
    # Analysis
    analyze_feature_correlation,
    get_feature_columns,
)

# Data Loading
from .data_loader import (
    # File I/O
    load_json,
    save_json,
    load_pickle,
    save_pickle,
    # Data merging
    merge_partition_files,
    merge_all_partitions,
    # Dataset loading
    deduplicate_list,
    load_dataset_raw,
    load_cleaned_data,
    transform_to_paper_based,
    # Quality checks
    check_data_quality,
    print_data_quality_report,
)

# Data Augmentation
from .augmentation import (
    build_candidate_pools,
    generate_positive_sample,
    generate_negative_samples,
    augment_dataset,
    split_by_partition,
)

# BibTeX Parsing
from .bibtex_parser import (
    clean_latex,
    normalize_id,
    parse_bibtex_fast,
    parse_bibtex_smart,
    parse_bibtex_content,
    process_dataframe_bibtex,
)


__all__ = [
    # Features
    'normalize_text_basic',
    'get_tokens', 
    'safe_year_diff',
    'compute_pairwise_features',
    'compute_tfidf_cosine_batch',
    'compute_tfidf_cosine_single',
    'extract_features_batch',
    'analyze_feature_correlation',
    'get_feature_columns',
    # Data Loading
    'load_json',
    'save_json',
    'load_pickle',
    'save_pickle',
    'merge_partition_files',
    'merge_all_partitions',
    'deduplicate_list',
    'load_dataset_raw',
    'load_cleaned_data',
    'transform_to_paper_based',
    'check_data_quality',
    'print_data_quality_report',
    # Augmentation
    'build_candidate_pools',
    'generate_positive_sample',
    'generate_negative_samples',
    'augment_dataset',
    'split_by_partition',
    # BibTeX
    'clean_latex',
    'normalize_id',
    'parse_bibtex_fast',
    'parse_bibtex_smart',
    'parse_bibtex_content',
    'process_dataframe_bibtex',
]
