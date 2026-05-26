import textstat

from app.chinese_readability.pipeline import ChineseReadabilityPipeline
from app.models import (
    ChineseReadability,
    EnglishReadability,
    ReadabilityWorkerOutput,
)

_zh_pipeline: ChineseReadabilityPipeline | None = None


def _get_zh_pipeline() -> ChineseReadabilityPipeline:
    global _zh_pipeline
    if _zh_pipeline is None:
        _zh_pipeline = ChineseReadabilityPipeline(device=-1)
    return _zh_pipeline


def run_readability(text: str, language: str, chinese_target_level: str = "L2") -> ReadabilityWorkerOutput:
    out = ReadabilityWorkerOutput()
    text = text.strip()
    if not text:
        return out

    if language.startswith("en"):
        out.english = EnglishReadability(
            flesch_kincaid_grade=textstat.flesch_kincaid_grade(text),
            flesch_reading_ease=textstat.flesch_reading_ease(text),
            smog_index=textstat.smog_index(text),
            automated_readability_index=textstat.automated_readability_index(text),
        )
    elif language.startswith("zh"):
        pipeline = _get_zh_pipeline()
        result = pipeline.analyze(text, target_level=chinese_target_level)
        out.chinese = ChineseReadability(**result.to_dict())
    return out
