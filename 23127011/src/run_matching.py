# src/run_matching.py
import os
import json
import bibtexparser
from tqdm import tqdm
from matcher import ReferenceMatcher

def load_extracted_refs_from_bib(bib_path):
    """
    Đọc file refs.bib do Pipeline 1 sinh ra.
    """
    if not os.path.exists(bib_path):
        return []
    
    with open(bib_path, 'r', encoding='utf-8') as f:
        parser = bibtexparser.bparser.BibTexParser(common_strings=True)
        parser.ignore_nonstandard_types = True
        db = bibtexparser.load(f, parser=parser)
    
    refs = []
    for entry in db.entries:
        raw_text = entry.get('text', '')
        if not raw_text:
            raw_text = f"{entry.get('title', '')} {entry.get('author', '')}"
            
        refs.append({
            "key": entry.get('ID'),
            "raw_text": raw_text
        })
    return refs

def run_matching_pipeline(data_output_path):
    print(f"🚀 Starting Matching Pipeline (Phase 2.2)...")
    print(f"   Target: {data_output_path}")

    paper_folders = [f for f in os.listdir(data_output_path) if os.path.isdir(os.path.join(data_output_path, f))]

    for paper_id in tqdm(paper_folders, desc="Matching References"):
        paper_dir = os.path.join(data_output_path, paper_id)
        
        # 1. Load Ground Truth
        gt_path = os.path.join(paper_dir, 'references.json')
        if not os.path.exists(gt_path):
            # Fallback tìm ở data_raw nếu chưa được copy
            raw_gt_path = os.path.join(os.path.dirname(data_output_path), '../data_raw', paper_id, 'references.json')
            # Sửa đường dẫn fallback tùy cấu trúc folder của bạn, hoặc bỏ qua nếu chắc chắn file đã ở output
            if os.path.exists(raw_gt_path):
                gt_path = raw_gt_path
            else:
                continue

        try:
            with open(gt_path, 'r', encoding='utf-8') as f:
                ground_truth_data = json.load(f)
        except Exception:
            continue

        # 2. Init & Fit Matcher
        # Threshold 0.55 để lọc bớt kết quả rác
        matcher = ReferenceMatcher(threshold=0.55)
        matcher.fit(ground_truth_data)

        # 3. Load Extracted Refs
        bib_path = os.path.join(paper_dir, 'refs.bib')
        extracted_refs = load_extracted_refs_from_bib(bib_path)

        if not extracted_refs:
            continue

        # 4. Perform Matching
        labels_output = []
        for ref in extracted_refs:
            key = ref['key']
            text = ref['raw_text']
            
            # Gọi hàm match -> nhận về dict có chứa 'score'
            match_result = matcher.match(text)
            
            if match_result:
                # Lấy điểm số (Mặc định 0 nếu lỗi)
                score = match_result.get('score', 0.0)

                ground_truth_obj = {
                    "id": match_result['id'],
                    "title": match_result['meta'].get("title", ""),
                    "authors": match_result['meta'].get("authors", []),
                    "submission_date": match_result['meta'].get("submissionDate", ""),
                    "match_score": round(score, 4) # [NEW] Lưu điểm số vào JSON (làm tròn 4 số)
                }
                
                labels_output.append({
                    "key": key,
                    "content": text,
                    "ground_truth": ground_truth_obj,
                    "source_paper_id": paper_id
                })

        # 5. Export labels.json
        if labels_output:
            labels_path = os.path.join(paper_dir, 'labels.json')
            with open(labels_path, 'w', encoding='utf-8') as f:
                json.dump(labels_output, f, indent=4, ensure_ascii=False)

    print("✅ Matching Complete. 'labels.json' generated in all folders.")

if __name__ == "__main__":
    # Cấu hình đường dẫn như bạn yêu cầu
    CURRENT_FILE = os.path.abspath(__file__)
    SRC_DIR = os.path.dirname(CURRENT_FILE)           
    STUDENT_DIR = os.path.dirname(SRC_DIR)            
    PROJECT_ROOT = os.path.dirname(STUDENT_DIR)       

    DATA_OUTPUT = os.path.join(PROJECT_ROOT, 'data_output_v2')
    
    print(f"📂 Đang tìm data tại: {DATA_OUTPUT}")

    if os.path.exists(DATA_OUTPUT):
        run_matching_pipeline(DATA_OUTPUT)
    else:
        print(f"❌ Vẫn không tìm thấy! Hãy kiểm tra lại tên thư mục.")
        print(f"   Đường dẫn hệ thống đang thử: {DATA_OUTPUT}")