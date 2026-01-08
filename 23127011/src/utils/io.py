"""
I/O Utilities
=============

Các hàm tiện ích cho đọc/ghi file.
"""

import json
import os
from typing import Any, Optional


def read_json(filepath: str) -> Optional[dict]:
    """
    Đọc file JSON.
    
    Args:
        filepath: Đường dẫn file JSON
        
    Returns:
        dict hoặc None nếu lỗi
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        return None


def write_json(data: Any, filepath: str, indent: int = 2) -> bool:
    """
    Ghi data ra file JSON.
    
    Args:
        data: Data cần ghi
        filepath: Đường dẫn file output
        indent: Số spaces indent (mặc định: 2)
        
    Returns:
        True nếu thành công
    """
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
        return True
    except Exception:
        return False


def read_text(filepath: str, encoding: str = 'utf-8') -> Optional[str]:
    """
    Đọc file text.
    
    Args:
        filepath: Đường dẫn file
        encoding: Encoding (mặc định: utf-8)
        
    Returns:
        Nội dung file hoặc None nếu lỗi
    """
    try:
        with open(filepath, 'r', encoding=encoding, errors='ignore') as f:
            return f.read()
    except FileNotFoundError:
        return None


def write_text(content: str, filepath: str, encoding: str = 'utf-8') -> bool:
    """
    Ghi text ra file.
    
    Args:
        content: Nội dung cần ghi
        filepath: Đường dẫn file output
        encoding: Encoding (mặc định: utf-8)
        
    Returns:
        True nếu thành công
    """
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding=encoding) as f:
            f.write(content)
        return True
    except Exception:
        return False


def ensure_dir(path: str) -> str:
    """
    Tạo thư mục nếu chưa tồn tại.
    
    Args:
        path: Đường dẫn thư mục
        
    Returns:
        Đường dẫn đã được tạo
    """
    os.makedirs(path, exist_ok=True)
    return path


def list_subdirs(path: str) -> list:
    """
    Liệt kê các thư mục con.
    
    Args:
        path: Đường dẫn thư mục cha
        
    Returns:
        List tên các thư mục con
    """
    if not os.path.exists(path):
        return []
    return [f for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]
