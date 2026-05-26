"""
Chinese readability hybrid pipeline.

依文字長度自動分流：
  - 中文字數 < SHORT_THRESHOLD  → TBCL 規則型（短文字，UI 場景）
  - 中文字數 >= LONG_THRESHOLD   → paper 31 features SVM（長文字，說明/條款）
  - 中間區段                      → 兩者都跑、合併（v2 再做）

SVM 部分尚未實作（Task #5+#6），暫時對所有文字 fallback 到規則型，
backend 標籤會誠實標示為 tbcl_rules_v1_fallback。
"""
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Literal, Optional

from app.chinese_readability.readability import ReadabilityAnalyzer, ReadabilityReport

# L1=1 ... L4=4 對照（與 readability.py 內定義一致）
LEVEL_ORDER = {"L1": 1, "L2": 2, "L3": 3, "L4": 4}

# 中文字數閾值
SHORT_THRESHOLD = 50      # < 50 字確定為短文字模式
LONG_THRESHOLD = 200      # >= 200 字確定為長文字模式

BackendType = Literal[
    "tbcl_rules_v1",            # 舊版短文字規則型（NAER 三等七級 lookup，已棄用）
    "tbcl_supervised_v2",       # 新版短文字 supervised classifier（RF + 跨主題詞頻 + mtms labels）
    "tbcl_rules_v1_fallback",   # 長文字但 SVM 未實作時的退路
    "svm_sung2014_v1",          # 長文字 paper 復刻 SVM
    "hybrid_v1",                # 中間區段兩者合併
]


@dataclass
class JargonInfo:
    """精簡版 jargon 資訊（從內部 JargonReport 對外輸出用）"""
    ratio: float
    abbreviations: list[str] = field(default_factory=list)
    alpha_codes: list[str] = field(default_factory=list)
    urls: list[str] = field(default_factory=list)
    emails: list[str] = field(default_factory=list)
    symbols: list[str] = field(default_factory=list)


@dataclass
class UnifiedReadability:
    """
    對外統一的中文可讀性結果。
    plugin 端永遠看到這個 schema，不用知道內部走哪條路。
    """
    required_level: str          # L1 / L2 / L3 / L4
    risk_score: float
    flag: bool
    target_level: str
    text_length: int             # 中文字數
    backend: BackendType
    hard_words: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    # jargon 偵測（任何後端都可填，兩層設計）
    jargon_detected: Optional[list[str]] = None     # 簡版：扁平 list 給下游快速判斷
    jargon_details: Optional[JargonInfo] = None     # 詳版：完整分類給 debug

    # 長文字 SVM 後端專屬（svm_sung2014_v1 完成後填入）
    svm_grade: Optional[int] = None                 # SVM 原始 grade 1-6
    confidence: Optional[float] = None              # SVM decision distance
    hard_sentences: Optional[list[dict]] = None

    def to_dict(self) -> dict:
        """plugin 用：序列化成 JSON-friendly dict"""
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None}


def _count_cjk(text: str) -> int:
    return sum(1 for c in text if "一" <= c <= "鿿")


def _convert_short_report(
    r: ReadabilityReport,
    text_length: int,
    backend: BackendType,
) -> UnifiedReadability:
    """把短文字 ReadabilityReport 轉成統一輸出。"""
    hard_words = [w for w, _, _ in r.over_target_words]
    jargon_detected = None
    jargon_details = None
    if r.jargon and r.jargon.total_items > 0:
        jargon_detected = (
            r.jargon.abbreviations
            + r.jargon.alpha_codes
            + r.jargon.urls
            + r.jargon.emails
            + r.jargon.symbols
        )
        jargon_details = JargonInfo(
            ratio=round(r.jargon.jargon_ratio, 3),
            abbreviations=r.jargon.abbreviations,
            alpha_codes=r.jargon.alpha_codes,
            urls=r.jargon.urls,
            emails=r.jargon.emails,
            symbols=r.jargon.symbols,
        )
    return UnifiedReadability(
        required_level=r.required_level,
        risk_score=r.risk_score,
        flag=r.flag,
        target_level=r.target_level,
        text_length=text_length,
        backend=backend,
        hard_words=hard_words,
        warnings=list(r.warnings),
        jargon_detected=jargon_detected,
        jargon_details=jargon_details,
    )


