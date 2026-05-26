"""
短文字 v2 analyzer：包裝 ShortFormExtractor + 訓練好的 RF classifier。

對應 hybrid pipeline 的 tbcl_supervised_v2 backend。
"""
import joblib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from app.chinese_readability.short_form_v2 import ShortFormExtractor, ShortFeatures, feature_vector
from app.chinese_readability.jargon import detect_jargon, JargonReport

MODEL_PATH = Path(__file__).parent / "data" / "short_form_v2.joblib"


@dataclass
class ShortFormV2Result:
    predicted_level: str         # L1 / L2 / L3 (3-class)
    confidence: float            # max class probability
    features: ShortFeatures
    jargon: JargonReport
    hard_words: list[str] = field(default_factory=list)


class ShortFormV2Analyzer:
    """Supervised classifier for short Chinese UI text (3-class L1/L2/L3)."""

    def __init__(self, model_path: Path = MODEL_PATH, device: int = -1):
        if not model_path.exists():
            raise FileNotFoundError(
                f"Short-form v2 model not found at {model_path}. "
                f"Run train_short_form_v2.py first."
            )
        bundle = joblib.load(model_path)
        self.pipeline = bundle["pipeline"]
        self.feature_names = bundle["feature_names"]
        self.labels = bundle["labels"]
        self.meta = {
            "best_classifier": bundle.get("best_classifier"),
            "cv_accuracy": bundle.get("cv_accuracy"),
            "n_samples": bundle.get("n_samples"),
        }
        self._extractor = ShortFormExtractor(device=device)

    def analyze(
        self,
        text: str,
        jargon_whitelist: Optional[set[str]] = None,
    ) -> ShortFormV2Result:
        features = self._extractor.extract(text, jargon_whitelist=jargon_whitelist)
        jargon = detect_jargon(text, whitelist=jargon_whitelist)
        X = [feature_vector(features)]

        pred = self.pipeline.predict(X)[0]
        try:
            probs = self.pipeline.predict_proba(X)[0]
            confidence = float(probs.max())
        except Exception:
            confidence = 0.0

        # hard words: 不在跨主題表 + 通用詞頻低
        hard_words = self._extract_hard_words(text)

        return ShortFormV2Result(
            predicted_level=pred,
            confidence=round(confidence, 3),
            features=features,
            jargon=jargon,
            hard_words=hard_words,
        )

    def _extract_hard_words(self, text: str) -> list[str]:
        """從 text 抽出對使用者「難讀」的詞清單。"""
        # 用 extractor 內部資源
        words, pos = self._extractor._inner.segment(text)
        hard = []
        SKIP_POS = {"COMMACATEGORY", "PERIODCATEGORY", "PAUSECATEGORY", "WHITESPACE"}
        for w, p in zip(words, pos):
            if p in SKIP_POS:
                continue
            if not any("一" <= c <= "鿿" for c in w):
                continue
            topic = self._extractor._topic(w)
            general = self._extractor._word_freq_general(w)
            # 不在跨主題表 + 通用頻率低
            if topic is None and (general is None or general < 5.0):
                hard.append(w)
        return hard
