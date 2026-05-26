"""
短文字模式 v2：拿掉 NAER 三等七級分級，用 104 年跨主題詞頻 + 人工標註 labels 訓 supervised classifier。

Features（不再 level lookup）：
  - avg_topic_coverage : 平均跨主題領域數 (0-5)，越高越通用
  - avg_log_freq       : NAER 104 詞頻 log 平均
  - hard_word_ratio    : 不在跨主題 + 通用詞頻表外的比例
  - avg_stroke         : 平均筆畫
  - char_outside_4808_ratio : 字超出教育部 4808 的比例
  - jargon_ratio       : UI jargon 偵測比例
  - n_words            : 詞數
"""
import math
import sqlite3
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

from app.chinese_readability.readability import ReadabilityAnalyzer
from app.chinese_readability.jargon import detect_jargon

DB = Path(__file__).parent / "data" / "lexicon.db"

LEVEL_ORDER = {"L1": 1, "L2": 2, "L3": 3, "L4": 4}
LEVEL_REV = {v: k for k, v in LEVEL_ORDER.items()}


@dataclass
class ShortFeatures:
    avg_topic_coverage: float = 0.0
    avg_log_freq: float = 0.0
    hard_word_ratio: float = 0.0
    avg_stroke: float = 0.0
    char_outside_4808_ratio: float = 0.0
    jargon_ratio: float = 0.0
    n_words: int = 0
    n_chars: int = 0


def _is_cjk(c):
    return "一" <= c <= "鿿"


class ShortFormExtractor:
    """負責抽 features，不分類。"""

    def __init__(self, db_path: Path = DB, device: int = -1):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._inner = ReadabilityAnalyzer(db_path=db_path, device=device)

    def _topic(self, word: str) -> Optional[int]:
        row = self.conn.execute(
            "SELECT topics_count FROM naer_104_topic_coverage WHERE word=?", (word,)
        ).fetchone()
        return row["topics_count"] if row else None

    def _word_freq_104(self, word: str) -> Optional[int]:
        row = self.conn.execute(
            "SELECT freq FROM naer_104_word_freq WHERE word=?", (word,)
        ).fetchone()
        return row["freq"] if row else None

    def _word_freq_general(self, word: str) -> Optional[float]:
        row = self.conn.execute(
            "SELECT avg_freq FROM word_freq WHERE word=?", (word,)
        ).fetchone()
        return row["avg_freq"] if row and row["avg_freq"] else None

    def _stroke(self, ch: str) -> Optional[int]:
        row = self.conn.execute(
            "SELECT strokes FROM strokes_lookup WHERE char=?", (ch,)
        ).fetchone()
        return row["strokes"] if row else None

    def _in_moe_4808(self, ch: str) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM moe_chars WHERE char=?", (ch,)
        ).fetchone()
        return row is not None

    def extract(self, text: str, jargon_whitelist: Optional[set] = None) -> ShortFeatures:
        f = ShortFeatures()
        if not text.strip():
            return f

        words, pos = self._inner.segment(text)

        # 詞層級 features
        topic_scores = []
        log_freqs = []
        hard_count = 0
        n_words = 0
        for w, p in zip(words, pos):
            if not any(_is_cjk(c) for c in w):
                continue
            if p in {"COMMACATEGORY", "PERIODCATEGORY", "PAUSECATEGORY", "WHITESPACE"}:
                continue
            n_words += 1
            t = self._topic(w)
            if t is not None:
                topic_scores.append(t)
            else:
                topic_scores.append(0)  # 不在跨主題表 = 0 領域

            freq = self._word_freq_104(w) or 0
            general = self._word_freq_general(w) or 0
            combined = max(freq, general)
            if combined > 0:
                log_freqs.append(math.log10(combined))
            else:
                log_freqs.append(0)

            # 難詞：不在跨主題 + 通用頻率低
            if t is None and (general is None or general < 1.0):
                hard_count += 1

        f.n_words = n_words
        if topic_scores:
            f.avg_topic_coverage = round(sum(topic_scores) / len(topic_scores), 3)
        if log_freqs:
            f.avg_log_freq = round(sum(log_freqs) / len(log_freqs), 3)
        if n_words > 0:
            f.hard_word_ratio = round(hard_count / n_words, 3)

        # 字層級 features
        strokes = []
        outside_4808 = 0
        n_chars = 0
        for ch in text:
            if not _is_cjk(ch):
                continue
            n_chars += 1
            s = self._stroke(ch)
            if s is not None:
                strokes.append(s)
            if not self._in_moe_4808(ch):
                outside_4808 += 1

        f.n_chars = n_chars
        if strokes:
            f.avg_stroke = round(sum(strokes) / len(strokes), 3)
        if n_chars > 0:
            f.char_outside_4808_ratio = round(outside_4808 / n_chars, 3)

        # Jargon
        j = detect_jargon(text, whitelist=jargon_whitelist)
        f.jargon_ratio = round(j.jargon_ratio, 3)

        return f


def feature_vector(f: ShortFeatures) -> list:
    return [
        f.avg_topic_coverage,
        f.avg_log_freq,
        f.hard_word_ratio,
        f.avg_stroke,
        f.char_outside_4808_ratio,
        f.jargon_ratio,
        f.n_words,
        f.n_chars,
    ]


FEATURE_NAMES = [
    "avg_topic_coverage", "avg_log_freq", "hard_word_ratio",
    "avg_stroke", "char_outside_4808_ratio", "jargon_ratio",
    "n_words", "n_chars",
]
