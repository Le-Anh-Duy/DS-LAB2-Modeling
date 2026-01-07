import os
import re
import uuid
import json
from src.utils.tex_cleaner import LatexCleaner
class LatexFlattener:
    """
    A class to flatten LaTeX documents by recursively merging all included files into a single structure.
    This class processes a root LaTeX file and recursively resolves all \input, \include, and \subfile
    commands to create a flattened representation of the entire document. It also handles circular
    dependencies, missing files, and removes comments and bibliography sections.
    Attributes:
        root_path (str): Absolute path to the root LaTeX file.
        root_dir (str): Directory containing the root LaTeX file.
        paper_id (str): Identifier for the paper being processed.
        version (str): Version identifier for the paper.
        remove_references (bool): Flag to control whether to remove bibliography sections.
        merged_files (list): List of relative paths of files successfully merged.
        missing_files (list): List of relative paths of files that could not be found.
    Methods:
        flatten():
            Main method that processes the root file and returns a dictionary containing
            the flattened content along with metadata.
            Returns:
                dict: A dictionary with keys:
                    - paper_id: Identifier of the paper
                    - version: Version of the paper
                    - root_file_path: Absolute path to root file
                    - metadata: Dictionary containing processing statistics
                    - content: Flattened LaTeX content as string
        _read_file(path):
            Reads content from a file with UTF-8 encoding.
            Args:
                path (str): Path to the file to read.
            Returns:
                str or None: File content if successful, None otherwise.
        _remove_comments(text):
            Removes LaTeX comments (lines starting with %) while preserving escaped percent signs.
            Args:
                text (str): LaTeX content to process.
            Returns:
                str: Content with comments removed.
        _remove_bibliography(text):
            Removes bibliography-related commands and environments from LaTeX content.
            Args:
                text (str): LaTeX content to process.
            Returns:
                str: Content with bibliography sections removed.
        _process_file(current_path, visited=None):
            Recursively processes a LaTeX file and all its dependencies.
            Args:
                current_path (str): Path to the current file being processed.
                visited (set, optional): Set of already visited file paths to detect circular dependencies.
            Returns:
                str: Flattened content with markers indicating file boundaries.
    Example:
        >>> flattener = LatexFlattener('/path/to/main.tex', 'paper123', 'v1', remove_references=True)
        >>> result = flattener.flatten()
        >>> print(result['metadata']['merged_count'])
    """
    def __init__(self, root_file_path, paper_id, version, remove_references=True):
        self.root_path = os.path.abspath(root_file_path)
        self.root_dir = os.path.dirname(self.root_path)
        self.paper_id = paper_id
        self.version = version
        self.remove_references = remove_references
        print(f"📝 Khởi tạo LatexFlattener cho Paper: {self.paper_id}, Version: {self.version}")
        print(f"   Remove references: {'Yes' if self.remove_references else 'No'}")
        self.merged_files = [] # Danh sách các file đã gộp thành công
        self.missing_files = [] # Danh sách các file bị thiếu

    def flatten(self):
        """
        Hàm chính: Thực hiện gộp và trả về cấu trúc Dictionary (JSON object)
        """
        # Bắt đầu đệ quy từ root
        full_content = self._process_file(self.root_path)
        
        # Tạo object kết quả
        result_object = {
            "paper_id": self.paper_id,
            "version": self.version,
            "root_file_path": self.root_path,
            "metadata": {
                "total_length": len(full_content),
                "merged_count": len(self.merged_files),
                "merged_files": self.merged_files,
                "missing_files": self.missing_files,
                "remove_references": self.remove_references
            },
            "content": full_content
        }
        return result_object

    def _read_file(self, path):
        if not os.path.exists(path): return None
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except: return None

    def _remove_comments(self, text):
        """Xóa comment gốc của tác giả để giảm nhiễu, nhưng giữ lại marker của mình sau này"""
        # Regex: Tìm ký tự % không đi sau dấu \
        return re.sub(r'(?<!\\)%.*', '', text)

    def _remove_bibliography(self, text):
        """Loại bỏ phần tài liệu tham khảo theo yêu cầu"""
        if not self.remove_references:
            return text
        
        text = re.sub(r'\\bibliography\{[^}]+\}', '', text)
        text = re.sub(r'\\printbibliography', '', text)
        text = re.sub(r'\\begin\{thebibliography\}.*?\\end\{thebibliography\}', '', text, flags=re.DOTALL)
        return text

    def _process_file(self, current_path, visited=None):
        if visited is None: visited = set()
        
        abs_path = os.path.abspath(current_path)
        rel_path = os.path.relpath(abs_path, self.root_dir).replace('\\', '/') # Chuẩn hóa đường dẫn
        
        # 1. Check vòng lặp
        if abs_path in visited:
            return f"\n% <WARNING: Circular dependency detected for {rel_path}>\n"
        visited.add(abs_path)

        # 2. Đọc nội dung
        raw_content = self._read_file(abs_path)
        if raw_content is None:
            self.missing_files.append(rel_path)
            return f"\n% <WARNING: File not found: {rel_path}>\n"
        
        self.merged_files.append(rel_path)

        # 3. Làm sạch sơ bộ (Xóa comment gốc + Xóa Bib nếu cờ bật)
        content = self._remove_comments(raw_content)
        content = self._remove_bibliography(content)

        # 4. Tìm và thay thế đệ quy các file con
        # Regex hỗ trợ: \input{file}, \include{file}, \subfile{file}, \input file
        pattern = re.compile(r'\\(?:input|include|subfile)(?:(?:\s*\{([^}]+)\})|(?:\s+([^\s%]+)))')

        def replace_match(match):
            fname = match.group(1) or match.group(2)
            if not fname: return ""
            fname = fname.strip()
            if not fname.lower().endswith('.tex'): fname += '.tex'
            
            # Resolve path
            child_path = os.path.join(self.root_dir, fname)
            if not os.path.exists(child_path):
                child_path = os.path.join(os.path.dirname(abs_path), fname)
            
            # Đệ quy
            child_content = self._process_file(child_path, visited)
            
            # QUAN TRỌNG: Kẹp nội dung giữa 2 Marker
            return (f"\n% <BEGIN_FILE: {fname}>\n"
                    f"{child_content}"
                    f"\n% <END_FILE: {fname}>\n")

        flattened_content = pattern.sub(replace_match, content)
        
        return flattened_content

