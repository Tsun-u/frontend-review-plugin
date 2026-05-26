"""
Chinese readability analyzer for UI text (MVP-S1 + S2).

短文字模式：CKIP 斷詞 + TBCL 分級字／詞表 + 通用詞頻 fallback + UI jargon 偵測。

risk_score 由四部分線性加總：
  - 字級超標比例
  - 詞級超標比例
  - OOV 比例
  - jargon 比例（英文縮寫/代碼/URL）
"""
import sqlite3
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from app.chinese_readability.jargon import JargonReport, detect_jargon

DB_PATH = Path(__file__).parent / "data" / "lexicon.db"

LEVEL_ORDER = {"L1": 1, "L2": 2, "L3": 3, "L4": 4}
LEVEL_REV = {v: k for k, v in LEVEL_ORDER.items()}

# OOV 詞用通用詞頻 fallback 推估 level
# 經驗 cutoff（後續可校準）
def freq_to_level(avg_freq_per_million: Optional[float]) -> str:
    if avg_freq_per_million is None:
        return "L4"  # 完全 OOV 視為高難度
    if avg_freq_per_million > 100:
        return "L2"
    if avg_freq_per_million > 10:
        return "L3"
    return "L4"


@dataclass
class WordResult:
    word: str
    level: str
    source: str  # "naer_words" / "freq_fallback" / "oov"
    tbcl_ji: Optional[int] = None
    tbcl_substar: int = 0
    avg_freq: Optional[float] = None


@dataclass
class CharResult:
    char: str
    level: Optional[str]  # None 表示 非 CJK 或不在 chars 表（極罕字）
    in_moe_4808: int = 0


@dataclass
class ReadabilityReport:
    text: str
    target_level: str
    required_level: str
    risk_score: float
    flag: bool
    char_stats: dict = field(default_factory=dict)
    word_stats: dict = field(default_factory=dict)
    jargon: Optional[JargonReport] = None
    warnings: list = field(default_factory=list)
    over_target_chars: list = field(default_factory=list)
    over_target_words: list = field(default_factory=list)
    segmented: list = field(default_factory=list)