def _convert_v2_result(
    r_v2,
    cjk_count: int,
    target_level: str,
    jargon_weight: float,
) -> "UnifiedReadability":
    """把 ShortFormV2Result 轉成統一輸出。"""
    pred = r_v2.predicted_level
    flag = LEVEL_ORDER[pred] > LEVEL_ORDER[target_level]

    jargon_detected = None
    jargon_details = None
    if r_v2.jargon and r_v2.jargon.total_items > 0:
        jargon_detected = (
            r_v2.jargon.abbreviations
            + r_v2.jargon.alpha_codes
            + r_v2.jargon.urls
            + r_v2.jargon.emails
            + r_v2.jargon.symbols
        )
        jargon_details = JargonInfo(
            ratio=round(r_v2.jargon.jargon_ratio, 3),
            abbreviations=r_v2.jargon.abbreviations,
            alpha_codes=r_v2.jargon.alpha_codes,
            urls=r_v2.jargon.urls,
            emails=r_v2.jargon.emails,
            symbols=r_v2.jargon.symbols,
        )

    # risk_score 用 confidence + jargon_ratio 組合
    chinese_w = 1.0 - jargon_weight
    risk = chinese_w * (LEVEL_ORDER[pred] - 1) / 3 + jargon_weight * r_v2.jargon.jargon_ratio

    warnings = []
    if flag:
        warnings.append(
            f"v2 預估需 {pred} 程度（confidence {r_v2.confidence}），超出目標 {target_level}"
        )
    if r_v2.hard_words:
        warnings.append(f"含難詞 {len(r_v2.hard_words)} 個：{r_v2.hard_words[:5]}")
    if jargon_detected:
        warnings.append(f"含非中文片段 {len(jargon_detected)} 個（請評估讀者是否熟悉）")
    if cjk_count < 10:
        warnings.append("文字過短，結果僅供參考")

    return UnifiedReadability(
        required_level=pred,
        risk_score=round(min(risk, 1.0), 3),
        flag=flag,
        target_level=target_level,
        text_length=cjk_count,
        backend="tbcl_supervised_v2",
        hard_words=r_v2.hard_words,
        warnings=warnings,
        jargon_detected=jargon_detected,
        jargon_details=jargon_details,
        confidence=r_v2.confidence,
    )


