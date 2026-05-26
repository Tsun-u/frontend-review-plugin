"""
UI jargon detector — MVP-S2

偵測 UI 文字中的英文縮寫、混合代碼、URL、特殊符號。
這些對非技術讀者是常見閱讀障礙，但「友善 vs 陌生」高度依賴
目標讀者群，所以由呼叫端透過 whitelist 自訂。
"""
import re
from dataclasses import dataclass, field

URL_RE = re.compile(
    r"https?://\S+|"
    r"\bwww\.\S+|"
    r"\b[\w-]+\.(?:com|net|org|edu|gov|tw|io|app|co)(?:/\S*)?\b",
    re.IGNORECASE,
)
EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w.-]+\.\w+\b")
ALPHA_NUM_RE = re.compile(
    r"\b(?:[A-Za-z]+\d+[A-Za-z\d]*|\d+[A-Za-z]+[A-Za-z\d]*)\b"
)
ALPHA_RE = re.compile(r"\b[A-Za-z]+(?:[-_][A-Za-z]+)*\b")
SYMBOL_RE = re.compile(r"[#@&%*+=<>~^|]+|[→←↑↓⇒⇐—…•※★☆◎○●]")


@dataclass
class JargonReport:
    abbreviations: list[str] = field(default_factory=list)
    alpha_codes: list[str] = field(default_factory=list)
    urls: list[str] = field(default_factory=list)
    emails: list[str] = field(default_factory=list)
    symbols: list[str] = field(default_factory=list)
    whitelisted: list[str] = field(default_factory=list)
    jargon_char_count: int = 0
    total_char_count: int = 0
    jargon_ratio: float = 0.0

    @property
    def total_items(self) -> int:
        return (
            len(self.abbreviations)
            + len(self.alpha_codes)
            + len(self.urls)
            + len(self.emails)
            + len(self.symbols)
        )


def detect_jargon(text: str, whitelist: set[str] | None = None) -> JargonReport:
    """
    偵測 UI 文字中的「非中文」片段並分類。

    Args:
        text: 待分析文字
        whitelist: 視為「友善熟詞」的字串集合（不區分大小寫）
                  例如 {"OK", "App", "Email"} 對一般使用者算熟詞

    Returns:
        JargonReport
    """
    if whitelist is None:
        whitelist = set()
    wl_lower = {w.lower() for w in whitelist}

    report = JargonReport()
    work = text

    # URL 先抓走（避免被當作 alpha）
    for m in URL_RE.findall(text):
        if m.lower() in wl_lower:
            report.whitelisted.append(m)
        else:
            report.urls.append(m)
    work = URL_RE.sub(" ", work)

    # Email
    for m in EMAIL_RE.findall(work):
        if m.lower() in wl_lower:
            report.whitelisted.append(m)
        else:
            report.emails.append(m)
    work = EMAIL_RE.sub(" ", work)

    # 數字+字母代碼（例如 "2FA"、"H.264"、"3DS"）
    for m in ALPHA_NUM_RE.findall(work):
        if m.lower() in wl_lower:
            report.whitelisted.append(m)
        else:
            report.alpha_codes.append(m)
    work = ALPHA_NUM_RE.sub(" ", work)

    # 純英文片段
    for m in ALPHA_RE.findall(work):
        if m.lower() in wl_lower:
            report.whitelisted.append(m)
        else:
            report.abbreviations.append(m)

    # 特殊符號
    for m in SYMBOL_RE.findall(text):
        report.symbols.append(m)

    # 統計
    jargon_items = (
        report.abbreviations
        + report.alpha_codes
        + report.urls
        + report.emails
        + report.symbols
    )
    report.jargon_char_count = sum(len(x) for x in jargon_items)
    report.total_char_count = sum(1 for c in text if not c.isspace())
    report.jargon_ratio = (
        report.jargon_char_count / report.total_char_count
        if report.total_char_count
        else 0.0
    )
    return report


def pretty_print(report: JargonReport):
    """Debug 用：印出 jargon report。"""
    print(f"  jargon: {report.total_items} items "
          f"({report.jargon_char_count}/{report.total_char_count} chars, "
          f"ratio={report.jargon_ratio:.2f})")
    if report.abbreviations:
        print(f"    縮寫/英文: {report.abbreviations}")
    if report.alpha_codes:
        print(f"    字母數字代碼: {report.alpha_codes}")
    if report.urls:
        print(f"    URL: {report.urls}")
    if report.emails:
        print(f"    Email: {report.emails}")
    if report.symbols:
        print(f"    符號: {report.symbols}")
    if report.whitelisted:
        print(f"    [白名單通過]: {report.whitelisted}")
