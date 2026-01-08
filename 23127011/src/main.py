#!/usr/bin/env python
"""
LaTeX Paper Processing Pipeline - CLI Entry Point
==================================================

Chạy pipeline từ command line:

    # Chạy full pipeline (xử lý + matching)
    python -m src.main --raw ./data_raw --output ./data_output

    # Chỉ chạy phase 1 (xử lý)
    python -m src.main --raw ./data_raw --output ./data_output --no-matching

    # Chạy song song với 8 threads
    python -m src.main --raw ./data_raw --output ./data_output --parallel --workers 8

    # Chỉ chạy matching (đã có data processed)
    python -m src.main --output ./data_output --matching-only

    # Merge labels thành dataset
    python -m src.main --merge --yymm 2403 --limit 50
"""

import argparse
import os
import sys

def get_project_paths():
    """Lấy đường dẫn project root từ vị trí file hiện tại."""
    current_file = os.path.abspath(__file__)
    src_dir = os.path.dirname(current_file)
    student_dir = os.path.dirname(src_dir)
    project_root = os.path.dirname(student_dir)
    return {
        "src": src_dir,
        "student": student_dir,
        "project": project_root,
        "data_raw_default": os.path.join(project_root, "data_raw"),
        "data_output_default": os.path.join(project_root, "data_output"),
        "dataset_final": os.path.join(project_root, "dataset_final")
    }


def cmd_process(args):
    """Chạy Phase 1: Pre-processing & Parsing."""
    from .pipeline import run_processing_pipeline
    
    print(f"📂 Input:  {args.raw}")
    print(f"📂 Output: {args.output}")
    print(f"⚙️  Parallel: {args.parallel} | Workers: {args.workers or 'auto'}")
    print()
    
    run_processing_pipeline(
        data_raw_path=args.raw,
        data_output_path=args.output,
        parallel=args.parallel,
        max_workers=args.workers
    )
    print("✅ Phase 1 Complete!")


def cmd_matching(args):
    """Chạy Phase 2: Reference Matching."""
    from .run_matching import run_matching_pipeline
    
    print(f"📂 Data Output: {args.output}")
    print()
    
    run_matching_pipeline(args.output)
    print("✅ Phase 2 Complete!")


def cmd_full(args):
    """Chạy Full Pipeline (Phase 1 + Phase 2)."""
    from . import run_full_pipeline
    
    result = run_full_pipeline(
        data_raw=args.raw,
        data_output=args.output,
        parallel=args.parallel,
        max_workers=args.workers,
        run_matching=not args.no_matching,
        verbose=True
    )
    
    print(f"\n📊 Summary:")
    print(f"   Processed: {result['processed']} papers")
    print(f"   Matched:   {result['matched']} papers")


def cmd_merge(args):
    """Chạy Phase 3: Merge Labels."""
    from .merge_labels import INPUT_DIR_PATH, OUTPUT_DIR
    import json
    import random
    
    # Override paths nếu được chỉ định
    input_dir = args.input or INPUT_DIR_PATH
    output_dir = args.output_dataset or OUTPUT_DIR
    
    print(f"📂 Input:  {input_dir}")
    print(f"📂 Output: {output_dir}")
    print(f"🔑 Prefix: {args.yymm}")
    
    if args.limit:
        print(f"🎲 Mode: Random Limit ({args.limit})")
    elif args.range:
        print(f"✂️  Mode: Range [{args.range[0]} -> {args.range[1]}]")
    else:
        print("🚀 Mode: Full Dataset")
    
    # Import và chạy logic merge
    # (Simplified version - full logic đã có trong merge_labels.py)
    print("\n⚠️  Để chạy merge với đầy đủ options, sử dụng:")
    print(f"   python -m src.merge_labels --yymm {args.yymm}", end="")
    if args.limit:
        print(f" --limit {args.limit}", end="")
    if args.range:
        print(f" --range {args.range[0]} {args.range[1]}", end="")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="LaTeX Paper Processing Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full pipeline
  python -m src.main --raw ./data_raw --output ./data_output
  
  # Processing only (no matching)
  python -m src.main --raw ./data_raw --output ./data_output --no-matching
  
  # Matching only (data already processed)
  python -m src.main --output ./data_output --matching-only
  
  # Merge labels into dataset
  python -m src.main --merge --yymm 2403 --limit 50
        """
    )
    
    paths = get_project_paths()
    
    # === Mode Selection ===
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--matching-only", 
        action="store_true",
        help="Chỉ chạy phase matching (bỏ qua processing)"
    )
    mode_group.add_argument(
        "--merge",
        action="store_true", 
        help="Chạy merge labels thành dataset"
    )
    
    # === Path Arguments ===
    parser.add_argument(
        "--raw", "-r",
        type=str,
        default=paths["data_raw_default"],
        help=f"Đường dẫn data raw (default: {paths['data_raw_default']})"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=paths["data_output_default"],
        help=f"Đường dẫn output (default: {paths['data_output_default']})"
    )
    
    # === Processing Options ===
    parser.add_argument(
        "--parallel", "-p",
        action="store_true",
        help="Sử dụng xử lý song song"
    )
    parser.add_argument(
        "--workers", "-w",
        type=int,
        default=None,
        help="Số workers cho parallel processing (default: số CPU)"
    )
    parser.add_argument(
        "--no-matching",
        action="store_true",
        help="Không chạy phase matching sau processing"
    )
    
    # === Merge Options ===
    parser.add_argument(
        "--yymm",
        type=str,
        help="Prefix năm-tháng cho merge (VD: 2403)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Giới hạn số papers random (cho merge)"
    )
    parser.add_argument(
        "--range",
        type=int,
        nargs=2,
        help="Lấy papers từ index A đến B (cho merge)"
    )
    parser.add_argument(
        "--input",
        type=str,
        help="Override input path cho merge"
    )
    parser.add_argument(
        "--output-dataset",
        type=str,
        help="Override output path cho dataset merge"
    )
    
    args = parser.parse_args()
    
    # === Dispatch ===
    try:
        if args.merge:
            if not args.yymm:
                parser.error("--merge requires --yymm argument")
            cmd_merge(args)
        elif args.matching_only:
            cmd_matching(args)
        else:
            cmd_full(args)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
