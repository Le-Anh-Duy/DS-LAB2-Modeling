# Introduction to Data Science - Milestone 2
## Hierarchical Parsing and Reference Matching Pipeline

**Student Name:** Lê Anh Duy
**Student ID:** 2317011
**Course:** Introduction to Data Science (KHDL1)

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