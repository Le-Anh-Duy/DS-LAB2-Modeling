import re
import os
import glob

class ReferenceProcessor:
    def __init__(self, paper_id, version, root_dir):
        self.paper_id = paper_id
        self.version = version
        self.root_dir = root_dir
        
        # Regex Filter Usage (Tìm các key được cite trong bài)
        self.REGEX_CITE = re.compile(r'\\cite[a-z]*\s*(?:\[.*?\])?\s*\{([^}]+)\}', re.IGNORECASE)
        
        # Regex Parse BibItem (Normalized) - Dùng cho cả .bbl và embedded
        self.REGEX_BIBITEM_NORMALIZED = re.compile(
            r'\\bibitem\s*(?:\[(.*?)\])?\s*\{(.*?)\}\s*(.*?)(?=(?:\\bibitem)|(?:\\end\{thebibliography\})|$)', 
            re.IGNORECASE | re.DOTALL 
        )
        
        self.raw_refs_pool = {} # Dùng dict để tự động khử trùng lặp key nếu quét nhiều file

    def process_references(self, flat_content):
        """
        Chiến lược: VÉT CẠN (Scan All).
        1. Quét tất cả file .bib/.bbl trong thư mục.
        2. Quét reference nhúng trong flat_content.
        3. Lọc lại chỉ giữ những key được \cite trong flat_content.
        """
        
        # 1. Xác định nhu cầu: Tìm tất cả các key được cite
        # Ta normalize content để regex hoạt động tốt hơn với các cite xuống dòng
        norm_flat_content = self._normalize_text(flat_content)
        
        used_keys = set()
        for match in self.REGEX_CITE.finditer(norm_flat_content):
            keys = match.group(1).split(',')
            for k in keys:
                used_keys.add(k.strip())
        
        # 2. Vét cạn nguồn cung: Quét toàn bộ file .bbl và .bib trong thư mục
        # Tìm tất cả file .bbl và .bib (không phân biệt hoa thường nếu trên Windows, Linux cần cẩn thận)
        all_files = os.listdir(self.root_dir)
        candidate_files = [f for f in all_files if f.lower().endswith(('.bbl', '.bib'))]
        
        for filename in candidate_files:
            if filename.lower().endswith('.bbl'):
                self._try_parse_bbl(filename)
            elif filename.lower().endswith('.bib'):
                self._try_parse_bib(filename)
                
        # 3. Fallback: Quét thêm embedded refs (trong chính file tex)
        # Phòng trường hợp \begin{thebibliography} viết thẳng trong main.tex
        self._parse_items_from_text(norm_flat_content, source_type="embedded")

        # 4. Matching: Chỉ giữ lại những ref mà bài báo CÓ DÙNG (nằm trong used_keys)
        final_refs = []
        
        # Duyệt qua các key đã tìm thấy trong pool
        for key, ref_data in self.raw_refs_pool.items():
            if key in used_keys:
                final_refs.append(ref_data)
        
        return flat_content, final_refs

    def _normalize_text(self, text):
        return re.sub(r'\s+', ' ', text)

    def _try_parse_bib(self, filename):
        path = os.path.join(self.root_dir, filename)
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                raw = f.read()
            # Regex quét @entry
            entries = re.findall(r'@(\w+)\s*\{\s*([^,]+)\s*,(.*?)(?=\n@|\Z)', raw, re.DOTALL)
            count = 0
            for type_name, key, body in entries:
                key = key.strip()
                if type_name.lower() in ['preamble', 'string', 'control']: continue
                
                # Chỉ thêm nếu chưa có (Ưu tiên file đọc trước)
                if key not in self.raw_refs_pool:
                    self.raw_refs_pool[key] = {
                        "key": key,
                        "raw_text": self._normalize_text(body),
                        "type": "bib_entry"
                    }
                    count += 1
        except Exception as e:
            print(f"         ❌ Error parsing {filename}: {e}")

    def _try_parse_bbl(self, filename):
        path = os.path.join(self.root_dir, filename)
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                raw_content = f.read()
            # Normalize .bbl nát vụn thành 1 dòng
            norm_content = self._normalize_text(raw_content)
            self._parse_items_from_text(norm_content, source_type="bbl")
        except Exception as e:
            print(f"         ❌ Error parsing {filename}: {e}")

    def _parse_items_from_text(self, normalized_text, source_type):
        # Dùng split để bắt trọn vẹn item cuối cùng
        raw_items = re.split(r'\\bibitem', normalized_text)
        count = 0
        for item in raw_items:
            item = item.strip()
            if not item: continue
            
            # Regex bắt: (Optional [label])? {Key} (Phần còn lại là Content)
            match = re.match(r'(?:\s*\[(.*?)\])?\s*\{(.*?)\}\s*(.*)', item)
            
            if match:
                key = match.group(2).strip()
                content = match.group(3).strip()
                # Clean rác cuối (\end{thebibliography}...)
                content = re.sub(r'\\end\s*\{thebibliography\}.*$', '', content, flags=re.IGNORECASE).strip()
                
                if key and key not in self.raw_refs_pool:
                    self.raw_refs_pool[key] = {
                        "key": key,
                        "raw_text": content,
                        "type": source_type
                    }
                    count += 1