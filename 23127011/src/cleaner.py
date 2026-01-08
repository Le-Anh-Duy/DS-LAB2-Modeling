import os
import re
import bibtexparser
from bibtexparser.bparser import BibTexParser
from TexSoup import TexSoup

class ReferenceProcessor:
    def __init__(self, paper_id, version, root_dir):
        self.paper_id = paper_id
        self.version = version
        self.root_dir = root_dir
        
        self.raw_refs = {} 
        
        # Regex tìm Citation Keys (Fallback)
        self.REGEX_CITE_FALLBACK = re.compile(r'\\cite[a-z]*\s*(?:\[.*?\])?\s*\{([^}]+)\}', re.IGNORECASE)

        # Regex tìm khối Bibliography Embedded (Quan trọng cho trường hợp của bạn)
        # Tìm từ \begin{thebibliography} đến \end{thebibliography} bất chấp nội dung ở giữa
        self.REGEX_THEBIB_BLOCK = re.compile(
            r'(\\begin\s*\{thebibliography\}.*?\\end\s*\{thebibliography\})', 
            re.DOTALL | re.IGNORECASE
        )

        # Regex BibItem (Sentinel Trick)
        self.REGEX_BIBITEM = re.compile(
            r'\\bibitem\s*(?:\[(.*?)\])?\s*\{(.*?)\}\s*(.*?)(?=(?:\\bibitem)|(?:\\end\{thebibliography\})|\Z)', 
            re.DOTALL | re.IGNORECASE
        )

    def process_references(self, flat_content):
        # 1. CHUẨN HÓA SƠ BỘ
        # Biến mọi xuống dòng thành space để tránh bị ngắt dòng làm trượt regex
        norm_content = re.sub(r'\s+', ' ', flat_content)
        
        print(f"   🔍 Scanning references for {self.version}...")

        # --- BƯỚC 1: TRÍCH XUẤT NHU CẦU (USED KEYS) ---
        used_keys = set()
        texsoup_success = False
        
        # Thử TexSoup (Ưu tiên)
        try:
            # Fix lỗi $$ để TexSoup chạy xa hơn
            sanitized_content = re.sub(r'\$\$(.*?)\$\$', r'\\[\1\\]', flat_content, flags=re.DOTALL)
            soup = TexSoup(sanitized_content)
            
            citation_cmds = soup.find_all(['cite', 'citet', 'citep', 'nocite', 'citeauthor', 'citeyear'])
            for cmd in citation_cmds:
                if cmd.args:
                    key_str = str(cmd.args[-1].string)
                    if key_str:
                        for k in key_str.split(','): used_keys.add(k.strip())
            texsoup_success = True
        except Exception:
            pass

        # Fallback Regex cho Citation
        if not texsoup_success or len(used_keys) == 0:
            print(f"      ⚠️ Citation fallback triggered.")
            for match in self.REGEX_CITE_FALLBACK.finditer(norm_content):
                keys = match.group(1).split(',')
                for k in keys: used_keys.add(k.strip())
        
        print(f"      Found {len(used_keys)} cited keys in text.")

        # --- BƯỚC 2: VÉT CẠN FILE NGOÀI (.bib/.bbl) ---
        all_files = os.listdir(self.root_dir)
        candidate_files = [f for f in all_files if f.lower().endswith(('.bbl', '.bib'))]
        for filename in candidate_files:
            if filename.lower().endswith('.bib'): self._try_parse_bib(filename)
            elif filename.lower().endswith('.bbl'): self._try_parse_bbl(filename)

        # --- BƯỚC 3: XỬ LÝ EMBEDDED (FIX QUAN TRỌNG) ---
        # Thay vì tin TexSoup, ta dùng Regex cắt khối thebibliography ra
        
        # Cách 1: Tìm khối \begin{thebibliography} trong content gốc
        block_match = self.REGEX_THEBIB_BLOCK.search(flat_content)
        if block_match:
            block_content = block_match.group(1)
            norm_block = re.sub(r'\s+', ' ', block_content)
            self._parse_bibitem_content(norm_block, source_type="embedded_block")
        else:
            # Cách 2: Nếu không có block (hoặc regex block trượt), quét toàn bộ content đã chuẩn hóa
            self._parse_bibitem_content(norm_content, source_type="embedded_fullscan")

        # --- BƯỚC 4: FILTER ---
        final_refs = []
        if len(used_keys) == 0:
             # Safety Net: Không tìm thấy cite nào thì lấy hết refs
            final_refs = list(self.raw_refs.values())
        else:
            is_wildcard = '*' in used_keys
            for key, ref_obj in self.raw_refs.items():
                if is_wildcard or key in used_keys:
                    final_refs.append(ref_obj)
        
        print(f"      Matched {len(final_refs)} references.")
        return flat_content, final_refs

    # --- CÁC HÀM PHỤ TRỢ (HELPER) ---
    def _try_parse_bib(self, filename):
        path = os.path.join(self.root_dir, filename)
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                parser = BibTexParser(common_strings=True)
                parser.ignore_nonstandard_types = True
                parser.homogenise_fields = False
                db = bibtexparser.load(f, parser=parser)
            for entry in db.entries:
                key = entry.get('ID', '').strip()
                if key and key not in self.raw_refs:
                    self.raw_refs[key] = {
                        "key": key,
                        "raw_text": self._dict_to_bibtex_string(entry),
                        "type": f"bib_{entry.get('ENTRYTYPE', 'misc').lower()}",
                        "source": filename
                    }
        except Exception: pass

    def _try_parse_bbl(self, filename):
        path = os.path.join(self.root_dir, filename)
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            norm_content = re.sub(r'\s+', ' ', content)
            self._parse_bibitem_content(norm_content, source_type=filename)
        except Exception: pass

    def _parse_bibitem_content(self, text, source_type="bibitem"):
        # SENTINEL TRICK: Thêm mốc giả để lookahead bắt được item cuối
        text += " \\bibitem{SENTINEL_MARKER_FIX} "
        
        matches = self.REGEX_BIBITEM.findall(text)
        count = 0
        for label, key, content in matches:
            clean_key = key.strip()
            if clean_key == "SENTINEL_MARKER_FIX": continue
            
            if clean_key and clean_key not in self.raw_refs:
                # Clean content
                content = re.sub(r'\\end\s*\{thebibliography\}.*$', '', content, flags=re.IGNORECASE).strip()
                content = re.sub(r'\s+', ' ', content).strip()
                
                self.raw_refs[clean_key] = {
                    "key": clean_key,
                    "raw_text": content,
                    "type": "bibitem",
                    "source": source_type
                }
                count += 1
        if count > 0:
             print(f"         -> Parsed {count} items from {source_type}")

    def _dict_to_bibtex_string(self, entry):
        lines = [f"@{entry.get('ENTRYTYPE', 'misc')}{{{entry.get('ID', '')},"]
        for k, v in entry.items():
            if k in ['ENTRYTYPE', 'ID']: continue
            lines.append(f"  {k} = {{{v}}},")
        lines.append("}")
        return "\n".join(lines)