"""
Sung et al. (2014) BRM 31 features extractor — 第一版。

實作的 features（17 個）：
  Word level (9)：X1-X9
  Semantics (2)：X10 內容詞數, X11 否定詞數
  Cohesion (10)：X21-X24 代詞 + X25-X30 連詞 6 類
  (跳過 X12-X14 語意類別、X15-X20 句法、X31 隱喻 — 需要更深層 NLP 工具)

paper 原始選用 multilevel SVM 的 15 features（F-score > 0.5）我們都有覆蓋。

特徵都是 raw count / ratio，正規化（per 100 詞）留給訓練階段。
"""
import math
import sqlite3
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

from app.chinese_readability.readability import ReadabilityAnalyzer

DB_PATH = Path(__file__).parent / "data" / "lexicon.db"

# CKIP POS tag 分類
NOUN_TAGS = {"Na", "Nb", "Nc", "Nd"}
PRONOUN_TAGS = {"Nh", "Nep"}
VERB_TAGS = {
    "VA", "VAC", "VB", "VC", "VCL", "VD", "VE",
    "VF", "VG", "VH", "VHC", "VI", "VJ", "VK", "VL",
}
ADJ_TAGS = {"A"}
ADV_TAGS = {"D", "Da", "Dfa", "Dfb", "Di", "Dk"}
PUNCT_TAGS = {
    "COMMACATEGORY", "PERIODCATEGORY", "QUESTIONCATEGORY",
    "EXCLAMATIONCATEGORY", "PAUSECATEGORY", "COLONCATEGORY",
    "SEMICOLONCATEGORY", "ETCCATEGORY", "DASHCATEGORY",
    "PARENTHESISCATEGORY", "SPCHANGECATEGORY", "WHITESPACE",
}

# 連詞 6 類（種子，可擴）
CONJ_POSITIVE = {"而且", "並且", "同時", "此外", "另外", "加上", "不但",
                 "更", "且", "又", "並", "也"}
CONJ_NEGATIVE = {"但", "但是", "可是", "不過", "然而", "卻", "只是",
                 "反而", "其實"}
CONJ_CAUSE = {"因為", "所以", "因此", "由於", "故", "故而", "致使",
              "以致", "以致於"}
CONJ_PURPOSE = {"為了", "以便", "以免", "為的是", "好讓", "免得"}
CONJ_CONCESSION = {"雖然", "即使", "儘管", "就算", "縱使", "雖",
                   "雖說", "誠然"}
CONJ_CONDITION = {"如果", "假如", "若", "倘若", "要是", "只要",
                  "除非", "無論", "不管"}

# 否定詞清單
NEGATION_WORDS = {"不", "沒", "沒有", "未", "別", "勿", "莫", "非",
                  "無", "毋", "不要", "不會", "不能", "不可"}

# 人稱代詞細分
PERSONAL_PRONOUNS = {
    "我", "我們", "你", "你們", "妳", "妳們",
    "他", "他們", "她", "她們", "它", "它們",
    "您", "您們", "本人", "咱", "咱們", "祢",
}
FIRST_PERSON = {"我", "我們", "本人", "咱", "咱們"}
THIRD_PERSON = {"他", "他們", "她", "她們", "它", "它們"}


@dataclass
class PaperFeatures:
    """Sung 2014 31 features 中的 17 個可抽取項。"""
    # Word level
    X1_short_stroke: int = 0      # 1-10 畫字數
    X2_mid_stroke: int = 0        # 11-20 畫字數
    X3_2char_words: int = 0       # 二字詞數
    X4_3char_words: int = 0       # 三字詞數
    X5_word_count: int = 0        # 總詞數（不含標點）
    X6_verb_count: int = 0        # 動詞數
    X7_adv_count: int = 0         # 副詞數
    X8_content_log_freq: float = 0.0  # 內容詞 log 平均詞頻
    X9_hard_words: int = 0        # 難詞數（不在 NAER 詞表+不在頻率表）
    # Semantics
    X10_content_words: int = 0    # 內容詞數
    X11_negation: int = 0         # 否定詞數
    # Cohesion
    X21_pronouns: int = 0         # 代詞總數
    X22_personal_pronouns: int = 0  # 人稱代詞數
    X23_first_person: int = 0
    X24_third_person: int = 0
    X25_positive_conj: int = 0    # 正面連詞
    X26_negative_conj: int = 0    # 負面連詞
    X27_cause_conj: int = 0       # 因果連詞
    X28_purpose_conj: int = 0     # 目的連詞
    X29_concession_conj: int = 0  # 讓步連詞
    X30_condition_conj: int = 0   # 條件連詞
    # meta
    text_char_count: int = 0      # 中文字數
    text_total_len: int = 0       # 含標點與英數的總長

    def to_dict(self) -> dict:
        return asdict(self)

    def normalize_per_100(self) -> dict:
        """
        正規化：每 100 個詞各 feature 的比例。

        例外不做 scale 的 feature：
          - X5_word_count：自己 scale 到 100 變 constant，改保留 raw word count
          - X8_content_log_freq：本身是 log，跟詞數無關
        """
        if self.X5_word_count == 0:
            return self.to_dict()
        scale = 100 / self.X5_word_count
        out = {}
        SKIP = {"X5_word_count", "X8_content_log_freq"}
        for k, v in self.to_dict().items():
            if k.startswith("X") and isinstance(v, (int, float)):
                if k in SKIP:
                    out[k] = v
                else:
                    out[k] = round(v * scale, 3)
            else:
                out[k] = v
        return out


