"""
Processing Module
=================

Xử lý và loại bỏ trùng lặp dữ liệu.

Classes:
    - ReferenceProcessor: Trích xuất references từ LaTeX
    - ReferenceDeduplicator: Loại bỏ references trùng lặp
    - ContentDeduplicator: Loại bỏ content trùng lặp

Functions:
    - replace_citations_in_text: Thay thế citation keys trong văn bản
"""

from .reference_processor import ReferenceProcessor
from .deduplicator import (
    ReferenceDeduplicator,
    ContentDeduplicator,
    replace_citations_in_text
)

__all__ = [
    'ReferenceProcessor',
    'ReferenceDeduplicator', 
    'ContentDeduplicator',
    'replace_citations_in_text'
]