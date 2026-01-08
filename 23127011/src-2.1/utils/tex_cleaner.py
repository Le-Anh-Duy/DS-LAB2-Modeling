import re
import uuid

class LatexCleaner:
    # --- CẤU HÌNH ---
    
    # Regex bắt caption (giữ nguyên logic của bạn)
    REGEX_CAPTION = re.compile(r'(\\caption)(\[.*?\])?\{((?:[^{}]|{[^{}]*})*)\}', re.DOTALL)
    REGEX_INCLUDE_GRAPHICS = re.compile(r'(\\includegraphics)(\[.*?\])?\{([^}]*)\}')

    # 1. Các lệnh rác DELETE BLOCK (Xóa cả lệnh lẫn nội dung bên trong)
    # Thêm 'abstract' vào đây nếu muốn xóa nội dung abstract cũ (tùy nhu cầu), 
    # nhưng thường ta chỉ muốn xóa TAG abstract thôi (xử lý ở hàm clean_structure_tags)
    COMMANDS_TO_DELETE_BLOCK = [
        'footnote', 'todo', 'comment', 'note', 'thanks', 
        'label', 'cite', 'ref', 'eqref', 'bibliographystyle',
        'input', 'include', 'bibliography', 'acknowledgments' 
    ]

    # 2. Các lệnh FORMATTING cần DELETE COMMAND (Giữ lại text bên trong)
    # Tách riêng các lệnh style phổ biến để xử lý chính xác hơn
    COMMANDS_UNWRAP = [
        'textbf', 'textit', 'emph', 'textsc', 'text', 'mathrm', 'mathbf', 
        'section', 'subsection', 'subsubsection', 'paragraph', 'subparagraph'
    ]

    # 3. Các lệnh layout chỉ cần xóa lệnh (Solo commands)
    COMMANDS_LAYOUT_DELETE = [
        'centering', 'newpage', 'clearpage', 'tableofcontents', 
        'noindent', 'hfill', 'vfill', 'break', 'pagebreak',
        # 'toprule', 'midrule', 'bottomrule', 'hline', 'cline',
        'FloatBarrier', 'newline', 'maketitle', 'nocite', 'hbadness', 'preprint'
    ]

    # --- REGEX COMPILE ---
    
    # Pattern inline math: $...$ hoặc \(...\)
    # Dùng để bảo vệ math trước khi clean text
    REGEX_INLINE_MATH = re.compile(r'(\$[^$]+\$|\\\([^\)]+\\\))')

    # Xóa lệnh rác: \cmd{...}
    REGEX_DELETE_BLOCK = re.compile(
        r'\\(' + '|'.join(COMMANDS_TO_DELETE_BLOCK) + r')(\[[^\]]*\])?\{[^}]*\}'
    )

    # Xóa lệnh layout: \cmd
    REGEX_DELETE_LAYOUT = re.compile(
        r'\\(' + '|'.join(COMMANDS_LAYOUT_DELETE) + r')\b'
    )
    
    # Xử lý \texorpdfstring{Math}{Text} -> Lấy Math (group 1)
    # Regex này xử lý trường hợp đơn giản không lồng ngoặc quá phức tạp
    REGEX_TEXORPDFSTRING = re.compile(r'\\texorpdfstring\s*\{((?:[^{}]|{[^{}]*})*)\}\s*\{((?:[^{}]|{[^{}]*})*)\}')

    # Xử lý Formatting: \cmd{content} -> content
    REGEX_UNWRAP_CMD = re.compile(
        r'\\(' + '|'.join(COMMANDS_UNWRAP) + r')(\[[^\]]*\])?\{((?:[^{}]|{[^{}]*})*)\}'
    )

    # Xóa môi trường abstract (Chỉ xóa tag \begin{abstract} và \end{abstract})
    REGEX_ABSTRACT_TAGS = re.compile(r'\\(begin|end)\{abstract\}')

    @staticmethod
    def clean_latex(text, is_preamble_safe=False):
        if not text: return ""

        # 1. Cắt Preamble (nếu cần)
        if not is_preamble_safe and r'\begin{document}' in text:
            parts = text.split(r'\begin{document}')
            text = parts[1]
        
        # 2. Xóa \end{document}
        text = text.replace(r'\end{document}', '')

        # 3. Xóa comment
        text = re.sub(r'(?<!\\)%.*', '', text)

        # --- BƯỚC QUAN TRỌNG: BẢO VỆ MATH ---
        # Thay thế tất cả inline math $...$ bằng placeholder độc nhất
        # Điều này ngăn các bước clean bên dưới xóa nhầm biến số như \nu, \alpha bên trong $ $
        placeholders = {}
        
        def protect_math(match):
            key = f"__MATH_PROTECT_{uuid.uuid4().hex}__"
            placeholders[key] = match.group(0)
            return key

        text = LatexCleaner.REGEX_INLINE_MATH.sub(protect_math, text)

        # --- BẮT ĐẦU CLEAN (Trên text đã bảo vệ math) ---

        # 4. Xử lý \texorpdfstring{math}{text} -> giữ lại math
        # Chạy vòng lặp để xử lý lồng nhau (đơn giản)
        for _ in range(3): 
            text = LatexCleaner.REGEX_TEXORPDFSTRING.sub(r'\1', text)

        # 5. Xóa các lệnh rác (footnote, cite...)
        text = LatexCleaner.REGEX_DELETE_BLOCK.sub('', text)

        # 6. Xóa các lệnh layout (centering, hfill...)
        text = LatexCleaner.REGEX_DELETE_LAYOUT.sub('', text)

        # 7. Xóa tags Abstract (\begin{abstract})
        text = LatexCleaner.REGEX_ABSTRACT_TAGS.sub('', text)

        # 8. Unwrap Formatting (\textbf{text} -> text)
        # Chạy vòng lặp để xử lý lồng nhau: \textbf{\textit{ABC}} -> \textit{ABC} -> ABC
        for _ in range(5): # Chạy 3-5 lần để bóc hết các lớp lồng nhau
            new_text = LatexCleaner.REGEX_UNWRAP_CMD.sub(r'\3', text)
            if new_text == text:
                break
            text = new_text

        # 9. Dọn dẹp Text rác còn sót lại
        # Thay thế ngoặc đơn lẻ hoặc các ký tự điều khiển nếu cần thiết
        # Lưu ý: Không dùng regex catch-all solo (\\[a-z]+) nữa vì rất nguy hiểm
        
        # --- BƯỚC KHÔI PHỤC: RESTORE MATH ---
        for key, value in placeholders.items():
            text = text.replace(key, value)

        # Polish
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text

    @staticmethod
    def clean_figure_table(raw_block):
        """
        Phiên bản MỚI: Giữ lại toàn bộ nội dung bên trong (tabular, subfigure...),
        chỉ làm sạch vỏ bọc và các lệnh rác.
        """
        # 1. Chuẩn hóa thẻ mở: \begin{table}[htbp] -> \begin{table}
        # Chỉ xóa phần [options]
        raw_block = re.sub(r'(\\begin\{(figure|table)\*?\})(\[.*?\])?', r'\1', raw_block, flags=re.IGNORECASE)

        # 2. Xóa các lệnh layout không mong muốn bên trong block này
        # Lưu ý: Không xóa lệnh kẻ bảng (hline, toprule)
        raw_block = re.sub(r'\\(centering|hfill|vfill|noindent)', '', raw_block)

        # 3. Xóa lệnh \label{...} vì không cần hiển thị
        raw_block = re.sub(r'\\label\{((?:[^{}]|{[^{}]*})*)\}', '', raw_block)

        # 4. Xử lý Caption (Optional): Nếu muốn clean text trong caption
        # Tìm caption và thay thế nội dung bên trong bằng text đã clean
        def clean_caption_inner(match):
            prefix = match.group(1) # \caption
            opt = match.group(2) if match.group(2) else "" # [opt]
            content = match.group(3)
            # Clean nhẹ text trong caption (bỏ bold, italic...)
            cleaned_content = LatexCleaner.clean_latex(content, is_preamble_safe=True)
            return f"{prefix}{opt}{{{cleaned_content}}}"

        raw_block = LatexCleaner.REGEX_CAPTION.sub(clean_caption_inner, raw_block)

        # 5. Clean whitespace thừa nhưng giữ lại newline quan trọng cho bảng
        # (Nếu xóa hết newline thì tabular code sẽ khó đọc, nhưng hiển thị thì không sao)
        # Ở đây ta chỉ trim đầu đuôi.
        return raw_block.strip()

    @staticmethod
    def clean_equation(raw_block):
        # ... (Giữ nguyên logic của bạn) ...
        content = raw_block.strip()
        if content.startswith('$$') and content.endswith('$$'):
            inner = content[2:-2]
        elif content.startswith(r'\[') and content.endswith(r'\]'):
            inner = content[2:-2]
        elif content.startswith(r'\begin{equation'):
             match = re.search(r'\\begin\{equation\*?\}(.*?)\\end\{equation\*?\}', content, re.DOTALL)
             inner = match.group(1) if match else content
        else:
            return content

        # Clean nội dung bên trong equation (nhưng cẩn thận không xóa lệnh toán)
        # Chỉ xóa label và layout cụ thể
        inner = re.sub(r'\\label\{[^}]*\}', '', inner)
        inner = re.sub(r'\\(nonumber|notag)', '', inner)
        
        inner = inner.strip()        
        return f"\\begin{{equation}}{inner}\\end{{equation}}"