class LatexStructureBuilder:
    def __init__(self, flattened_content, paper_id, version):
        self.content = flattened_content
        self.paper_id = paper_id
        self.version = version
        # Định nghĩa thứ tự cấp bậc (nhỏ hơn là cấp cao hơn/cha)
        self.HIERARCHY_LEVELS = {
            'document': 0,      # Root
            'part': 1,
            'chapter': 2,
            'section': 3,
            'subsection': 4,
            'subsubsection': 5,
            'paragraph': 6,
            'subparagraph': 7
        }
        # Regex để bắt các header: \section{Title}, \section*{Title}, \chapter{...}
        # Group 1: command (section, chapter...)
        # Group 2: * (nếu có)
        # Group 3: Title
        self.SECTION_START_REGEX = re.compile(
            r'\\(part|chapter|section|subsection|subsubsection|paragraph|subparagraph)(\*?)\s*\{', 
            re.IGNORECASE
        )

    def _extract_balanced_title(self, start_idx):
        """
        Hàm phụ trợ để lấy nội dung trong ngoặc nhọn {} có lồng nhau.
        start_idx: Vị trí ngay sau dấu '{' mở đầu.
        Returns: (title_content, end_idx)
        """
        depth = 1
        current_idx = start_idx
        max_len = len(self.content)
        
        while current_idx < max_len and depth > 0:
            char = self.content[current_idx]
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
            
            if depth > 0:
                current_idx += 1
        
        # current_idx lúc này đang ở dấu '}' đóng cuối cùng
        title = self.content[start_idx:current_idx]
        return title, current_idx + 1  # +1 để nhảy qua dấu '}'

    def build_coarse_tree(self):
        root = {
            'id': f'{self.paper_id}-{self.version}-document-{uuid.uuid4()}',
            'type': 'document',
            'title': 'Root Document',
            'level': 0,
            'raw_content': "",
            'children': []
        }
        stack = [root]
        
        cleaner = LatexCleaner()
        # SỬA 2: Logic lặp thay đổi để kết hợp Regex + Manual Counting
        cursor = 0
        
        # Tìm tất cả các điểm bắt đầu
        # Lưu ý: finditer sẽ tìm các match.
        matches = list(self.SECTION_START_REGEX.finditer(self.content))
        
        for match in matches:
            match_start = match.start()
            match_end = match.end() # Vị trí ngay sau dấu '{'
            
            # Nếu match nằm trước cursor (đã bị xử lý bởi logic lồng nhau nào đó - hiếm gặp nhưng cứ check), bỏ qua
            if match_start < cursor: 
                continue

            command = match.group(1)
            is_starred = match.group(2) == '*'
            
            # SỬA 3: Dùng hàm đếm ngoặc để lấy title chính xác
            # title_raw sẽ chứa: "\textbf{Spiral-type galaxies}" (bao gồm cả command bên trong)
            title_raw, end_idx = self._extract_balanced_title(match_end)
            
            # SỬA 4: Clean title ngay tại đây (Dùng LatexCleaner đã viết ở câu trước)
            # Bước này cực quan trọng để biến "\textbf{Spiral...}" thành "Spiral..."
            # Giả sử bạn đã import class LatexCleaner
            # title_clean = LatexCleaner.clean_latex(title_raw) 
            title_clean = cleaner.clean_latex(title_raw) # Tạm thời để raw nếu chưa tích hợp Cleaner

            # --- Logic Gán Content & Tạo Node (như cũ) ---
            current_level = self.HIERARCHY_LEVELS.get(command, 100)
            
            # Lấy text đoạn trước header này gán cho node trước đó
            text_segment = self.content[cursor:match_start]
            if text_segment.strip():
                if 'raw_content' not in stack[-1]: stack[-1]['raw_content'] = ""
                stack[-1]['raw_content'] += text_segment

            # Adjust Stack
            while len(stack) > 1 and stack[-1]['level'] >= current_level:
                stack.pop()
            
            parent = stack[-1]

            # Bỏ qua References (Optional)
            if 'references' in title_clean.lower() or 'tài liệu tham khảo' in title_clean.lower():
                cursor = end_idx # Nhảy qua header này
                # Tùy logic của bạn: có thể muốn gán references vào content của parent
                # hoặc tạo một node riêng. Ở đây ta pass để xử lý tiếp content
                # pass 
            
            new_node = {
                'id': f'{self.paper_id}-{self.version}-{command}-{uuid.uuid4()}',
                'type': command,
                'title': title_clean.strip(), # Title đã sạch
                'level': current_level,
                'is_starred': is_starred,
                'raw_content': "", 
                'children': []
            }

            parent['children'].append(new_node)
            stack.append(new_node)
            
            # Cập nhật cursor đến hết phần header vừa xử lý (bao gồm cả dấu đóng ngoặc đúng)
            cursor = end_idx

        # Xử lý phần dư cuối cùng
        remaining_text = self.content[cursor:]
        if remaining_text.strip():
            if 'raw_content' not in stack[-1]: stack[-1]['raw_content'] = ""
            stack[-1]['raw_content'] += remaining_text

        return root

    def print_tree(self, node, indent=0):
        """Hàm helper để in cây ra console kiểm tra"""
        prefix = "  " * indent
        preview = (node.get('raw_content', '')[:50] + '...') if node.get('raw_content') else "[Empty]"
        print(f"{prefix}- [{node['type'].upper()}] {node['title']} (ID: {node['id'][:8]})")
        print(f"{prefix}  Content Preview: {preview}")
        
        for child in node['children']:
            self.print_tree(child, indent + 1)
    
    def print_tree_to_file(self, root_node, output_path):
        """
        In cây ra file JSON với danh sách nodes và edges
        
        Args:
            root_node: Node gốc của cây
            output_path: Đường dẫn file JSON để lưu
        
        Output format:
        {
            "nodes": [
                {
                    "id": "uuid",
                    "type": "section",
                    "title": "Section Title",
                    "level": 3,
                    "content": "raw content..."
                }
            ],
            "edges": [
                {
                    "from": "parent_id",
                    "to": "child_id"
                }
            ]
        }
        """
        nodes = []
        edges = []
        
        def traverse(node, parent_id=None):
            # Thêm node hiện tại vào danh sách
            node_data = {
                "id": node['id'],
                "type": node['type'],
                "title": node['title'],
                "level": node['level'],
                "content": node.get('raw_content', '')
            }
            nodes.append(node_data)
            
            # Nếu có parent, tạo edge
            if parent_id is not None:
                edges.append({
                    "from": parent_id,
                    "to": node['id']
                })
            
            # Đệ quy cho các children
            for child in node.get('children', []):
                traverse(child, node['id'])
        
        # Bắt đầu traverse từ root
        traverse(root_node)
        
        # Tạo cấu trúc dữ liệu cuối cùng
        output_data = {
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "total_nodes": len(nodes),
                "total_edges": len(edges)
            }
        }
        
        # Ghi ra file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Đã lưu cấu trúc cây vào: {output_path}")
        print(f"   - Tổng số nodes: {len(nodes)}")
        print(f"   - Tổng số edges: {len(edges)}")

    def export_to_markdown(self, root_node):
        """
        Export the parsed tree to Markdown format.
        
        Args:
            root_node: The root node of the parsed tree.
            
        Returns:
            str: The content in Markdown format.
        """
        def traverse_and_build(node, depth=0):
            md = ""
            
            # --- HANDLE METADATA NODES ---
            if node['type'] == 'title':
                return f"# {node['title']}\n\n"
            
            if node['type'] == 'author':
                # Lấy nội dung author (có thể lưu ở title hoặc content/raw_content)
                val = node.get('content', node.get('raw_content', node['title']))
                return f"**Authors:** {val}\n\n"

            if node['type'] == 'abstract':
                md += "## Abstract\n\n"
                # Abstract children are sentences, handled by recursion
            
            # 1. Add Header with appropriate Markdown level
            # Skip header for metadata nodes handled above
            elif node['level'] > 0 and node['level'] < 99:
                # Map LaTeX levels to Markdown headers
                md_level = min(node['level'], 6)
                md += f"\n{'#' * md_level} {node['title']}\n\n"
            
            # 2. Add Content based on type
            raw_content = node.get('raw_content', '').strip()
            
            if node['type'] == 'equation':
                md += f"$$\n{raw_content}\n$$\n\n"
            
            elif node['type'] == 'figure':
                md += f"> **[{node['title']}]**\n> {raw_content}\n\n"
            
            elif node['type'] == 'list':
                md += "\n"  # Lists handled by children
            
            elif node['type'] == 'list_item':
                indent = "  " * depth
                md += f"{indent}- {raw_content}\n"
            
            elif node['type'] == 'sentence':
                md += f"{raw_content}\n\n"
            
            elif node['type'] not in ['abstract'] and raw_content:
                # For other types, just add raw content if exists
                md += f"{raw_content}\n\n"
            
            # 3. Recurse Children
            for child in node.get('children', []):
                # Increase depth for list items
                child_depth = depth + 1 if node['type'] == 'list' else depth
                md += traverse_and_build(child, child_depth)
            
            return md
        
        markdown_content = traverse_and_build(root_node)
        return markdown_content.strip()

    def export_to_html(self, root_node):
        """
        Export the parsed tree to HTML format.
        
        Args:
            root_node: The root node of the parsed tree.
            
        Returns:
            str: The content in HTML format.
        """
        def traverse_and_build(node):
            html = ""
            
            # --- HANDLE METADATA NODES ---
            if node['type'] == 'title':
                return f"<h1 class='paper-title'>{node['title']}</h1>\n"
            
            if node['type'] == 'author':
                 val = node.get('content', node.get('raw_content', node['title']))
                 return f"<div class='authors'><strong>Authors:</strong> {val}</div>\n"
            
            if node['type'] == 'abstract':
                html += "<section class='abstract'>\n<h2>Abstract</h2>\n"
                for child in node.get('children', []):
                    html += traverse_and_build(child)
                html += "</section>\n"
                return html

            # 1. Add Header with appropriate HTML tag
            if node['level'] > 0 and node['level'] < 99:
                html_level = min(node['level'], 6)
                html += f"<h{html_level}>{node['title']}</h{html_level}>\n"
            
            # 2. Add Content based on type
            raw_content = node.get('raw_content', '').strip()
            
            if node['type'] == 'equation':
                # Use MathJax/KaTeX compatible format
                html += f'<div class="equation">\n$$\n{raw_content}\n$$\n</div>\n'
            
            elif node['type'] == 'figure':
                html += f'<figure>\n<figcaption>{node["title"]}</figcaption>\n<blockquote>{raw_content}</blockquote>\n</figure>\n'
            
            elif node['type'] == 'list':
                # Determine list type
                list_tag = "ol" if "enumerate" in node.get('title', '').lower() else "ul"
                html += f"<{list_tag}>\n"
                
                # Process children
                for child in node.get('children', []):
                    html += traverse_and_build(child)
                
                html += f"</{list_tag}>\n"
                return html  # Return early to avoid duplicate child processing
            
            elif node['type'] == 'list_item':
                html += f"<li>{raw_content}</li>\n"
            
            elif node['type'] == 'sentence':
                html += f"<p>{raw_content}</p>\n"
            
            elif raw_content:
                # For other types, wrap in div or paragraph
                html += f"<div>{raw_content}</div>\n"
            
            # 3. Recurse Children (skip if already handled like in list or abstract)
            if node['type'] != 'list' and node['type'] != 'abstract':
                for child in node.get('children', []):
                    html += traverse_and_build(child)
            
            return html
        
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{self.paper_id} - {self.version}</title>
    <script src="https://polyfill.io/v3/polyfill.min.js?features=es6"></script>
    <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; max-width: 900px; margin: 0 auto; padding: 40px; line-height: 1.6; color: #333; }}
        h1.paper-title {{ text-align: center; color: #2c3e50; margin-bottom: 10px; }}
        .authors {{ text-align: center; font-style: italic; color: #555; margin-bottom: 30px; }}
        .abstract {{ background: #f9f9f9; padding: 20px; border-radius: 8px; margin-bottom: 30px; border-left: 5px solid #3498db; }}
        h1, h2, h3, h4, h5, h6 {{ color: #2c3e50; margin-top: 24px; }}
        .equation {{ margin: 20px 0; text-align: center; background: #fff; padding: 10px; overflow-x: auto; }}
        figure {{ border: 1px solid #ddd; padding: 10px; margin: 20px 0; border-radius: 4px; background: #fafafa; }}
        figcaption {{ font-weight: bold; margin-bottom: 5px; color: #666; }}
        blockquote {{ margin: 0; color: #777; font-style: italic; }}
        p {{ margin-bottom: 12px; }}
        li {{ margin-bottom: 5px; }}
    </style>
</head>
<body>
{traverse_and_build(root_node)}
</body>
</html>"""
        
        return html_content

    def export_cleaned_paper(self, root_node):
        """
        Reconstruct the cleaned LaTeX content from the tree.
        This allows checking if the parsing logic preserved the content integrity.
        
        Args:
            root_node: The root node of the parsed tree.
            
        Returns:
            str: The reconstructed LaTeX string.
        """
        def traverse_and_build(node):
            text = ""
            
            # 1. Reconstruct Header (if not Document root)
            if node['level'] > 0 and node['level'] < 99:
                lat_sections = {'part', 'chapter', 'section', 'subsection', 'subsubsection', 'paragraph', 'subparagraph'}
                if node['type'] in lat_sections:
                    star = "*" if node.get('is_starred') else ""
                    text += f"\n\\{node['type']}{star}{{{node['title']}}}\n\n"
            
            # 2. Add Content based on type
            raw_content = node.get('raw_content', '').strip()
            
            if node['type'] == 'equation':
                text += f"\n{raw_content}\n\n"
            elif node['type'] == 'figure':
                text += f"\n{raw_content}\n\n"
            elif node['type'] == 'list_item':
                text += f"\\item {raw_content}\n"
            elif node['type'] == 'list':
                list_type = "itemize"
                if "enumerate" in node.get('title', '').lower():
                    list_type = "enumerate"
                text += f"\n\\begin{{{list_type}}}\n"
                for child in node.get('children', []):
                    text += traverse_and_build(child)
                text += f"\\end{{{list_type}}}\n\n"
                return text  # Return early to avoid duplicate processing
            elif raw_content:
                text += f"{raw_content}\n\n"
            
            # 3. Recurse Children
            if node['type'] != 'list':
                for child in node.get('children', []):
                    text += traverse_and_build(child)
                
            return text

        return traverse_and_build(root_node).strip()

class LatexContentProcessor:
    def __init__(self, paper_id, version):
        self.paper_id = paper_id
        self.version = version
        
        # --- REGEX PATTERNS ---
        
        # 1. Block Math: $$...$$, \[...\], \begin{equation}...
        self.REGEX_MATH_BLOCK = re.compile(
            r'\\begin\{equation\*?\}.*?\\end\{equation\*?\}|\\\[.*?\\\]|\$\$.*?\$\$', 
            re.DOTALL
        )
        
        # 2. Figures/Tables: \begin{figure/table}...
        self.REGEX_FIGURE = re.compile(
            r'\\begin\{(?:figure|table)\*?\}.*?\\end\{(?:figure|table)\*?\}', 
            re.DOTALL | re.IGNORECASE
        )
        
        # 3. Lists: \begin{itemize/enumerate}...
        self.REGEX_LIST = re.compile(
            r'(\\begin\{(itemize|enumerate)\}.*?\\end\{(itemize|enumerate)\})', 
            re.DOTALL
        )
        
        # 4. Sentence Splitter: Tìm dấu chấm/hỏi/thán kết thúc câu
        # Xử lý các trường hợp đặc biệt: abbreviations, số thập phân, trích dẫn
        
        # Danh sách abbreviations phổ biến trong paper khoa học
        abbrev_pattern = r'(?:Fig|Eq|Eqs|Tab|Sec|Ref|Vol|No|Ch|Dr|Prof|Ph\.D|' \
                        r'et al|i\.e|e\.g|vs|cf|etc|approx|ca|viz)'
        
        # Pattern chính:
        # - Không phải sau abbreviations
        # - Không phải giữa chữ cái đơn (U.S.)
        # - Không phải số thập phân (3.14)
        # - Cho phép dấu ngoặc kép/đơn sau dấu câu
        self.REGEX_SENTENCE = re.compile(
                    r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s+(?=[A-Z\(])'
                )

    def process_tree(self, node):
        """
        Duyệt đệ quy cây cấu trúc thô để "mổ xẻ" raw_content thành các elements.
        """
        # 1. Xử lý raw_content của node hiện tại (nếu có)
        if node.get('raw_content') and node['raw_content'].strip():
            # Tách nội dung thành các node con chi tiết (câu, hình, công thức...)

            if node.get('level') == 0 and node['type'] == 'document':
                # Với document root, ta có thể muốn xử lý preamble riêng
                # Giả sử ta có hàm _process_preamble để trích xuất title, author, abstract
                preamble_nodes = self._process_preamble(node['raw_content'])
                
                # Chèn các node preamble vào đầu danh sách children
                node['children'] = preamble_nodes + node['children']
                
                # Xóa raw_content để giải phóng bộ nhớ và đánh dấu là đã xử lý
                del node['raw_content']
            else:
                fine_grained_nodes = self.parse_content_blocks(node['raw_content'])
                # print(fine_grained_nodes)
                # QUAN TRỌNG: Chèn các node nội dung vào ĐẦU danh sách children
                # Lý do: Trong LaTeX, text của Section luôn nằm trước Subsection con.
                node['children'] = fine_grained_nodes + node['children']
                
                # Xóa raw_content để giải phóng bộ nhớ và đánh dấu là đã xử lý
                del node['raw_content']

        # 2. Đệ quy xử lý các con (bao gồm cả các Subsection cũ và các List mới tạo)
        # Lưu ý: Ta chỉ đệ quy vào các node cấu trúc (part, chapter, section...) 
        # hoặc list, không cần đệ quy vào sentence/equation (node lá).
        for child in node['children']:
            # Chỉ đệ quy nếu node con đó có thể chứa content con (ví dụ List hoặc Section con)
            if child['type'] not in ['sentence', 'equation', 'figure', 'list_item']:
                self.process_tree(child)

    def parse_content_blocks(self, text):
        """
        Cắt chuỗi text hỗn hợp thành danh sách các Node Elements
        """
        elements = []
        
        # Pattern tổng hợp để split: Math OR Figure OR List

        combined_pattern_str = f"({self.REGEX_MATH_BLOCK.pattern}|{self.REGEX_FIGURE.pattern}|{self.REGEX_LIST.pattern})"

        pattern = re.compile(combined_pattern_str, re.DOTALL | re.IGNORECASE)
        # pattern = re.compile(
        #     f"({self.REGEX_MATH_BLOCK.pattern}|{self.REGEX_FIGURE.pattern}|{self.REGEX_LIST.pattern})",
        #     re.DOTALL | re.IGNORECASE
        # )
        # print(text)
        # Split text, giữ lại delimiter (chính là nội dung block)
        parts = pattern.split(text)
        cleaner = LatexCleaner()


        for part in parts:
            if not part: continue
            part = part.strip()
            if not part: continue

            # print(part)
            # --- PHÂN LOẠI & TẠO NODE ---
            
            # 1. Math Block
            if self.REGEX_MATH_BLOCK.fullmatch(part):
                elements.append(self._create_node(
                    type_name='equation',
                    title='Equation Block',
                    raw_content= cleaner.clean_equation(part)
                ))
            
            # 2. Figure/Table
            elif self.REGEX_FIGURE.fullmatch(part):
                elements.append(self._create_node(
                    type_name='figure',
                    title='Figure/Table',
                    raw_content= cleaner.clean_figure_table(part) #self._clean_latex(part)
                ))
            
            # 3. List (Itemize/Enumerate) -> Tạo cấu trúc lồng nhau
            elif self.REGEX_LIST.fullmatch(part):
                list_node = self._process_list_block(part)
                elements.append(list_node)
            
            # 4. Text thuần -> Tách thành Sentence Nodes
            else:
                sentences = self._split_sentences(part)
                for sent in sentences:
                    elements.append(self._create_node(
                        type_name='sentence',
                        title=sent[:30] + "...", # Title xem trước
                        raw_content=cleaner.clean_latex(sent)
                    ))
                    
        return elements
    
    def _process_preamble(self, preamble_text):
        """
        Input: Text vùng preamble.
        Output: List các Node (Title Node, Author Node, Abstract Node)
        """
        print("🔍 Xử lý Preamble để trích xuất Title, Authors, Abstract...")
        nodes = []
        cleaner = LatexCleaner()
        # 1. Trích xuất Title (Leaf Node)
        title_match = re.search(r'\\title(?:\s*\[.*?\])?\s*\{((?:[^{}]|{[^{}]*})*)\}', preamble_text, re.DOTALL | re.IGNORECASE)
        if title_match:
            clean_title = cleaner.clean_latex(title_match.group(1))
            nodes.append({
                "id": f"{self.paper_id}-{self.version}-title-{uuid.uuid4()}",
                "title": clean_title,
                "content": clean_title,
                "type": "title",
                "level": 99,
                "children": [] # Title là lá
            })

        # 2. Trích xuất Authors (Leaf Node)
        # Gom tất cả author thành 1 chuỗi hoặc tạo list
        authors = []
        for match in re.finditer(r'\\author(?:\s*\[.*?\])?\s*\{((?:[^{}]|{[^{}]*})*)\}', preamble_text, re.DOTALL | re.IGNORECASE):
            clean_auth = cleaner.clean_latex(match.group(1))
            if clean_auth:
                authors.append(clean_auth)
        
        if authors:
            nodes.append({
                "id": f"{self.paper_id}-{self.version}-authors-{uuid.uuid4()}",
                "title": ", ".join(authors), # Nối lại hoặc để array tùy cấu trúc của bạn
                "content": ", ".join(authors),
                "type": "author",
                "level": 99,
                "children": []
            })

        # 3. Trích xuất Abstract (Component Node - Có con là sentences) co level cung voi paragraph
        # Tìm abstract environment
        abs_match = re.search(r'\\begin\s*\{abstract\}(.*?)\\end\s*\{abstract\}', preamble_text, re.DOTALL | re.IGNORECASE)
        if not abs_match:
             # Fallback tìm lệnh \abstract{}
             abs_match = re.search(r'\\abstract\s*\{((?:[^{}]|{[^{}]*})*)\}', preamble_text, re.DOTALL | re.IGNORECASE)

        if abs_match:
            raw_abstract = abs_match.group(1)
            
            # QUAN TRỌNG: Dùng LatexContentProcessor để tách câu cho Abstract
            # Cắt chuỗi text hỗn hợp thành danh sách các Node Elements
            abstract_sentences = self.parse_content_blocks(raw_abstract)
            
            # Gán ID cha cho các câu này là abstract
            for sent in abstract_sentences:
                sent['parent'] = "abstract"

            nodes.append({
                "id": f"{self.paper_id}-{self.version}-abstract-{uuid.uuid4()}",
                "title": "Abstract",
                "content": "Abstract",
                "type": "abstract", # Đánh dấu nó là 1 section đặc biệt
                "level": 2,
                "children": abstract_sentences
            })

        return nodes

    def _process_list_block(self, list_content):
        """Xử lý riêng cho Itemize/Enumerate để tách các \item"""
        # 1. Xác định loại list (itemize hay enumerate)
        # Group 1 sẽ bắt được tên môi trường (itemize/enumerate)
        match = re.match(r'\\begin\{(itemize|enumerate)\}', list_content, re.IGNORECASE)
        list_type = match.group(1) if match else "itemize"

        list_node = self._create_node(
            type_name='list',
            title=f'List ({list_type})',
            raw_content="" 
        )
        
        # 2. Bóc vỏ (Unwrap) an toàn
        # Xóa thẻ mở đầu tiên (chỉ xóa 1 lần - count=1)
        # Regex bắt: \begin{type} theo sau có thể là [options]
        content_inner = re.sub(r'^\\begin\{' + list_type + r'\}(\[.*?\])?', '', list_content, count=1, flags=re.IGNORECASE).strip()
        
        # Xóa thẻ đóng cuối cùng (Neo vào cuối chuỗi $)
        content_inner = re.sub(r'\\end\{' + list_type + r'\}\s*$', '', content_inner, count=1, flags=re.IGNORECASE).strip()

        # 3. Tách các \item
        # Lúc này content_inner chỉ còn nội dung ruột, các list con (nếu có) vẫn nguyên vẹn
        items = re.split(r'\\item\s+', content_inner)
        
        for item in items:
            # Bỏ qua phần text rác trước \item đầu tiên (thường là khoảng trắng)
            if not item.strip(): 
                continue
                
            # Clean nội dung item
            # Lưu ý: KHÔNG dùng replace \end nữa vì ta đã bóc vỏ ở bước 2 rồi
            clean_content = self._clean_latex(item)
            
            if clean_content:
                item_node = self._create_node(
                    type_name='list_item',
                    title='List Item',
                    raw_content=clean_content
                )
                list_node['children'].append(item_node)
                
        return list_node
    

    def _create_node(self, type_name, title, raw_content):
        """Helper tạo node chuẩn theo format ID của bạn"""
        return {
            'id': f'{self.paper_id}-{self.version}-{type_name}-{uuid.uuid4()}',
            'type': type_name,
            'title': title,
            'level': 99, # Level thấp nhất (lá)
            'raw_content': raw_content,
            'children': []
        }

    def _split_sentences(self, text):
        """Tách câu"""
        text = re.sub(r'\s+', ' ', text) # Gộp newline thành space
        sentences = self.REGEX_SENTENCE.split(text)
        return [s.strip() for s in sentences if s.strip()]

    def _normalize_math(self, content):
        """Chuẩn hóa toán học: Convert $$ -> equation"""
        if content.startswith('$$') and content.endswith('$$'):
            inner = content[2:-2].strip()
            return f"\\begin{{equation}}{inner}\\end{{equation}}"
        elif content.startswith(r'\['):
            inner = content[2:-2].strip()
            return f"\\begin{{equation}}{inner}\\end{{equation}}"
        
        cleaner = LatexCleaner()
        content = cleaner.clean_equation(content)
        return content

    def _clean_latex(self, text):
        """Xóa các lệnh format rác"""
        # Xóa \centering, \hfill, label, cite, ref... tùy nhu cầu
        text = re.sub(r'\\(centering|hfill|vfill|noindent|small|tiny|large)', '', text)
        # Xóa optional params [htbp] của figure
        text = re.sub(r'\\begin\{(figure|table)\}\[.*?\]', r'\\begin{\1}', text)
        return text.strip()