def _is_cjk(ch: str) -> bool:
    return "一" <= ch <= "鿿"


class PaperFeatureExtractor:
    def __init__(self, db_path: Path = DB_PATH, device: int = -1):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._inner = ReadabilityAnalyzer(db_path=db_path, device=device)

    def _stroke(self, ch: str) -> Optional[int]:
        row = self.conn.execute(
            "SELECT strokes FROM strokes_lookup WHERE char=?", (ch,)
        ).fetchone()
        return row["strokes"] if row else None

    def _word_freq(self, word: str) -> Optional[float]:
        row = self.conn.execute(
            "SELECT avg_freq FROM word_freq WHERE word=?", (word,)
        ).fetchone()
        return row["avg_freq"] if row and row["avg_freq"] else None

    def _in_naer(self, word: str) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM words WHERE word=?", (word,)
        ).fetchone()
        return row is not None

    def extract(self, text: str) -> PaperFeatures:
        f = PaperFeatures()
        f.text_total_len = len(text)
        f.text_char_count = sum(1 for c in text if _is_cjk(c))

        if not text.strip():
            return f

        words, pos_tags = self._inner.segment(text)
        content_freqs = []

        for w, pos in zip(words, pos_tags):
            if pos in PUNCT_TAGS or not w.strip():
                continue

            # X3, X4 詞長
            cjk_len = sum(1 for c in w if _is_cjk(c))
            if cjk_len == 2:
                f.X3_2char_words += 1
            elif cjk_len == 3:
                f.X4_3char_words += 1

            # X5 總詞數
            f.X5_word_count += 1

            # X6/X7 動詞、副詞
            if pos in VERB_TAGS:
                f.X6_verb_count += 1
            if pos in ADV_TAGS:
                f.X7_adv_count += 1

            # X10 內容詞（含 freq for X8）
            is_content = (
                pos.startswith("N") or pos in VERB_TAGS or pos in ADJ_TAGS
            ) and pos not in PRONOUN_TAGS
            if is_content:
                f.X10_content_words += 1
                freq = self._word_freq(w)
                if freq:
                    content_freqs.append(freq)

            # X9 難詞（中文但不在任何詞表）
            if cjk_len > 0 and not self._in_naer(w) and self._word_freq(w) is None:
                f.X9_hard_words += 1

            # X11 否定詞
            if w in NEGATION_WORDS:
                f.X11_negation += 1

            # X21-X24 代詞
            if pos in PRONOUN_TAGS or w in PERSONAL_PRONOUNS:
                f.X21_pronouns += 1
                if w in PERSONAL_PRONOUNS:
                    f.X22_personal_pronouns += 1
                    if w in FIRST_PERSON:
                        f.X23_first_person += 1
                    if w in THIRD_PERSON:
                        f.X24_third_person += 1

            # X25-X30 連詞分類
            if w in CONJ_POSITIVE:
                f.X25_positive_conj += 1
            elif w in CONJ_NEGATIVE:
                f.X26_negative_conj += 1
            elif w in CONJ_CAUSE:
                f.X27_cause_conj += 1
            elif w in CONJ_PURPOSE:
                f.X28_purpose_conj += 1
            elif w in CONJ_CONCESSION:
                f.X29_concession_conj += 1
            elif w in CONJ_CONDITION:
                f.X30_condition_conj += 1

        # X1, X2 筆畫
        for ch in text:
            s = self._stroke(ch)
            if s is None:
                continue
            if s <= 10:
                f.X1_short_stroke += 1
            elif s <= 20:
                f.X2_mid_stroke += 1

        # X8 內容詞 log avg freq
        if content_freqs:
            f.X8_content_log_freq = round(
                sum(math.log10(max(fr, 0.1)) for fr in content_freqs) / len(content_freqs),
                3,
            )

        return f