class ReadabilityAnalyzer:
    def __init__(self, db_path: Path = DB_PATH, device: int = -1):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._ws = None
        self._pos = None
        self._device = device

    def _load_ckip(self):
        if self._ws is None:
            from ckip_transformers.nlp import CkipWordSegmenter, CkipPosTagger
            self._ws = CkipWordSegmenter(model="bert-base", device=self._device)
            self._pos = CkipPosTagger(model="bert-base", device=self._device)

    def segment(self, text: str) -> tuple[list[str], list[str]]:
        self._load_ckip()
        words_batch = self._ws([text])
        pos_batch = self._pos(words_batch)
        return words_batch[0], pos_batch[0]

    def lookup_word(self, word: str) -> WordResult:
        row = self.conn.execute(
            "SELECT level, tbcl_ji, tbcl_substar FROM words WHERE word=?",
            (word,),
        ).fetchone()
        if row:
            return WordResult(
                word=word,
                level=row["level"],
                source="naer_words",
                tbcl_ji=row["tbcl_ji"],
                tbcl_substar=row["tbcl_substar"],
            )
        row = self.conn.execute(
            "SELECT avg_freq FROM word_freq WHERE word=?", (word,)
        ).fetchone()
        if row:
            avg = row["avg_freq"]
            return WordResult(
                word=word,
                level=freq_to_level(avg),
                source="freq_fallback",
                avg_freq=avg,
            )
        return WordResult(word=word, level="L4", source="oov")

    def lookup_char(self, ch: str) -> CharResult:
        row = self.conn.execute(
            "SELECT level, in_moe_4808 FROM chars WHERE char=?", (ch,)
        ).fetchone()
        if row:
            return CharResult(char=ch, level=row["level"], in_moe_4808=row["in_moe_4808"])
        # 不在 NAER 3100 字表：可能仍在 MOE 4808
        row = self.conn.execute(
            "SELECT 1 FROM moe_chars WHERE char=?", (ch,)
        ).fetchone()
        if row:
            return CharResult(char=ch, level="L3", in_moe_4808=1)
        return CharResult(char=ch, level=None, in_moe_4808=0)

    def _is_cjk(self, ch: str) -> bool:
        return "一" <= ch <= "鿿"

    def analyze(
        self,
        text: str,
        target_level: str = "L2",
        jargon_whitelist: Optional[set[str]] = None,
        jargon_weight: float = 0.2,
    ) -> ReadabilityReport:
        """
        Args:
            text: 待分析文字
            target_level: 目標讀者程度 L1-L4，預設 L2 (國中)
            jargon_whitelist: 視為熟詞的英文集合（plugin 端依產品/讀者群自訂）
            jargon_weight: jargon_ratio 在 risk_score 內的權重 (0-1)；0 = 忽略 jargon

        Returns:
            ReadabilityReport
        """
        if target_level not in LEVEL_ORDER:
            raise ValueError(f"target_level must be L1-L4, got {target_level}")
        target_n = LEVEL_ORDER[target_level]

        words, pos_tags = self.segment(text)
        jargon = detect_jargon(text, whitelist=jargon_whitelist)

        # POS 過濾：跳過標點 / 純數字
        SKIP_POS = {
            "COMMACATEGORY", "PERIODCATEGORY", "QUESTIONCATEGORY",
            "EXCLAMATIONCATEGORY", "PAUSECATEGORY", "COLONCATEGORY",
            "SEMICOLONCATEGORY", "ETCCATEGORY", "DASHCATEGORY",
            "PARENTHESISCATEGORY", "SPCHANGECATEGORY", "WHITESPACE",
            "FW",  # foreign word
            "Neu",  # 數詞
        }

        word_results = []
        over_target_words = []
        word_levels = []
        for w, pos in zip(words, pos_tags):
            if pos in SKIP_POS or not w.strip():
                continue
            # 純標點/數字也跳
            if all(not self._is_cjk(c) for c in w):
                continue
            r = self.lookup_word(w)
            word_results.append(r)
            word_levels.append(LEVEL_ORDER[r.level])
            if LEVEL_ORDER[r.level] > target_n:
                over_target_words.append(r)

        # 字級分析
        char_results = []
        over_target_chars = []
        char_levels = []
        for ch in text:
            if not self._is_cjk(ch):
                continue
            r = self.lookup_char(ch)
            char_results.append(r)
            if r.level:
                char_levels.append(LEVEL_ORDER[r.level])
                if LEVEL_ORDER[r.level] > target_n:
                    over_target_chars.append(r)
            else:
                # 完全沒收錄的字：視為 L4
                char_levels.append(4)
                over_target_chars.append(r)

        if not word_levels and not char_levels:
            # 純英數內容也要傳回 jargon report
            warnings = ["無中文內容"]
            if jargon.total_items > 0:
                warnings.append(f"含 {jargon.total_items} 個英文/代碼/符號")
            return ReadabilityReport(
                text=text, target_level=target_level,
                required_level="L1", risk_score=jargon.jargon_ratio,
                flag=jargon.jargon_ratio > 0.5,
                jargon=jargon,
                warnings=warnings,
            )

        required_word_n = max(word_levels) if word_levels else 1
        required_char_n = max(char_levels) if char_levels else 1
        required_n = max(required_word_n, required_char_n)
        required_level = LEVEL_REV[required_n]

        n_words = len(word_results)
        n_chars = len(char_results)
        over_word_ratio = len(over_target_words) / n_words if n_words else 0
        over_char_ratio = len(over_target_chars) / n_chars if n_chars else 0
        oov_count = sum(1 for r in word_results if r.source == "oov")
        oov_ratio = oov_count / n_words if n_words else 0

        # risk_score：四項線性加總，jargon_weight 控制 jargon 影響力
        # 中文側權重 (1 - jargon_weight) 內部 split 為 word:char:oov = 5:3:2
        chinese_w = 1.0 - jargon_weight
        risk_score = (
            chinese_w * (0.5 * over_word_ratio + 0.3 * over_char_ratio + 0.2 * oov_ratio)
            + jargon_weight * jargon.jargon_ratio
        )
        flag = required_n > target_n or jargon.jargon_ratio > 0.3

        warnings = []
        if required_n > target_n:
            warnings.append(
                f"預估需 {required_level} 程度才能無障礙閱讀，超出目標 {target_level}"
            )
        if oov_count > 0:
            warnings.append(f"{oov_count} 個詞不在分級／頻率表（OOV）")
        if jargon.total_items > 0:
            kinds = []
            if jargon.abbreviations: kinds.append(f"{len(jargon.abbreviations)} 英文片段")
            if jargon.alpha_codes:   kinds.append(f"{len(jargon.alpha_codes)} 字母數字代碼")
            if jargon.urls:          kinds.append(f"{len(jargon.urls)} URL")
            if jargon.emails:        kinds.append(f"{len(jargon.emails)} email")
            if jargon.symbols:       kinds.append(f"{len(jargon.symbols)} 特殊符號")
            warnings.append(f"含非中文片段：{', '.join(kinds)}（請評估讀者是否熟悉）")
        if len(text) < 50 and n_chars < 10:
            warnings.append("文字過短，結果僅供參考")

        return ReadabilityReport(
            text=text,
            target_level=target_level,
            required_level=required_level,
            risk_score=round(risk_score, 3),
            flag=flag,
            char_stats={
                "total": n_chars,
                "over_target": len(over_target_chars),
                "over_ratio": round(over_char_ratio, 3),
            },
            word_stats={
                "total": n_words,
                "over_target": len(over_target_words),
                "over_ratio": round(over_word_ratio, 3),
                "oov": oov_count,
                "oov_ratio": round(oov_ratio, 3),
            },
            jargon=jargon,
            warnings=warnings,
            over_target_chars=[(r.char, r.level) for r in over_target_chars],
            over_target_words=[
                (r.word, r.level, r.source) for r in over_target_words
            ],
            segmented=list(zip(words, pos_tags)),
        )


