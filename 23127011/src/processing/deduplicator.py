"""
Deduplicator Module
===================

Các class để loại bỏ trùng lặp references và content.
"""

import hashlib
import re


class ReferenceDeduplicator:
    """
    Loại bỏ references trùng lặp giữa các versions.
    
    Sử dụng MD5 fingerprint để so sánh nội dung references.
    
    Example:
        >>> dedup = ReferenceDeduplicator()
        >>> dedup.add_references("paper/v1", refs_v1)
        >>> dedup.add_references("paper/v2", refs_v2)
        >>> replacements = dedup.get_replacements("paper/v2")
        >>> bib_string = dedup.export_bib_string()
    """
    
    def __init__(self):
        # Kho chứa reference duy nhất: { fingerprint: {data} }
        self.unique_refs_pool = {} 
        
        # Danh sách key chuẩn theo thứ tự: ['ref_0', 'ref_1', ...]
        self.canonical_keys = []
        
        # Map để thay thế trong text: { version: { old_key: new_key } }
        self.version_maps = {}

    def _create_fingerprint(self, text: str) -> str:
        """
        Tạo dấu vân tay từ nội dung reference.
        Chỉ giữ lại chữ cái và số để so sánh.
        """
        clean_text = re.sub(r'[^a-z0-9]', '', text.lower())
        return hashlib.md5(clean_text.encode('utf-8')).hexdigest()

    def add_references(self, version: str, refs_list: list):
        """
        Thêm danh sách refs từ một version và xử lý dedup.
        
        Args:
            version: Version identifier (e.g., "paper_id/v1")
            refs_list: List of ref dicts với keys 'key' và 'raw_text'
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
                
                # Cập nhật nếu bản mới đầy đủ hơn
                if len(raw_text) > len(self.unique_refs_pool[fp]['raw_text']):
                     self.unique_refs_pool[fp]['raw_text'] = raw_text
                     
            else:
                # Chưa tồn tại -> Tạo mới
                new_idx = len(self.canonical_keys)
                canonical_key = f"ref_{new_idx}"
                
                self.unique_refs_pool[fp] = {
                    'canonical_key': canonical_key,
                    'raw_text': raw_text,
                    'original_refs': []
                }
                self.canonical_keys.append(canonical_key)
            
            # 3. Lưu mapping cho version này
            if old_key != canonical_key:
                self.version_maps[version][old_key] = canonical_key

    def get_replacements(self, version: str) -> dict:
        """Trả về dict {old_key: new_key} để replace trong text."""
        return self.version_maps.get(version, {})

    def export_bib_string(self) -> str:
        """Xuất chuỗi BibTeX chuẩn cho file refs.bib"""
        bib_content = ""
        for fp in self.unique_refs_pool:
            item = self.unique_refs_pool[fp]
            key = item['canonical_key']
            text = item['raw_text']
            entry = f"@misc{{{key},\n  text = {{{text}}}\n}}\n\n"
            bib_content += entry
        return bib_content

    def get_all_deduplicated_refs(self) -> list:
        """Trả về danh sách các reference duy nhất."""
        return list(self.unique_refs_pool.values())


class ContentDeduplicator:
    """
    Loại bỏ content trùng lặp giữa các versions của document.
    
    Sử dụng MD5 hash để so sánh content của các nodes trong cây cấu trúc.
    """
    
    def __init__(self):
        # elements: { "id": "content string" }
        self.global_elements = {}
        
        # Helper to find existing IDs by content: { "hash": "id" }
        self.content_hash_map = {}
        
        # hierarchy: { "1": { "child_id": "parent_id" }, "2": ... }
        self.final_hierarchy = {}

    def _get_content_hash(self, content: str, type_name: str) -> str:
        """Hash content + type để xác định duplicates."""
        if content is None: content = ""
        raw_str = f"{type_name}:{str(content).strip()}"
        return hashlib.md5(raw_str.encode('utf-8')).hexdigest()

    def _extract_version_number(self, version_str: str) -> str:
        """
        Trích xuất version number từ folder name.
        Example: '2403-00531/v1' -> '1'
        """
        parts = version_str.split('v')
        if len(parts) > 1:
            return parts[-1]
        return version_str

    def register_node(self, node: dict) -> str:
        """
        Đăng ký node content.
        
        Returns:
            str: ID của node (existing ID nếu duplicate, new ID nếu mới)
        """
        content = node.get('raw_content', '')
        if not content:
            content = node.get('content', '')
            
        node_type = node.get('type', 'unknown')
        
        # Case 1: Node không có content
        if not content.strip():
            if node.get('title'):
                 self.global_elements[node['id']] = node['title']
            return node['id']

        # Case 2: Node có content -> Deduplicate
        content_hash = self._get_content_hash(content, node_type)
        
        if content_hash in self.content_hash_map:
            # Duplicate found!
            return self.content_hash_map[content_hash]
        
        # New content
        current_id = node['id']
        self.global_elements[current_id] = content
        self.content_hash_map[content_hash] = current_id
        
        return current_id

    def process_version(self, full_version_str: str, root_node: dict):
        """
        Duyệt cây cho một version cụ thể.
        
        Args:
            full_version_str: Version identifier (e.g., "paper_id/v1")
            root_node: Root node của cây cấu trúc
        """
        ver_num = self._extract_version_number(full_version_str)
        version_map = {}
        
        def traverse(current_node, parent_id_context=None):
            unified_id = self.register_node(current_node)
            
            if parent_id_context:
                version_map[unified_id] = parent_id_context

            for child in current_node.get('children', []):
                traverse(child, parent_id_context=unified_id)
        
        traverse(root_node)
        self.final_hierarchy[ver_num] = version_map
        
    def get_final_json(self) -> dict:
        """
        Xuất JSON structure cuối cùng.
        
        Returns:
            dict với keys 'hierarchy' và 'elements'
        """
        return {
            "hierarchy": self.final_hierarchy,
            "elements": self.global_elements
        }


def replace_citations_in_text(text: str, replacement_map: dict) -> str:
    """
    Thay thế \\cite{old} thành \\cite{new} trong văn bản.
    
    Args:
        text: Văn bản LaTeX
        replacement_map: Dict {old_key: new_key}
        
    Returns:
        Văn bản đã được thay thế
    """
    if not replacement_map:
        return text
        
    def replace_match(match):
        inner = match.group(2)
        keys = [k.strip() for k in inner.split(',')]
        new_keys = [replacement_map.get(k, k) for k in keys]
        return f"{match.group(1)}{', '.join(new_keys)}{match.group(3)}"

    pattern = re.compile(r'(\\cite[a-z]*\s*(?:\[.*?\])?\s*\{)([^}]+)(\})', re.IGNORECASE)
    return pattern.sub(replace_match, text)
