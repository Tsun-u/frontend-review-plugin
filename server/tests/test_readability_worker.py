from app.workers.readability_worker import run_readability


def test_english_text_returns_fk():
    r = run_readability(
        "The quick brown fox jumps over the lazy dog. This is a simple sentence.",
        language="en",
    )
    assert r.english is not None
    assert r.english.flesch_kincaid_grade > 0
    assert r.chinese is None


def test_chinese_short_text_returns_rules():
    r = run_readability("請輸入密碼登入系統", language="zh-TW")
    assert r.chinese is not None
    assert r.chinese.backend == "tbcl_supervised_v2"
    assert r.chinese.required_level in ("L1", "L2", "L3", "L4")
    assert r.chinese.text_length > 0
    assert r.english is None


def test_chinese_long_text_returns_svm():
    long_text = (
        "根據調查結果顯示，超過七成的受訪者認為政府應該加強對於食品安全的監管力度。"
        "這項研究被認為對於了解氣候變遷的影響具有重要的參考價值。"
        "在全球化的脈絡下，如何在追求經濟成長的同時維護本土文化的多元性，"
        "已成為各國政策制定者必須面對的核心議題。"
    )
    r = run_readability(long_text, language="zh-TW")
    assert r.chinese is not None
    assert r.chinese.backend in ("svm_sung2014_v1", "tbcl_rules_v1_fallback")
    assert r.chinese.text_length >= 50
    assert r.english is None


def test_empty_text_returns_empty():
    r = run_readability("", language="en")
    assert r.english is None
    assert r.chinese is None


def test_unknown_language_skipped():
    r = run_readability("Hello world", language="ja")
    assert r.english is None
    assert r.chinese is None
