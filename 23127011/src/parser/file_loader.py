import os
import re

# Các thư mục không cần quét để tối ưu tốc độ
BLOCKLIST_DIRS = {'.git', 'images', 'figures', '__pycache__', 'node_modules', 'media'}

def build_dependency_map(folder_path):
    """
    Xây dựng bản đồ phụ thuộc: File nào bị file nào gọi?
    Trả về dict: { 'child_full_path': ['parent_full_path'] }
    """
    dependency_map = {}
    name_to_path = {}
    
    # 1. Map toàn bộ file .tex trong folder này để tra cứu nhanh
    for root, dirs, files in os.walk(folder_path):
        dirs[:] = [d for d in dirs if d not in BLOCKLIST_DIRS]
        for f in files:
            if f.lower().endswith('.tex'):
                full_path = os.path.join(root, f)
                name_to_path[f] = full_path

    # 2. Quét nội dung để tìm quan hệ cha-con
    for root, dirs, files in os.walk(folder_path):
        dirs[:] = [d for d in dirs if d not in BLOCKLIST_DIRS]
        for file in files:
            if not file.lower().endswith('.tex'): continue
            
            parent_path = os.path.join(root, file)
            try:
                with open(parent_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    # Tìm lệnh \input, \include, \subfile
                    # Regex bắt: \input{filename}
                    matches = re.findall(r'\\(?:input|include|subfile)(?:\[.*?\])?\{([^}]+)\}', content)
                    
                    for match in matches:
                        child_name = os.path.basename(match.strip())
                        if not child_name.lower().endswith('.tex'): 
                            child_name += '.tex'
                        
                        # Nếu file con tồn tại trong danh sách file của folder
                        if child_name in name_to_path:
                            child_path = name_to_path[child_name]
                            
                            # Ghi nhận: child_path bị gọi bởi parent_path
                            if child_path not in dependency_map:
                                dependency_map[child_path] = []
                            dependency_map[child_path].append(parent_path)
            except:
                pass
                
    return dependency_map

def get_score(file_path, content, context_files, dependency_map):
    """Hàm chấm điểm logic LaTeX chuẩn"""
    filename = os.path.basename(file_path)
    base_name = os.path.splitext(filename)[0]
    clean_content = re.sub(r'%.*', '', content) # Xóa comment
    
    score = 0
    
    # --- 1. CẤU TRÚC BẮT BUỘC (GATEKEEPER) ---
    # Nếu không có documentclass -> Loại ngay (Theo yêu cầu bỏ Plain TeX)
    if r'\documentclass' not in clean_content:
        return -1000 
    
    # Có documentclass là đạt yêu cầu cơ bản
    score += 20
    
    if r'\begin{document}' in clean_content:
        score += 20
        
    # --- 2. DEPENDENCY CHECK (QUAN TRỌNG) ---
    # Nếu file này bị file khác gọi -> Nó là file con -> Trừ điểm cực nặng
    if file_path in dependency_map:
        # Trừ 50 điểm cho mỗi lần bị gọi
        score -= 50 * len(dependency_map[file_path])

    # --- 3. DẤU HIỆU "VỆ TINH" (FORENSICS) ---
    # File .bbl sinh ra trùng tên file gốc -> Dấu hiệu mạnh nhất
    if f"{base_name}.bbl" in context_files: score += 60
    if f"{base_name}.bib" in context_files: score += 20
    if f"{base_name}.log" in context_files: score += 30
    
    # --- 4. NỘI DUNG ---
    if r'\bibliography' in clean_content or r'\begin{thebibliography}' in clean_content: score += 15
    if r'\maketitle' in clean_content: score += 10
    if r'\begin{abstract}' in clean_content: score += 10
    
    # Đếm số lượng file con mà nó gọi (Nhạc trưởng thường gọi nhiều nhạc công)
    input_count = len(re.findall(r'\\(input|include|subfile)\{', clean_content))
    score += min(input_count * 3, 30) # Max cộng 30 điểm

    # --- 5. HEURISTIC TÊN FILE ---
    lower_name = filename.lower()
    
    # Điểm cộng tên chuẩn
    if lower_name in ['main.tex', 'ms.tex', 'paper.tex', 'article.tex']: 
        score += 10
    
    # Điểm trừ tên file rác/template
    if any(x in lower_name for x in ['template', 'sample', 'example']) and score < 60:
        score -= 10
    if 'response' in lower_name or 'reply' in lower_name or 'letter' in lower_name:
        score -= 50
        
    # Trừ điểm file slide, standalone
    if r'\documentclass{beamer}' in clean_content: score -= 50
    if r'\documentclass{standalone}' in clean_content: score -= 20
    if r'\documentclass{letter}' in clean_content: score -= 50

    return score

def find_root_tex_file(version_folder_path):
    """
    Hàm chính: Tìm file LaTeX gốc trong thư mục version.
    Input: Đường dẫn tới folder chứa code (vd: .../tex/version1)
    Output: Đường dẫn tuyệt đối tới file main.tex (hoặc None nếu không tìm thấy)
    """
    # 1. Xây dựng bản đồ phụ thuộc trước
    dep_map = build_dependency_map(version_folder_path)
    
    # 2. Lấy danh sách toàn bộ file để check vệ tinh (.bbl, .bib)
    all_files = set()
    tex_files = []
    
    for root, dirs, files in os.walk(version_folder_path):
        dirs[:] = [d for d in dirs if d not in BLOCKLIST_DIRS]
        for f in files:
            all_files.add(f)
            if f.lower().endswith('.tex'):
                tex_files.append(os.path.join(root, f))
    
    if not tex_files:
        return None

    # 3. Chấm điểm từng ứng viên
    candidates = []
    for path in tex_files:
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                score = get_score(path, content, all_files, dep_map)
                
                # Chỉ lấy ứng viên có điểm dương hoặc ít nhất không bị loại (-1000)
                if score > -100:
                    candidates.append({
                        'path': path, 
                        'name': os.path.basename(path),
                        'score': score, 
                        'len': len(content)
                    })
        except:
            pass

    if not candidates:
        return None
    
    # 4. Sắp xếp: Ưu tiên Điểm cao -> Sau đó đến độ dài nội dung
    candidates.sort(key=lambda x: (x['score'], x['len']), reverse=True)
    
    # 5. Xử lý Tie-breaker (nếu Top 1 và Top 2 điểm bằng nhau)
    if len(candidates) >= 2:
        top1 = candidates[0]
        top2 = candidates[1]
        
        # Nếu điểm chênh lệch không đáng kể (< 5)
        if (top1['score'] - top2['score']) < 5:
            # Ưu tiên file có tên chuẩn
            prio_names = ['main.tex', 'ms.tex', 'paper.tex', 'article.tex']
            if top1['name'].lower() not in prio_names and top2['name'].lower() in prio_names:
                return top2['path']
            
            # Nếu tên cũng không giúp ích, lấy file NẶNG HƠN ĐÁNG KỂ
            if top2['len'] > top1['len'] * 1.5: 
                return top2['path']

    # Trả về đường dẫn của ứng viên số 1
    return candidates[0]['path']