class ChineseReadabilityPipeline:
    """
    對外統一入口。內部依文字長度自動分流。

    用法：
        pipeline = ChineseReadabilityPipeline(device=0)
        result = pipeline.analyze("啟用雙因素驗證", target_level="L2")
        print(result.required_level, result.risk_score, result.flag)
    """

    def __init__(self, db_path: Optional[Path] = None, device: int = -1):
        self._device = device
        self._db_path = db_path
        self._short_v1 = None       # 舊規則型（保留作 fallback）
        self._short_v2 = None       # 新 supervised classifier
        self._long = None

    def _get_short_v1(self) -> ReadabilityAnalyzer:
        """v1：NAER 三等七級 lookup（保留作 fallback / 取 jargon details）。"""
        if self._short_v1 is None:
            if self._db_path:
                self._short_v1 = ReadabilityAnalyzer(
                    db_path=self._db_path, device=self._device
                )
            else:
                self._short_v1 = ReadabilityAnalyzer(device=self._device)
        return self._short_v1

    def _get_short_v2(self):
        """v2：supervised classifier (RF + 跨主題詞頻 + mtms labels)。"""
        if self._short_v2 is None:
            from app.chinese_readability.short_form_v2_analyzer import ShortFormV2Analyzer
            self._short_v2 = ShortFormV2Analyzer(device=self._device)
        return self._short_v2

    def _get_long(self):
        """長文字 SVM analyzer（lazy load）。"""
        if self._long is None:
            from app.chinese_readability.long_form_analyzer import LongFormAnalyzer
            self._long = LongFormAnalyzer(device=self._device)
        return self._long

    def analyze(
        self,
        text: str,
        target_level: str = "L2",
        jargon_whitelist: Optional[set[str]] = None,
        jargon_weight: float = 0.2,
    ) -> UnifiedReadability:
        """
        Args:
            text: 待分析中文文字
            target_level: 目標讀者程度 L1-L4，預設 L2 (國中可讀)
            jargon_whitelist: 視為熟詞的英文集合，由 plugin 端依產品定義
            jargon_weight: jargon_ratio 在 risk_score 內的權重 (0-1)

        Returns:
            UnifiedReadability — 對外統一 schema
        """
        cjk_count = _count_cjk(text)

        if cjk_count < SHORT_THRESHOLD:
            # 短文字 → supervised v2（主路徑）
            try:
                v2 = self._get_short_v2()
                r_v2 = v2.analyze(text, jargon_whitelist=jargon_whitelist)
                return _convert_v2_result(
                    r_v2, cjk_count, target_level, jargon_weight
                )
            except FileNotFoundError:
                # v2 model 不存在 → fallback 到 v1
                short = self._get_short_v1()
                r = short.analyze(
                    text,
                    target_level=target_level,
                    jargon_whitelist=jargon_whitelist,
                    jargon_weight=jargon_weight,
                )
                unified = _convert_short_report(r, cjk_count, backend="tbcl_rules_v1")
                unified.warnings.insert(
                    0, "v2 supervised model 未找到，fallback 到 v1 規則型"
                )
                return unified

        # 長文字 → 走 SVM 主路徑
        # v1 規則型短文字也跑一次取 jargon details / warnings 補充
        short = self._get_short_v1()
        r_short = short.analyze(
            text,
            target_level=target_level,
            jargon_whitelist=jargon_whitelist,
            jargon_weight=jargon_weight,
        )
        try:
            long_analyzer = self._get_long()
            r_long = long_analyzer.analyze(text)
        except FileNotFoundError as e:
            # SVM model 沒生成 → 退回 fallback
            unified = _convert_short_report(
                r_short, cjk_count, backend="tbcl_rules_v1_fallback"
            )
            unified.warnings.insert(0, f"SVM model 未找到（{e}），fallback 到 TBCL 規則型")
            return unified

        # SVM 結果與短文字 jargon / hard_words 合併
        unified = _convert_short_report(
            r_short, cjk_count, backend="svm_sung2014_v1"
        )
        # 用 SVM 預測覆蓋 required_level / flag / svm_grade / confidence
        unified.required_level = r_long.predicted_level
        unified.flag = (
            LEVEL_ORDER[r_long.predicted_level] > LEVEL_ORDER[target_level]
        )
        unified.confidence = r_long.decision_distance
        unified.svm_grade = LEVEL_ORDER[r_long.predicted_level]
        # warnings 同步：移除短文字模式留下的「預估需 X」、改 SVM 版
        unified.warnings = [
            w for w in unified.warnings
            if not w.startswith("預估需")
        ]
        if unified.flag:
            unified.warnings.insert(
                0,
                f"SVM 預估需 {r_long.predicted_level} 程度（信心距離 "
                f"{r_long.decision_distance}），超出目標 {target_level}"
            )
        return unified


def pretty_print(result: UnifiedReadability):
    """除錯用：列印 UnifiedReadability 結果。"""
    print(f"\n原文長度: {result.text_length} 中文字")
    print(f"backend: {result.backend}")
    print(f"target: {result.target_level}  /  required: {result.required_level}"
          f"  /  flag: {result.flag}  /  risk: {result.risk_score}")
    if result.hard_words:
        print(f"  hard words: {result.hard_words}")
    if result.jargon_details:
        j = result.jargon_details
        bits = []
        if j.abbreviations: bits.append(f"英文: {j.abbreviations}")
        if j.alpha_codes:   bits.append(f"代碼: {j.alpha_codes}")
        if j.urls:          bits.append(f"URL: {j.urls}")
        if j.emails:        bits.append(f"Email: {j.emails}")
        if j.symbols:       bits.append(f"符號: {j.symbols}")
        print(f"  jargon (ratio={j.ratio}): " + "; ".join(bits))
    if result.svm_grade is not None:
        print(f"  SVM grade: {result.svm_grade}  confidence: {result.confidence}")
    for w in result.warnings:
        print(f"  ⚠ {w}")
