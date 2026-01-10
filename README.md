# Introduction to Data Science - Milestone 2
## Hierarchical Parsing and Reference Matching Pipeline

**Student Name:** Lê Anh Duy
**Student ID:** 23127011
**Course:** Introduction to Data Science (KHDL2)

---

## 1. Project Overview
This project implements a complete data science pipeline to process unstructured LaTeX scientific papers into structured hierarchical data and perform reference matching using Machine Learning.

The system consists of two main components:
1.  **Hierarchical Parser:** Recursively parses multi-file LaTeX sources (`.tex`, `.bib`, `.bbl`), standardizes content (math, text), and constructs a hierarchical JSON tree down to the sentence/equation level.
2.  **Reference Matching Pipeline:** A machine learning system that deduplicates references and matches extracted citations with a ground-truth dataset (`references.json`) using feature engineering and supervised learning.

---

## 2. Repository Structure
The project follows the required submission structure:

```text
[Student_ID]/
├── src/                        # Source code directory
│   ├── parser/                 # Latex parsing & Hierarchy construction logic
│   ├── processing/             # Text cleaning & Deduplication logic
│   ├── matching/               # Feature engineering & ML Model
│   ├── utils/                  # Helper functions (I/O)
│   └── main.py                 # Entry point to run the pipeline
├── requirements.txt            # Python dependencies
├── README.md                   # Project documentation
└── Report.pdf                  # Final report
```

---

## 3. Environment Setup

### Prerequisites

* Python 3.8 or higher.
* Recommended: Use a virtual environment (venv/conda).

### Installation

1. Navigate to the project directory:
```bash
cd [Student_ID]

```


2. Install required libraries:
```bash
pip install -r requirements.txt

```



*(Note: The `requirements.txt` includes standard libraries like `scikit-learn`, `numpy`, `pandas`, `tqdm`, etc.)*

---

## 4. Usage Instructions

### Data Preparation

Ensure the raw data (folder of LaTeX sources) is placed in a `data_raw` directory (or specify the path in arguments). The system expects the standard structure: `data_raw/<arxiv_id>/...`

### Running the Pipeline

You can run the entire pipeline (Parsing -> Labeling -> Training -> Prediction) using the `main.py` script.

### Output

The script generates the following files in `[output_dir]/[Student_ID]/[yymm-id]/`:

* `hierarchy.json`: Parsed content tree (Listing 1 format).
* `refs.bib`: Cleaned and deduplicated BibTeX.
* `metadata.json` & `references.json`: Paper metadata.
* `pred.json`: ML matching results with top-5 candidates (Listing 2 format).

---

## 5. Implementation Highlights

### A. Parser Logic

* **Recursive Multi-file Gathering:** Automatically detects the main `.tex` file and recursively resolves `\input` and `\include` commands to flatten the source.
* **Robust Hierarchy:** Parses Document -> Section -> Subsection -> ... -> Sentences/Equations/Figures.
* **Abstract Handling:** Treats Abstract as a component section with sentence-level leaves.
* **BibTeX & BBL Handling:** Can parse both standard `.bib` files and convert `.bbl` files to BibTeX format if the `.bib` is missing.

### B. Standardization & Deduplication

* **Math Normalization:** Unifies inline math to `$ ... $` and block math to `\begin{equation}`.
* **Ref Deduplication:** Merges references across versions based on content matching (Jaccard/Levenshtein) and unifies citation keys.
* **Content Deduplication:** Identifies identical text content across versions to optimize `hierarchy.json`.

### C. Machine Learning Pipeline

* **Features:** Uses string similarity metrics (Jaccard, Levenshtein) on Titles and Authors, plus Year difference features.
* **Model:** Random Forest Classifier (or XGBoost).
* **Evaluation:** Optimized for Mean Reciprocal Rank (MRR).

---

## 6. Notes for Graders

* **Source Code:** All logic is implemented in `src/`. No external pre-trained LLMs were used for the core parsing logic (using only regex).
* **Data:** The `data_raw` and `data_output` folders are excluded from this zip file to reduce size, as per instructions.
* **Reproducibility:** The code uses a fixed random seed in the ML pipeline for consistent results.
* *Submission*: The submited code was in ./23127011 folder other folders is just for testing and verification.

---
