import json
import os
import concurrent.futures
import argparse
from typing import List, Dict, Any
from src.matcher import ReferenceMatcher # <--- Import class mới

ROOT_DIR = r"D:\GHuy\Studying\I2DS\Lab1\data2"
OUTPUT_DIR = r"D:\GHuy\Studying\I2DS\Lab2\data"

def labels_tfidf(ref_path: str, used_ref_path: str, output_path: str) -> None:
    # 1. Kiểm tra file input
    if not os.path.exists(ref_path) or not os.path.exists(used_ref_path):
        return
    if os.stat(ref_path).st_size == 0 or os.stat(used_ref_path).st_size == 0:
        return

    try:
        # 2. Load dữ liệu
        with open(ref_path, 'r', encoding='utf-8') as f:
            references_db = json.load(f) # Ground Truth
        
        with open(used_ref_path, 'r', encoding='utf-8') as f:
            used_references_list = json.load(f) # Extracted Refs

        # --- KHỞI TẠO MATCHER ---
        matcher = ReferenceMatcher(threshold=0.35) # TF-IDF cần ngưỡng cao hơn Jaccard một chút
        matcher.fit(references_db)
        # ------------------------

        output_data = []

        # 3. Matching
        if isinstance(used_references_list, list):
            for entry in used_references_list:
                if isinstance(entry, dict):
                    for cite_key, cite_text in entry.items():
                        
                        # --- GỌI TF-IDF MATCHING ---
                        match_result = matcher.match(cite_text)
                        # ---------------------------

                        if match_result:
                            # match_result = {"id": "...", "meta": {...}}
                            best_match_id = match_result['id']
                            meta = match_result['meta']

                            # Tạo format output y hệt code cũ để không phá hỏng merge_labels.py
                            ground_truth_obj = {
                                "id": best_match_id,
                                "title": meta.get("title", ""),
                                "authors": meta.get("authors", []),
                                "submission_date": meta.get("submission_date", "")
                                # Có thể thêm year, abstract nếu cần
                            }

                            output_data.append({
                                "key": cite_key,
                                "content": cite_text,
                                "ground_truth": ground_truth_obj
                            })

        # 4. Xuất file kết quả
        if output_data:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=4)
            print(f"Matched {len(output_data)} items for {output_path}")
        
    except Exception as e:
        print(f"Error processing {output_path}: {e}")

def process_batch(ids: List[str], max_workers: int = 4):
    print(f"Starting TF-IDF labeling for {len(ids)} items...")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_id = {}
        for id in ids:
            ref_path = os.path.join(ROOT_DIR, id, "references.json")
            used_ref_path = os.path.join(OUTPUT_DIR, id, "used_references.json")
            output_path = os.path.join(OUTPUT_DIR, id, "labels.json")
            
            future = executor.submit(labels_tfidf, ref_path, used_ref_path, output_path)
            future_to_id[future] = id
            
        for future in concurrent.futures.as_completed(future_to_id):
            id = future_to_id[future]
            try:
                future.result()
            except Exception as exc:
                print(f"[{id}] Exception: {exc}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate detailed labels.json using TF-IDF.")
    parser.add_argument("--yymm", type=str, required=True, help="yymm part (e.g., 2312)")
    parser.add_argument("--id", type=int, nargs=2, required=True, help="start and end ID")

    args = parser.parse_args()
    yymm = args.yymm
    start_id, end_id = args.id
    
    id_list = [f"{yymm}.{str(i).rjust(5, '0')}" for i in range(start_id, end_id + 1)]
    
    process_batch(id_list, max_workers=8)