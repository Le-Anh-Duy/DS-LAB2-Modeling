import glob
import os
import json
import re
import argparse
import concurrent.futures
from typing import List, Dict, Any, Set, Union
from parser import parse_tex, parse_bbl, parse_bib

ROOT_DIR = r"D:\GHuy\Studying\I2DS\Lab1\data2"
OUTPUT_DIR = r"D:\GHuy\Studying\I2DS\Lab2\data"

STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "then", "else", "when", 
    "at", "by", "for", "from", "in", "into", "of", "off", "on", "onto", 
    "out", "over", "to", "up", "with", "is", "are", "was", "were", "be",
    "been", "being", "have", "has", "had", "do", "does", "did", "et", "al"
}

def clean_text_for_matching(data: Union[str, Dict[str, Any]]) -> str:
    raw_text = ""
    if isinstance(data, dict):
        title = data.get("title", "")
        authors = " ".join(data.get("authors", [])) if isinstance(data.get("authors"), list) else str(data.get("authors", ""))
        raw_text = f"{title} {authors}"
    else:
        raw_text = str(data)

    # Lowercasing
    text = raw_text.lower()

    # Remove special characters
    text = re.sub(r'[^a-z0-9\s]', ' ', text)

    # Tokenization & Stop-word removal
    tokens = text.split()
    cleaned_tokens = [t for t in tokens if t not in STOPWORDS and len(t) > 1]

    return " ".join(cleaned_tokens)

def extract_ref(id: str, output_path: str) -> None:
    final_refs: Dict[str, str] = {}
    
    # Find files
    tex_files = glob.glob(f'{id}/tex/**/src/**/*.tex', root_dir=ROOT_DIR, recursive=True)
    bbl_files = glob.glob(f'{id}/tex/**/src/**/*.bbl', root_dir=ROOT_DIR, recursive=True)
    bib_files = glob.glob(f'{id}/tex/**/src/**/*.bib', root_dir=ROOT_DIR, recursive=True)

    found_source = False

    # .bib
    if bib_files:
        for bib_rel_path in bib_files:
            full_path = os.path.join(ROOT_DIR, bib_rel_path)
            items = parse_bib(full_path) 
            
            if items:
                found_source = True
                for item in items:
                    key = list(item.keys())[0]
                    content = list(item.values())[0]
                    
                    final_refs[key] = clean_text_for_matching(content)

    # .bbl
    if not found_source and bbl_files:
        for bbl_rel_path in bbl_files:
            full_path = os.path.join(ROOT_DIR, bbl_rel_path)
            items = parse_bbl(full_path)
            
            if items:
                found_source = True
                for item in items:
                    key = list(item.keys())[0]
                    content = list(item.values())[0]
                    
                    final_refs[key] = clean_text_for_matching(content)

    # .tex
    if not found_source:
        for tex_rel_path in tex_files:
            full_path = os.path.join(ROOT_DIR, tex_rel_path)
            items = parse_tex(full_path)
            
            for item in items:
                key = list(item.keys())[0]
                content = list(item.values())[0]
                
                final_refs[key] = clean_text_for_matching(content)

    output_data = [{k: v} for k, v in final_refs.items()]

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=4)
        print(f"[{id}] Successfully extracted {len(output_data)} references.")
    except IOError as e:
        print(f"[{id}] Error writing to {output_path}: {e}")

def process_batch(ids: List[str], max_workers: int = 4):
    print(f"Starting batch process for {len(ids)} items with {max_workers} threads...")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_id = {}
        for id in ids:
            output_path = os.path.join(OUTPUT_DIR, id, 'used_references.json')
            
            # Submit task
            future = executor.submit(extract_ref, id, output_path)
            future_to_id[future] = id

        for future in concurrent.futures.as_completed(future_to_id):
            id = future_to_id[future]
            try:
                future.result()
            except Exception as exc:
                print(f"[{id}] Generated an exception: {exc}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract and clean references from arXiv sources.")
    parser.add_argument("--yymm", type=str, required=True, help="yymm part of arXiv paper's ID (e.g., 2312)")
    parser.add_argument("--id", type=int, nargs=2, required=True, help="start and end ID (e.g., 100 200)")

    args = parser.parse_args()
    yymm = args.yymm
    start_id, end_id = args.id

    # Tạo danh sách ID: yymm.00xxx
    id_list = [yymm + '.' + str(i).rjust(5, '0') for i in range(start_id, end_id + 1)]
    
    # Chạy xử lý
    process_batch(id_list, max_workers=8)