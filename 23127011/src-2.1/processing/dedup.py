import hashlib
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
        print(f"🔄 Processing hierarchy for version: {ver_num} (from {full_version_str})")
        
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
                # Root node might not be listed as a key, or points to null/root-marker
                # Listing 1 says: "higher-component-id": "root-document-id"
                # If current is root, we can skip adding it as a key, 
                # OR add it with a special parent if needed. 
                # Usually, we only map children to parents.
                pass 

            # C. Recursion
            for child in current_node.get('children', []):
                traverse(child, parent_id_context=unified_id)
        
        # Start traversal
        traverse(root_node, parent_id_context=None)
        
        # Store in final hierarchy
        self.final_hierarchy[ver_num] = version_map

    def get_final_json(self):
        return {
            "elements": self.global_elements,
            "hierarchy": self.final_hierarchy
        }