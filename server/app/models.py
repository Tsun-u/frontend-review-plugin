from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

Viewport = Literal["desktop", "tablet", "mobile"]


class ReviewOptions(BaseModel):
    skip_deepgaze: bool = False
    skip_wcag_extended: bool = False
    use_psi_api: bool = True
    chinese_target_level: Literal["L1", "L2", "L3", "L4"] = "L2"


class AuthCookie(BaseModel):
    name: str
    value: str
    domain: str
    path: str = "/"
    httpOnly: bool = False
    secure: bool = False
    sameSite: Literal["Strict", "Lax", "None"] = "Lax"


class ReviewAuth(BaseModel):
    cookies: list[AuthCookie] | None = None
    storage_state: dict | None = None
    extra_headers: dict[str, str] | None = None


class ReviewRequest(BaseModel):
    url: HttpUrl
    viewports: list[Viewport] = Field(default_factory=lambda: ["desktop", "tablet", "mobile"])
    options: ReviewOptions = Field(default_factory=ReviewOptions)
    auth: ReviewAuth | None = None


class ErrorResponse(BaseModel):
    error_code: Literal["BAD_URL", "AUTH_FAILED", "TIMEOUT", "WORKER_FAILED", "INTERNAL"]
    message: str
    details: dict | None = None


# --- Playwright worker output schemas ---


class LighthouseScore(BaseModel):
    performance: int
    accessibility: int
    best_practices: int
    seo: int


class AxeViolation(BaseModel):
    rule: str
    node: str
    impact: Literal["minor", "moderate", "serious", "critical"]


class WcagViolation(BaseModel):
    rule: str
    element_selector: str
    severity: Literal["critical", "major", "minor"]
    bbox: list[int]
    model_config = {"extra": "allow"}


class WcagExtended(BaseModel):
    summary: dict
    violations: list[WcagViolation]


class ExtractedText(BaseModel):
    by_section: dict[str, str]
    language_detected: str


class TextStylingElement(BaseModel):
    selector: str
    text: str
    text_decoration_line: str
    font_weight: str
    font_style: str
    text_transform: str
    letter_spacing: str
    is_link: bool


class TextStyling(BaseModel):
    summary: dict
    elements: list[TextStylingElement]


class PlaywrightWorkerOutput(BaseModel):
    lighthouse: LighthouseScore
    axe_violations: list[AxeViolation]
    wcag_extended: WcagExtended
    screenshots: dict[str, str]
    dom_html: str
    extracted_text: ExtractedText
    ctas_layout: dict[str, list[dict]] = Field(default_factory=dict)
    text_styling: TextStyling | None = None
    warnings: list[str] = Field(default_factory=list)


# --- Readability worker output schemas ---


class EnglishReadability(BaseModel):
    flesch_kincaid_grade: float
    flesch_reading_ease: float
    smog_index: float
    automated_readability_index: float


class ChineseReadability(BaseModel):
    """Unified Chinese readability output from hybrid pipeline."""
    required_level: str
    risk_score: float
    flag: bool
    target_level: str
    text_length: int
    backend: str
    hard_words: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    jargon_detected: list[str] | None = None
    jargon_details: dict | None = None
    svm_grade: int | None = None
    confidence: float | None = None
    hard_sentences: list[dict] | None = None
    model_config = {"extra": "allow"}


class ReadabilityWorkerOutput(BaseModel):
    english: EnglishReadability | None = None
    chinese: ChineseReadability | None = None


# --- DeepGaze worker output schemas ---


class FixationPoint(BaseModel):
    x: int
    y: int
    weight: float


class CtaDetection(BaseModel):
    selector: str
    bbox: list[int]
    in_top_attention: bool
    rank: int


class DeepgazeWorkerOutput(BaseModel):
    saliency_heatmap: str
    saliency_overlay: str
    top_fixation_points: list[FixationPoint]
    ctas_detected: list[CtaDetection]


# --- Source-scan schemas ---

ChineseLevel = Literal["L1", "L2", "L3", "L4"]


class ScanString(BaseModel):
    text: str
    source_file: str
    line: int | None = None


class SourceScanRequest(BaseModel):
    strings: list[ScanString]
    expected_level: ChineseLevel = "L2"
    jargon_whitelist: list[str] | None = None


class StringAnalysis(BaseModel):
    text: str
    source_file: str
    line: int | None = None
    required_level: str
    risk_score: float
    flag: bool
    backend: str
    hard_words: list[str] = Field(default_factory=list)
    jargon_detected: list[str] | None = None
    warnings: list[str] = Field(default_factory=list)


class SourceFileResult(BaseModel):
    source_file: str
    string_count: int
    flagged_count: int
    max_required_level: str
    strings: list[StringAnalysis] = Field(default_factory=list)


class SourceScanProject(BaseModel):
    expected_level: str
    summary: dict
    files: list[SourceFileResult] = Field(default_factory=list)
    model_config = {"extra": "allow"}
