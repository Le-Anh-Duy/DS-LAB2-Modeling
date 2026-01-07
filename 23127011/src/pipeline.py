import os
import shutil
import json
import uuid
import re
from src.parser import LatexFlattener, LatexStructureBuilder, LatexContentProcessor, find_root_tex_file
from src.cleaner import ReferenceProcessor
from src.deduplicator import ReferenceDeduplicator, ContentDeduplicator, replace_citations_in_text

def run_processing_pipeline(data_raw_path, data_output_path):
    """
    Main pipeline to process all papers.
    Each paper is processed independently.
    1. Flatten & Extract Refs
    2. Dedup Refs
    3. Replace Refs in Text
    4. Parse Structure & Content
    5. Dedup Content
    6. Export
    """
    if not os.path.exists(data_output_path):
        os.makedirs(data_output_path)
    
    paper_folders = [f for f in os.listdir(data_raw_path) if os.path.isdir(os.path.join(data_raw_path, f))]
    
    for paper_id in paper_folders:
        print(f"📄 Processing Paper: {paper_id}")

        paper_raw_path = os.path.join(data_raw_path, paper_id)
        paper_output_dir = os.path.join(data_output_path, paper_id)
        
        if not os.path.exists(paper_output_dir):
            os.makedirs(paper_output_dir)

        # Initialize Deduplicators PER PAPER
        ref_deduplicator = ReferenceDeduplicator()
        content_deduplicator = ContentDeduplicator()
        
        # Intermediate content for this paper
        intermediate_versions = {}
        
        tex_path = os.path.join(paper_raw_path, 'tex')
        if not os.path.exists(tex_path):
            continue

        versions = sorted(os.listdir(tex_path))
        
        # --- PHASE 1: PRE-PROCESSING (Flatten & Referencing) ---
        for ver in versions:
            ver_path = os.path.join(tex_path, ver)
            if not os.path.isdir(ver_path): continue
            
            # 1. Flatten
            root_file = find_root_tex_file(ver_path)
            if not root_file:
                continue
            
            try:
                # Step A: Flatten with references (for extraction)
                flattener_refs = LatexFlattener(root_file, paper_id, ver, remove_references=False)
                flat_content_refs = flattener_refs.flatten()['content']
                
                # 2. Extract References
                ref_proc = ReferenceProcessor(paper_id, ver, ver_path)
                _, refs = ref_proc.process_references(flat_content_refs)
                print(f"      Found {len(refs)} references in {ver}.")
                
                # 3. Add to Dedup Pool
                ref_deduplicator.add_references(f"{paper_id}/{ver}", refs)
                
                # Step B: Flatten without references (for cleaning/tree building)
                flattener_clean = LatexFlattener(root_file, paper_id, ver, remove_references=True)
                flat_content_clean = flattener_clean.flatten()['content']
                
                # Store clean content for Phase 2
                intermediate_versions[ver] = flat_content_clean
                
            except Exception as e:
                print(f"      ❌ Error in Phase 1 for {ver}: {e}")

        # --- PHASE 2: PARSING & CONTENT DEDUPLICATION ---
        for ver, raw_content in intermediate_versions.items():
            full_ver_key = f"{paper_id}/{ver}"
            
            try:
                # 4. Get Replacements & Replace in Text
                replacements = ref_deduplicator.get_replacements(full_ver_key)
                if replacements:
                    raw_content = replace_citations_in_text(raw_content, replacements)
                
                # 5. Parse Structure
                builder = LatexStructureBuilder(raw_content, paper_id, ver)
                root_tree = builder.build_coarse_tree()
                
                # 6. Process Content (Clean & Split)
                processor = LatexContentProcessor(paper_id, ver)
                processor.process_tree(root_tree)
                
                # 7. Dedup Content
                content_deduplicator.process_version(full_ver_key, root_tree)
            
            except Exception as e:
                print(f"      ❌ Error in Phase 2 for {ver}: {e}")

        # --- PHASE 3: EXPORT ARTIFACTS ---
        try:
            # 8. Export refs.bib
            refs_output_path = os.path.join(paper_output_dir, "refs.bib")
            with open(refs_output_path, "w", encoding="utf-8") as f:
                f.write(ref_deduplicator.export_bib_string())
            
            # 9. Export hierarchy.json
            hier_output_path = os.path.join(paper_output_dir, "hierarchy.json")
            final_json = content_deduplicator.get_final_json()
            with open(hier_output_path, "w", encoding="utf-8") as f:
                json.dump(final_json, f, indent=2, ensure_ascii=False)
                
            # 10. Copy Metadata
            for meta_file in ['metadata.json', 'references.json']:
                src_meta = os.path.join(paper_raw_path, meta_file)
                if os.path.exists(src_meta):
                    shutil.copy2(src_meta, paper_output_dir)
                    
            print(f"   ✅ Finished processing {paper_id}")
            
        except Exception as e:
            print(f"      ❌ Error in Export Phase: {e}")

if __name__ == "__main__":
    # Example usage
    BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # 23127011
    ROOT_PROJECT = os.path.dirname(BASE_PATH) # Milestone2_Project
    
    DATA_RAW = os.path.join(ROOT_PROJECT, 'data_raw')
    DATA_OUTPUT = os.path.join(ROOT_PROJECT, 'data_output')
    
    run_processing_pipeline(DATA_RAW, DATA_OUTPUT)
