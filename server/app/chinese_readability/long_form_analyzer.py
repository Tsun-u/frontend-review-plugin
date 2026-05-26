"""
長文字 SVM analyzer：把訓練好的 SVM model + paper features 包成 API。

對應 hybrid pipeline 的 svm_sung2014_v1 backend。
"""
import joblib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from app.chinese_readability.paper_features import PaperFeatureExtractor, PaperFeatures

MODEL_PATH = Path(__file__).parent / "data" / "svm_v0.joblib"


@dataclass
class LongFormResult:
    """長文字 SVM 預測結果。"""
    predicted_level: str         # L1-L4
    decision_distance: float     # SVM decision function 最大值（信心度代理）
    features: PaperFeatures
    text_length: int


class LongFormAnalyzer:
    """SVM-based long-form readability classifier."""

    def __init__(self, model_path: Path = MODEL_PATH, device: int = -1):
        if not model_path.exists():
            raise FileNotFoundError(
                f"SVM model not found at {model_path}. "
                f"Run train_svm_baseline.py first to generate it."
            )
        bundle = joblib.load(model_path)
        self.pipeline = bundle["pipeline"]
        self.feature_cols = bundle["feature_cols"]
        self.labels = bundle["labels"]
        self.meta = {
            "trained_on": bundle.get("trained_on"),
            "cv_mean_accuracy": bundle.get("cv_mean_accuracy"),
            "adjacent_accuracy": bundle.get("adjacent_accuracy"),
        }
        self._extractor = PaperFeatureExtractor(device=device)

    def analyze(self, text: str) -> LongFormResult:
        features = self._extractor.extract(text)
        norm = features.normalize_per_100()
        X = [[norm[c] for c in self.feature_cols]]

        pred_label = self.pipeline.predict(X)[0]
        # 用 decision_function 取信心代理
        try:
            decisions = self.pipeline.decision_function(X)[0]
            max_dist = float(abs(decisions).max())
        except Exception:
            max_dist = 0.0

        return LongFormResult(
            predicted_level=pred_label,
            decision_distance=round(max_dist, 3),
            features=features,
            text_length=features.text_char_count,
        )
