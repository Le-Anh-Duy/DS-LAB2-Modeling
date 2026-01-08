"""
LaTeX Paper Processing Pipeline
===============================

Pipeline xử lý và trích xuất dữ liệu từ LaTeX papers.

Modules chính:
- pipeline: Điều phối toàn bộ quá trình xử lý
- parser: Phân tích cấu trúc LaTeX (flatten, build tree, process content)
- processing: Xử lý và loại bỏ trùng lặp (dedup)
- matching: So khớp reference với ground truth
- utils: Tiện ích hỗ trợ (I/O, cleaner)

Sử dụng nhanh:
    from src import run_full_pipeline
    run_full_pipeline(data_raw="path/to/raw", data_output="path/to/output")

Hoặc từng phase riêng:
    from src import run_processing_pipeline, run_matching_pipeline, run_merge_pipeline
"""

# =============================================================================
# PHASE 1: Pre-processing & Parsing Pipeline
# =============================================================================
from .pipeline import (
    run_processing_pipeline,
    process_single_paper
)

# =============================================================================
# PHASE 2: Reference Matching Pipeline  
# =============================================================================
from .run_matching import run_matching_pipeline

# =============================================================================
# PHASE 3: Dataset Merging
# =============================================================================
from .merge_labels import (
    load_selected_papers,
    save_json
)

# =============================================================================
# Core Components (for advanced usage)
# =============================================================================
from .parser import (
    LatexFlattener,
    LatexStructureBuilder, 
    LatexContentProcessor,
    find_root_tex_file
)

# Import từ submodules đã refactor
from .processing import (
    ReferenceProcessor,
    ReferenceDeduplicator,
    ContentDeduplicator,
    replace_citations_in_text
)

from .matching import ReferenceMatcher

# =============================================================================
# Convenience Function: Run Full Pipeline
# =============================================================================
def run_full_pipeline(
    data_raw: str,
    data_output: str,
    parallel: bool = True,
    max_workers: int = None,
    run_matching: bool = True,
    verbose: bool = True
) -> dict:
    """
    Chạy toàn bộ pipeline từ đầu đến cuối.
    
    Args:
        data_raw: Đường dẫn thư mục chứa LaTeX papers thô
        data_output: Đường dẫn thư mục xuất kết quả
        parallel: Sử dụng xử lý song song (mặc định: True)
        max_workers: Số luồng tối đa (mặc định: số CPU)
        run_matching: Chạy phase matching sau khi xử lý (mặc định: True)
        verbose: In thông tin tiến trình (mặc định: True)
    
    Returns:
        dict: Thống kê kết quả xử lý
            - processed: Số papers đã xử lý
            - matched: Số papers đã match (nếu run_matching=True)
            - output_path: Đường dẫn output
    
    Example:
        >>> from src import run_full_pipeline
        >>> result = run_full_pipeline(
        ...     data_raw="./data_raw",
        ...     data_output="./data_output",
        ...     parallel=True
        ... )
        >>> print(f"Processed {result['processed']} papers")
    """
    import os
    
    stats = {
        "processed": 0,
        "matched": 0,
        "output_path": data_output
    }
    
    if verbose:
        print("=" * 60)
        print("🚀 PHASE 1: Pre-processing & Parsing")
        print("=" * 60)
    
    # Phase 1: Processing
    run_processing_pipeline(
        data_raw_path=data_raw,
        data_output_path=data_output,
        parallel=parallel,
        max_workers=max_workers
    )
    
    # Count processed
    if os.path.exists(data_output):
        stats["processed"] = len([
            f for f in os.listdir(data_output) 
            if os.path.isdir(os.path.join(data_output, f))
        ])
    
    if verbose:
        print(f"\n✅ Phase 1 Complete: {stats['processed']} papers processed")
    
    # Phase 2: Matching (optional)
    if run_matching:
        if verbose:
            print("\n" + "=" * 60)
            print("🔍 PHASE 2: Reference Matching")
            print("=" * 60)
        
        run_matching_pipeline(data_output)
        
        # Count matched
        for folder in os.listdir(data_output):
            labels_path = os.path.join(data_output, folder, "labels.json")
            if os.path.exists(labels_path):
                stats["matched"] += 1
        
        if verbose:
            print(f"\n✅ Phase 2 Complete: {stats['matched']} papers matched")
    
    if verbose:
        print("\n" + "=" * 60)
        print("🎉 PIPELINE COMPLETE!")
        print(f"   Output: {data_output}")
        print("=" * 60)
    
    return stats


# =============================================================================
# Version Info
# =============================================================================
__version__ = "1.0.0"
__author__ = "23127011"

__all__ = [
    # Main pipeline functions
    "run_full_pipeline",
    "run_processing_pipeline",
    "run_matching_pipeline",
    
    # Core processing
    "process_single_paper",
    
    # Parser components
    "LatexFlattener",
    "LatexStructureBuilder",
    "LatexContentProcessor",
    "find_root_tex_file",
    
    # Processors
    "ReferenceProcessor",
    "ReferenceMatcher",
    
    # Deduplicators
    "ReferenceDeduplicator",
    "ContentDeduplicator",
    "replace_citations_in_text",
    
    # Merge utilities
    "load_selected_papers",
    "save_json",
]
