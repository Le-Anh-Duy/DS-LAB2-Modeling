import hashlib
import re

class ReferenceDeduplicator:
    def __init__(self):
        # Kho chứa reference duy nhất: { fingerprint: {data} }
        self.unique_refs_pool = {} 
        
        # Danh sách key chuẩn theo thứ tự: ['ref_0', 'ref_1', ...]
        self.canonical_keys = []
        
        # Map để thay thế trong text: { version: { old_key: new_key } }
        self.version_maps = {}

    def _create_fingerprint(self, text):
        """
        Tạo dấu vân tay từ nội dung reference.
        Chỉ giữ lại chữ cái và số, bỏ qua dấu câu và khoảng trắng để so sánh chính xác.
        """
        # Xóa mọi thứ không phải chữ/số và chuyển về chữ thường
        clean_text = re.sub(r'[^a-z0-9]', '', text.lower())
        return hashlib.md5(clean_text.encode('utf-8')).hexdigest()

    def add_references(self, version, refs_list):
        """
        Nhận danh sách refs từ một version và xử lý dedup.
        """
        self.version_maps[version] = {}
        
        for ref in refs_list:
            old_key = ref['key']
            raw_text = ref['raw_text']
            
            # 1. Tạo fingerprint
            fp = self._create_fingerprint(raw_text)
            
            canonical_key = None
            
            # 2. Kiểm tra trùng lặp
            if fp in self.unique_refs_pool:
                # Đã tồn tại -> Lấy key chuẩn cũ
                canonical_key = self.unique_refs_pool[fp]['canonical_key']
                
                # Unionize: Cập nhật thông tin nếu bản mới đầy đủ hơn bản cũ (Optional)
                # Ví dụ: Nếu bản cũ ngắn quá, lấy bản mới dài hơn làm raw_text chính
                if len(raw_text) > len(self.unique_refs_pool[fp]['raw_text']):
                     self.unique_refs_pool[fp]['raw_text'] = raw_text
                     
            else:
                # Chưa tồn tại -> Tạo mới
                new_idx = len(self.canonical_keys)
                canonical_key = f"ref_{new_idx}" # Tạo key chuẩn: ref_0, ref_1...
                
                self.unique_refs_pool[fp] = {
                    'canonical_key': canonical_key,
                    'raw_text': raw_text,
                    'original_refs': [] # Để trace lại nếu cần
                }
                self.canonical_keys.append(canonical_key)
            
            # 3. Lưu mapping cho version này (Old Key -> Canonical Key)
            # Chỉ lưu nếu key khác nhau để tối ưu hiệu năng replace
            if old_key != canonical_key:
                self.version_maps[version][old_key] = canonical_key

    def get_replacements(self, version):
        """Trả về dict {old: new} để replace trong text của version đó"""
        return self.version_maps.get(version, {})

    def export_bib_string(self):
        """Xuất chuỗi BibTeX chuẩn cho file refs.bib"""
        bib_content = ""
        # Duyệt theo thứ tự canonical keys để file đẹp
        for fp in self.unique_refs_pool:
            item = self.unique_refs_pool[fp]
            key = item['canonical_key']
            text = item['raw_text']
            
            # Tạo entry @misc đơn giản chứa full text
            # Vì ta trích xuất từ \bibitem nên không có field tách biệt, tống hết vào title/note
            entry = f"@misc{{{key},\n  text = {{{text}}}\n}}\n\n"
            bib_content += entry
            
        return bib_content

