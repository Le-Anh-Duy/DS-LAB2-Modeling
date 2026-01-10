# LaTeX Paper Processing Pipeline

Pipeline xử lý và trích xuất dữ liệu từ các bài báo khoa học viết bằng LaTeX.

## Cấu trúc thư mục

```
src/
├── __init__.py          # Main exports & run_full_pipeline()
├── main.py              # CLI entry point
├── config.py            # Cấu hình pipeline
├── pipeline.py          # Phase 1: Pre-processing & Parsing
├── run_matching.py      # Phase 2: Reference Matching
├── merge_labels.py      # Phase 3: Dataset Merging
│
├── parser/              # Phân tích cấu trúc LaTeX
│   ├── file_loader.py   # Tìm file .tex gốc
│   ├── tex_parser.py    # Flatten, Build Tree, Process Content
│   ├── bib_parser.py    # Parse BibTeX
│   └── reference_parser.py
│
├── processing/          # Xử lý deduplication
│   ├── cleaner.py
│   └── dedup.py
│
├── matching/            # ML-based reference matching
│   ├── features.py      # Feature engineering
│   ├── metrics.py       # Evaluation metrics
│   └── model.py         # ML models
│
├── utils/               # Utilities
│   ├── io.py            # I/O helpers
│   └── tex_cleaner.py   # LaTeX cleaning
│
├── cleaner.py           # ReferenceProcessor
├── matcher.py           # ReferenceMatcher (TF-IDF)
└── deduplicator.py      # ReferenceDeduplicator, ContentDeduplicator
```

## Cách sử dụng

### 1. Sử dụng trong Python

```python
# Cách đơn giản nhất - chạy full pipeline
from src import run_full_pipeline

result = run_full_pipeline(
    data_raw="./data_raw",       # Thư mục chứa LaTeX papers
    data_output="./data_output", # Thư mục xuất kết quả
    parallel=True,               # Xử lý song song
    max_workers=8                # Số luồng (optional)
)

print(f"Đã xử lý {result['processed']} papers")
print(f"Đã match {result['matched']} papers")
```

```python
# Chạy từng phase riêng biệt
from src import run_processing_pipeline, run_matching_pipeline

# Phase 1: Pre-processing
run_processing_pipeline("./data_raw", "./data_output", parallel=True)

# Phase 2: Matching
run_matching_pipeline("./data_output")
```

### 2. Sử dụng Command Line (CLI)

```bash
# Full pipeline
python -m src.main --raw ./data_raw --output ./data_output --parallel

# Chỉ Phase 1 (không matching)
python -m src.main --raw ./data_raw --output ./data_output --no-matching

# Chỉ Phase 2 (đã có data processed)
python -m src.main --output ./data_output --matching-only

# Merge labels thành dataset
python -m src.main --merge --yymm 2403 --limit 50
```

### 3. Sử dụng Notebook

Xem file `notebooks/full_pipeline_tutorial.ipynb` để biết cách sử dụng chi tiết với hướng dẫn từng bước.

## Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           FULL PIPELINE                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌───────────────┐    ┌───────────────┐    ┌───────────────┐            │
│  │   DATA RAW    │ -> │   PHASE 1     │ -> │   PHASE 2     │            │
│  │  (LaTeX .tex) │    │  Processing   │    │   Matching    │            │
│  └───────────────┘    └───────────────┘    └───────────────┘            │
│                              │                    │                     │
│                              v                    v                     │
│                       hierarchy.json        labels.json                 │
│                       refs.bib                                          │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Phase 1: Pre-processing & Parsing
1. **Flatten LaTeX**: Gộp các file `\input`, `\include` thành một file duy nhất
2. **Extract References**: Trích xuất từ `.bbl`, `.bib`, `\bibitem`
3. **Dedup References**: Loại bỏ reference trùng lặp giữa các versions
4. **Build Structure Tree**: Xây dựng cây cấu trúc (Section → Subsection → ...)
5. **Process Content**: Làm sạch và tách câu
6. **Dedup Content**: Loại bỏ nội dung trùng lặp giữa các versions
7. **Export**: `hierarchy.json`, `refs.bib`

### Phase 2: Reference Matching
1. **Load Ground Truth**: Đọc `references.json` (từ arXiv API)
2. **Load Extracted Refs**: Đọc `refs.bib` từ Phase 1
3. **TF-IDF Matching**: So khớp bằng cosine similarity
4. **Export**: `labels.json`

### Phase 3: Dataset Merging
1. **Load Labels**: Đọc tất cả `labels.json`
2. **Split**: Chia train/val/test
3. **Export**: `auto.json`, `manual.json`

## Input Format

```
data_raw/
├── 2403-00530/
│   ├── tex/
│   │   ├── v1/          # Version 1
│   │   │   ├── main.tex
│   │   │   ├── chapter1.tex
│   │   │   └── refs.bib
│   │   └── v2/          # Version 2
│   │       ├── main.tex
│   │       └── refs.bbl
│   ├── metadata.json    # Paper metadata
│   └── references.json  # Ground truth references
├── 2403-00531/
│   └── ...
```

## Output Format

```
data_output/
├── 2403-00530/
│   ├── hierarchy.json   # Cấu trúc cây (dedup across versions)
│   ├── refs.bib         # References đã dedup
│   ├── labels.json      # Kết quả matching
│   ├── metadata.json    # Copied from raw
│   └── references.json  # Copied from raw
├── 2403-00531/
│   └── ...
```

## Configuration

```python
from src.config import PipelineConfig, create_config

# Tạo config tùy chỉnh
config = create_config(
    data_raw="./my_data",
    data_output="./my_output",
    parallel=True,
    max_workers=8,
    matching_threshold=0.6
)

print(config)
```

## Requirements

```
bibtexparser
scikit-learn
numpy
tqdm
```

Cài đặt:
```bash
pip install -r requirements.txt
```

