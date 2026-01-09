import json
import os
import argparse
import random
from typing import List, Dict

# ==============================================================================
# CẤU HÌNH ĐƯỜNG DẪN MẶC ĐỊNH
# ==============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_INPUT_DIR = os.path.join(BASE_DIR, '../../data_output_v2') 
DEFAULT_OUTPUT_DIR = os.path.join(BASE_DIR, '../../dataset_final')
# ==============================================================================

def load_selected_papers(input_dir: str, folder_names: List[str]) -> Dict[str, List[dict]]:
    """
    Đọc dữ liệu từ danh sách folder đã được lọc (Limit/Range).
    
    Args:
        input_dir: Đường dẫn thư mục chứa data
        folder_names: Danh sách tên folder cần load
    """
    papers_map = {}
    print(f"🔄 Loading data from {len(folder_names)} folders...")

    for folder_name in folder_names:
        file_path = os.path.join(input_dir, folder_name, 'labels.json')
        if not os.path.exists(file_path): continue
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, list) and len(data) > 0:
                papers_map[folder_name] = data
        except Exception:
            pass
            
    return papers_map

def save_json(data_list, filepath):
    if not data_list: return
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data_list, f, ensure_ascii=False, indent=4)
    print(f"   💾 Saved: {os.path.basename(filepath)} ({len(data_list)} items)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Split dataset into Auto/Manual with Limits.")
    parser.add_argument("--yymm", type=str, required=True, help="yymm prefix (e.g., 2403)")
    
    # --- OPTION ĐƯỜNG DẪN ---
    parser.add_argument("--input", type=str, default=DEFAULT_INPUT_DIR,
                        help=f"Input directory path (default: {DEFAULT_INPUT_DIR})")
    parser.add_argument("--output", type=str, default=DEFAULT_OUTPUT_DIR,
                        help=f"Output directory path (default: {DEFAULT_OUTPUT_DIR})")
    
    # --- OPTION GIỚI HẠN SỐ LƯỢNG ---
    parser.add_argument("--limit", type=int, help="Chỉ lấy ngẫu nhiên N bài (VD: 50)")
    parser.add_argument("--range", type=int, nargs=2, help="Lấy từ index A đến B (VD: 0 100)")
    
    args = parser.parse_args()
    
    # Sử dụng paths từ arguments
    INPUT_DIR_PATH = os.path.abspath(args.input)
    OUTPUT_DIR = os.path.abspath(args.output)

    print(f"📂 Input Directory:  {INPUT_DIR_PATH}")
    print(f"📂 Output Directory: {OUTPUT_DIR}")
    
    if not os.path.exists(INPUT_DIR_PATH):
        print(f"❌ Error: Path not found!")
        exit(1)

    # 1. QUÉT TẤT CẢ FOLDER
    all_items = os.listdir(INPUT_DIR_PATH)
    valid_folders = [
        name for name in all_items 
        if os.path.isdir(os.path.join(INPUT_DIR_PATH, name)) 
        and name.startswith(args.yymm)
    ]
    valid_folders.sort() # Sắp xếp để đảm bảo thứ tự cho --range
    
    if not valid_folders:
        print(f"❌ No folders found starting with {args.yymm}")
        exit(1)

    print(f"📋 Found total {len(valid_folders)} folders matching prefix.")

    # 2. ÁP DỤNG LIMIT / RANGE
    target_folders = []
    
    if args.range:
        start, end = args.range
        target_folders = valid_folders[start:end]
        print(f"✂️  Mode: RANGE [{start} -> {end}]")
    elif args.limit:
        if args.limit < len(valid_folders):
            print(f"🎲 Mode: RANDOM LIMIT ({args.limit} papers)")
            random.seed(42)
            # Shuffle toàn bộ rồi lấy N phần tử đầu
            # Copy list để không ảnh hưởng list gốc
            temp_list = list(valid_folders)
            random.shuffle(temp_list)
            target_folders = temp_list[:args.limit]
        else:
            target_folders = valid_folders
            print(f"⚠️ Limit ({args.limit}) > Total. Taking all.")
    else:
        target_folders = valid_folders
        print(f"🚀 Mode: FULL DATASET")

    if not target_folders:
        print("❌ Error: Target list is empty after filtering.")
        exit(1)

    print(f"   👉 Processing subset of {len(target_folders)} papers.")

    # 3. LOAD DỮ LIỆU (Chỉ load những bài đã lọc)
    papers_db = load_selected_papers(INPUT_DIR_PATH, target_folders)
    all_loaded_ids = list(papers_db.keys())
    
    if not all_loaded_ids:
        print("❌ Error: No valid labels.json found in the selected subset.")
        exit(1)

    # 4. TÌM ỨNG VIÊN CHO MANUAL (Ref >= 20)
    candidates_manual = []
    for pid, refs in papers_db.items():
        if len(refs) >= 20:
            candidates_manual.append(pid)
            
    print(f"🎯 Candidates for Manual (>= 20 refs): {len(candidates_manual)} papers")
    
    if len(candidates_manual) < 5:
        print("❌ ERROR: Not enough candidates for manual selection!")
        print(f"   Requirement: 5 papers with >= 20 refs.")
        print(f"   Found: {len(candidates_manual)}")
        print("   💡 Suggestion: Increase your --limit or expand your --range.")
        exit(1)

    # 5. CHỌN 5 BÀI MANUAL (3 Train, 1 Val, 1 Test)
    random.seed(42)
    random.shuffle(candidates_manual)
    
    selected_manual = candidates_manual[:5]
    
    manual_train_ids = selected_manual[:3]
    manual_val_ids   = selected_manual[3:4]
    manual_test_ids  = selected_manual[4:5]
    
    print("\n✍️  SELECTED MANUAL PAPERS:")
    print(f"   Train (3): {manual_train_ids}")
    print(f"   Val   (1): {manual_val_ids}")
    print(f"   Test  (1): {manual_test_ids}")

    # 6. PHÂN LOẠI AUTO (Còn lại)
    # Auto = (Tất cả bài đã load) - (5 bài manual)
    auto_pool_ids = [pid for pid in all_loaded_ids if pid not in selected_manual]
    
    random.shuffle(auto_pool_ids)
    total_auto = len(auto_pool_ids)
    
    # Chia 80/10/10
    tr_end = int(total_auto * 0.8)
    val_end = int(total_auto * 0.9)
    
    # Xử lý trường hợp tập dữ liệu quá nhỏ (<10 bài)
    if total_auto < 10:
        print("⚠️ Small auto dataset. Putting all into Train.")
        auto_train_ids = auto_pool_ids
        auto_val_ids = []
        auto_test_ids = []
    else:
        auto_train_ids = auto_pool_ids[:tr_end]
        auto_val_ids   = auto_pool_ids[tr_end:val_end]
        auto_test_ids  = auto_pool_ids[val_end:]
    
    print(f"\n🤖 AUTO DATASET SPLIT ({total_auto} papers):")
    print(f"   Train: {len(auto_train_ids)} | Val: {len(auto_val_ids)} | Test: {len(auto_test_ids)}")

    # 7. GHI FILE
    def process_and_save(subset_name, auto_ids, manual_ids):
        auto_data = []
        for pid in auto_ids: auto_data.extend(papers_db[pid])
        
        manual_data = []
        for pid in manual_ids: manual_data.extend(papers_db[pid])
            
        base_path = os.path.join(OUTPUT_DIR, subset_name)
        print(f"\n📂 Writing {subset_name.upper()}...")
        
        if auto_data: save_json(auto_data, os.path.join(base_path, 'auto.json'))
        if manual_data: save_json(manual_data, os.path.join(base_path, 'manual.json'))

    process_and_save('train', auto_train_ids, manual_train_ids)
    process_and_save('validation', auto_val_ids, manual_val_ids)
    process_and_save('test', auto_test_ids, manual_test_ids)

    print(f"\n🎉 DONE! Saved to: {OUTPUT_DIR}")