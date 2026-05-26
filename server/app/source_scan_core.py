"""
Source-scan 彙整核心 — server 端。

對外契約（在 switchboard 與 tools/dev 敲定）：
  analyze_extracted_strings(strings, expected_level, jargon_whitelist) -> dict

stateless：字串進 → 逐筆 pipeline.analyze() → group by source_file → 彙整 summary
→ 回傳對齊 SourceScanProject schema 的 dict。不寫 DB、不存報告（隱私）。

pipeline 用 module-level singleton（跟 readability_worker 一致、device=-1 CPU、
避免每次 request 重載 CKIP / model）。
"""
from collections import Counter
from typing import Optional

LEVEL_ORDER = {"L1": 1, "L2": 2, "L3": 3, "L4": 4}

_pipeline = None


def _get_pipeline():
    """Lazy-load 的 module-level singleton ChineseReadabilityPipeline。"""
    global _pipeline
    if _pipeline is None:
        from app.chinese_readability.pipeline import ChineseReadabilityPipeline
        _pipeline = ChineseReadabilityPipeline(device=-1)
    return _pipeline


def _max_level(levels: list[str]) -> str:
    """回傳一組 level 中最難的（L4 > L3 > L2 > L1）。"""
    return max(levels, key=lambda lv: LEVEL_ORDER.get(lv, 0))


def analyze_extracted_strings(
    strings: list[dict],
    expected_level: str = "L2",
    jargon_whitelist: Optional[set[str]] = None,
) -> dict:
    """
    逐筆分析 client 上傳的字串、彙整成 SourceScanProject dict。

    Args:
        strings: [{text, source_file, line}]，line 可能為 None
        expected_level: 目標讀者程度 L1-L4（flag = required_level > expected_level）
        jargon_whitelist: 視為熟詞的英文集合（plugin / 產品自訂）

    Returns:
        dict，對齊 SourceScanProject schema：
          {
            expected_level,
            summary: {total_files, total_strings, flagged_strings, flag_rate,
                      level_distribution{}, backend_distribution{}},
            files: [{source_file, string_count, flagged_count,
                     max_required_level, strings: [StringAnalysis...]}]
          }
    """
    if expected_level not in LEVEL_ORDER:
        raise ValueError(f"expected_level must be L1-L4, got {expected_level!r}")

    pipeline = _get_pipeline()

    by_file: dict[str, list[dict]] = {}
    level_dist: Counter = Counter()
    backend_dist: Counter = Counter()
    flagged_total = 0

    for s in strings:
        text = (s.get("text") or "").strip()
        if not text:
            continue
        source_file = s.get("source_file") or "(unknown)"
        line = s.get("line")

        result = pipeline.analyze(
            text,
            target_level=expected_level,
            jargon_whitelist=jargon_whitelist,
        )
        d = result.to_dict()

        analysis = {
            "text": text,
            "source_file": source_file,
            "line": line,
            "required_level": d["required_level"],
            "risk_score": d["risk_score"],
            "flag": d["flag"],
            "backend": d["backend"],
            "hard_words": d.get("hard_words", []),
            "jargon_detected": d.get("jargon_detected"),
            "warnings": d.get("warnings", []),
        }

        by_file.setdefault(source_file, []).append(analysis)
        level_dist[analysis["required_level"]] += 1
        backend_dist[analysis["backend"]] += 1
        if analysis["flag"]:
            flagged_total += 1

    # 彙整 per-file
    files = []
    for source_file, analyses in by_file.items():
        flagged = sum(1 for a in analyses if a["flag"])
        max_lvl = _max_level([a["required_level"] for a in analyses])
        files.append({
            "source_file": source_file,
            "string_count": len(analyses),
            "flagged_count": flagged,
            "max_required_level": max_lvl,
            "strings": analyses,
        })
    # 按 flag 率高的檔排前面（方便使用者先看問題最多的檔）
    files.sort(key=lambda f: (-f["flagged_count"], -f["string_count"]))

    total_strings = sum(len(a) for a in by_file.values())
    summary = {
        "total_files": len(by_file),
        "total_strings": total_strings,
        "flagged_strings": flagged_total,
        "flag_rate": round(flagged_total / total_strings, 3) if total_strings else 0.0,
        "level_distribution": dict(sorted(level_dist.items())),
        "backend_distribution": dict(backend_dist),
    }

    return {
        "expected_level": expected_level,
        "summary": summary,
        "files": files,
    }