class ContentDeduplicator:
    def __init__(self):
        # elements: { "id": "content string" }
        self.global_elements = {}
        
        # Helper to find existing IDs by content: { "hash": "id" }
        self.content_hash_map = {}
        
        # hierarchy: { "1": { "child_id": "parent_id" }, "2": ... }
        self.final_hierarchy = {}

    def _get_content_hash(self, content, type_name):
        """Hash content + type to identify duplicates."""
        if content is None: content = ""
        # Combine type and content to ensure uniqueness (e.g. Title vs Sentence)
        raw_str = f"{type_name}:{str(content).strip()}"
        return hashlib.md5(raw_str.encode('utf-8')).hexdigest()

    def _extract_version_number(self, version_str):
        """
        Extracts the version number from the folder name.
        Example: '2403-00531v1' -> '1'
        Example: '2403-00531v2' -> '2'
        """
        # Split by 'v' and take the last part.
        # Handle cases like 'v1', 'paper_v1', '2403.1234v2'
        parts = version_str.split('v')
        if len(parts) > 1:
            return parts[-1]
        return version_str # Fallback if no 'v' found

    def register_node(self, node):
        """
        Registers a node content.
        - If content exists: Returns existing ID.
        - If new: Returns new ID (current node ID) and stores content.
        """
        # Priority: raw_content (cleaned) > content > empty
        content = node.get('raw_content', '')
        if not content:
            content = node.get('content', '')
            
        node_type = node.get('type', 'unknown')
        
        # Case 1: Node has no meaningful content (e.g. wrapper Section without title text)
        # We generally track ID but don't dedup based on empty string unless it's structural
        if not content.strip():
            if node.get('title'):
                 self.global_elements[node['id']] = node['title']
            return node['id']

        # Case 2: Node has content -> Deduplicate
        content_hash = self._get_content_hash(content, node_type)
        
        if content_hash in self.content_hash_map:
            # Duplicate found! Return the ORIGINAL ID
            return self.content_hash_map[content_hash]
        
        # New content
        current_id = node['id']
        self.global_elements[current_id] = content
        self.content_hash_map[content_hash] = current_id
        
        return current_id

    def process_version(self, full_version_str, root_node):
        """
        Traverses the tree for a specific version.
        Builds a map: { "child_id": "parent_id" }
        """
        # 1. Extract version number (e.g., "1")
        ver_num = self._extract_version_number(full_version_str)
        
        # 2. Initialize hierarchy map for this version
        # Format: "child_id": "parent_id"
        version_map = {}
        
        def traverse(current_node, parent_id_context=None):
            # A. Get Unified ID (Reuse old ID if content matches)
            unified_id = self.register_node(current_node)
            
            # B. Record relationship: Child -> Parent
            # According to Listing 1: "smallest-element-id": "higher-component-id"
            if parent_id_context:
                version_map[unified_id] = parent_id_context
            else:
                # Root node
                pass 

            # C. Recursion
            for child in current_node.get('children', []):
                traverse(child, parent_id_context=unified_id)
        
        # Start traversal from root
        traverse(root_node)
        
        # 3. Store in final hierarchy
        self.final_hierarchy[ver_num] = version_map
        
    def get_final_json(self):
        """
        Outputs the final JSON structure suitable for Listing 1.
        Keys: "0", "1", ... (versions)
        Value: { "child_id": "parent_id", ... }
        And "elements": { "id": "content", ... }
        """
        return {
            "hierarchy": self.final_hierarchy,
            "elements": self.global_elements
        }

def replace_citations_in_text(text, replacement_map):
    """
    Thay thế \cite{old} thành \cite{new} trong toàn bộ văn bản.
    """
    if not replacement_map:
        return text
        
    def replace_match(match):
        # match.group(0) là toàn bộ \cite{...}
        # match.group(1) là nội dung bên trong {}
        inner = match.group(2)
        keys = [k.strip() for k in inner.split(',')]
        
        new_keys = []
        for k in keys:
            # Nếu key có trong map thì đổi, không thì giữ nguyên
            new_keys.append(replacement_map.get(k, k))
            
        return f"{match.group(1)}{', '.join(new_keys)}{match.group(3)}"

    # Regex bắt \cite{...}
    pattern = re.compile(r'(\\cite[a-z]*\s*(?:\[.*?\])?\s*\{)([^}]+)(\})', re.IGNORECASE)
    
    return pattern.sub(replace_match, text)
