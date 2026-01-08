"""
Configuration Module
====================

Quản lý cấu hình và đường dẫn mặc định cho pipeline.
"""

import os
from dataclasses import dataclass, field
from typing import Optional


def _get_project_root():
    """Tự động xác định project root từ vị trí file config."""
    current_file = os.path.abspath(__file__)
    src_dir = os.path.dirname(current_file)
    student_dir = os.path.dirname(src_dir)
    return os.path.dirname(student_dir)


@dataclass
class PipelineConfig:
    """
    Cấu hình cho toàn bộ pipeline.
    
    Attributes:
        project_root: Thư mục gốc của project
        data_raw: Thư mục chứa dữ liệu thô
        data_output: Thư mục xuất kết quả
        dataset_final: Thư mục chứa dataset cuối cùng
        parallel: Có sử dụng xử lý song song không
        max_workers: Số luồng tối đa (None = auto)
        matching_threshold: Ngưỡng score cho matching (0.0 - 1.0)
        log_file: Tên file log
    
    Example:
        >>> config = PipelineConfig()
        >>> config.data_raw
        '/path/to/Milestone2_Project/data_raw'
        
        >>> # Custom config
        >>> config = PipelineConfig(
        ...     data_raw="/custom/path",
        ...     parallel=True,
        ...     max_workers=8
        ... )
    """
    
    # Paths
    project_root: str = field(default_factory=_get_project_root)
    data_raw: Optional[str] = None
    data_output: Optional[str] = None
    dataset_final: Optional[str] = None
    
    # Processing
    parallel: bool = True
    max_workers: Optional[int] = None
    
    # Matching
    matching_threshold: float = 0.55
    
    # Logging
    log_file: str = "pipeline.log"
    log_level: str = "INFO"
    
    def __post_init__(self):
        """Thiết lập các đường dẫn mặc định nếu chưa được chỉ định."""
        if self.data_raw is None:
            self.data_raw = os.path.join(self.project_root, "data_raw")
        if self.data_output is None:
            self.data_output = os.path.join(self.project_root, "data_output")
        if self.dataset_final is None:
            self.dataset_final = os.path.join(self.project_root, "dataset_final")
        if self.max_workers is None:
            self.max_workers = os.cpu_count() or 4
    
    def get_paper_raw_path(self, paper_id: str) -> str:
        """Lấy đường dẫn tới folder paper trong data_raw."""
        return os.path.join(self.data_raw, paper_id)
    
    def get_paper_output_path(self, paper_id: str) -> str:
        """Lấy đường dẫn tới folder paper trong data_output."""
        return os.path.join(self.data_output, paper_id)
    
    def get_log_path(self) -> str:
        """Lấy đường dẫn file log."""
        return os.path.join(self.data_output, self.log_file)
    
    def validate(self) -> bool:
        """
        Kiểm tra tính hợp lệ của config.
        
        Returns:
            True nếu tất cả đường dẫn tồn tại
            
        Raises:
            FileNotFoundError: Nếu data_raw không tồn tại
        """
        if not os.path.exists(self.data_raw):
            raise FileNotFoundError(f"Data raw path not found: {self.data_raw}")
        return True
    
    def ensure_output_dirs(self):
        """Tạo các thư mục output nếu chưa tồn tại."""
        os.makedirs(self.data_output, exist_ok=True)
        os.makedirs(self.dataset_final, exist_ok=True)
    
    def to_dict(self) -> dict:
        """Chuyển config sang dictionary."""
        return {
            "project_root": self.project_root,
            "data_raw": self.data_raw,
            "data_output": self.data_output,
            "dataset_final": self.dataset_final,
            "parallel": self.parallel,
            "max_workers": self.max_workers,
            "matching_threshold": self.matching_threshold,
            "log_file": self.log_file,
            "log_level": self.log_level
        }
    
    def __str__(self):
        return f"""PipelineConfig:
  Project Root:    {self.project_root}
  Data Raw:        {self.data_raw}
  Data Output:     {self.data_output}
  Dataset Final:   {self.dataset_final}
  Parallel:        {self.parallel}
  Max Workers:     {self.max_workers}
  Match Threshold: {self.matching_threshold}
"""


# =============================================================================
# Default Configuration Instance
# =============================================================================

# Singleton config để sử dụng toàn project
DEFAULT_CONFIG = PipelineConfig()


# =============================================================================
# Convenience Functions
# =============================================================================

def get_config() -> PipelineConfig:
    """Lấy instance config mặc định."""
    return DEFAULT_CONFIG


def create_config(**kwargs) -> PipelineConfig:
    """
    Tạo config mới với các tham số tùy chỉnh.
    
    Example:
        >>> config = create_config(
        ...     data_raw="./my_data",
        ...     parallel=False
        ... )
    """
    return PipelineConfig(**kwargs)
