import json
import os
import argparse
from typing import List, Dict, Any

# Cấu hình đường dẫn
ROOT_DIR = r"D:\GHuy\Studying\I2DS\Lab2\data"
OUTPUT_DIR = r"D:\GHuy\Studying\I2DS\Lab2"

def merge_json_files(ids: list[str], output_path: str):
    """
    Gộp các file labels.json thành một file duy nhất.
    Dữ liệu được deduplicate dựa trên 'key'.
    """
    
    # Dictionary dùng để deduplicate: Key = citation_key, Value = Full Item Object
    merged_dict: Dict[str, Dict[str, Any]] = {}
    
    files = [os.path.join(ROOT_DIR, id, 'labels.json') for id in ids]
    existing_files = [f for f in files if os.path.exists(f)]
    
    print(f"Merging {len(existing_files)} files to {output_path}...")
    
    file_count = 0
    skipped_count = 0
    
    for file_path in existing_files:
        if os.path.abspath(file_path) == os.path.abspath(output_path):
            continue

        if os.stat(file_path).st_size == 0:
            skipped_count += 1
            continue
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            if isinstance(data, list):
                for item in data:
                    # Item phải là dict và có trường 'key'
                    if isinstance(item, dict) and "key" in item:
                        # Ghi đè vào dict tổng (key trùng sẽ lấy giá trị mới nhất)
                        merged_dict[item["key"]] = item
                file_count += 1
            else:
                # Bỏ qua nếu gặp file format cũ (Dict) hoặc lạ
                skipped_count += 1
            
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            skipped_count += 1

    # Chuyển Values thành List
    final_list = list(merged_dict.values())

    if final_list:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(final_list, f, ensure_ascii=False, indent=4)
            
            print("-" * 30)
            print(f"SUCCESS! Merged {file_count} files.")
            print(f"Skipped {skipped_count} invalid/empty files.")
            print(f"Output saved to: {output_path}")
            print(f"Total Unique Labeled Items: {len(final_list)}")
            print("-" * 30)
        except Exception as e:
            print(f"Error writing output file: {e}")
    else:
        print(f"Result is empty. No valid data found.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge labels.json files.")
    parser.add_argument("--yymm", type=str, required=True, help="yymm part")
    parser.add_argument("--id", type=int, nargs=2, required=True, help="start and end ID")

    args = parser.parse_args()
    yymm = args.yymm
    start_id, end_id = args.id

    id_list = [f"{yymm}.{str(i).rjust(5, '0')}" for i in range(start_id, end_id + 1)]
    
    # Chia tập dữ liệu Train/Val/Test
    # Bạn hãy điều chỉnh logic chia tập này theo ý muốn
    if len(id_list) >= 8:
        print("Processing TEST set...")
        merge_json_files([id_list[0], id_list[5]], os.path.join(OUTPUT_DIR, 'dataset/test', 'labels.json'))

        print("Processing VALIDATION set...")
        merge_json_files([id_list[1], id_list[6]], os.path.join(OUTPUT_DIR, 'dataset/validation', 'labels.json'))

        print("Processing TRAIN set...")
        train_ids = id_list[2:5] + id_list[7:]
        merge_json_files(train_ids, os.path.join(OUTPUT_DIR, 'dataset/train', 'labels.json'))
    else:
        print("Not enough IDs to split. Merging all to train.")
        merge_json_files(id_list, os.path.join(OUTPUT_DIR, 'dataset/train', 'labels.json'))