def pretty_print(report: ReadabilityReport):
    print(f"\n原文: {report.text}")
    if report.segmented:
        seg = " | ".join(f"{w}/{p}" for w, p in report.segmented)
        print(f"斷詞: {seg}")
    print(f"目標: {report.target_level}  /  預估需要: {report.required_level}  "
          f"/  flag: {report.flag}  /  risk: {report.risk_score}")
    print(f"  字級統計: {report.char_stats}")
    print(f"  詞級統計: {report.word_stats}")
    if report.over_target_words:
        print(f"  超標詞: " + ", ".join(
            f"{w}({lvl},{src})" for w, lvl, src in report.over_target_words
        ))
    if report.over_target_chars:
        print(f"  超標字: " + ", ".join(
            f"{c}({lvl})" for c, lvl in report.over_target_chars[:10]
        ))
    if report.jargon and report.jargon.total_items > 0:
        j = report.jargon
        bits = []
        if j.abbreviations: bits.append(f"英文: {j.abbreviations}")
        if j.alpha_codes:   bits.append(f"代碼: {j.alpha_codes}")
        if j.urls:          bits.append(f"URL: {j.urls}")
        if j.emails:        bits.append(f"Email: {j.emails}")
        if j.symbols:       bits.append(f"符號: {j.symbols}")
        if j.whitelisted:   bits.append(f"[白名單]: {j.whitelisted}")
        print(f"  jargon (ratio={j.jargon_ratio:.2f}): " + "; ".join(bits))
    for w in report.warnings:
        print(f"  ⚠ {w}")
