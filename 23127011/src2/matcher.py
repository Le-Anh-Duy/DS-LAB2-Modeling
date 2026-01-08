import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict, Any, Tuple

class ReferenceMatcher:
    def __init__(self, threshold: float = 0.4):
        """
        threshold: Ngưỡng Cosine Similarity để chấp nhận match (0.0 -> 1.0).
        Với TF-IDF, ngưỡng thường cao hơn Jaccard, khoảng 0.4 - 0.7 tùy dữ liệu.
        """
        self.threshold = threshold
        self.vectorizer = TfidfVectorizer(analyzer='word', ngram_range=(1, 2), stop_words='english')
        self.candidates_meta = [] # Lưu metadata của ground truth
        self.is_fitted = False
        self.tfidf_matrix = None

    def fit(self, ground_truth_refs: Dict[str, Any]):
        """
        Chuẩn bị dữ liệu từ references.json (Ground Truth)
        """
        corpus = []
        self.candidates_meta = []

        for arxiv_id, meta in ground_truth_refs.items():
            # 1. Tạo chuỗi đại diện: Title + Authors + Year
            title = meta.get('title', '')
            authors = " ".join(meta.get('authors', [])) if isinstance(meta.get('authors'), list) else str(meta.get('authors', ''))
            year = str(meta.get('year', ''))
            
            # Chuỗi text để vector hóa
            text_representation = f"{title} {authors} {year}"
            
            corpus.append(text_representation)
            self.candidates_meta.append({
                "id": arxiv_id,
                "meta": meta
            })

        if not corpus:
            print("⚠️ Warning: No ground truth references to fit.")
            return

        # 2. Học từ vựng và tạo ma trận Vector cho Ground Truth
        try:
            self.tfidf_matrix = self.vectorizer.fit_transform(corpus)
            self.is_fitted = True
        except ValueError:
            # Xảy ra nếu corpus rỗng hoặc chỉ toàn stop words
            print("⚠️ TF-IDF fit failed (empty vocabulary).")

    def match(self, raw_ref_text: str) -> Dict[str, Any]:
        """
        Tìm bài báo khớp nhất cho một chuỗi trích dẫn thô.
        Trả về object ground truth hoặc None.
        """
        if not self.is_fitted:
            return None

        # 1. Vector hóa trích dẫn thô
        query_vec = self.vectorizer.transform([raw_ref_text])

        # 2. Tính Cosine Similarity với toàn bộ database
        # cosine_similarity trả về mảng [[score1, score2, ...]]
        scores = cosine_similarity(query_vec, self.tfidf_matrix).flatten()

        # 3. Tìm điểm cao nhất
        best_idx = np.argmax(scores)
        best_score = scores[best_idx]

        # 4. Kiểm tra ngưỡng
        if best_score >= self.threshold:
            return self.candidates_meta[best_idx]
        
        return None